# USAJobs 2210 Data Explorer

Pull 2210 job data from USAJobs API and explore it in a web interface.

## Usage

### Install Requirements

```
pip install -r requirements.txt
```

### Data Collection

```
python usajobs_data_puller.py --start-date 2023-01-01 --end-date 2023-01-31 --output data.json
```

### Configuration

Edit `config.js` to customize displayed fields, filters, and appearance.

### View Site Locally

```
python3 -m http.server 8000  
```

## Term and Temp Hiring Outcomes

Check whether term and temp announcements are less likely to end in a selection than permanent ones for the same kind of job, using GSA's [Federal Hiring Assessments and Selection Outcome Dataset](https://catalog.data.gov/dataset/federal-hiring-assessments-and-selection-outcome-dataset) (FY2020 through Dec 2023). Downloads the files into `gsa_data/` the first time.

```
jupyter notebook hiring_outcomes_analysis.ipynb
```

Note: GSA dropped temporary-only announcements from this dataset, so "temp" here means announcements listing Temporary as one of several appointment types.
