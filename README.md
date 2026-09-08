# Dubai Smart Parking ETL Pipeline

**Course:** Data Engineering  
**Author:** · O'kah Ahone Ebwekoh

---

## Project Overview

This project builds an ETL pipeline that integrates two fragmented urban mobility datasets into a unified PostgreSQL data warehouse, enabling real-time parking occupancy analysis across Dubai zones.

**Problem:** Dubai's parking data is split across static infrastructure records (RTA) and dynamic IoT sensor streams (Kaggle). No single source supports real-time capacity planning.

**Solution:** A Python-based ETL pipeline that cleans, joins, and loads both sources into a Star Schema, visualised via a Streamlit dashboard.

---

## Folder Structure

```text
dubai_smart_parking_etl/
├── dashboards/
│   └── dashboard.py
├── data/
│   ├── raw/                 # Local source datasets — not tracked
│   └── processed/           # Local ETL outputs — not tracked
├── diagrams/
│   ├── E-R diagram.png
│   └── architecture diagram.png
├── documentation/
│   └── README.md
├── notebooks/
│   └── main_pipeline.ipynb
├── references/
│   └── citation_list.bib
├── screenshots/
│   └── screenshot 1.png
├── scripts/
│   ├── db_schema.sql
│   ├── etl_pipeline.py
│   └── export_processed.py
├── requirements.txt
└── README.md
```

---

## Datasets

The pipeline integrates two datasets:

| Dataset | Source | Rows | Description |
|---|---|---:|---|
| Dubai Pulse / RTA | [Dubai Open Data](https://data.dubai.gov.ae) | 84 | Zone-level parking capacity for Dubai communities |
| IIoT Smart Parking | [Kaggle](https://www.kaggle.com/datasets/datasetengineer/smart-parking-management-dataset) | 1,000 | Sensor-based parking occupancy events with timestamps |

The source datasets are not included in this repository. Download them from their respective sources and place them in the local `data/raw/` directory before running the ETL pipeline.

---

## Setup Instructions

### 1. Prerequisites

- Python 3.9+
- PostgreSQL 17 installed and running on port 5432

### 2. Install dependencies

```bash
pip install pandas sqlalchemy psycopg2-binary streamlit plotly
```

### 3. Prepare the data

Download the two source datasets from the links above and place them in:

```text
data/raw/
├── IIoT_Smart_Parking_Management.csv
└── number_of_parking_spaces_per_zone_2026-05-21_02-02-07_1.csv
```

### 4. Configure database credentials

Configure your PostgreSQL connection using your local environment variables.
The required variables are : 
DB_HOST
DB_PORT
DB_NAME
DB_USER
DB_PASSWORD

### 5. Run the ETL pipeline

```bash
python scripts/etl_pipeline.py
```

Expected output:
```
Extracting data...
  Kaggle rows: 1000
  RTA rows: 84
Transforming RTA data...
  Clean RTA zones: 83
Transforming Kaggle data...
Running quality checks...
  Null zone_ids: 0 (should be 0)
  Duplicate spot+timestamp rows: 0 (should be 0)
  Invalid occupancy status rows: 0 (should be 0)
Connecting to PostgreSQL...
  Created database 'smart_parking'
  Tables created
  Loaded 83 rows into dim_zones
  Loaded 1000 rows into fact_occupancy
ETL pipeline complete!
```

### 6. Launch the dashboard

```bash
streamlit run dashboards/dashboard.py
```

The dashboard opens at `http://localhost:8501`

---

## Tools & Technologies

| Category | Tool |
|---|---|
| Data processing | Python, Pandas, NumPy |
| Database | PostgreSQL 17 |
| Pipeline scripting | SQLAlchemy, Psycopg2 |
| Visualisation | Streamlit, Plotly |
| Schema design | dbdiagram.io |
| Architecture diagram | Mermaid / draw.io |
| Version control | Git / GitHub |

---

## Star Schema Design

```
dim_zones (zone_id PK, zone_name, community_num, parking_area, total_capacity, load_timestamp)
    |
    | 1 : many
    |
fact_occupancy (id PK, event_timestamp, zone_id FK, spot_id, occupancy_status,
                is_occupied, peak_hour_flag, vehicle_type, payment_amount,
                parking_duration_mins, weather_temp, traffic_level)
```

---

## Key Engineering Decisions

**Zone lookup table:** The two datasets share no natural key. The Kaggle dataset uses generic section labels (Zone A–D) while the RTA data uses Dubai community names. We engineered a manual mapping table to bridge them, assigning each section to a geographically representative Dubai community (Al Ras, Burj Khalifa, Al Satwa, Hor Al Anz).

**Feature engineering:** Two derived columns were added during transformation — `is_occupied` (binary integer for easy SQL aggregation) and `peak_hour_flag` (marks AM peak 7–9h and PM peak 17–19h based on Dubai traffic patterns).

**Quality checks:** Three checks run before any data is loaded — null zone ID detection, duplicate sensor reading detection, and occupancy status value validation.
