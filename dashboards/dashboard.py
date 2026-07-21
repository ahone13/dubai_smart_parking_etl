# ============================================================
# Dubai Smart Parking — Streamlit Analytics Dashboard
# Run: streamlit run dashboard.py
# ============================================================

import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
DB_CONFIG = {
    "host":     "127.0.0.1",
    "port":     5432,
    "database": "smart_parking",
    "user":     "postgres",
    "password": "postgres123"
}

st.set_page_config(
    page_title="Dubai Smart Parking",
    page_icon="🅿️",
    layout="wide"
)

# ------------------------------------------------------------
# DB CONNECTION
# ------------------------------------------------------------
@st.cache_resource
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

@st.cache_data(ttl=60)
def run_query(sql):
    conn = get_connection()
    return pd.read_sql(sql, conn)

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------
df_zones = run_query("SELECT * FROM dim_zones")

df_occupancy = run_query("""
    SELECT
        f.id,
        f.event_timestamp,
        f.spot_id,
        f.occupancy_status,
        f.is_occupied,
        f.peak_hour_flag,
        f.vehicle_type,
        f.payment_amount,
        f.parking_duration_mins,
        f.weather_temp,
        f.traffic_level,
        z.zone_name,
        z.total_capacity
    FROM fact_occupancy f
    JOIN dim_zones z ON f.zone_id = z.zone_id
""")

df_occupancy["event_timestamp"] = pd.to_datetime(df_occupancy["event_timestamp"])
df_occupancy["hour"] = df_occupancy["event_timestamp"].dt.hour
df_occupancy["day_of_week"] = df_occupancy["event_timestamp"].dt.day_name()

# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
st.sidebar.title("Filters")
selected_zones = st.sidebar.multiselect(
    "Select zones",
    options=df_occupancy["zone_name"].unique(),
    default=df_occupancy["zone_name"].unique()
)

selected_status = st.sidebar.radio(
    "Occupancy status",
    options=["All", "Occupied", "Vacant"],
    index=0
)

df = df_occupancy[df_occupancy["zone_name"].isin(selected_zones)]
if selected_status != "All":
    df = df[df["occupancy_status"] == selected_status]

# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------
st.title("🅿️ Dubai Smart Parking Dashboard")
st.caption("Integrating RTA zone capacity data with IIoT sensor streams")
st.divider()

# ------------------------------------------------------------
# KPI CARDS
# ------------------------------------------------------------
total_events   = len(df)
occupied_count = df["is_occupied"].sum()
vacant_count   = total_events - occupied_count
avg_occ_pct    = round((occupied_count / total_events * 100), 1) if total_events > 0 else 0
avg_duration   = round(df["parking_duration_mins"].mean(), 1)
peak_events    = df["peak_hour_flag"].sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total events",       f"{total_events:,}")
col2.metric("Occupied",           f"{occupied_count:,}")
col3.metric("Vacant",             f"{vacant_count:,}")
col4.metric("Avg occupancy",      f"{avg_occ_pct}%")
col5.metric("Avg duration (min)", f"{avg_duration}")

st.divider()

# ------------------------------------------------------------
# ROW 1: Occupancy by zone + Vehicle type breakdown
# ------------------------------------------------------------
col_a, col_b = st.columns([2, 1])

with col_a:
    st.subheader("Occupancy rate by zone")
    zone_stats = (
        df.groupby("zone_name")
        .agg(
            total=("is_occupied", "count"),
            occupied=("is_occupied", "sum"),
            capacity=("total_capacity", "first")
        )
        .assign(occupancy_pct=lambda x: round(x["occupied"] / x["total"] * 100, 1))
        .reset_index()
        .sort_values("occupancy_pct", ascending=True)
    )
    fig1 = px.bar(
        zone_stats,
        x="occupancy_pct",
        y="zone_name",
        orientation="h",
        text="occupancy_pct",
        color="occupancy_pct",
        color_continuous_scale="RdYlGn_r",
        range_color=[40, 70],
        labels={"occupancy_pct": "Occupancy %", "zone_name": "Zone"}
    )
    fig1.update_traces(texttemplate="%{text}%", textposition="outside")
    fig1.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=0, r=20, t=10, b=0),
        height=250
    )
    st.plotly_chart(fig1, use_container_width=True)

