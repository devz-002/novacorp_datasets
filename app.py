"""NovaCorp workforce analytics dashboard.

Interactive rebuild of notebooks/01_EDA.ipynb: headcount & tenure, attrition
patterns, engagement signals, and performance/compensation, filterable by
department. Run locally with `streamlit run app.py`.
"""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_utils import (
    RATING_ORDER, SCORE_COLS, attrition_rate, filter_by_department,
    load_raw, overall_attrition_rate,
)

# ---------------------------------------------------------------- palette --
CATEGORICAL = [
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
    "#e87ba4", "#008300", "#4a3aa7", "#e34948",
]
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = CATEGORICAL
ORDINAL_BLUE = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
GRIDLINE = "#e1e0d9"
AXIS = "#c3c2b7"
MUTED = "#898781"

st.set_page_config(page_title="NovaCorp Workforce Analytics", layout="wide")


def style_fig(fig, height=380, showlegend=False):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color="#0b0b0b"),
        margin=dict(l=10, r=10, t=40, b=10),
        height=height,
        showlegend=showlegend,
        hoverlabel=dict(bgcolor="#fcfcfb", font_color="#0b0b0b"),
    )
    fig.update_xaxes(gridcolor=GRIDLINE, zerolinecolor=AXIS, linecolor=AXIS)
    fig.update_yaxes(gridcolor=GRIDLINE, zerolinecolor=AXIS, linecolor=AXIS)
    return fig


# --------------------------------------------------------------- load data --
emp, att, eng, perf = load_raw()

st.sidebar.title("Filters")
departments = sorted(emp["department"].dropna().unique())
selected_depts = st.sidebar.multiselect("Department", departments, default=departments)

emp_f, att_f, eng_f, perf_f = filter_by_department(emp, att, eng, perf, selected_depts)

st.title("NovaCorp Workforce Analytics")
st.caption(
    "Interactive companion to notebooks/01_EDA.ipynb — headcount, attrition, "
    "engagement and performance signals behind the FY2025 annual report."
)

if len(emp_f) == 0:
    st.warning("No employees match the selected filters.")
    st.stop()

# ------------------------------------------------------------------- KPIs --
overall_rate = overall_attrition_rate(emp_f)
active_headcount = int((emp_f["status"] == "active").sum())
avg_tenure_years = (emp_f["tenure_months"] / 12).mean()
regrettable_share = att_f["regrettable_flag"].mean() * 100 if len(att_f) else 0.0
avg_compa = emp_f["compa_ratio"].mean()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Active headcount", f"{active_headcount:,}")
k2.metric("Overall attrition rate", f"{overall_rate:.1f}%")
k3.metric("Avg tenure", f"{avg_tenure_years:.1f} yrs")
k4.metric("Regrettable exits", f"{regrettable_share:.0f}% of leavers")
k5.metric("Avg compa-ratio", f"{avg_compa:.2f}")

tab_workforce, tab_attrition, tab_engagement, tab_perf, tab_takeaways = st.tabs(
    ["Workforce", "Attrition", "Engagement", "Performance & Comp", "Takeaways"]
)

# --------------------------------------------------------------- Workforce --
with tab_workforce:
    st.subheader("Who works at NovaCorp")
    col1, col2 = st.columns(2)

    with col1:
        dept_counts = emp_f["department"].value_counts().sort_values()
        fig = go.Figure(go.Bar(
            x=dept_counts.values, y=dept_counts.index, orientation="h",
            marker_color=BLUE,
            hovertemplate="%{y}: %{x} employees<extra></extra>",
        ))
        fig.update_layout(title="Headcount by department", xaxis_title="Employees")
        st.plotly_chart(style_fig(fig), use_container_width=True)

    with col2:
        fig = px.histogram(
            emp_f, x=emp_f["tenure_months"] / 12, nbins=30,
            color_discrete_sequence=[BLUE],
        )
        fig.update_layout(
            title="Tenure distribution (years)",
            xaxis_title="Years at NovaCorp", yaxis_title="Employees",
        )
        fig.update_traces(hovertemplate="%{x:.1f} yrs: %{y} employees<extra></extra>")
        st.plotly_chart(style_fig(fig), use_container_width=True)

