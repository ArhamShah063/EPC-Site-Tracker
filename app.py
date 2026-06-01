
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="EPC PMO Control Tower",
    page_icon="🏗️",
    layout="wide"
)

st.title("🏗️ EPC PMO Control Tower")
st.caption("Portfolio Monitoring • Delay Analytics • Launch Tracking")

# ---------------------------------------------------
# FILE UPLOAD
# ---------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload EPC Master Data",
    type=["xlsx", "xls", "csv"]
)

if uploaded_file is None:
    st.info("Upload the EPC master dataset to continue.")
    st.stop()

# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------
@st.cache_data
def load_data(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)

df = load_data(uploaded_file)

# ---------------------------------------------------
# REQUIRED COLUMNS
# ---------------------------------------------------
required_cols = [
    "Site Name",
    "Zone",
    "State",
    "PM",
    "Actual Start Date",
    "Planned Finish Date",
    "Forecasted Finish Date",
    "Actual Finish Date",
    "LAUNCHED / YTL",
    "Planned (Month) Bucket",
    "Actual (Month) Bucket",
    "Area (Sqft)"
]

missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"Missing Columns: {missing}")
    st.write("Columns found:")
    st.write(df.columns.tolist())
    st.stop()

# ---------------------------------------------------
# DATE CLEANING
# ---------------------------------------------------
date_cols = [
    "Actual Start Date",
    "Planned Finish Date",
    "Forecasted Finish Date",
    "Actual Finish Date"
]

for col in date_cols:
    df[col] = pd.to_datetime(df[col], errors="coerce")

# ---------------------------------------------------
# CALCULATIONS
# ---------------------------------------------------
df["Delay (Days)"] = (
    df["Actual Finish Date"]
    - df["Planned Finish Date"]
).dt.days

df["Delay (Days)"] = df["Delay (Days)"].fillna(0)

df["Is Delayed"] = df["Delay (Days)"] > 0

df["Forecast Error"] = (
    df["Actual Finish Date"]
    - df["Forecasted Finish Date"]
).dt.days

# ---------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------
st.sidebar.header("Filters")

zone_filter = st.sidebar.multiselect(
    "Zone",
    sorted(df["Zone"].dropna().unique()),
    default=sorted(df["Zone"].dropna().unique())
)

state_filter = st.sidebar.multiselect(
    "State",
    sorted(df["State"].dropna().unique()),
    default=sorted(df["State"].dropna().unique())
)

pm_filter = st.sidebar.multiselect(
    "PM",
    sorted(df["PM"].dropna().unique()),
    default=sorted(df["PM"].dropna().unique())
)

status_filter = st.sidebar.multiselect(
    "Launch Status",
    ["LAUNCHED", "YTL"],
    default=["LAUNCHED", "YTL"]
)

delay_threshold = st.sidebar.slider(
    "Minimum Delay Days",
    0,
    180,
    0
)

fdf = df.copy()

fdf = fdf[fdf["Zone"].isin(zone_filter)]
fdf = fdf[fdf["State"].isin(state_filter)]
fdf = fdf[fdf["PM"].isin(pm_filter)]
fdf = fdf[fdf["LAUNCHED / YTL"].isin(status_filter)]
fdf = fdf[fdf["Delay (Days)"] >= delay_threshold]

# ---------------------------------------------------
# KPI SECTION
# ---------------------------------------------------
st.subheader("Executive Dashboard")

total = len(fdf)

launched = (
    fdf["LAUNCHED / YTL"] == "LAUNCHED"
).sum()

ytl = (
    fdf["LAUNCHED / YTL"] == "YTL"
).sum()

delayed = fdf["Is Delayed"].sum()

avg_delay = round(
    fdf["Delay (Days)"].mean(), 1
)

on_time = (
    (fdf["Delay (Days)"] <= 0)
    &
    (fdf["LAUNCHED / YTL"] == "LAUNCHED")
).sum()

on_time_pct = (
    round(on_time / total * 100, 1)
    if total
    else 0
)

health_score = max(
    0,
    round(
        100 - (
            fdf["Delay (Days)"]
            .clip(lower=0)
            .mean() / 30 * 100
        ),
        1
    )
)

c1,c2,c3,c4,c5,c6,c7 = st.columns(7)

c1.metric("Total Sites", total)
c2.metric("Launched", launched)
c3.metric("YTL", ytl)
c4.metric("Delayed", delayed)
c5.metric("Avg Delay", avg_delay)
c6.metric("On Time %", on_time_pct)
c7.metric("Health Score", health_score)

st.divider()

# ---------------------------------------------------
# SITE SEARCH
# ---------------------------------------------------
st.subheader("Site Search")

site_search = st.text_input(
    "Search Site Name"
)

