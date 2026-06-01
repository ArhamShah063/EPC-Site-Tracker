import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(
    page_title="EPC Site Launch Tracker",
    page_icon="🏗️",
    layout="wide"
)

st.title("🏗️ EPC Site Launch Progress Tracker")
st.caption("Upload the master data sheet to get instant insights — no manual work needed.")

# ─── FILE UPLOAD ───────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload Master Data (Excel or CSV)",
    type=["xlsx", "xls", "csv"]
)

if uploaded_file is None:
    st.info("👆 Upload your master data file above to get started. Use the sample_data.csv for a demo.")
    st.stop()

# ─── LOAD & CLEAN DATA ─────────────────────────────────────────
@st.cache_data
def load_data(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    return df

df = load_data(uploaded_file)

date_cols = ["Planned Finish Date", "Actual Finish Date",
             "Forecasted Finish Date", "Actual Start Date", "RFC Date"]
for col in date_cols:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

df["Delay (Days)"] = (
    df["Actual Finish Date"] - df["Planned Finish Date"]
).dt.days.fillna(0).astype(int)
df["Is Delayed"] = df["Delay (Days)"] > 0

# ─── KPI CARDS ─────────────────────────────────────────────────
st.subheader("📊 Project Snapshot")

total      = len(df)
launched   = int((df["LAUNCHED / YTL"] == "LAUNCHED").sum())
ytl        = int((df["LAUNCHED / YTL"] == "YTL").sum())
delayed    = int(df["Is Delayed"].sum())
avg_delay  = df[df["Is Delayed"]]["Delay (Days)"].mean()
launch_pct = round(launched / total * 100, 1) if total else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Sites",      total)
c2.metric("Launched",         launched, f"{launch_pct}%")
c3.metric("Yet to Launch",    ytl)
c4.metric("Sites Delayed",    delayed)
c5.metric("Avg Delay (Days)", f"{avg_delay:.0f}" if not pd.isna(avg_delay) else "0")
c6.metric("On-Time Launches", launched - delayed if launched > delayed else 0)

st.divider()

# ─── FILTERS ───────────────────────────────────────────────────
st.subheader("🔍 Delay Analysis")

f1, f2, f3, f4 = st.columns(4)
zones   = ["All"] + sorted(df["Zone"].dropna().unique().tolist())
pms     = ["All"] + sorted(df["PM"].dropna().unique().tolist())
states  = ["All"] + sorted(df["State"].dropna().unique().tolist())
statuses = ["All", "LAUNCHED", "YTL"]

zone_f   = f1.selectbox("Zone",   zones)
pm_f     = f2.selectbox("PM",     pms)
state_f  = f3.selectbox("State",  states)
status_f = f4.selectbox("Status", statuses)

fdf = df.copy()
if zone_f   != "All": fdf = fdf[fdf["Zone"]             == zone_f]
if pm_f     != "All": fdf = fdf[fdf["PM"]               == pm_f]
if state_f  != "All": fdf = fdf[fdf["State"]            == state_f]
if status_f != "All": fdf = fdf[fdf["LAUNCHED / YTL"]   == status_f]

show_cols = ["Site Name", "Zone", "State", "PM",
             "Planned Finish Date", "Actual Finish Date",
             "Delay (Days)", "LAUNCHED / YTL"]

delayed_df = fdf[fdf["Is Delayed"]].sort_values("Delay (Days)", ascending=False)

if delayed_df.empty:
    st.success("✅ No delayed sites for the selected filters.")
else:
    st.dataframe(
        delayed_df[show_cols].reset_index(drop=True),
        use_container_width=True
    )

st.divider()

# ─── CHARTS ────────────────────────────────────────────────────
ch1, ch2 = st.columns(2)

with ch1:
    st.subheader("Delays by Zone")
    zone_delay = df.groupby("Zone")["Is Delayed"].sum().reset_index()
    zone_delay.columns = ["Zone", "Delayed Sites"]
    fig_bar = px.bar(
        zone_delay, x="Zone", y="Delayed Sites",
        color="Delayed Sites", color_continuous_scale="Reds",
        title="Number of Delayed Sites per Zone"
    )
    fig_bar.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig_bar, use_container_width=True)

