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