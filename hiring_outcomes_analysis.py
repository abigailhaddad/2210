#!/usr/bin/env python3
"""
Are term and temp job announcements less likely to end in a selection,
holding job type fixed?

Uses GSA's Federal Hiring Assessments and Selection Outcome Dataset
(https://catalog.data.gov/dataset/federal-hiring-assessments-and-selection-outcome-dataset).
Downloads the files into gsa_data/ if they aren't there yet.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf
import requests

BASE = "https://inventory.data.gov/dataset/4189591b-d78e-4ad3-9d75-582175ad0b3f/resource"
FILES = [
    f"{BASE}/ef9d8bb1-2b4f-4618-98d1-bf96deaa6503/download/hiring_selections_and_outcomes_public_data_set_as_of_dec_31_2023_fy2020_fy2021.xlsx",
    f"{BASE}/dc0a8624-0f45-4d39-97d7-2a6694810d19/download/hiring_selections_and_outcomes_public_data_set_as_of_dec_31_2023_fy2022_fy2023.xlsx",
    f"{BASE}/6de5e82a-3e16-491c-baf9-204c3b2f4767/download/hiring_selections_and_outcomes_public_data_set_as_of_dec_31_2023_fy2024.xlsx",
]
EXPECTED_ROWS = 1161779

# GSA counts an announcement toward selection outcomes only after it has been
# open for four months. The data runs through Dec 31, 2023.
LAST_MATURE_OPEN_DATE = "2023-08-31"

GROUPS = ["Permanent", "Term", "Multiple incl. Temporary"]

SPECS = {
    "raw": "{y} ~ term + temp_mix",
    "series x grade FE": "{y} ~ term + temp_mix | series_grade",
    "+ bureau, FY, ann. type FE": "{y} ~ term + temp_mix | series_grade + ab + fy + anntype",
    "series x grade x bureau FE + FY + ann. type": "{y} ~ term + temp_mix | sg_ab + fy + anntype",
    "previous + log(apps+1)": "{y} ~ term + temp_mix + np.log1p(apps) | sg_ab + fy + anntype",
}


def download(data_dir):
    """Download the GSA xlsx files that aren't already in data_dir."""
    data_dir.mkdir(exist_ok=True)
    for url in FILES:
        path = data_dir / url.rsplit("/", 1)[1]
        if path.exists():
            continue
        print(f"Downloading {path.name}")
        with requests.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)


def load(data_dir):
    """Read and stack the yearly files."""
    frames = []
    for url in FILES:
        path = data_dir / url.rsplit("/", 1)[1]
        sheets = pd.read_excel(path, sheet_name=None, engine="calamine", dtype=str)
        if len(sheets) != 1:
            raise ValueError(f"Expected one sheet in {path.name}, found {list(sheets)}")
        frames.append(next(iter(sheets.values())))
    df = pd.concat(frames, ignore_index=True)
    if len(df) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} rows, got {len(df)}")
    return df


def appointment_group(appt_type, appt_list):
    """Collapse Appointment_Type / Appointment_Type_List into analysis groups."""
    if appt_type == "Permanent":
        return "Permanent"
    if isinstance(appt_type, str) and appt_type.startswith("Term"):
        return "Term"
    if appt_type == "Multiple Appointment Types":
        parts = [p.strip() for p in str(appt_list).split(",")]
        if "Temporary" in parts:
            return "Multiple incl. Temporary"
        if "Term" in parts:
            return "Multiple incl. Term (no temp)"
        return "Multiple other"
    return "Other (intermittent/seasonal/etc.)"


def prepare(df):
    """Drop immature announcements and build outcome, group, and fixed-effect columns."""
    df = df.copy()
    df["open"] = pd.to_datetime(df.Announcement_Open_Date)
    df = df[df.open <= LAST_MATURE_OPEN_DATE].copy()
    df["appt"] = [appointment_group(t, l) for t, l in zip(df.Appointment_Type, df.Appointment_Type_List)]
    df["sel"] = (df.Selection_Made_off_this_Job_Announcement == "Yes").astype(int)
    df["sel_any"] = ((df.sel == 1) | (df.Selection_Made_through_Separate_Announcement == "Yes")).astype(int)
    df["series_grade"] = df.Job_Series_Number.str.strip("'") + "|" + df.Pay_Plan + "-" + df.Grade.str.strip("'")
    df["ab"] = df.Agency + "|" + df.Bureau.fillna("(none)")
    df["sg_ab"] = df.series_grade + "|" + df.ab
    df["fy"] = df.Announcement_Open_Date_FY
    df["anntype"] = df.Announcement_Type.str.upper().str.strip()
    df["apps"] = pd.to_numeric(df.Total_Applications, errors="coerce")
    df["term"] = (df.appt == "Term").astype(int)
    df["temp_mix"] = (df.appt == "Multiple incl. Temporary").astype(int)
    return df


