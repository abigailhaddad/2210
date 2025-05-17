#!/usr/bin/env python3
"""
USAJobs Historic 2210 Data Puller

Pulls IT Management (2210) jobs from the USAJobs Historical API,
scrapes each job's page, extracts Duties and Requirements sections,
and saves the structured data to a JSON file.

Usage:
    python usajobs_historic_2210.py --start-date 2023-01-01 --end-date 2023-01-15 --output data.json
"""

import argparse
import json
import time
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

API_URL = "https://data.usajobs.gov/api/historicjoa"


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch USAJobs historical 2210 jobs")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", default="data.json", help="Output JSON file path (default: data.json)")
    return parser.parse_args()


def get_job_data_page(params: Optional[Dict] = None, next_url: Optional[str] = None) -> Dict:
    """Fetch a page of job data from the API."""
    if next_url:
        response = requests.get(next_url)
    else:
        response = requests.get(API_URL, params=params)

    print(f"Requesting: {response.url} -> {response.status_code}")
    response.raise_for_status()
    return response.json()


def scrape_job_sections(control_number: int) -> Dict[str, Optional[str]]:
    """Scrape the job page and extract Duties and Requirements sections."""
    url = f"https://www.usajobs.gov/job/{control_number}"
    sections = {"jobDutiesText": None, "jobRequirementsText": None}
    try:
        print(f"Scraping: {url}")
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for section_name, label in [("jobDutiesText", "duties"), ("jobRequirementsText", "requirements")]:
            header = soup.find(lambda tag: tag.name in ["h2", "h3"] and label in tag.get_text(strip=True).lower())
            if header:
                content = header.find_next_sibling()
                if content:
                    sections[section_name] = content.get_text(separator="\n", strip=True)

        time.sleep(0.5)  # Polite delay
        return sections

    except requests.RequestException as e:
        print(f"Failed to scrape {url}: {e}")
        return sections


def fetch_jobs(start_date: str, end_date: str) -> List[Dict]:
    """Fetch job data from the API and scrape Duties + Requirements."""
    all_jobs = []
    params = {
        "PositionSeries": "2210",
        "StartPositionOpenDate": start_date,
        "EndPositionOpenDate": end_date
    }

    next_url = None
    while True:
        try:
            data = get_job_data_page(params=params, next_url=next_url)
        except Exception as e:
            print(f"Error fetching job data: {e}")
            break

        jobs = data.get("data", [])
        for job in jobs:
            control_number = job.get("usajobsControlNumber")
            if control_number:
                sections = scrape_job_sections(control_number)
                job.update(sections)
            all_jobs.append(job)

        next_path = data.get("paging", {}).get("next")
        if next_path:
            next_url = f"https://data.usajobs.gov{next_path}"
            params = None  # Only needed for the first request
        else:
            break

    return all_jobs


def flatten_job(job: dict) -> dict:
    """Flatten nested job structure for easier output."""
    flat = {
        "controlNumber": job.get("usajobsControlNumber"),
        "agencyName": job.get("hiringAgencyName"),
        "departmentName": job.get("hiringDepartmentName"),
        "positionTitle": job.get("positionTitle"),
        "openDate": job.get("positionOpenDate"),
        "closeDate": job.get("positionCloseDate"),
        "announcementNumber": job.get("announcementNumber"),
        "appointmentType": job.get("appointmentType"),
        "workSchedule": job.get("workSchedule"),
        "payScale": job.get("payScale"),
        "salaryRange": f"{job.get('minimumSalary')} - {job.get('maximumSalary')}",
        "promotionPotential": job.get("promotionPotential"),
        "supervisoryStatus": job.get("supervisoryStatus"),
        "teleworkEligible": job.get("teleworkEligible"),
        "securityClearance": job.get("securityClearance"),
        "positionStatus": job.get("positionOpeningStatus"),
        "totalOpenings": job.get("totalOpenings"),
        "serviceType": job.get("serviceType"),
        "jobDutiesText": job.get("jobDutiesText"),
        "jobRequirementsText": job.get("jobRequirementsText")
    }

    # Join hiring paths
    hiring_paths = [p.get("hiringPath") for p in job.get("HiringPaths", [])]
    flat["hiringPaths"] = ", ".join(hiring_paths)

    # Join job series
    job_series = [c.get("series") for c in job.get("JobCategories", [])]
    flat["jobSeries"] = ", ".join(job_series)

    # Join location strings
    locations = []
    for loc in job.get("PositionLocations", []):
        parts = [loc.get("positionLocationCity"), loc.get("positionLocationState"), loc.get("positionLocationCountry")]
        locations.append(", ".join(filter(None, parts)))
    flat["locations"] = " | ".join(locations)

    return flat


def main():
    args = parse_args()
    raw_jobs = fetch_jobs(args.start_date, args.end_date)
    print(f"\nFetched {len(raw_jobs)} job records")

    if raw_jobs:
        print("\nSample full job entry:")
        print(json.dumps(raw_jobs[0], indent=2))

    flattened_jobs = [flatten_job(job) for job in raw_jobs]

    with open(args.output, "w") as f:
        json.dump(flattened_jobs, f, indent=2)
    print(f"\nSaved flattened job data to: {args.output}")


if __name__ == "__main__":
    main()
