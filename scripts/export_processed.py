# ============================================================
# Dubai Smart Parking — Export Processed Data
# Queries PostgreSQL and saves clean tables to data/processed/
# Run: python export_processed.py
# ============================================================

import pandas as pd
from sqlalchemy import create_engine
import os

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
DB_USER     = "postgres"
DB_PASSWORD = "postgres123"
DB_HOST     = "127.0.0.1"
DB_PORT     = "5432"
DB_NAME     = "smart_parking"

OUTPUT_DIR  = r"C:\Users\Ahone\Desktop\data_engineering_csv\data\processed"

# ------------------------------------------------------------
# CONNECT
# ------------------------------------------------------------
engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Output folder: {OUTPUT_DIR}\n")

# ------------------------------------------------------------
# EXPORT 1 — dim_zones
# ------------------------------------------------------------
df_zones = pd.read_sql("SELECT * FROM dim_zones ORDER BY zone_id", engine)
path1 = os.path.join(OUTPUT_DIR, "dim_zones_processed.csv")
df_zones.to_csv(path1, index=False)
print(f"Exported dim_zones:     {len(df_zones)} rows → dim_zones_processed.csv")

# ------------------------------------------------------------
# EXPORT 2 — fact_occupancy
# ------------------------------------------------------------
df_fact = pd.read_sql("SELECT * FROM fact_occupancy ORDER BY id", engine)
path2 = os.path.join(OUTPUT_DIR, "fact_occupancy_processed.csv")
df_fact.to_csv(path2, index=False)
print(f"Exported fact_occupancy: {len(df_fact)} rows → fact_occupancy_processed.csv")

# ------------------------------------------------------------
# EXPORT 3 — zone occupancy summary view
# ------------------------------------------------------------
df_summary = pd.read_sql("""
    SELECT
        z.zone_name,
        z.total_capacity,
        COUNT(f.id)                        AS total_events,
        SUM(f.is_occupied)                 AS occupied_events,
        ROUND(AVG(f.is_occupied) * 100, 1) AS avg_occupancy_pct
    FROM fact_occupancy f
    JOIN dim_zones z ON f.zone_id = z.zone_id
    GROUP BY z.zone_name, z.total_capacity
    ORDER BY avg_occupancy_pct DESC
""", engine)
path3 = os.path.join(OUTPUT_DIR, "zone_occupancy_summary.csv")
df_summary.to_csv(path3, index=False)
print(f"Exported summary:        {len(df_summary)} rows → zone_occupancy_summary.csv")

# ------------------------------------------------------------
# EXPORT 4 — hourly occupancy trend
# ------------------------------------------------------------
df_hourly = pd.read_sql("""
    SELECT
        EXTRACT(HOUR FROM event_timestamp)  AS hour_of_day,
        COUNT(*)                            AS total_events,
        ROUND(AVG(is_occupied) * 100, 1)    AS avg_occupancy_pct
    FROM fact_occupancy
    GROUP BY hour_of_day
    ORDER BY hour_of_day
""", engine)
path4 = os.path.join(OUTPUT_DIR, "hourly_occupancy_trend.csv")
df_hourly.to_csv(path4, index=False)
print(f"Exported hourly trend:   {len(df_hourly)} rows → hourly_occupancy_trend.csv")

print("\nAll processed files exported successfully.")
print(f"Location: {OUTPUT_DIR}")
