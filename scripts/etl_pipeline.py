# ============================================================
# Dubai Smart Parking ETL Pipeline
# ============================================================
# Team: O'kah Ahone Ebwekoh, Muhammad Sharjeel Zahid, Tharun Kumar Reddy
# Made by : O'kah Ahone Ebwekoh
# Run: python etl_pipeline.py
# ============================================================

import pandas as pd
from sqlalchemy import create_engine, text

# ------------------------------------------------------------
# 0. CONFIG — update DB_PASSWORD if yours is different
# ------------------------------------------------------------
DB_USER     = "postgres"
DB_PASSWORD = "postgres123"   
DB_HOST     = "127.0.0.1"
DB_PORT     = "5432"
DB_NAME     = "smart_parking"

KAGGLE_CSV  = r"C:\Users\Ahone\Desktop\data_engineering_csv\IIoT_Smart_Parking_Management.csv"
RTA_CSV     = r"C:\Users\Ahone\Desktop\data_engineering_csv\number_of_parking_spaces_per_zone_2026-05-21_02-02-07_1.csv"

# ------------------------------------------------------------
# 1. EXTRACT
# ------------------------------------------------------------
print("Extracting data...")
df_kaggle = pd.read_csv(KAGGLE_CSV)
df_rta    = pd.read_csv(RTA_CSV)

print(f"  Kaggle rows: {len(df_kaggle)}")
print(f"  RTA rows:    {len(df_rta)}")

# ------------------------------------------------------------
# 2. TRANSFORM — RTA (Dim_Zones)
# ------------------------------------------------------------
print("\nTransforming RTA data...")

df_rta = df_rta.rename(columns={
    "community_name_en": "zone_name",
    "community_num":     "community_num",
    "parking_area":      "parking_area",
    "park_spaces_count": "total_capacity",
    "load_timestamp":    "load_timestamp"
})

# Drop rows with unknown zone names or zero capacity
df_rta = df_rta[df_rta["zone_name"] != "Unknown"]
df_rta = df_rta[df_rta["total_capacity"] > 0]
df_rta["zone_name"] = df_rta["zone_name"].str.strip().str.upper()
df_rta = df_rta.drop_duplicates(subset=["zone_name"])
df_rta = df_rta.reset_index(drop=True)
df_rta["zone_id"] = df_rta.index + 1  # surrogate key

print(f"  Clean RTA zones: {len(df_rta)}")

# ------------------------------------------------------------
# 3. TRANSFORM — Zone Lookup (bridges Kaggle sections to Dubai zones)
# ------------------------------------------------------------
# Kaggle has 4 generic sections (Zone A-D).
# We map each to a real Dubai community from the RTA data.
zone_lookup = {
    "Zone A": "AL RAS",
    "Zone B": "BURJ KHALIFA",
    "Zone C": "AL SATWA",
    "Zone D": "HOR AL ANZ"
}

# Validate all mapped zones exist in RTA data
for section, community in zone_lookup.items():
    if community not in df_rta["zone_name"].values:
        print(f"  WARNING: '{community}' not found in RTA data — check spelling")

# ------------------------------------------------------------
# 4. TRANSFORM — Kaggle (Fact_Occupancy)
# ------------------------------------------------------------
print("\nTransforming Kaggle data...")

df_kaggle["Timestamp"] = pd.to_datetime(df_kaggle["Timestamp"])
df_kaggle["zone_name"] = df_kaggle["Parking_Lot_Section"].map(zone_lookup).str.upper()

# Join zone_id from dim table
zone_id_map = df_rta.set_index("zone_name")["zone_id"]
df_kaggle["zone_id"] = df_kaggle["zone_name"].map(zone_id_map)

# Feature engineering
df_kaggle["is_occupied"]    = (df_kaggle["Occupancy_Status"] == "Occupied").astype(int)
df_kaggle["hour"]           = df_kaggle["Timestamp"].dt.hour
df_kaggle["peak_hour_flag"] = df_kaggle["hour"].between(7, 9) | df_kaggle["hour"].between(17, 19)
df_kaggle["peak_hour_flag"] = df_kaggle["peak_hour_flag"].astype(int)