# --------------------------------------------------------------- Attrition --
with tab_attrition:
    st.subheader("Attrition patterns")
    st.caption(
        "Where is attrition concentrated, and does it match the FY2025 annual "
        "report's Entity_B integration risk and Risk & Compliance talent-loss claims?"
    )
    col1, col2 = st.columns(2)

    with col1:
        rate_by_dept = attrition_rate(emp_f, "department").sort_values()
        fig = go.Figure(go.Bar(
            x=rate_by_dept.values, y=rate_by_dept.index, orientation="h",
            marker_color=RED,
            hovertemplate="%{y}: %{x:.1f}%% departed<extra></extra>",
        ))
        fig.add_vline(x=overall_rate, line_dash="dash", line_color=MUTED,
                       annotation_text=f"firm avg {overall_rate:.1f}%")
        fig.update_layout(title="Attrition rate by department", xaxis_title="% departed")
        st.plotly_chart(style_fig(fig), use_container_width=True)

    with col2:
        rate_by_cohort = attrition_rate(emp_f, "legacy_entity_code").sort_values()
        fig = go.Figure(go.Bar(
            x=rate_by_cohort.values, y=rate_by_cohort.index, orientation="h",
            marker_color=ORANGE,
            hovertemplate="%{y}: %{x:.1f}%% departed<extra></extra>",
        ))
        fig.add_vline(x=overall_rate, line_dash="dash", line_color=MUTED,
                       annotation_text=f"firm avg {overall_rate:.1f}%")
        fig.update_layout(title="Attrition rate by acquisition cohort", xaxis_title="% departed")
        st.plotly_chart(style_fig(fig), use_container_width=True)

    rc = emp_f[emp_f["department"] == "Risk & Compliance"]
    if len(rc):
        rc_by_level = attrition_rate(rc, "role_level").sort_index()
        fig = go.Figure(go.Bar(
            x=[str(x) for x in rc_by_level.index], y=rc_by_level.values,
            marker_color=RED,
            hovertemplate="Level %{x}: %{y:.1f}%% departed<extra></extra>",
        ))
        fig.update_layout(
            title="Risk & Compliance attrition by role level",
            xaxis_title="Role level", yaxis_title="% departed",
        )
        st.plotly_chart(style_fig(fig, height=340), use_container_width=True)

    st.markdown("**Exit characteristics** (departed employees in the current filter)")
    c1, c2, c3 = st.columns(3)
    if len(att_f):
        for col, field, color, title in [
            (c1, "exit_type", BLUE, "Exit type"),
            (c2, "pathway", AQUA, "Pathway (push = left for a reason here, pull = left for elsewhere)"),
            (c3, "regrettable_flag", RED, "Regrettable exit?"),
        ]:
            counts = att_f[field].astype(str).value_counts()
            fig = go.Figure(go.Bar(
                x=counts.index, y=counts.values, marker_color=color,
                hovertemplate="%{x}: %{y}<extra></extra>",
            ))
            fig.update_layout(title=title)
            col.plotly_chart(style_fig(fig, height=320), use_container_width=True)
    else:
        st.info("No leavers in the current filter.")

# -------------------------------------------------------------- Engagement --
with tab_engagement:
    st.subheader("Engagement signals")
    st.caption(
        'The CEO letter calls out survey non-responders as a population "our '
        'data suggests is disproportionately at flight risk."'
    )

    trend = eng_f[eng_f["response_flag"]].groupby("wave_number")[SCORE_COLS].mean()
    if len(trend):
        fig = go.Figure()
        for i, col in enumerate(SCORE_COLS):
            fig.add_trace(go.Scatter(
                x=trend.index, y=trend[col], mode="lines+markers",
                name=col.replace("_", " ").title(),
                line=dict(color=CATEGORICAL[i % len(CATEGORICAL)], width=2),
                marker=dict(size=8),
                hovertemplate="%{y:.2f}<extra>" + col.replace("_", " ").title() + "</extra>",
            ))
        fig.update_layout(
            title="Engagement scores by wave (respondents only)",
            xaxis_title="Wave", yaxis_title="Average score (1-5)",
            hovermode="x unified",
        )
        st.plotly_chart(style_fig(fig, height=460, showlegend=True), use_container_width=True)
    else:
        st.info("No engagement responses in the current filter.")

    attrition_by_responder = attrition_rate(emp_f, "low_responder")
    labels = {False: "Regular responder", True: "Low/non-responder (<50%)"}
    fig = go.Figure(go.Bar(
        x=[labels.get(i, str(i)) for i in attrition_by_responder.index],
        y=attrition_by_responder.values,
        marker_color=[BLUE, RED] if len(attrition_by_responder) == 2 else BLUE,
        text=[f"{v:.1f}%" for v in attrition_by_responder.values],
        textposition="outside",
        hovertemplate="%{x}: %{y:.1f}%% departed<extra></extra>",
    ))
    fig.update_layout(
        title="Attrition rate: survey responders vs non-responders",
        yaxis_title="% departed",
    )
    st.plotly_chart(style_fig(fig, height=380), use_container_width=True)