def raw_rates(df):
    """Selection rates by appointment group."""
    return (
        df.groupby("appt")
        .agg(n=("sel", "size"), sel_rate=("sel", "mean"), sel_any_rate=("sel_any", "mean"), median_apps=("apps", "median"))
        .sort_values("n", ascending=False)
    )


def regressions(df):
    """Linear probability models of selection on term / temp, clustered by bureau."""
    m = df[df.appt.isin(GROUPS)]
    rows = []
    # sel_any uses Selection_Made_through_Separate_Announcement, which only USA Staffing reports
    for y, sample in [("sel", m), ("sel_any", m[m.Source == "USA_Staffing"])]:
        for name, f in SPECS.items():
            fit = pf.feols(f.format(y=y), data=sample, vcov={"CRV1": "ab"})
            t = fit.tidy()
            for v in ["term", "temp_mix"]:
                rows.append(dict(outcome=y, spec=name, var=v, coef=t.loc[v, "Estimate"], se=t.loc[v, "Std. Error"], n=fit._N))
    res = pd.DataFrame(rows)
    res["ci_lo"] = res.coef - 1.96 * res.se
    res["ci_hi"] = res.coef + 1.96 * res.se
    return res


def matched_cells(df):
    """Term-weighted term-minus-permanent gap within series x grade x bureau x FY cells that have both."""
    c = df[df.appt.isin(["Permanent", "Term"])]
    cell = c.groupby(["sg_ab", "fy", "appt"]).sel.agg(["mean", "size"]).unstack("appt").dropna()
    w = cell[("size", "Term")]
    return {
        "cells": len(cell),
        "term_listings_matched": int(w.sum()),
        "term_listings_total": int((c.appt == "Term").sum()),
        "perm_rate": float(np.average(cell[("mean", "Permanent")], weights=w)),
        "term_rate": float(np.average(cell[("mean", "Term")], weights=w)),
    }


def by_agency(df, top_n=8):
    """Term gap within each of the agencies posting the most term listings."""
    m = df[df.appt.isin(GROUPS)]
    rows = []
    for agency, n_term in m[m.term == 1].Agency.value_counts().head(top_n).items():
        sub = m[m.Agency == agency]
        t = pf.feols("sel ~ term + temp_mix | sg_ab + fy + anntype", data=sub, vcov={"CRV1": "ab"}).tidy()
        rows.append(dict(agency=agency, term_listings=n_term, coef=t.loc["term", "Estimate"], se=t.loc["term", "Std. Error"]))
    return pd.DataFrame(rows)


def is_stem(series):
    """Science/tech series: 04xx bio sciences, 08xx engineering, 13xx physical sciences, 15xx math/stats/CS, 2210 IT."""
    s = series.str.strip("'")
    return s.str[:2].isin(["04", "08", "13", "15"]) | (s == "2210")


def applicant_share(df, agency="Department of Defense"):
    """Term gap at one agency with and without controlling for log applications, all jobs vs STEM."""
    m = df[df.appt.isin(GROUPS) & (df.Agency == agency)]
    rows = []
    for label, sub in [("all jobs", m), ("STEM", m[is_stem(m.Job_Series_Number)])]:
        base = pf.feols("sel ~ term + temp_mix | sg_ab + fy + anntype", data=sub, vcov={"CRV1": "ab"}).tidy()
        ctrl = pf.feols("sel ~ term + temp_mix + np.log1p(apps) | sg_ab + fy + anntype", data=sub, vcov={"CRV1": "ab"}).tidy()
        terms = sub[sub.term == 1]
        perms = sub[(sub.term == 0) & (sub.temp_mix == 0)]
        rows.append(dict(
            jobs=label,
            term_listings=len(terms),
            median_apps_term=terms.apps.median(),
            median_apps_perm=perms.apps.median(),
            gap=base.loc["term", "Estimate"],
            gap_se=base.loc["term", "Std. Error"],
            gap_ctrl_apps=ctrl.loc["term", "Estimate"],
            gap_ctrl_apps_se=ctrl.loc["term", "Std. Error"],
        ))
    res = pd.DataFrame(rows)
    res["share_explained_by_apps"] = 1 - res.gap_ctrl_apps / res.gap
    return res


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", default="gsa_data", help="Where to store the GSA files")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    download(data_dir)
    df = prepare(load(data_dir))
    print(f"Announcements opened by {LAST_MATURE_OPEN_DATE}: {len(df)}\n")

    pd.set_option("display.width", 200)
    print(raw_rates(df).round(3).to_string(), "\n")
    print(regressions(df).round(4).to_string(), "\n")

    mc = matched_cells(df)
    print(
        f"Matched cells: {mc['cells']} ({mc['term_listings_matched']} of {mc['term_listings_total']} term listings). "
        f"Permanent {mc['perm_rate']:.3f} vs term {mc['term_rate']:.3f} (diff {mc['term_rate'] - mc['perm_rate']:+.3f})\n"
    )
    print(by_agency(df).round(4).to_string(), "\n")
    print("Department of Defense:")
    print(applicant_share(df).round(4).to_string())


if __name__ == "__main__":
    main()
