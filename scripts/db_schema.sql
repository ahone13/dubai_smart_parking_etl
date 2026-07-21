-- ============================================================
-- Dubai Smart Parking — PostgreSQL Schema
-- Database: smart_parking
-- Architecture: Star Schema (1 dimension, 1 fact table)
-- ============================================================

-- Drop existing tables (order matters due to foreign key)
DROP TABLE IF EXISTS fact_occupancy CASCADE;
DROP TABLE IF EXISTS dim_zones CASCADE;

-- ------------------------------------------------------------
-- Dimension table: dim_zones
-- Source: Dubai Pulse / RTA
-- Contains static metadata for each parking zone in Dubai
-- ------------------------------------------------------------
CREATE TABLE dim_zones (
    zone_id        SERIAL PRIMARY KEY,
    zone_name      VARCHAR(100) NOT NULL UNIQUE,
    community_num  INT,
    parking_area   VARCHAR(100),
    total_capacity INT NOT NULL,
    load_timestamp TIMESTAMP
);

-- ------------------------------------------------------------
-- Fact table: fact_occupancy
-- Source: Kaggle IIoT Smart Parking Management Dataset
-- Contains time-series occupancy events per parking spot
-- Joined to dim_zones via zone_id (foreign key)
-- ------------------------------------------------------------
CREATE TABLE fact_occupancy (
    id                    SERIAL PRIMARY KEY,
    event_timestamp       TIMESTAMP NOT NULL,
    zone_id               INT REFERENCES dim_zones(zone_id),
    spot_id               INT NOT NULL,
    occupancy_status      VARCHAR(20),
    is_occupied           SMALLINT,       -- 1 = Occupied, 0 = Vacant
    peak_hour_flag        SMALLINT,       -- 1 = peak hours (7-9h, 17-19h), 0 = off-peak
    vehicle_type          VARCHAR(50),
    payment_amount        FLOAT,
    parking_duration_mins INT,
    weather_temp          FLOAT,
    traffic_level         VARCHAR(20)
);

-- ------------------------------------------------------------
-- Indexes for query performance
-- ------------------------------------------------------------
CREATE INDEX idx_fact_zone_id        ON fact_occupancy(zone_id);
CREATE INDEX idx_fact_timestamp      ON fact_occupancy(event_timestamp);
CREATE INDEX idx_fact_peak_flag      ON fact_occupancy(peak_hour_flag);
CREATE INDEX idx_fact_occupancy_status ON fact_occupancy(occupancy_status);

-- ------------------------------------------------------------
-- Useful analytical views
-- ------------------------------------------------------------

-- Zone-level occupancy summary
CREATE OR REPLACE VIEW vw_zone_occupancy AS
SELECT
    z.zone_name,
    z.total_capacity,
    COUNT(f.id)                        AS total_events,
    SUM(f.is_occupied)                 AS occupied_events,
    ROUND(AVG(f.is_occupied) * 100, 1) AS avg_occupancy_pct
FROM fact_occupancy f
JOIN dim_zones z ON f.zone_id = z.zone_id
GROUP BY z.zone_name, z.total_capacity
ORDER BY avg_occupancy_pct DESC;

-- Hourly occupancy trend
CREATE OR REPLACE VIEW vw_hourly_occupancy AS
SELECT
    EXTRACT(HOUR FROM event_timestamp)  AS hour_of_day,
    COUNT(*)                            AS total_events,
    ROUND(AVG(is_occupied) * 100, 1)    AS avg_occupancy_pct
FROM fact_occupancy
GROUP BY hour_of_day
ORDER BY hour_of_day;

-- Peak vs off-peak comparison
CREATE OR REPLACE VIEW vw_peak_comparison AS
SELECT
    CASE WHEN peak_hour_flag = 1 THEN 'Peak hours' ELSE 'Off-peak' END AS period,
    COUNT(*)                           AS total_events,
    ROUND(AVG(is_occupied) * 100, 1)   AS avg_occupancy_pct
FROM fact_occupancy
GROUP BY peak_hour_flag
ORDER BY peak_hour_flag DESC;