# -------------------------------------------------------- Performance/Comp --
with tab_perf:
    st.subheader("Performance & compensation")
    st.caption(
        "Compensation compression for high-potential employees, and whether "
        "performance/promotion signals relate to attrition."
    )
    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        for flag, color, label in [(False, BLUE, "Not HiPo"), (True, ORANGE, "HiPo")]:
            subset = emp_f.loc[emp_f["hipo_flag"] == flag, "compa_ratio"].dropna()
            fig.add_trace(go.Box(
                y=subset, name=label, marker_color=color,
                boxmean=True,
            ))
        fig.update_layout(
            title="Compa-ratio: high-potential vs rest of workforce",
            yaxis_title="Compa-ratio (1.0 = at role midpoint)",
        )
        st.plotly_chart(style_fig(fig, height=420), use_container_width=True)

    with col2:
        rate_by_rating = attrition_rate(emp_f, "performance_rating").reindex(RATING_ORDER)
        fig = go.Figure(go.Bar(
            x=RATING_ORDER, y=rate_by_rating.values,
            marker_color=ORDINAL_BLUE,
            hovertemplate="%{x}: %{y:.1f}%% departed<extra></extra>",
        ))
        fig.update_layout(
            title="Attrition rate by most recent performance rating",
            yaxis_title="% departed",
        )
        st.plotly_chart(style_fig(fig, height=420), use_container_width=True)

# --------------------------------------------------------------- Takeaways --
with tab_takeaways:
    st.subheader("Takeaways for initial mentor meeting")

    rate_by_cohort_all = attrition_rate(emp_f, "legacy_entity_code")
    entity_b = rate_by_cohort_all.get("Entity_B", float("nan"))
    origin = rate_by_cohort_all.get("NovaCorp-Origin", float("nan"))

    rc_all = emp_f[emp_f["department"] == "Risk & Compliance"]
    rc_dept_rate = overall_attrition_rate(rc_all) if len(rc_all) else float("nan")
    rc_l4 = rc_all[rc_all["role_level"] == 4]
    rc_l4_rate = overall_attrition_rate(rc_l4) if len(rc_l4) else float("nan")

    resp_rates = attrition_rate(emp_f, "low_responder")
    resp_rate_val = resp_rates.get(False, float("nan"))
    nonresp_rate_val = resp_rates.get(True, float("nan"))

    compa_by_hipo = emp_f.groupby("hipo_flag")["compa_ratio"].mean()

    st.markdown(f"""
1. **Entity_B cohort:** ~{entity_b:.0f}% attrition compared to ~{origin:.0f}% in NovaCorp-Origin.
   Matches the annual report's "primary integration risk for FY2026."
2. **Risk & Compliance Director level (role_level 4):** spikes to ~{rc_l4_rate:.0f}%,
   vs ~{rc_dept_rate:.0f}% department-wide. Sharper than the report states — check sample size first
   ({len(rc_l4)} employees at that level in the current filter).
3. **Survey non-responders** leave at ~{nonresp_rate_val / resp_rate_val:.1f}x the rate of
   respondents ({nonresp_rate_val:.1f}% vs {resp_rate_val:.1f}%). A testable version of the
   CEO's "flight risk" claim.
4. **High-potential employees** show pay compression (compa-ratio {compa_by_hipo.get(True, float('nan')):.2f})
   vs the rest of the workforce ({compa_by_hipo.get(False, float('nan')):.2f}). Matches the
   report's "7-8 point compression" claim.
5. **Performance vs attrition** needs a clean read: are we losing low performers (managed exits)
   or high performers (regrettable loss)? Ties to `regrettable_flag`.

**Questions to ask:**
- Which of these causes is worth committing to for this project?
- Many of these causes are already outlined in the annual report by the CEO — is this a trap?
- Do the small-sample points (e.g. R&C Director level) hold up statistically?
- Is the current solution (People Investment Programme, $47M) targeting the right areas?
""")