with ch2:
    st.subheader("Launch Status by Zone")
    zone_status = df.groupby(["Zone", "LAUNCHED / YTL"]).size().reset_index(name="Count")
    fig_pie = px.bar(
        zone_status, x="Zone", y="Count",
        color="LAUNCHED / YTL",
        barmode="group",
        color_discrete_map={"LAUNCHED": "#2ecc71", "YTL": "#e74c3c"},
        title="Launched vs YTL by Zone"
    )
    fig_pie.update_layout(height=350)
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# ─── S-CURVE ───────────────────────────────────────────────────
st.subheader("📈 S-Curve: Cumulative Planned vs Actual Launches")

MONTH_ORDER = [
    "Apr-24","May-24","Jun-24","Jul-24","Aug-24","Sep-24",
    "Oct-24","Nov-24","Dec-24","Jan-25","Feb-25","Mar-25",
    "Apr-25","May-25","Jun-25","Jul-25","Aug-25","Sep-25",
    "Oct-25","Nov-25","Dec-25"
]

planned_counts = (
    df["Planned (Month) Bucket"]
    .value_counts()
    .reindex(MONTH_ORDER, fill_value=0)
)

actual_counts = (
    df[df["Actual (Month) Bucket"].notna() & (df["Actual (Month) Bucket"] != "")]
    ["Actual (Month) Bucket"]
    .value_counts()
    .reindex(MONTH_ORDER, fill_value=0)
)

planned_cum = planned_counts.cumsum()
actual_cum  = actual_counts.cumsum()

fig_s = go.Figure()
fig_s.add_trace(go.Scatter(
    x=MONTH_ORDER, y=planned_cum.values,
    mode="lines+markers", name="Planned",
    line=dict(color="#3498db", dash="dash", width=2),
    marker=dict(size=6)
))
fig_s.add_trace(go.Scatter(
    x=MONTH_ORDER, y=actual_cum.values,
    mode="lines+markers", name="Actual",
    line=dict(color="#2ecc71", width=2),
    marker=dict(size=6)
))
fig_s.update_layout(
    xaxis_title="Month",
    yaxis_title="Cumulative Sites Launched",
    height=420,
    legend=dict(x=0.01, y=0.99),
    hovermode="x unified"
)
st.plotly_chart(fig_s, use_container_width=True)

# Gap annotation
gap = int(planned_cum.iloc[-1] - actual_cum.iloc[-1])
if gap > 0:
    st.warning(f"⚠️ Current gap: **{gap} sites** are behind planned cumulative launches.")
else:
    st.success("✅ Actual launches are on track or ahead of plan.")

st.divider()

# ─── AI SUMMARY ────────────────────────────────────────────────
st.subheader("🤖 AI Weekly Summary")
st.caption("Generates a ready-to-paste executive paragraph from your data.")

if st.button("Generate AI Summary", type="primary"):
    top5 = (
        df[df["Is Delayed"]][["Site Name", "Zone", "PM", "Delay (Days)"]]
        .sort_values("Delay (Days)", ascending=False)
        .head(5)
        .to_string(index=False)
    )

    zone_summary = (
        df.groupby("Zone")
        .agg(Total=("Site Name","count"), Launched=("LAUNCHED / YTL", lambda x:(x=="LAUNCHED").sum()))
        .assign(Pending=lambda d: d["Total"]-d["Launched"])
        .to_string()
    )

    prompt = f"""You are a project reporting assistant for an EPC department at a large retail company.

Weekly Project Data:
- Total Sites: {total}
- Launched: {launched} ({launch_pct}%)
- Yet to Launch: {ytl}
- Sites with Delays: {delayed}
- Average Delay: {avg_delay:.0f} days

Zone-wise Summary:
{zone_summary}

Top 5 Most Delayed Sites:
{top5}

Write a professional 2-paragraph executive summary for the weekly management review meeting.
Paragraph 1: Overall project status and progress.
Paragraph 2: Key risks, delay patterns, and one specific recommended action.
Be direct and factual. No fluff."""

    try:
        from groq import Groq
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=450
        )
        summary = response.choices[0].message.content

        st.success(summary)
        st.download_button(
            "📥 Download Summary as .txt",
            data=summary,
            file_name="weekly_summary.txt",
            mime="text/plain"
        )

    except Exception as e:
        st.error(f"AI call failed: {e}")
        st.info("Make sure GROQ_API_KEY is set in your Streamlit secrets.")