with col_b:
    st.subheader("Vehicle types")
    vehicle_counts = df["vehicle_type"].value_counts().reset_index()
    vehicle_counts.columns = ["vehicle_type", "count"]
    fig2 = px.pie(
        vehicle_counts,
        names="vehicle_type",
        values="count",
        hole=0.4
    )
    fig2.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        height=250,
        showlegend=True,
        legend=dict(orientation="v", x=1, y=0.5)
    )
    st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------
# ROW 2: Hourly trend + Peak vs off-peak
# ------------------------------------------------------------
col_c, col_d = st.columns([2, 1])

with col_c:
    st.subheader("Occupancy by hour of day")
    hourly = (
        df.groupby("hour")["is_occupied"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"mean": "occupancy_rate", "count": "events"})
    )
    hourly["occupancy_pct"] = round(hourly["occupancy_rate"] * 100, 1)
    fig3 = px.line(
        hourly,
        x="hour",
        y="occupancy_pct",
        markers=True,
        labels={"hour": "Hour of day", "occupancy_pct": "Occupancy %"},
    )
    fig3.add_vrect(x0=7, x1=9,   fillcolor="orange", opacity=0.15, line_width=0, annotation_text="AM peak")
    fig3.add_vrect(x0=17, x1=19, fillcolor="orange", opacity=0.15, line_width=0, annotation_text="PM peak")
    fig3.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250)
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    st.subheader("Peak vs off-peak")
    peak_df = df.groupby("peak_hour_flag")["is_occupied"].mean().reset_index()
    peak_df["label"] = peak_df["peak_hour_flag"].map({0: "Off-peak", 1: "Peak hours"})
    peak_df["occupancy_pct"] = round(peak_df["is_occupied"] * 100, 1)
    fig4 = px.bar(
        peak_df,
        x="label",
        y="occupancy_pct",
        color="label",
        text="occupancy_pct",
        color_discrete_map={"Peak hours": "#E85D24", "Off-peak": "#3B8BD4"},
        labels={"occupancy_pct": "Occupancy %", "label": ""}
    )
    fig4.update_traces(texttemplate="%{text}%", textposition="outside")
    fig4.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0),
        height=250
    )
    st.plotly_chart(fig4, use_container_width=True)

# ------------------------------------------------------------
# ROW 3: Capacity vs demand + Traffic level
# ------------------------------------------------------------
col_e, col_f = st.columns([2, 1])

with col_e:
    st.subheader("Zone capacity vs occupied events")
    cap_df = (
        df.groupby("zone_name")
        .agg(
            total_capacity=("total_capacity", "first"),
            occupied_events=("is_occupied", "sum")
        )
        .reset_index()
    )
    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        name="Total capacity",
        x=cap_df["zone_name"],
        y=cap_df["total_capacity"],
        marker_color="#B5D4F4"
    ))
    fig5.add_trace(go.Bar(
        name="Occupied events",
        x=cap_df["zone_name"],
        y=cap_df["occupied_events"],
        marker_color="#E85D24"
    ))
    fig5.update_layout(
        barmode="group",
        margin=dict(l=0, r=0, t=10, b=0),
        height=250,
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig5, use_container_width=True)

with col_f:
    st.subheader("Traffic level distribution")
    traffic = df["traffic_level"].value_counts().reset_index()
    traffic.columns = ["traffic_level", "count"]
    fig6 = px.bar(
        traffic,
        x="traffic_level",
        y="count",
        color="traffic_level",
        color_discrete_sequence=["#3B8BD4", "#EF9F27", "#E24B4A"],
        labels={"traffic_level": "Traffic level", "count": "Events"}
    )
    fig6.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0),
        height=250
    )
    st.plotly_chart(fig6, use_container_width=True)

# ------------------------------------------------------------
# RAW DATA TABLE
# ------------------------------------------------------------
with st.expander("View raw data"):
    st.dataframe(
        df[[
            "event_timestamp", "zone_name", "spot_id",
            "occupancy_status", "vehicle_type",
            "parking_duration_mins", "payment_amount",
            "weather_temp", "traffic_level"
        ]].sort_values("event_timestamp", ascending=False),
        use_container_width=True,
        height=300
    )

st.caption("Data sources: Dubai Pulse / RTA · Kaggle IIoT Smart Parking Dataset")