# Select final fact columns
df_fact = df_kaggle[[
    "Timestamp", "zone_id", "Parking_Spot_ID",
    "Occupancy_Status", "is_occupied", "peak_hour_flag",
    "Vehicle_Type", "Payment_Amount", "Parking_Duration",
    "Weather_Temperature", "Nearby_Traffic_Level"
]].rename(columns={
    "Timestamp":           "event_timestamp",
    "Parking_Spot_ID":     "spot_id",
    "Occupancy_Status":    "occupancy_status",
    "Vehicle_Type":        "vehicle_type",
    "Payment_Amount":      "payment_amount",
    "Parking_Duration":    "parking_duration_mins",
    "Weather_Temperature": "weather_temp",
    "Nearby_Traffic_Level":"traffic_level"
})

# ------------------------------------------------------------
# 5. QUALITY CHECKS
# ------------------------------------------------------------
print("\nRunning quality checks...")

# Check 1: No null zone_ids in fact table
null_zones = df_fact["zone_id"].isna().sum()
print(f"  Null zone_ids: {null_zones} (should be 0)")

# Check 2: No duplicate spot+timestamp combos
dupes = df_fact.duplicated(subset=["event_timestamp", "spot_id"]).sum()
print(f"  Duplicate spot+timestamp rows: {dupes} (should be 0)")

# Check 3: Occupancy status only has valid values
valid_statuses = {"Occupied", "Vacant"}
invalid = ~df_fact["occupancy_status"].isin(valid_statuses)
print(f"  Invalid occupancy status rows: {invalid.sum()} (should be 0)")

# ------------------------------------------------------------
# 6. LOAD — Create DB and tables, then insert data
# ------------------------------------------------------------
print("\nConnecting to PostgreSQL...")

# First connect to default 'postgres' db to create our database
engine_default = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"
)

with engine_default.connect() as conn:
    conn.execution_options(isolation_level="AUTOCOMMIT")
    result = conn.execute(
        text(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
    )
    if not result.fetchone():
        conn.execute(text(f"CREATE DATABASE {DB_NAME}"))
        print(f"  Created database '{DB_NAME}'")
    else:
        print(f"  Database '{DB_NAME}' already exists")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Create tables
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS fact_occupancy CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS dim_zones CASCADE"))

    conn.execute(text("""
        CREATE TABLE dim_zones (
            zone_id        SERIAL PRIMARY KEY,
            zone_name      VARCHAR(100) NOT NULL UNIQUE,
            community_num  INT,
            parking_area   VARCHAR(100),
            total_capacity INT NOT NULL,
            load_timestamp TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE fact_occupancy (
            id                    SERIAL PRIMARY KEY,
            event_timestamp       TIMESTAMP NOT NULL,
            zone_id               INT REFERENCES dim_zones(zone_id),
            spot_id               INT NOT NULL,
            occupancy_status      VARCHAR(20),
            is_occupied           SMALLINT,
            peak_hour_flag        SMALLINT,
            vehicle_type          VARCHAR(50),
            payment_amount        FLOAT,
            parking_duration_mins INT,
            weather_temp          FLOAT,
            traffic_level         VARCHAR(20)
        )
    """))
    conn.commit()
    print("  Tables created")

# Insert data
dim_cols = ["zone_id", "zone_name", "community_num", "parking_area", "total_capacity", "load_timestamp"]
df_rta[dim_cols].to_sql("dim_zones", engine, if_exists="append", index=False)
print(f"  Loaded {len(df_rta)} rows into dim_zones")

df_fact.to_sql("fact_occupancy", engine, if_exists="append", index=False)
print(f"  Loaded {len(df_fact)} rows into fact_occupancy")

# ------------------------------------------------------------
# 7. VERIFY — Quick sanity query
# ------------------------------------------------------------
print("\nVerification queries:")

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT z.zone_name, z.total_capacity,
               COUNT(f.id) AS total_events,
               SUM(f.is_occupied) AS occupied_events,
               ROUND(AVG(f.is_occupied) * 100, 1) AS avg_occupancy_pct
        FROM fact_occupancy f
        JOIN dim_zones z ON f.zone_id = z.zone_id
        GROUP BY z.zone_name, z.total_capacity
        ORDER BY avg_occupancy_pct DESC
    """))
    rows = result.fetchall()
    print(f"\n  {'Zone':<25} {'Capacity':>10} {'Events':>8} {'Avg Occ%':>10}")
    print("  " + "-" * 57)
    for row in rows:
        print(f"  {row[0]:<25} {row[1]:>10} {row[2]:>8} {row[4]:>9}%")

print("\nETL pipeline complete!")