if site_search:
    search_df = fdf[
        fdf["Site Name"]
        .str.contains(
            site_search,
            case=False,
            na=False
        )
    ]

    st.dataframe(
        search_df,
        use_container_width=True
    )

# ---------------------------------------------------
# DELAY TABLE
# ---------------------------------------------------
st.subheader("Delayed Sites")

delay_table = (
    fdf[fdf["Is Delayed"]]
    .sort_values(
        "Delay (Days)",
        ascending=False
    )
)

st.dataframe(
    delay_table,
    use_container_width=True
)

# ---------------------------------------------------
# CHARTS ROW 1
# ---------------------------------------------------
col1,col2 = st.columns(2)

with col1:

    zone_delay = (
        fdf.groupby("Zone")
        ["Is Delayed"]
        .sum()
        .reset_index()
    )

    fig = px.bar(
        zone_delay,
        x="Zone",
        y="Is Delayed",
        color="Is Delayed",
        title="Delayed Sites by Zone"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

with col2:

    status_zone = (
        fdf.groupby(
            ["Zone","LAUNCHED / YTL"]
        )
        .size()
        .reset_index(name="Count")
    )

    fig = px.bar(
        status_zone,
        x="Zone",
        y="Count",
        color="LAUNCHED / YTL",
        barmode="group",
        title="Launch Status by Zone"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# ---------------------------------------------------
# HEATMAP
# ---------------------------------------------------
st.subheader("Delay Heatmap")

heat = pd.pivot_table(
    fdf,
    values="Delay (Days)",
    index="State",
    columns="Zone",
    aggfunc="mean"
)

fig = px.imshow(
    heat,
    text_auto=True,
    aspect="auto"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ---------------------------------------------------
# PM PERFORMANCE
# ---------------------------------------------------
st.subheader("PM Performance")

pm_perf = (
    fdf.groupby("PM")
    .agg(
        Sites=("Site Name","count"),
        Avg_Delay=("Delay (Days)","mean")
    )
    .reset_index()
)

fig = px.bar(
    pm_perf,
    x="PM",
    y="Avg_Delay",
    color="Avg_Delay"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ---------------------------------------------------
# TREEMAP
# ---------------------------------------------------
st.subheader("Portfolio Treemap")

fig = px.treemap(
    fdf,
    path=["Zone","State","Site Name"],
    values="Area (Sqft)",
    color="Delay (Days)"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ---------------------------------------------------
# GANTT CHART
# ---------------------------------------------------
st.subheader("Project Gantt Chart")

gantt = fdf.copy()

fig = px.timeline(
    gantt,
    x_start="Actual Start Date",
    x_end="Planned Finish Date",
    y="Site Name",
    color="Zone"
)

fig.update_yaxes(
    autorange="reversed"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ---------------------------------------------------
# BUBBLE CHART
# ---------------------------------------------------
st.subheader("Area vs Delay")

fig = px.scatter(
    fdf,
    x="Area (Sqft)",
    y="Delay (Days)",
    size="Area (Sqft)",
    color="Zone",
    hover_name="Site Name"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ---------------------------------------------------
# FORECAST ACCURACY
# ---------------------------------------------------
st.subheader("Forecast Accuracy")

fig = px.histogram(
    fdf,
    x="Forecast Error",
    nbins=25
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ---------------------------------------------------
# S CURVE
# ---------------------------------------------------
st.subheader("S Curve")

planned_counts = (
    fdf["Planned (Month) Bucket"]
    .value_counts()
    .sort_index()
)

actual_counts = (
    fdf["Actual (Month) Bucket"]
    .dropna()
    .value_counts()
    .sort_index()
)

all_months = sorted(
    set(planned_counts.index)
    |
    set(actual_counts.index)
)

planned_counts = planned_counts.reindex(
    all_months,
    fill_value=0
)

actual_counts = actual_counts.reindex(
    all_months,
    fill_value=0
)

planned_cum = planned_counts.cumsum()
actual_cum = actual_counts.cumsum()

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=all_months,
        y=planned_cum,
        mode="lines+markers",
        name="Planned"
    )
)

fig.add_trace(
    go.Scatter(
        x=all_months,
        y=actual_cum,
        mode="lines+markers",
        name="Actual"
    )
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ---------------------------------------------------
# TOP RISK SITES
# ---------------------------------------------------
st.subheader("Top Risk Sites")

risk_sites = (
    fdf.sort_values(
        "Delay (Days)",
        ascending=False
    )
    .head(15)
)

st.dataframe(
    risk_sites[
        [
            "Site Name",
            "Zone",
            "State",
            "PM",
            "Delay (Days)"
        ]
    ],
    use_container_width=True
)

# ---------------------------------------------------
# EXPORT
# ---------------------------------------------------
st.subheader("Export")

csv = fdf.to_csv(index=False)

st.download_button(
    "Download Filtered Data",
    csv,
    file_name="filtered_epc_data.csv",
    mime="text/csv"
)
```
