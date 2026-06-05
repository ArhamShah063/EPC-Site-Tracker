import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import date as date_type

# ─── SUPABASE CONNECTION
DB_OK = False
DB_ERROR = ""
sb = None

@st.cache_resource
def get_supabase():
    from supabase import create_client
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY missing from secrets")
    return create_client(url, key)

try:
    sb = get_supabase()
    DB_OK = True
except Exception as e:
    DB_OK = False
    DB_ERROR = str(e)

# ─── PAGE CONFIG
st.set_page_config(
    page_title="EPC Site Launch Tracker",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── PROFESSIONAL CSS
st.markdown("""
<style>
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 1.9rem !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        opacity: 0.75;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        padding: 10px 22px;
        font-weight: 500;
        font-size: 0.9rem;
    }
    /* Labels */
    div[data-testid="stSelectbox"] label,
    div[data-testid="stTextInput"] label,
    div[data-testid="stMultiSelect"] label,
    div[data-testid="stCheckbox"] label {
        font-weight: 600;
        font-size: 0.84rem;
        letter-spacing: 0.02em;
    }
    /* Primary button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1a56db, #1e3a8a);
        border: none;
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.03em;
        padding: 10px 28px;
    }
    /* Download button */
    .stDownloadButton > button {
        border-radius: 8px;
        font-weight: 500;
    }
    /* Dataframe */
    .stDataFrame { border-radius: 8px; }
    /* Divider */
    hr { opacity: 0.35; }
</style>
""", unsafe_allow_html=True)

# ─── HEADER
st.markdown("""
<div style="background:linear-gradient(135deg,#1a1f3c 0%,#1e3a8a 100%);
            border-radius:16px; padding:28px 36px; margin-bottom:20px;
            border:1px solid #2d3a6b; box-shadow:0 4px 24px rgba(30,58,138,0.25);">
  <div style="display:flex; align-items:center; gap:18px;">
    <div style="font-size:2.8rem; line-height:1;">🏗️</div>
    <div>
      <div style="font-size:1.75rem; font-weight:800; color:#f0f4ff; letter-spacing:-0.02em;">
        EPC Site Launch Tracker
      </div>
      <div style="font-size:0.87rem; color:#94a3c0; margin-top:5px; letter-spacing:0.02em;">
        Infrastructure Project Dashboard &nbsp;·&nbsp; Real-time Analytics &nbsp;·&nbsp; Executive Reporting
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── FILE UPLOAD
with st.expander("📂 Upload Data Source (Managers & Planners)", expanded=True):
    uploaded_file = st.file_uploader(
        "Upload Master Data (Excel or CSV)",
        type=["xlsx", "xls", "csv"],
        help="Upload your EPC master tracking sheet — supports .xlsx, .xls, .csv"
    )
    if uploaded_file is None:
        st.info("📋 Site Engineers & Zonal Heads: Use the Inspection Log and Issue Tracker tabs directly — no upload needed. | 📊 Managers & Planners: Upload your master data file above to access all dashboard tabs.")

# ─── ENGINEER-ONLY TABS (no upload needed)
if uploaded_file is None:
    eng_tab1, eng_tab2 = st.tabs(["📋  Inspection Log", "✅  Issue Tracker"])

    with eng_tab1:
        st.markdown("### 📋 Inspection Log")
        st.caption("Zonal heads log site visits, observations, and flag issues.")

        if not DB_OK:
            st.error(f"Database not connected: {DB_ERROR}")
            st.info("Check SUPABASE_URL and SUPABASE_KEY in Streamlit secrets.")
            st.stop()

        with st.form("inspection_form_eng", clear_on_submit=True):
            st.markdown("#### Log New Inspection")
            if1, if2 = st.columns(2)
            insp_site = if1.text_input("Site Name", placeholder="e.g. Reliance Smart Mumbai - 3")
            insp_id   = if2.text_input("Site Unique ID (optional)", placeholder="e.g. APEX10023")
            insp_zh   = st.text_input("Zonal Head Name", placeholder="Enter your full name")
            id1, id2  = st.columns(2)
            insp_date = id1.date_input("Inspection Date", value=date_type.today())
            insp_time = id2.time_input("Inspection Time")
            insp_notes = st.text_area("General Observations / Notes",
                                      placeholder="Overall site condition, progress, concerns…", height=100)
            st.markdown("#### Issues Found During Inspection")
            st.caption("Leave blank if no issue. Add up to 6.")
            issues_to_save = []
            for i in range(6):
                ic1, ic2 = st.columns([4, 1])
                i_desc = ic1.text_input(f"Issue {i+1}", placeholder=f"Describe issue {i+1}…", key=f"eng_idesc_{i}")
                i_sev  = ic2.selectbox("Severity", ["Low","Medium","High","Critical"], key=f"eng_isev_{i}")
                if i_desc.strip():
                    issues_to_save.append({"description": i_desc.strip(), "severity": i_sev})
            submitted = st.form_submit_button("✅ Submit Inspection", type="primary")
            if submitted:
                if not insp_site.strip() or not insp_zh.strip():
                    st.error("Site Name and Zonal Head Name are required.")
                else:
                    try:
                        site_label = insp_site.strip()
                        if insp_id.strip():
                            site_label = f"{insp_site.strip()} ({insp_id.strip()})"
                        insp_payload = {
                            "site_name":       site_label,
                            "zonal_head":      insp_zh.strip(),
                            "inspection_date": str(insp_date),
                            "inspection_time": str(insp_time),
                            "notes":           insp_notes.strip()
                        }
                        result  = sb.table("inspections").insert(insp_payload).execute()
                        insp_id_saved = result.data[0]["id"]
                        for iss in issues_to_save:
                            sb.table("issues").insert({
                                "inspection_id":     insp_id_saved,
                                "issue_description": iss["description"],
                                "severity":          iss["severity"],
                                "status":            "Open"
                            }).execute()
                        st.success(f"✅ Inspection logged for **{site_label}**. {len(issues_to_save)} issue(s) recorded.")
                    except Exception as e:
                        st.error(f"Failed to save: {e}")

        st.divider()
        st.markdown("#### Recent Inspections")
        try:
            recent = sb.table("inspections").select("site_name, zonal_head, inspection_date, inspection_time, notes").order("created_at", desc=True).limit(20).execute()
            if recent.data:
                st.dataframe(pd.DataFrame(recent.data), use_container_width=True, hide_index=True)
            else:
                st.info("No inspections logged yet.")
        except Exception as e:
            st.warning(f"Could not load recent inspections: {e}")

    with eng_tab2:
        st.markdown("### ✅ Issue Tracker & Engineer Checklist")
        st.caption("View and resolve issues flagged during inspections.")

        if not DB_OK:
            st.error(f"Database not connected: {DB_ERROR}")
            st.stop()

        it_site = st.text_input("Enter Your Site Name or ID", placeholder="e.g. Reliance Smart Mumbai - 3 or APEX10023")

        if it_site.strip():
            try:
                insp_for_site = sb.table("inspections").select("id, zonal_head, inspection_date, notes").ilike("site_name", f"%{it_site.strip()}%").order("inspection_date", desc=True).execute()
                if not insp_for_site.data:
                    st.info("No inspections recorded for this site yet.")
                else:
                    all_issues = []
                    for insp in insp_for_site.data:
                        iss = sb.table("issues").select("*").eq("inspection_id", insp["id"]).execute()
                        for issue in iss.data:
                            issue["inspection_date"] = insp["inspection_date"]
                            issue["zonal_head"]      = insp["zonal_head"]
                            all_issues.append(issue)
                    open_issues     = [i for i in all_issues if i["status"] == "Open"]
                    resolved_issues = [i for i in all_issues if i["status"] == "Resolved"]
                    im1, im2, im3 = st.columns(3)
                    im1.metric("Total Issues",    len(all_issues))
                    im2.metric("Open",            len(open_issues),     delta=f"{len(open_issues)} need action", delta_color="inverse")
                    im3.metric("Resolved",        len(resolved_issues), delta=f"{len(resolved_issues)} done",    delta_color="normal")
                    st.divider()
                    if open_issues:
                        st.markdown("#### 🔴 Open Issues — Action Required")
                        for iss in sorted(open_issues, key=lambda x: ["Critical","High","Medium","Low"].index(x.get("severity","Low"))):
                            sev_icon = {"Low":"🟡","Medium":"🟠","High":"🔴","Critical":"🚨"}.get(iss["severity"],"⚪")
                            rc1, rc2, rc3 = st.columns([4, 1, 1])
                            rc1.markdown(f"{sev_icon} **{iss['issue_description']} — Flagged by {iss['zonal_head']} on {iss['inspection_date']}")
                            rc2.markdown(f"**{iss['severity']}**")
                            if rc3.button("Mark Resolved ✅", key=f"eng_res_{iss['id']}"):
                                sb.table("issues").update({"status": "Resolved"}).eq("id", iss["id"]).execute()
                                st.rerun()
                    else:
                        st.success("✅ All issues resolved for this site.")
                    if resolved_issues:
                        with st.expander(f"✅ {len(resolved_issues)} Resolved Issue(s)"):
                            for iss in resolved_issues:
                                st.markdown(f"✅ ~~{iss['issue_description']}~~ · *{iss['zonal_head']}* · {iss['inspection_date']}")
            except Exception as e:
                st.error(f"Could not load issues: {e}")
        else:
            st.info("Enter your site name or ID above to see open issues.")

    st.stop()

# ─── DATA LOADING
@st.cache_data
def load_data(file):
    return pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

df = load_data(uploaded_file)

# ─── DATE PARSING
DATE_COLS = [
    "Planned Finish Date", "Actual Finish Date",
    "Forecasted Finish Date", "Actual Start Date", "RFC Date"
]
for col in DATE_COLS:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

today = pd.Timestamp.today().normalize()

# ─── MATHEMATICALLY CORRECT DELAY CALCULATION
# LAUNCHED  → delay = max(0, actual_finish  − planned_finish)
# YTL       → delay = max(0, (forecasted OR today) − planned_finish)
# Missing planned date → 0
def compute_delay(row):
    planned = row.get("Planned Finish Date")
    if pd.isna(planned):
        return 0
    raw_status = row.get("LAUNCHED / YTL")
    status = str(raw_status).strip().upper() if not pd.isna(raw_status) else ""
    if status == "LAUNCHED":
        actual = row.get("Actual Finish Date")
        return 0 if pd.isna(actual) else max(0, int((actual - planned).days))
    else:   # YTL or unknown
        fcast = row.get("Forecasted Finish Date")
        ref = fcast if not pd.isna(fcast) else today
        return max(0, int((ref - planned).days))

df["Delay (Days)"] = df.apply(compute_delay, axis=1)
df["Is Delayed"]   = df["Delay (Days)"] > 0

# Pre-computed helper columns
df["_launched"] = df["LAUNCHED / YTL"].fillna("").str.strip().str.upper() == "LAUNCHED"
df["_pending"]  = ~df["_launched"]

# ─── KPI CALCULATIONS (CORRECT)
# On-time = sites that ARE launched AND are NOT delayed (not a subtraction hack)
total       = len(df)
launched    = int(df["_launched"].sum())
ytl         = total - launched
delayed     = int(df["Is Delayed"].sum())
on_time     = int((df["_launched"] & ~df["Is Delayed"]).sum())
avg_delay   = df.loc[df["Is Delayed"], "Delay (Days)"].mean() if df["Is Delayed"].any() else 0.0
launch_pct  = round(launched / total * 100, 1) if total else 0.0
delay_pct   = round(delayed  / total * 100, 1) if total else 0.0

# ─── SHARED LAYOUT HELPERS
PLOT_CFG = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    title_font_size=13,
    margin=dict(t=52, b=42, l=42, r=20)
)
GRID = dict(showgrid=True, gridcolor="rgba(0,0,0,0.07)")


#
# NAVIGATION
#
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊  Dashboard",
    "🔍  Store Search & Analysis",
    "🏪  Site Directory",
    "⚠️  Delay Analysis",
    "📋  Inspection Log",
    "✅  Issue Tracker",
    "🤖  AI Summary"
])



# TAB 1 — DASHBOARD
#
with tab1:

    # ── KPI Row
    st.markdown("#### Project Snapshot")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Sites",       total)
    k2.metric("Launched",          launched,    f"{launch_pct}%")
    k3.metric("Yet to Launch",     ytl)
    k4.metric("Delayed (All)",     delayed,     f"{delay_pct}% of portfolio",   delta_color="inverse")
    k5.metric("Avg Delay",         f"{avg_delay:.0f} d",                         delta_color="inverse")
    k6.metric("On-Time Launches",  on_time,     f"of {launched} launched")

    st.divider()

    # ── Zone Charts Row
    zc1, zc2 = st.columns(2)

    with zc1:
        zone_agg = (
            df.groupby("Zone", dropna=True)
            .agg(
                Delayed_Sites=("Is Delayed", "sum"),
                Avg_Delay=("Delay (Days)",
                            lambda x: round(x[x > 0].mean(), 1) if (x > 0).any() else 0)
            )
            .reset_index()
        )
        fig = px.bar(
            zone_agg, x="Zone", y="Delayed_Sites", color="Avg_Delay",
            color_continuous_scale=[[0, "#22c55e"], [0.5, "#f59e0b"], [1, "#ef4444"]],
            text="Delayed_Sites",
            labels={"Delayed_Sites": "Delayed Sites", "Avg_Delay": "Avg Delay (d)"},
            title="Delayed Sites by Zone (color = average delay severity)"
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=380,
            coloraxis_colorbar=dict(title="Avg Delay (d)"),
            yaxis=GRID,
            **PLOT_CFG
        )
        zc1.plotly_chart(fig, use_container_width=True)

    with zc2:
        zone_status = (
            df.groupby(["Zone", "LAUNCHED / YTL"], dropna=True)
            .size()
            .reset_index(name="Count")
        )
        fig2 = px.bar(
            zone_status, x="Zone", y="Count", color="LAUNCHED / YTL",
            barmode="stack",
            color_discrete_map={"LAUNCHED": "#22c55e", "YTL": "#ef4444"},
            title="Launch Status by Zone (LAUNCHED vs Yet-to-Launch)",
            labels={"LAUNCHED / YTL": "Status"}
        )
        fig2.update_layout(height=380, yaxis=GRID, **PLOT_CFG)
        zc2.plotly_chart(fig2, use_container_width=True)

    # ── PM Performance Matrix
    st.markdown("#### Project Manager Performance Matrix")
    pm_agg = (
        df.groupby("PM", dropna=True)
        .agg(
            Total=("Site Name",    "count"),
            Launched=("_launched", "sum"),
            Delayed=("Is Delayed", "sum"),
            Avg_Delay=("Delay (Days)",
                        lambda x: round(x[x > 0].mean(), 1) if (x > 0).any() else 0)
        )
        .reset_index()
    )
    pm_agg["Launch %"]     = (pm_agg["Launched"] / pm_agg["Total"] * 100).round(1)
    pm_agg["Delay Rate %"] = (pm_agg["Delayed"]  / pm_agg["Total"] * 100).round(1)
    pm_agg["Avg_Delay"]    = pm_agg["Avg_Delay"].fillna(0)

    fig_pm = px.scatter(
        pm_agg, x="Launch %", y="Delay Rate %",
        size="Total", color="Avg_Delay",
        hover_name="PM",
        hover_data={"Total": True, "Launched": True, "Delayed": True,
                    "Launch %": ":.1f", "Delay Rate %": ":.1f"},
        color_continuous_scale=[[0, "#22c55e"], [0.5, "#f59e0b"], [1, "#ef4444"]],
        labels={"Avg_Delay": "Avg Delay (d)"},
        title="PM Performance Matrix — Launch % vs Delay Rate  "
              "(bubble size = portfolio size, color = avg delay severity)"
    )
    fig_pm.add_hline(y=50,  line_dash="dot", line_color="#94a3b8", opacity=0.45,
                     annotation_text="50% delay threshold",  annotation_position="bottom right")
    fig_pm.add_vline(x=50,  line_dash="dot", line_color="#94a3b8", opacity=0.45,
                     annotation_text="50% launch threshold", annotation_position="top left")
    fig_pm.update_layout(
        height=460,
        xaxis=dict(range=[0, 112], title="Launch %",      **GRID),
        yaxis=dict(range=[0, 112], title="Delay Rate %",  **GRID),
        **PLOT_CFG
    )
    st.plotly_chart(fig_pm, use_container_width=True)

    st.divider()

    # ── S-Curve
    st.markdown("#### 📈 S-Curve — Cumulative Planned vs Actual Launches")

    MONTHS = [
        "Apr-24", "May-24", "Jun-24", "Jul-24", "Aug-24", "Sep-24",
        "Oct-24", "Nov-24", "Dec-24", "Jan-25", "Feb-25", "Mar-25",
        "Apr-25", "May-25", "Jun-25", "Jul-25", "Aug-25", "Sep-25",
        "Oct-25", "Nov-25", "Dec-25"
    ]

    def monthly_counts(col_name):
        if col_name not in df.columns:
            return pd.Series(0, index=MONTHS)
        mask = df[col_name].notna() & (df[col_name].astype(str).str.strip() != "")
        return df.loc[mask, col_name].value_counts().reindex(MONTHS, fill_value=0)

    plan_cnt  = monthly_counts("Planned (Month) Bucket")
    act_cnt   = monthly_counts("Actual (Month) Bucket")
    plan_cum  = plan_cnt.cumsum()
    act_cum   = act_cnt.cumsum()

    last_act_idx = next(
        (i for i in range(len(MONTHS) - 1, -1, -1) if act_cum.iloc[i] > 0),
        None
    )

    fig_s = go.Figure()
    fig_s.add_trace(go.Scatter(
        x=MONTHS, y=plan_cum.values, name="Planned",
        mode="lines+markers",
        line=dict(color="#3b82f6", dash="dash", width=2.5),
        marker=dict(size=7, color="#3b82f6"),
        hovertemplate="<b>%{x}</b> &nbsp;|&nbsp; Planned: <b>%{y}</b><extra></extra>"
    ))
    fig_s.add_trace(go.Scatter(
        x=MONTHS, y=act_cum.values, name="Actual",
        mode="lines+markers",
        line=dict(color="#22c55e", width=2.5),
        marker=dict(size=7, color="#22c55e"),
        fill="tonexty", fillcolor="rgba(239,68,68,0.07)",
        hovertemplate="<b>%{x}</b> &nbsp;|&nbsp; Actual: <b>%{y}</b><extra></extra>"
    ))

    if last_act_idx is not None:
        gap_at_last = int(plan_cum.iloc[last_act_idx] - act_cum.iloc[last_act_idx])
        if gap_at_last > 0:
            mid_y = (plan_cum.iloc[last_act_idx] + act_cum.iloc[last_act_idx]) / 2
            fig_s.add_annotation(
                x=MONTHS[last_act_idx], y=mid_y,
                text=f"Gap: {gap_at_last} sites",
                font=dict(color="#ef4444", size=12),
                arrowcolor="#ef4444", arrowhead=2, showarrow=True, arrowwidth=1.5
            )

    fig_s.update_layout(
        xaxis=dict(title="Month", tickangle=45, **GRID),
        yaxis=dict(title="Cumulative Sites Launched", **GRID),
        height=460, hovermode="x unified",
        legend=dict(x=0.02, y=0.97, bgcolor="rgba(255,255,255,0.82)",
                    bordercolor="#e2e8f0", borderwidth=1),
        **PLOT_CFG
    )
    st.plotly_chart(fig_s, use_container_width=True)

    final_gap = int(plan_cum.iloc[-1] - act_cum.iloc[-1])
    sg1, sg2, sg3 = st.columns(3)
    sg1.metric("Planned (End of Period)",  int(plan_cum.iloc[-1]))
    sg2.metric("Actual Launched",           int(act_cum.iloc[-1]))
    sg3.metric("Cumulative Gap",            final_gap,
               delta_color="inverse" if final_gap > 0 else "normal")

    if final_gap > 0:
        st.warning(f"⚠️ **{final_gap} sites** remain behind the cumulative planned schedule.")
    else:
        st.success("✅ Actual launches are on track or ahead of plan.")


#
# TAB 2 — STORE SEARCH & ANALYSIS
#
with tab2:

    #
    # SECTION A — STORE LOOKUP
    #
    st.markdown("### 🔍 Store Lookup")
    st.caption("Search by name (partial or exact) to view full store data, milestone timeline, and benchmarks.")

    sc1, sc2 = st.columns([5, 1])
    with sc1:
        query = st.text_input(
            "store_search", label_visibility="collapsed",
            placeholder="🔍  Type a store / site name…"
        )
    with sc2:
        exact = st.checkbox("Exact match", value=False)

    store = None   # sentinel

    if query:
        if exact:
            hits = df[df["Site Name"].str.strip().str.upper() == query.strip().upper()]
        else:
            hits = df[df["Site Name"].str.contains(query.strip(), case=False, na=False)]

        if hits.empty:
            st.warning(f"No stores found matching **'{query}'**.")
        elif len(hits) > 1:
            st.info(f"Found **{len(hits)}** matching stores — select one to continue:")
            chosen = st.selectbox("", hits["Site Name"].tolist(), label_visibility="collapsed")
            store = hits[hits["Site Name"] == chosen].iloc[0]
        else:
            store = hits.iloc[0]

    if store is not None:
        st.divider()

        # ── Profile Card
        raw_status = store.get("LAUNCHED / YTL")
        status     = str(raw_status).strip().upper() if not pd.isna(raw_status) else "N/A"
        delay_days = int(store.get("Delay (Days)", 0))
        is_delayed = bool(store.get("Is Delayed", False))
        zone_s     = str(store.get("Zone", "—"))
        state_s    = str(store.get("State", "—")) if "State" in store.index else "—"
        pm_s       = str(store.get("PM",    "—"))

        s_bg  = "#dcfce7" if status == "LAUNCHED" else "#fee2e2"
        s_col = "#166534" if status == "LAUNCHED" else "#991b1b"
        s_ico = "✅"       if status == "LAUNCHED" else "🔴"
        d_bg  = "#fef9c3" if is_delayed else "#dcfce7"
        d_col = "#854d0e" if is_delayed else "#166534"
        d_txt = f"⚠️ Delayed by {delay_days} d" if is_delayed else "✅ On Schedule"

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#f0f6ff,#e8f0fe);
                    border-radius:16px; padding:28px 32px;
                    border:1px solid #c7d7f5; margin-bottom:20px;
                    box-shadow:0 2px 14px rgba(30,58,138,0.09);">
          <div style="font-size:1.5rem; font-weight:800; color:#1e3a8a; margin-bottom:14px;">
            🏪 {store['Site Name']}
          </div>
          <div style="display:flex; gap:10px; flex-wrap:wrap;">
            <span style="background:{s_bg};color:{s_col};border-radius:20px;
                         padding:5px 15px;font-size:0.82rem;font-weight:700;letter-spacing:0.04em;">
              {s_ico} {status}
            </span>
            <span style="background:{d_bg};color:{d_col};border-radius:20px;
                         padding:5px 15px;font-size:0.82rem;font-weight:700;">
              {d_txt}
            </span>
            <span style="background:#f0f4ff;color:#3b4db8;border-radius:20px;
                         padding:5px 15px;font-size:0.82rem;font-weight:600;">
              📍 {zone_s} · {state_s}
            </span>
            <span style="background:#f5f0ff;color:#6b21a8;border-radius:20px;
                         padding:5px 15px;font-size:0.82rem;font-weight:600;">
              👤 PM: {pm_s}
            </span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Zone",   zone_s)
        m2.metric("State",  state_s)
        m3.metric("PM",     pm_s)
        m4.metric("Delay",  f"{delay_days} d",
                  delta_color="inverse" if delay_days > 0 else "normal")
        m5.metric("Status", status)

        # ── Complete Record Table
        st.markdown("#### 📋 Complete Store Record")
        record_rows = []
        for field, val in zip(store.index, store.values):
            if str(field).startswith("_"):   # hide internal helper columns
                continue
            try:
                is_na = pd.isna(val)
            except Exception:
                is_na = False
            if is_na:
                display_val = "—"
            elif isinstance(val, pd.Timestamp):
                display_val = val.strftime("%d %b %Y")
            elif isinstance(val, (bool, np.bool_)):
                display_val = "Yes" if val else "No"
            else:
                display_val = str(val)
            record_rows.append({"Field": field, "Value": display_val})

        st.dataframe(
            pd.DataFrame(record_rows),
            use_container_width=True,
            hide_index=True,
            height=400
        )

        # ── Milestone Timeline
        st.markdown("#### 📅 Milestone Timeline")
        timeline_map = {
            "Actual Start":      store.get("Actual Start Date"),
            "RFC":               store.get("RFC Date"),
            "Planned Finish":    store.get("Planned Finish Date"),
            "Forecasted Finish": store.get("Forecasted Finish Date"),
            "Actual Finish":     store.get("Actual Finish Date"),
        }
        valid_ms = {k: v for k, v in timeline_map.items() if pd.notna(v)}

        if valid_ms:
            TCOLORS = {
                "Actual Start":      "#3b82f6",
                "RFC":               "#8b5cf6",
                "Planned Finish":    "#22c55e",
                "Forecasted Finish": "#f59e0b",
                "Actual Finish":     "#16a34a"
            }
            sorted_ms    = sorted(valid_ms.items(), key=lambda x: x[1])
            dates_only   = [v for _, v in sorted_ms]

            fig_tl = go.Figure()
            # baseline rail
            fig_tl.add_shape(
                type="line",
                x0=min(dates_only), x1=max(dates_only),
                y0=0.5, y1=0.5,
                line=dict(color="#cbd5e1", width=3)
            )
            for i, (lbl, dt) in enumerate(sorted_ms):
                color_hex = TCOLORS.get(lbl, "#64748b")
                y_pos = 0.82 if i % 2 == 0 else 0.18   # alternate above / below
                # drop line
                fig_tl.add_shape(
                    type="line", x0=dt, x1=dt, y0=0.5, y1=y_pos,
                    line=dict(color=color_hex, width=1.5, dash="dot")
                )
                fig_tl.add_trace(go.Scatter(
                    x=[dt], y=[y_pos],
                    mode="markers+text",
                    marker=dict(size=16, color=color_hex,
                                line=dict(color="white", width=2.5)),
                    text=[f"<b>{lbl}</b><br>{dt.strftime('%d %b %Y')}"],
                    textposition="top center" if y_pos > 0.5 else "bottom center",
                    textfont=dict(size=10, color="#1e293b"),
                    name=lbl, showlegend=True
                ))

            fig_tl.update_layout(
                height=310,
                yaxis=dict(visible=False, range=[-0.15, 1.45]),
                xaxis=dict(title="Date", showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
                showlegend=True,
                legend=dict(orientation="h", y=-0.28, x=0.5, xanchor="center"),
                **PLOT_CFG
            )
            st.plotly_chart(fig_tl, use_container_width=True)
        else:
            st.info("No milestone date data available for this store.")

        # ── Benchmark Comparison
        st.markdown("#### 📊 Benchmark Comparison")
        bc1, bc2 = st.columns(2)

        with bc1:
            zone_avg_d    = (df.loc[df["Zone"] == zone_s, "Delay (Days)"].mean()
                             if zone_s in df["Zone"].values else 0)
            portfolio_avg = df["Delay (Days)"].mean()

            bench_labels = ["This Store", f"Zone '{zone_s}' Avg", "Portfolio Avg"]
            bench_vals   = [delay_days, round(zone_avg_d, 1), round(portfolio_avg, 1)]
            bench_colors = [
                "#ef4444" if delay_days > portfolio_avg else "#22c55e",
                "#f59e0b",
                "#3b82f6"
            ]
            fig_bc = go.Figure(go.Bar(
                x=bench_labels, y=bench_vals,
                marker_color=bench_colors,
                text=[f"{v:.1f} d" for v in bench_vals],
                textposition="outside",
                width=0.4
            ))
            fig_bc.update_layout(
                title="Delay Benchmarking",
                yaxis=dict(title="Days", **GRID),
                height=340, **PLOT_CFG
            )
            bc1.plotly_chart(fig_bc, use_container_width=True)

        with bc2:
            zl = (
                df.groupby("Zone", dropna=True)
                .agg(Total=("Site Name", "count"), Launched=("_launched", "sum"))
                .reset_index()
            )
            zl["Launch %"] = (zl["Launched"] / zl["Total"] * 100).round(1)
            bar_colors = ["#1e3a8a" if z == zone_s else "#93c5fd" for z in zl["Zone"]]

            fig_zl = go.Figure(go.Bar(
                x=zl["Zone"], y=zl["Launch %"],
                marker_color=bar_colors,
                text=zl["Launch %"].apply(lambda v: f"{v:.1f}%"),
                textposition="outside"
            ))
            fig_zl.update_layout(
                title=f"Launch % by Zone  (this store's zone highlighted: {zone_s})",
                yaxis=dict(title="Launch %", range=[0, 115], **GRID),
                height=340, **PLOT_CFG
            )
            bc2.plotly_chart(fig_zl, use_container_width=True)

    elif not query:
        st.info("👆 Type a store name above to view its full profile, timeline, and analytics.")

    #
    # SECTION B — CUSTOM PLOT BUILDER
    #
    st.divider()
    st.markdown("### 🎛️ Custom Parameter Plot Builder")
    st.caption(
        "Select any metric and dimension — all figures are aggregated correctly per group. "
        "Results update instantly."
    )

    # Available metrics → internal key
    METRICS = {
        "Count of Sites":           "count",
        "Launched Sites (count)":   "launched",
        "Pending Sites (count)":    "pending",
        "Launch % (per group)":     "launch_pct",
        "Delayed Sites (count)":    "delayed",
        "Delay Rate % (per group)": "delay_pct",
        "Avg Delay — Days":         "avg_delay",
        "Total Delay — Days":       "total_delay",
    }

    # Available dimensions
    cat_dims  = [c for c in df.select_dtypes(include=["object"]).columns
                 if c not in ("Site Name", "LAUNCHED / YTL") and df[c].nunique() <= 50]
    time_dims = [c for c in ("Planned (Month) Bucket", "Actual (Month) Bucket")
                 if c in df.columns]
    all_dims  = cat_dims + time_dims

    pb1, pb2, pb3, pb4 = st.columns([3, 3, 2, 2])
    with pb1:
        metric_sel = st.selectbox("Metric (Y-Axis)", list(METRICS.keys()), key="pb_metric")
    with pb2:
        dim_sel    = st.selectbox("Group By (X-Axis)", all_dims, key="pb_dim") if all_dims else None
    with pb3:
        chart_sel  = st.selectbox("Chart Type",
                                  ["Bar", "Horizontal Bar", "Pie", "Treemap", "Line"],
                                  key="pb_chart")
    with pb4:
        sort_order = st.selectbox("Sort By", ["Value (↓ High→Low)", "Value (↑ Low→High)", "Label (A→Z)"],
                                  key="pb_sort")

    if dim_sel:
        mtype = METRICS[metric_sel]
        grp   = df.groupby(dim_sel, dropna=True)

        # ── Aggregations (all mathematically correct)
        if mtype == "count":
            agg = grp.size().reset_index(name="Value")

        elif mtype == "launched":
            agg = grp["_launched"].sum().reset_index(name="Value")

        elif mtype == "pending":
            agg = grp["_pending"].sum().reset_index(name="Value")

        elif mtype == "launch_pct":
            tmp = grp.agg(
                Total=("Site Name",  "count"),
                Launched=("_launched", "sum")
            ).reset_index()
            tmp["Value"] = (tmp["Launched"] / tmp["Total"] * 100).round(2)
            agg = tmp[[dim_sel, "Value"]]

        elif mtype == "delayed":
            agg = grp["Is Delayed"].sum().reset_index(name="Value")

        elif mtype == "delay_pct":
            tmp = grp.agg(
                Total=("Site Name",    "count"),
                Delayed=("Is Delayed", "sum")
            ).reset_index()
            tmp["Value"] = (tmp["Delayed"] / tmp["Total"] * 100).round(2)
            agg = tmp[[dim_sel, "Value"]]

        elif mtype == "avg_delay":
            agg = grp["Delay (Days)"].mean().reset_index(name="Value")
            agg["Value"] = agg["Value"].round(1)

        elif mtype == "total_delay":
            agg = grp["Delay (Days)"].sum().reset_index(name="Value")

        agg = agg.dropna(subset=["Value"])

        # ── Sort
        if sort_order == "Value (↓ High→Low)":
            agg = agg.sort_values("Value", ascending=False)
        elif sort_order == "Value (↑ Low→High)":
            agg = agg.sort_values("Value", ascending=True)
        else:
            agg = agg.sort_values(dim_sel)

        title_str = f"{metric_sel} by {dim_sel}"

        # ── Chart generation
        if chart_sel == "Bar":
            fig_cp = px.bar(
                agg, x=dim_sel, y="Value",
                color="Value", color_continuous_scale="Blues",
                text=agg["Value"].apply(lambda v: f"{v:,.1f}"),
                labels={"Value": metric_sel},
                title=title_str
            )
            fig_cp.update_traces(textposition="outside")
            fig_cp.update_layout(coloraxis_showscale=False)

        elif chart_sel == "Horizontal Bar":
            fig_cp = px.bar(
                agg, y=dim_sel, x="Value", orientation="h",
                color="Value", color_continuous_scale="Blues",
                text=agg["Value"].apply(lambda v: f"{v:,.1f}"),
                labels={"Value": metric_sel},
                title=title_str
            )
            fig_cp.update_traces(textposition="outside")
            fig_cp.update_layout(coloraxis_showscale=False)

        elif chart_sel == "Pie":
            fig_cp = px.pie(
                agg, names=dim_sel, values="Value",
                title=title_str,
                hole=0.35   # donut style
            )

        elif chart_sel == "Treemap":
            fig_cp = px.treemap(
                agg, path=[dim_sel], values="Value",
                color="Value", color_continuous_scale="Blues",
                labels={"Value": metric_sel},
                title=title_str
            )

        elif chart_sel == "Line":
            fig_cp = px.line(
                agg, x=dim_sel, y="Value",
                markers=True,
                labels={"Value": metric_sel},
                title=title_str
            )

        fig_cp.update_layout(
            height=460,
            xaxis=GRID,
            yaxis=GRID,
            **PLOT_CFG
        )
        st.plotly_chart(fig_cp, use_container_width=True)

        with st.expander("📊 View underlying aggregated data table"):
            st.dataframe(agg.reset_index(drop=True), use_container_width=True, hide_index=True)
    else:
        st.info("No suitable categorical columns detected in the uploaded file.")


#
# TAB 4 — DELAY ANALYSIS
#
with tab4:
    st.markdown("### ⚠️ Delay Analysis")
    st.caption("Filter by any dimension to drill into delayed sites. Table is sorted by delay severity.")

    f1, f2, f3, f4 = st.columns(4)
    z_opts   = ["All"] + sorted(df["Zone"].dropna().unique().tolist())
    pm_opts  = ["All"] + sorted(df["PM"].dropna().unique().tolist())
    st_opts  = (["All"] + sorted(df["State"].dropna().unique().tolist())
                if "State" in df.columns else ["All"])
    s_opts   = ["All", "LAUNCHED", "YTL"]

    zone_f   = f1.selectbox("Zone",   z_opts,  key="da_z")
    pm_f     = f2.selectbox("PM",     pm_opts, key="da_pm")
    state_f  = f3.selectbox("State",  st_opts, key="da_s") if "State" in df.columns else "All"
    status_f = f4.selectbox("Status", s_opts,  key="da_st")

    fdf = df.copy()
    if zone_f   != "All": fdf = fdf[fdf["Zone"] == zone_f]
    if pm_f     != "All": fdf = fdf[fdf["PM"]   == pm_f]
    if "State" in df.columns and state_f != "All":
        fdf = fdf[fdf["State"] == state_f]
    if status_f != "All":
        fdf = fdf[fdf["_launched"] == (status_f == "LAUNCHED")]

    dm1, dm2, dm3, dm4 = st.columns(4)
    dm1.metric("Sites in Filter",      len(fdf))
    dm2.metric("Delayed in Filter",    int(fdf["Is Delayed"].sum()))
    filt_delay_pct = round(fdf["Is Delayed"].mean() * 100, 1) if len(fdf) else 0
    dm3.metric("Delay Rate (Filter)",  f"{filt_delay_pct}%")
    filt_avg = fdf.loc[fdf["Is Delayed"], "Delay (Days)"].mean()
    dm4.metric("Avg Delay (Filter)",   f"{filt_avg:.1f} d" if not pd.isna(filt_avg) else "0 d")

    st.divider()

    show_cols = [c for c in [
        "Site Name", "Zone", "State", "PM",
        "Planned Finish Date", "Actual Finish Date", "Forecasted Finish Date",
        "Delay (Days)", "LAUNCHED / YTL"
    ] if c in fdf.columns]

    delayed_fdf = fdf[fdf["Is Delayed"]].sort_values("Delay (Days)", ascending=False)

    if delayed_fdf.empty:
        st.success("✅ No delayed sites for the selected filters.")
    else:
        st.markdown(f"##### {len(delayed_fdf)} delayed site(s)")
        st.dataframe(
            delayed_fdf[show_cols].reset_index(drop=True),
            use_container_width=True,
            height=380,
            column_config={
                "Delay (Days)":           st.column_config.NumberColumn("Delay (Days)", format="%d d"),
                "Planned Finish Date":    st.column_config.DateColumn(),
                "Actual Finish Date":     st.column_config.DateColumn(),
                "Forecasted Finish Date": st.column_config.DateColumn(),
            }
        )

        # Delay distribution
        mean_d = delayed_fdf["Delay (Days)"].mean()
        med_d  = delayed_fdf["Delay (Days)"].median()
        fig_hist = px.histogram(
            delayed_fdf, x="Delay (Days)", nbins=25,
            color_discrete_sequence=["#ef4444"],
            title="Distribution of Delay Days — Delayed Sites in Current Filter",
            labels={"Delay (Days)": "Delay (Days)", "count": "Number of Sites"}
        )
        fig_hist.add_vline(x=mean_d, line_dash="dash", line_color="#1e3a8a",
                           annotation_text=f"Mean: {mean_d:.0f} d",
                           annotation_position="top right")
        fig_hist.add_vline(x=med_d,  line_dash="dot",  line_color="#6366f1",
                           annotation_text=f"Median: {med_d:.0f} d",
                           annotation_position="top left")
        fig_hist.update_layout(height=340, yaxis=GRID, **PLOT_CFG)
        st.plotly_chart(fig_hist, use_container_width=True)

        # Download
        csv_data = delayed_fdf[show_cols].to_csv(index=False)
        st.download_button(
            "📥 Download Delayed Sites Report (.csv)",
            data=csv_data, file_name="delayed_sites_report.csv", mime="text/csv"
        )


#
# TAB 7 — AI SUMMARY
#
with tab7:
    st.markdown("### 🤖 AI Executive Summary Generator")
    st.caption("Powered by Groq LLaMA-3.3-70B · Generates a management-ready briefing from live project data.")

    ai1, ai2 = st.columns([2, 1])
    with ai2:
        tone      = st.selectbox("Report Tone", [
            "Executive (concise)", "Detailed analysis", "Risk-focused"
        ])
        incl_recs = st.checkbox("Include recommended actions", value=True)
    with ai1:
        extra = st.text_area(
            "Additional context (optional)",
            placeholder="e.g., Q2 target is 80 launches. Board review on Friday.",
            height=100
        )

    if st.button("⚡ Generate Executive Summary", type="primary"):
        top5 = (
            df[df["Is Delayed"]][["Site Name", "Zone", "PM", "Delay (Days)"]]
            .sort_values("Delay (Days)", ascending=False)
            .head(5)
            .to_string(index=False)
        )
        zone_tbl = (
            df.groupby("Zone", dropna=True)
            .agg(
                Total=("Site Name",    "count"),
                Launched=("_launched", "sum"),
                Delayed=("Is Delayed", "sum"),
                Avg_Delay=("Delay (Days)", "mean")
            )
            .round(1)
            .to_string()
        )
        pm_tbl = (
            df.groupby("PM", dropna=True)
            .agg(
                Total=("Site Name",    "count"),
                Launched=("_launched", "sum"),
                Delayed=("Is Delayed", "sum")
            )
            .to_string()
        )

        tone_map = {
            "Executive (concise)":
                "Be concise. Max 3 sentences per paragraph. Use executive-level language only.",
            "Detailed analysis":
                "Be thorough. Include specific data points, trends, and PM-level analysis.",
            "Risk-focused":
                "Focus on risks, blockers, and mitigation. Flag items that need escalation explicitly."
        }

        prompt = f"""You are a senior project reporting analyst for an EPC team at a large retail chain.

Live Project Data (as of today):
- Total Sites: {total} | Launched: {launched} ({launch_pct}%) | YTL: {ytl}
- Total Delayed: {delayed} ({delay_pct}% of portfolio) | On-Time: {on_time} of {launched} launched
- Avg Delay (delayed sites only): {avg_delay:.0f} days

Zone-Wise Summary:
{zone_tbl}

PM Portfolio Summary:
{pm_tbl}

Top 5 Critical Delay Sites:
{top5}

Additional Context: {extra if extra.strip() else 'None provided.'}

Report Style: {tone_map[tone]}

Task: Write a professional 2-paragraph executive summary for today's management review meeting.
Paragraph 1: Overall project health, progress against plan, and key achievements.
Paragraph 2: Risks, delay patterns by zone/PM, and {"three specific recommended actions with named owners (PM names)" if incl_recs else "the top risk areas requiring leadership attention"}.
Be direct, data-driven, specific. No filler language. No preamble."""

        try:
            from groq import Groq
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            with st.spinner("Generating executive summary…"):
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=650
                )
            summary = resp.choices[0].message.content.strip()

            st.divider()
            st.markdown("#### 📄 Executive Summary")
            st.markdown(f"""
            <div style="background:#f8fafc; border-left:4px solid #1e3a8a;
                        border-radius:0 12px 12px 0; padding:22px 26px;
                        font-size:0.95rem; line-height:1.85; color:#1e293b;
                        box-shadow:0 1px 6px rgba(0,0,0,0.06);">
              {summary.replace(chr(10), "<br>")}
            </div>""", unsafe_allow_html=True)

            st.download_button(
                "📥 Download as .txt", data=summary,
                file_name="executive_summary.txt", mime="text/plain"
            )
        except Exception as e:
            st.error(f"AI call failed: {e}")
            st.info("Set `GROQ_API_KEY` in `.streamlit/secrets.toml` to enable AI summaries.")



#
# TAB 3 — SITE DIRECTORY
#
with tab3:
    st.markdown("### 🏪 Site Directory")
    st.caption("Browse all sites. Click any site to expand its full profile and inspection history.")

    # Filters
    sd1, sd2, sd3 = st.columns(3)
    dir_zone   = sd1.selectbox("Zone",   ["All"] + sorted(df["Zone"].dropna().unique().tolist()),   key="dir_z")
    dir_status = sd2.selectbox("Status", ["All", "LAUNCHED", "YTL"],                                key="dir_s")
    dir_search = sd3.text_input("Search Site Name", placeholder="Type to filter…",                  key="dir_q")

    dir_df = df.copy()
    if dir_zone   != "All": dir_df = dir_df[dir_df["Zone"] == dir_zone]
    if dir_status != "All": dir_df = dir_df[dir_df["LAUNCHED / YTL"] == dir_status]
    if dir_search:          dir_df = dir_df[dir_df["Site Name"].str.contains(dir_search, case=False, na=False)]

    dir_df = dir_df.sort_values("Delay (Days)", ascending=False)
    st.markdown(f"Showing **{len(dir_df)}** site(s)")

    for _, row in dir_df.iterrows():
        s_icon     = "✅" if row.get("LAUNCHED / YTL") == "LAUNCHED" else "🔄"
        delay_days = int(row.get("Delay (Days)", 0))
        delay_txt  = f"⚠️ {delay_days}d delayed" if delay_days > 0 else "✅ On track"
        label      = f"{s_icon}  {row['Site Name']}  ·  {row.get('City','—')}  ·  {row.get('Zone','—')}  ·  {delay_txt}"

        with st.expander(label):
            c1, c2, c3 = st.columns(3)

            with c1:
                st.markdown("**📍 Location**")
                st.write(f"Zone: {row.get('Zone','—')}")
                st.write(f"State: {row.get('State','—')}")
                st.write(f"City: {row.get('City','—')}")
                st.write(f"Cluster: {row.get('Cluster','—')}")
                st.write(f"Area: {row.get('Area (Sqft)','—')} sqft")

            with c2:
                st.markdown("**👥 Team**")
                st.write(f"PM Head: {row.get('PM Head','—')}")
                st.write(f"PM: {row.get('PM','—')}")
                st.write(f"Planner: {row.get('PM Planner','—')}")
                st.write(f"EIC: {row.get('EIC','—')}")
                st.write(f"ZH: {row.get('ZH','—')}")

            with c3:
                st.markdown("**📅 Dates & Status**")
                st.write(f"Planned Finish: {str(row.get('Planned Finish Date','—'))[:10]}")
                st.write(f"Actual Finish:  {str(row.get('Actual Finish Date','—'))[:10]}")
                st.write(f"Forecasted:     {str(row.get('Forecasted Finish Date','—'))[:10]}")
                st.write(f"Delay: **{delay_days} days**")
                st.write(f"Status: **{row.get('LAUNCHED / YTL','—')}**")
                st.write(f"FY: {row.get('FY','—')}  |  {row.get('AOP / NON AOP','—')}")

            # Inspection history from Supabase
            if DB_OK:
                st.markdown("---")
                st.markdown("**🔍 Inspection History**")
                try:
                    insp_res = sb.table("inspections").select("id, zonal_head, inspection_date, inspection_time, notes").eq("site_name", row["Site Name"]).order("inspection_date", desc=True).execute()
                    if insp_res.data:
                        for insp in insp_res.data:
                            st.markdown(f"📅 **{insp['inspection_date']}** at {insp['inspection_time']} — ZH: *{insp['zonal_head']}*")
                            if insp.get("notes"):
                                st.markdown(f"> {insp['notes']}")
                            # Issues for this inspection
                            iss_res = sb.table("issues").select("issue_description, severity, status").eq("inspection_id", insp["id"]).execute()
                            if iss_res.data:
                                for iss in iss_res.data:
                                    sev_icon = {"Low":"🟡","Medium":"🟠","High":"🔴","Critical":"🚨"}.get(iss["severity"],"⚪")
                                    done_icon = "✅" if iss["status"] == "Resolved" else "🔴"
                                    st.markdown(f"&nbsp;&nbsp;&nbsp;{done_icon} {sev_icon} {iss['issue_description']} — *{iss['severity']}* — **{iss['status']}**")
                    else:
                        st.info("No inspections recorded yet for this site.")
                except Exception as e:
                    st.warning(f"Could not load inspections: {e}")


#
# TAB 5 — INSPECTION LOG
#
with tab5:
    st.markdown("### 📋 Inspection Log")
    st.caption("Zonal heads log site visits, observations, and flag issues.")

    if not DB_OK:
        st.error(f"Database not connected: {DB_ERROR}")
        st.info("Check SUPABASE_URL and SUPABASE_KEY in Streamlit secrets.")
        st.stop()

    site_list = sorted(df["Site Name"].dropna().unique().tolist())

    with st.form("inspection_form", clear_on_submit=True):
        st.markdown("#### Log New Inspection")

        if1, if2 = st.columns(2)
        insp_site = if1.selectbox("Site Name", site_list, key="if_site")
        insp_zh   = if2.text_input("Zonal Head Name", placeholder="Enter your name")

        id1, id2 = st.columns(2)
        insp_date = id1.date_input("Inspection Date", value=date_type.today())
        insp_time = id2.time_input("Inspection Time")

        insp_notes = st.text_area("General Observations / Notes",
                                   placeholder="Overall site condition, progress, concerns…", height=100)

        st.markdown("#### Issues Found During Inspection")
        st.caption("Leave blank if no issue. Add up to 6.")

        issues_to_save = []
        for i in range(6):
            ic1, ic2 = st.columns([4, 1])
            i_desc = ic1.text_input(f"Issue {i+1}", placeholder=f"Describe issue {i+1}…", key=f"idesc_{i}")
            i_sev  = ic2.selectbox("Severity", ["Low","Medium","High","Critical"], key=f"isev_{i}")
            if i_desc.strip():
                issues_to_save.append({"description": i_desc.strip(), "severity": i_sev})

        submitted = st.form_submit_button("✅ Submit Inspection", type="primary")

        if submitted:
            if not insp_zh.strip():
                st.error("Please enter the Zonal Head name.")
            else:
                try:
                    insp_payload = {
                        "site_name":       insp_site,
                        "zonal_head":      insp_zh.strip(),
                        "inspection_date": str(insp_date),
                        "inspection_time": str(insp_time),
                        "notes":           insp_notes.strip()
                    }
                    result = sb.table("inspections").insert(insp_payload).execute()
                    insp_id = result.data[0]["id"]

                    for iss in issues_to_save:
                        sb.table("issues").insert({
                            "inspection_id":     insp_id,
                            "issue_description": iss["description"],
                            "severity":          iss["severity"],
                            "status":            "Open"
                        }).execute()

                    st.success(f"✅ Inspection logged for **{insp_site}**. {len(issues_to_save)} issue(s) recorded.")
                except Exception as e:
                    st.error(f"Failed to save: {e}")

    # Recent inspections table
    st.divider()
    st.markdown("#### Recent Inspections")
    try:
        recent = sb.table("inspections").select("site_name, zonal_head, inspection_date, inspection_time, notes").order("created_at", desc=True).limit(30).execute()
        if recent.data:
            st.dataframe(pd.DataFrame(recent.data), use_container_width=True, hide_index=True)
        else:
            st.info("No inspections logged yet.")
    except Exception as e:
        st.warning(f"Could not load recent inspections: {e}")


#
# TAB 6 — ISSUE TRACKER
#
with tab6:
    st.markdown("### ✅ Issue Tracker & Engineer Checklist")
    st.caption("Site engineers view issues flagged during inspections and mark them resolved.")

    if not DB_OK:
        st.error(f"Database not connected: {DB_ERROR}")
        st.info("Check SUPABASE_URL and SUPABASE_KEY in Streamlit secrets.")
        st.stop()

    site_list2 = sorted(df["Site Name"].dropna().unique().tolist())
    it_site = st.selectbox("Select Your Site", site_list2, key="it_site")

    try:
        insp_for_site = sb.table("inspections").select("id, zonal_head, inspection_date, notes").eq("site_name", it_site).order("inspection_date", desc=True).execute()

        if not insp_for_site.data:
            st.info("No inspections recorded for this site yet.")
        else:
            all_issues = []
            for insp in insp_for_site.data:
                iss = sb.table("issues").select("*").eq("inspection_id", insp["id"]).execute()
                for issue in iss.data:
                    issue["inspection_date"] = insp["inspection_date"]
                    issue["zonal_head"]      = insp["zonal_head"]
                    all_issues.append(issue)

            open_issues     = [i for i in all_issues if i["status"] == "Open"]
            resolved_issues = [i for i in all_issues if i["status"] == "Resolved"]

            # Summary metrics
            im1, im2, im3 = st.columns(3)
            im1.metric("Total Issues",    len(all_issues))
            im2.metric("Open",            len(open_issues),     delta=f"{len(open_issues)} need action", delta_color="inverse")
            im3.metric("Resolved",        len(resolved_issues), delta=f"{len(resolved_issues)} done",    delta_color="normal")

            st.divider()

            if open_issues:
                st.markdown("#### 🔴 Open Issues — Action Required")
                for iss in sorted(open_issues, key=lambda x: ["Critical","High","Medium","Low"].index(x.get("severity","Low"))):
                    sev_icon  = {"Low":"🟡","Medium":"🟠","High":"🔴","Critical":"🚨"}.get(iss["severity"],"⚪")
                    rc1, rc2, rc3 = st.columns([4, 1, 1])
                    rc1.markdown(f"{sev_icon} **{iss['issue_description']}**  \n*Flagged by {iss['zonal_head']} on {iss['inspection_date']}*")
                    rc2.markdown(f"**{iss['severity']}**")
                    if rc3.button("Mark Resolved ✅", key=f"res_{iss['id']}"):
                        sb.table("issues").update({"status": "Resolved"}).eq("id", iss["id"]).execute()
                        st.rerun()
            else:
                st.success("✅ All issues resolved for this site.")

            if resolved_issues:
                with st.expander(f"✅ {len(resolved_issues)} Resolved Issue(s)"):
                    for iss in resolved_issues:
                        st.markdown(f"✅ ~~{iss['issue_description']}~~ · *{iss['zonal_head']}* · {iss['inspection_date']}")

    except Exception as e:
        st.error(f"Could not load issues: {e}")


# ─── FOOTER
st.divider()
st.caption(
    "EPC Site Launch Tracker &nbsp;·&nbsp; Built with Streamlit & Plotly "
    "&nbsp;·&nbsp; Data accurate as of upload time &nbsp;·&nbsp; Internal use only"
)
