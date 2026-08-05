"""NovaCorp workforce analytics dashboard.

Interactive rebuild of notebooks/01_EDA.ipynb and the EDA.ipynb discovery
notebook: headcount & tenure, attrition patterns, engagement / non-responder
signals, and performance & compensation, all drillable through a shared set
of global filters. Run locally with `streamlit run app.py`.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_utils import (
    AGE_BAND_ORDER, ATTRITION_GROUP_OPTIONS, COMPA_BUCKET_ORDER,
    COMPENSATION_GROUP_OPTIONS, ENGAGEMENT_GROUP_OPTIONS, FILTER_SPECS,
    PRIMARY_FILTER_COLS, RATING_ORDER, SCORE_COLS, TENURE_BUCKET_ORDER,
    apply_filters, apply_response_choice, attrition_rate, build_full,
    filter_options, load_raw, nonresponder_lift, overall_attrition_rate,
    replacement_cost_range, slice_related,
)

from hypothesis_tabs import render_hypothesis_tab
from executive_story_tab import render_executive_story_tab
from flight_risk_tab import render_flight_risk_tab
 
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


# ------------------------------------------------------- reusable charts --
def attrition_bar(rate_series, title, xaxis_title="% departed", color=RED,
                   add_avg=None, order=None):
    """Horizontal bar of an attrition_rate() result. `order` pins a logical
    category order (e.g. tenure buckets); otherwise sorted by rate."""
    s = rate_series.dropna()
    s = s.reindex([o for o in order if o in s.index]) if order else s.sort_values()
    fig = go.Figure(go.Bar(
        x=s.values, y=[str(i) for i in s.index], orientation="h",
        marker_color=color,
        hovertemplate="%{y}: %{x:.1f}%% departed<extra></extra>",
    ))
    if add_avg is not None:
        fig.add_vline(x=add_avg, line_dash="dash", line_color=MUTED,
                       annotation_text=f"firm avg {add_avg:.1f}%")
    fig.update_layout(title=title, xaxis_title=xaxis_title)
    return fig


def count_bar(counts, title, color=BLUE, xaxis_title=None, yaxis_title="Count"):
    """Vertical bar of a value_counts() result."""
    fig = go.Figure(go.Bar(
        x=[str(i) for i in counts.index], y=counts.values, marker_color=color,
        hovertemplate="%{x}: %{y}<extra></extra>",
    ))
    fig.update_layout(title=title, xaxis_title=xaxis_title, yaxis_title=yaxis_title)
    return fig


def grouped_bar(categories, series_dict, title, yaxis_title="", colors=None):
    """Grouped (side-by-side) bar comparing 2+ series across categories."""
    colors = colors or CATEGORICAL
    fig = go.Figure()
    for i, (name, values) in enumerate(series_dict.items()):
        fig.add_trace(go.Bar(
            x=categories, y=values, name=name, marker_color=colors[i % len(colors)],
            hovertemplate="%{x}: %{y:.2f}<extra>" + name + "</extra>",
        ))
    fig.update_layout(title=title, yaxis_title=yaxis_title, barmode="group")
    return fig


def box_by_group(df, group_col, value_col, title, yaxis_title=None, order=None, colors=None):
    """Boxplot of value_col split by group_col (booleans shown as Yes/No)."""
    work = df[[group_col, value_col]].copy()
    if work[group_col].dtype == bool:
        work[group_col] = work[group_col].map({True: "Yes", False: "No"})
    colors = colors or CATEGORICAL
    cats = [o for o in order if o in set(work[group_col].dropna())] if order else sorted(
        work[group_col].dropna().unique(), key=str
    )
    fig = go.Figure()
    for i, cat in enumerate(cats):
        subset = work.loc[work[group_col] == cat, value_col].dropna()
        if len(subset) == 0:
            continue
        fig.add_trace(go.Box(y=subset, name=str(cat), marker_color=colors[i % len(colors)], boxmean=True))
    fig.update_layout(title=title, yaxis_title=yaxis_title or value_col.replace("_", " ").title())
    return fig


def heatmap_ct(df, row_col, col_col, title, row_order=None, col_order=None):
    """Crosstab heatmap of counts between two categorical columns."""
    import pandas as pd
    ct = pd.crosstab(df[row_col], df[col_col])
    if row_order:
        ct = ct.reindex([r for r in row_order if r in ct.index])
    if col_order:
        ct = ct[[c for c in col_order if c in ct.columns]]
    fig = go.Figure(go.Heatmap(
        z=ct.values, x=[str(c) for c in ct.columns], y=[str(r) for r in ct.index],
        colorscale=[[0, "#f5f4ef"], [1, BLUE]],
        hovertemplate="%{y} / %{x}: %{z}<extra></extra>",
        showscale=True,
    ))
    fig.update_layout(title=title)
    return fig


# --------------------------------------------------------------- load data --
emp, att, eng, perf = load_raw()
full = build_full(emp, att, eng, perf)

# ------------------------------------------------------------- Global Filters --
st.sidebar.title("Global Filters")


def _filter_opts(col):
    if col == "role_level":
        return filter_options(full, col), (lambda x: f"Level {x}")
    if full[col].dtype == bool:
        return [False, True], (lambda x: "Yes" if x else "No")
    order = {
        "age_band": AGE_BAND_ORDER, "tenure_bucket": TENURE_BUCKET_ORDER,
        "compa_bucket": COMPA_BUCKET_ORDER, "performance_rating": RATING_ORDER,
    }.get(col)
    return filter_options(full, col, order=order), str


def _render_filter(label, col):
    """Single-choice dropdown: either "All" (no filter) or exactly one value."""
    opts, fmt = _filter_opts(col)
    choices = ["All"] + list(opts)
    ms_key = f"filter_{col}"
    if ms_key not in st.session_state:
        st.session_state[ms_key] = "All"

    def _fmt(x):
        return "All" if x == "All" else fmt(x)

    choice = st.selectbox(label, choices, key=ms_key, format_func=_fmt)
    return opts if choice == "All" else [choice]


selections = {}
with st.sidebar:
    st.caption("PRIMARY FILTERS")
    for label, col in FILTER_SPECS:
        if col in PRIMARY_FILTER_COLS:
            selections[col] = _render_filter(label, col)

    response_choice = st.radio(
        "Survey Response", ["All", "Responders", "Non-Responders"], horizontal=True,
        help="Non-Responders = employees who never answered a single engagement survey wave.",
    )

    advanced_cols = [(l, c) for l, c in FILTER_SPECS if c not in PRIMARY_FILTER_COLS]
    with st.expander(f"Advanced filters ({len(advanced_cols)})", expanded=False):
        for label, col in advanced_cols:
            selections[col] = _render_filter(label, col)

full_f = apply_filters(full, selections)
full_f = apply_response_choice(full_f, response_choice)
att_f, eng_f, perf_f = slice_related(att, eng, perf, full_f["employee_id"])

st.title("NovaCorp Workforce Analytics")
st.caption(
    "Explore workforce trends across NovaCorp using interactive visualizations."
    " Analyse attrition, engagement, performance, compensation, and workforce composition"
    "by department, legacy entity, role level, and other employee segments"
)

if len(full_f) == 0:
    st.warning("No employees match the selected filters.")
    st.stop()

# ------------------------------------------------------------------- KPIs --
overall_rate = overall_attrition_rate(full_f)
active_headcount = int((full_f["status"] == "active").sum())
avg_tenure_years = (full_f["tenure_months"] / 12).mean()
regrettable_share = att_f["regrettable_flag"].mean() * 100 if len(att_f) else 0.0
avg_compa = full_f["compa_ratio"].mean()
avg_response_rate = full_f["survey_response_rate"].mean() * 100
avg_engagement = full_f["engagement_mean"].mean()
avg_goal_achievement = full_f["goal_achievement_score"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Headcount (selection)", f"{len(full_f):,}", help=f"{active_headcount:,} active")
k2.metric("Attrition rate", f"{overall_rate:.1f}%")
k3.metric("Avg tenure", f"{avg_tenure_years:.1f} yrs")
k4.metric("Regrettable exits", f"{regrettable_share:.0f}% of leavers")

k5, k6, k7, k8 = st.columns(4)
k5.metric("Avg compa-ratio", f"{avg_compa:.2f}" if avg_compa == avg_compa else "n/a")
k6.metric("Survey response rate", f"{avg_response_rate:.1f}%" if avg_response_rate == avg_response_rate else "n/a")
k7.metric("Avg engagement score", f"{avg_engagement:.2f}" if avg_engagement == avg_engagement else "n/a")
k8.metric("Avg goal achievement", f"{avg_goal_achievement:.1f}" if avg_goal_achievement == avg_goal_achievement else "n/a")

tab_exec, tab_flight_risk, tab_overview, tab_hypothesis, tab_takeaways = st.tabs(
    ["Executive Story", "Flight Risk Model", "Overview", "Hypothesis", "Takeaways"]
# tab_exec, tab_flight_risk, tab_workforce, tab_attrition, tab_engagement, tab_perf, tab_comp, tab_takeaways, tab_hypothesis = st.tabs(
#     ["Executive Story", "Flight Risk Model", "Workforce", "Attrition", "Engagement", "Performance", "Compensation", "Takeaways", "Hypothesis"]
)

# ---------------------------------------------------------- Executive Story --
with tab_exec:
    render_executive_story_tab(full, eng, style_fig, CATEGORICAL)
  
# ------------------------------------------------------- Flight Risk Model --
with tab_flight_risk:
    render_flight_risk_tab(full, style_fig, CATEGORICAL)

# ------------------------------------------------------------------- Overview --
# with tab_overview:
#     sub_workforce, sub_attrition, sub_engagement, sub_perf, sub_comp = st.tabs(
#         ["Workforce", "Attrition", "Engagement", "Performance", "Compensation"]


# --------------------------------------------------------------- Workforce --
with tab_workforce:
    st.subheader("Who works at NovaCorp")
    st.caption(
        f"Headcount, tenure and role composition for the {len(full_f):,} employees "
        "matching the current filters — the base population every other tab's "
        "attrition/engagement/performance rates are measured against."
    )

    # --------------------------------------------------------------- Workforce --
    with sub_workforce:
        st.subheader("Who works at NovaCorp")
        st.caption(
            f"Headcount, tenure and role composition for the {len(full_f):,} employees "
            "matching the current filters — the base population every other tab's "
            "attrition/engagement/performance rates are measured against."
        )
        col1, col2 = st.columns(2)

        with col1:
            dept_counts = full_f["department"].value_counts().sort_values()
            fig = go.Figure(go.Bar(
                x=dept_counts.values, y=dept_counts.index, orientation="h",
                marker_color=BLUE,
                hovertemplate="%{y}: %{x} employees<extra></extra>",
            ))
            fig.update_layout(title="Headcount by department", xaxis_title="Employees")
            st.plotly_chart(style_fig(fig), use_container_width=True)
            top_dept = dept_counts.idxmax()
            st.caption(
                f"This chart shows how the selected {len(full_f):,} employees split across "
                f"departments. {top_dept} is the largest at {dept_counts.max():,} employees "
                f"({dept_counts.max() / len(full_f) * 100:.0f}% of the selection)."
            )

        with col2:
            color_label = st.selectbox(
                "Split tenure by", ["None"] + list(ENGAGEMENT_GROUP_OPTIONS.keys()), key="tenure_split",
            )
            color_col = ENGAGEMENT_GROUP_OPTIONS.get(color_label)
            fig = px.histogram(
                full_f, x=full_f["tenure_months"] / 12, nbins=30,
                color=full_f[color_col] if color_col else None,
                color_discrete_sequence=CATEGORICAL if color_col else [BLUE],
            )
            fig.update_layout(
                title="Tenure distribution (years)",
                xaxis_title="Years at NovaCorp", yaxis_title="Employees",
            )
            fig.update_traces(hovertemplate="%{x:.1f} yrs: %{y} employees<extra></extra>")
            st.plotly_chart(style_fig(fig, showlegend=bool(color_col)), use_container_width=True)
            st.caption(
                "This chart shows how long the selected employees have been at NovaCorp."
                + (f" Colour-split by {color_label} to compare tenure shape across groups." if color_col
                   else " Use \"Split tenure by\" above to compare tenure shape across a dimension.")
            )

        st.divider()
        st.markdown("**Drill down: headcount composition**")
        wf_group_label = st.selectbox("Group by", list(ENGAGEMENT_GROUP_OPTIONS.keys()), key="wf_group")
        wf_group_col = ENGAGEMENT_GROUP_OPTIONS[wf_group_label]
        wf_order = {"age_band": AGE_BAND_ORDER}.get(wf_group_col)
        wf_counts = full_f[wf_group_col].value_counts()
        wf_counts = wf_counts.reindex([o for o in wf_order if o in wf_counts.index]) if wf_order else wf_counts.sort_values()
        fig = go.Figure(go.Bar(
            x=wf_counts.values, y=[str(i) for i in wf_counts.index], orientation="h",
            marker_color=BLUE, text=[f"{v/len(full_f)*100:.0f}%" for v in wf_counts.values],
            textposition="outside",
            hovertemplate="%{y}: %{x} employees<extra></extra>",
        ))
        fig.update_layout(title=f"Headcount by {wf_group_label}", xaxis_title="Employees")
        st.plotly_chart(style_fig(fig, height=420), use_container_width=True)
        st.caption(f"This chart breaks the {len(full_f):,}-employee selection down by {wf_group_label}, as a headcount and % share of the selection.")

        col3, col4 = st.columns(2)
        with col3:
            role_counts = full_f["role_level"].value_counts().sort_index()
            fig = go.Figure(go.Bar(
                x=[f"Level {r}" for r in role_counts.index], y=role_counts.values,
                marker_color=ORDINAL_BLUE[:len(role_counts)] if len(role_counts) <= 5 else BLUE,
                hovertemplate="%{x}: %{y} employees<extra></extra>",
            ))
            fig.update_layout(title="Headcount by role level", yaxis_title="Employees")
            st.plotly_chart(style_fig(fig, height=360), use_container_width=True)
            st.caption("This chart shows the seniority mix of the current selection, Level 1 (most junior) to Level 8 (most senior).")

        with col4:
            avg_tenure_by_dept = (full_f.groupby("department")["tenure_months"].mean() / 12).sort_values()
            fig = go.Figure(go.Bar(
                x=avg_tenure_by_dept.values, y=avg_tenure_by_dept.index, orientation="h",
                marker_color=AQUA,
                hovertemplate="%{y}: %{x:.1f} yrs avg tenure<extra></extra>",
            ))
            fig.update_layout(title="Average tenure by department", xaxis_title="Years")
            st.plotly_chart(style_fig(fig, height=360), use_container_width=True)
            st.caption("This chart shows which departments skew toward longer- or shorter-tenured staff, a useful lens alongside the Attrition tab's department view.")

    # --------------------------------------------------------------- Attrition --
    with sub_attrition:
        st.subheader("Attrition patterns")
        st.caption(
            "Where is attrition concentrated, and does it match the FY2025 annual "
            "report's Entity_B integration risk and Risk & Compliance talent-loss claims?"
        )
        col1, col2 = st.columns(2)

        with col1:
            rate_by_dept = attrition_rate(full_f, "department")
            st.plotly_chart(
                style_fig(attrition_bar(rate_by_dept, "Attrition rate by department",
                                         color=RED, add_avg=overall_rate)),
                use_container_width=True,
            )
            top = rate_by_dept.idxmax()
            st.caption(
                f"This chart compares attrition across departments for the current selection. "
                f"{top} runs highest at {rate_by_dept.max():.1f}%, vs a {overall_rate:.1f}% "
                f"firm-wide average (dashed line)."
            )

        with col2:
            rate_by_cohort = attrition_rate(full_f, "legacy_entity_code")
            st.plotly_chart(
                style_fig(attrition_bar(rate_by_cohort, "Attrition rate by acquisition cohort",
                                         color=ORANGE, add_avg=overall_rate)),
                use_container_width=True,
            )
            top_cohort = rate_by_cohort.idxmax()
            st.caption(
                f"This chart compares attrition across the four legacy entities from NovaCorp's "
                f"acquisition history. {top_cohort} runs highest at {rate_by_cohort.max():.1f}%."
            )

        rc = full_f[full_f["department"] == "Risk & Compliance"]
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
            st.caption(
                "This chart drills into Risk & Compliance specifically, since the FY2025 annual "
                "report flags FAR-driven attrition risk at Director level (role level 4) in this "
                f"department ({len(rc):,} employees in the current selection)."
            )

        st.markdown("**Exit characteristics** (departed employees in the current filter)")
        st.caption(
            "These three charts show how the current selection's leavers break down by exit "
            "type (voluntary/involuntary), pathway (pushed out vs pulled elsewhere), and whether "
            "the exit was flagged regrettable — the preventable, high-value losses this dashboard "
            "is ultimately trying to reduce."
        )
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

        st.divider()
        st.markdown("**Drill down: attrition by any dimension**")
        group_label = st.selectbox("Group by", list(ATTRITION_GROUP_OPTIONS.keys()), key="attr_group")
        kind, group_col = ATTRITION_GROUP_OPTIONS[group_label]

        order_map = {
            "age_band": AGE_BAND_ORDER, "tenure_bucket": TENURE_BUCKET_ORDER,
            "performance_rating": RATING_ORDER,
        }
        if kind == "rate":
            series = attrition_rate(full_f, group_col)
            st.plotly_chart(
                style_fig(attrition_bar(
                    series, f"Attrition rate by {group_label}", color=RED,
                    add_avg=overall_rate, order=order_map.get(group_col),
                ), height=420),
                use_container_width=True,
            )
            st.caption(f"This chart compares attrition across {group_label.lower()} for the current selection, against the {overall_rate:.1f}% firm-wide average (dashed line).")
        else:
            if len(att_f):
                counts = att_f[group_col].astype(str).value_counts()
                st.plotly_chart(
                    style_fig(count_bar(counts, f"{group_label} — distribution among leavers", color=AQUA), height=380),
                    use_container_width=True,
                )
                st.caption(f"This chart shows how the {len(att_f):,} leavers in the current selection break down by {group_label.lower()} — a distribution among leavers, not an attrition rate.")
            else:
                st.info("No leavers in the current filter.")

        if len(att_f):
            st.plotly_chart(
                style_fig(heatmap_ct(att_f, "pathway", "exit_type", "Pathway vs exit type (leavers)"), height=340),
                use_container_width=True,
            )
            st.caption(
                "This heatmap cross-tabs why leavers left (push = a reason here, pull = something "
                "elsewhere) against how their exit was recorded (voluntary/involuntary), among the "
                f"{len(att_f):,} leavers in the current selection."
            )

    # -------------------------------------------------------------- Engagement --
    with sub_engagement:
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

        attrition_by_responder = attrition_rate(full_f, "low_responder")
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
            title="Attrition rate: survey responders vs low/non-responders (<50%)",
            yaxis_title="% departed",
        )
        st.plotly_chart(style_fig(fig, height=380), use_container_width=True)

        st.divider()
        st.markdown("**Non-responder deep dive** — employees who never answered a single survey wave")
        st.caption(
            "\"Non-Responder\" = has engagement.csv records but always declined (EDA.ipynb's "
            "506-employee definition). This is kept separate from \"No Survey Data\" = zero "
            "engagement.csv rows at all, i.e. never administered a survey wave in the first "
            "place — a different, structural population that should not be counted as a "
            "behavioural non-response signal."
        )
        nonresp_f = full_f[full_f["response_category"] == "Non-Responder"]
        no_survey_f = full_f[full_f["response_category"] == "No Survey Data"]
        nonresp_rate = overall_attrition_rate(nonresp_f) if len(nonresp_f) else float("nan")
        lift = nonresp_rate / overall_rate if overall_rate else float("nan")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("True non-responders (selection)", f"{len(nonresp_f):,}")
        c2.metric("Attrition rate among them", f"{nonresp_rate:.1f}%" if nonresp_rate == nonresp_rate else "n/a")
        c3.metric("Lift vs firm baseline", f"{lift:.2f}x" if lift == lift else "n/a")
        c4.metric("No survey data at all (selection)", f"{len(no_survey_f):,}")

        st.plotly_chart(
            style_fig(attrition_bar(
                attrition_rate(full_f, "response_category"),
                "Attrition rate by survey response category", color=RED, add_avg=overall_rate,
                order=["No Survey Data", "Non-Responder", "Low Responder", "Responder"],
            ), height=380),
            use_container_width=True,
        )

        eng_group_label = st.selectbox("Break down non-responder concentration by", list(ENGAGEMENT_GROUP_OPTIONS.keys()), key="eng_group")
        eng_group_col = ENGAGEMENT_GROUP_OPTIONS[eng_group_label]
        lift_df = nonresponder_lift(full_f, eng_group_col)
        if len(lift_df):
            order = order_map = {"age_band": AGE_BAND_ORDER}.get(eng_group_col)
            cats = [c for c in order if c in lift_df.index] if order else list(lift_df.sort_values("lift", ascending=False).index)
            fig = grouped_bar(
                [str(c) for c in cats],
                {"% of non-responders": lift_df.loc[cats, "nonresponder_pct"].values,
                 "% of firm-wide population": lift_df.loc[cats, "firmwide_pct"].values},
                f"Where non-responders work, by {eng_group_label}", yaxis_title="% share",
                colors=[RED, BLUE],
            )
            st.plotly_chart(style_fig(fig, height=420, showlegend=True), use_container_width=True)
            st.caption(
                "A group's bar for non-responders sitting well above its firm-wide share means "
                "that group is over-represented among people who never respond to engagement surveys."
            )
        else:
            st.info("No non-responders in the current filter to break down.")

        st.divider()
        st.markdown("### 🎯 Executive finding: the compounding flight-risk segment")
        st.caption(
            "Not a single-factor cut — this is what happens when HiPo status, survey silence, and "
            "acquisition cohort compound on the same employees. Computed live from the current "
            "filter selection; narrow the sidebar to test whether it still holds in a specific slice."
        )
        hipo_f = full_f[full_f["hipo_flag"] == True]
        hipo_rate = overall_attrition_rate(hipo_f) if len(hipo_f) else float("nan")
        hipo_nonresp_f = full_f[(full_f["hipo_flag"] == True) & (full_f["response_category"] == "Non-Responder")]
        hipo_nonresp_rate = overall_attrition_rate(hipo_nonresp_f) if len(hipo_nonresp_f) else float("nan")
        lift_vs_firm = hipo_nonresp_rate / overall_rate if overall_rate else float("nan")
        lift_vs_hipo = hipo_nonresp_rate / hipo_rate if hipo_rate else float("nan")

        e1, e2, e3, e4 = st.columns(4)
        e1.metric("HiPo employees (selection)", f"{len(hipo_f):,}")
        e2.metric("HiPo + Non-Responder", f"{len(hipo_nonresp_f):,}")
        e3.metric("Attrition rate, this segment", f"{hipo_nonresp_rate:.1f}%" if hipo_nonresp_rate == hipo_nonresp_rate else "n/a")
        e4.metric(
            "Lift vs firm baseline", f"{lift_vs_firm:.2f}x" if lift_vs_firm == lift_vs_firm else "n/a",
            help=f"{lift_vs_hipo:.2f}x vs the HiPo-only baseline of {hipo_rate:.1f}%" if lift_vs_hipo == lift_vs_hipo else None,
        )

        fig = go.Figure(go.Bar(
            x=["Firm baseline", "HiPo (all)", "HiPo + Non-Responder"],
            y=[overall_rate, hipo_rate, hipo_nonresp_rate],
            marker_color=[BLUE, ORANGE, RED],
            text=[f"{v:.1f}%" if v == v else "n/a" for v in [overall_rate, hipo_rate, hipo_nonresp_rate]],
            textposition="outside",
            hovertemplate="%{x}: %{y:.1f}%% departed<extra></extra>",
        ))
        fig.update_layout(title="Attrition compounds as risk factors stack", yaxis_title="% departed")
        st.plotly_chart(style_fig(fig, height=380), use_container_width=True)
        st.caption(
            "This chart shows attrition rising as risk factors stack: firm-wide baseline, then "
            "HiPo employees alone, then the narrower HiPo + Non-Responder intersection at the "
            "centre of this dashboard's primary hypothesis."
        )

        if len(hipo_nonresp_f):
            hipo_nonresp_entity_lift = nonresponder_lift(hipo_f, "legacy_entity_code")
            entity_c_share = (
                hipo_nonresp_entity_lift.loc["Entity_C", "nonresponder_pct"]
                if "Entity_C" in hipo_nonresp_entity_lift.index else None
            )

            departed_hipo = full_f[full_f["attrited"] & (full_f["hipo_flag"] == True)].copy()
            departed_hipo["is_regrettable"] = departed_hipo["regrettable_flag"] == "Yes"
            regrettable_hipo = departed_hipo[departed_hipo["is_regrettable"]]
            lo, hi = replacement_cost_range(regrettable_hipo) if len(regrettable_hipo) else (0.0, 0.0)

            entity_c_sentence = (
                f" Of the {len(hipo_nonresp_f)} employees in this segment, {entity_c_share:.0f}% are "
                f"from Entity_C — despite Entity_C being a small share of the firm."
                if entity_c_share is not None else ""
            )
            st.markdown(
                f"**Why it matters:**{entity_c_sentence} Regrettable HiPo exits alone carry an "
                f"estimated **\\${lo:,.0f}–\\${hi:,.0f}** replacement cost in the current selection "
                f"(50–200% of `salary_at_exit`, {len(regrettable_hipo)} regrettable HiPo departures)."
            )

        st.markdown("**Engagement dimensions: active vs departed**")
        active_scores = full_f.loc[~full_f["attrited"], SCORE_COLS].mean()
        departed_scores = full_f.loc[full_f["attrited"], SCORE_COLS].mean()
        fig = grouped_bar(
            [c.replace("_", " ").title() for c in SCORE_COLS],
            {"Active": active_scores.values, "Departed": departed_scores.values},
            "Engagement dimensions by attrition status", yaxis_title="Average score (1-5)",
            colors=[BLUE, RED],
        )
        st.plotly_chart(style_fig(fig, height=440, showlegend=True), use_container_width=True)
        st.caption(
            "This chart compares average scores across all 8 engagement dimensions between "
            "employees who are still active and those who departed, for respondents in the "
            "current selection — a widening gap on a dimension flags where disengagement "
            "precedes departure."
        )

    # ------------------------------------------------------------- Performance --
    with sub_perf:
        st.subheader("Performance")
        st.caption("Do performance/promotion signals relate to attrition?")

        p1, p2 = st.columns(2)
        with p1:
            promo_rate = (full_f["promotion_recommendation"] == "Yes").mean() * 100
            st.metric("Promotion recommendation rate", f"{promo_rate:.1f}%")
        with p2:
            st.metric("Avg goal achievement score", f"{avg_goal_achievement:.1f}" if avg_goal_achievement == avg_goal_achievement else "n/a")

        col1, col2 = st.columns(2)
        with col1:
            rate_by_rating = attrition_rate(full_f, "performance_rating").reindex(RATING_ORDER)
            fig = go.Figure(go.Bar(
                x=RATING_ORDER, y=rate_by_rating.values,
                marker_color=ORDINAL_BLUE,
                hovertemplate="%{x}: %{y:.1f}%% departed<extra></extra>",
            ))
            fig.update_layout(title="Attrition rate by most recent performance rating", yaxis_title="% departed")
            st.plotly_chart(style_fig(fig, height=420), use_container_width=True)
            st.caption(
                "This chart tests whether NovaCorp is losing low performers (managed exits, "
                "expected) or high performers (regrettable, costly losses) — each employee's "
                "most recent rating before they left or as of today if still active."
            )

        with col2:
            if len(att_f):
                counts = att_f["performance_band_at_exit"].value_counts().reindex(
                    [r for r in RATING_ORDER if r in att_f["performance_band_at_exit"].unique()]
                )
                st.plotly_chart(
                    style_fig(count_bar(counts, "Performance band at exit (leavers)", color=AQUA), height=420),
                    use_container_width=True,
                )
                st.caption(f"This chart shows the performance rating leavers held specifically at their exit, among the {len(att_f):,} leavers in the current selection.")
            else:
                st.info("No leavers in the current filter.")

        col3, col4 = st.columns(2)
        with col3:
            if len(att_f):
                promo_leavers = full_f.loc[full_f["attrited"], "promotion_recommendation"].value_counts()
                st.plotly_chart(
                    style_fig(count_bar(promo_leavers, "Promotion recommendation for employees who left", color=VIOLET), height=380),
                    use_container_width=True,
                )
                st.caption("This chart shows whether leavers had a pending promotion recommendation — a \"Yes\" here often signals a regrettable, avoidable loss.")
            else:
                st.info("No leavers in the current filter.")

        with col4:
            st.plotly_chart(
                style_fig(heatmap_ct(
                    full_f, "performance_rating", "promotion_recommendation",
                    "Performance rating vs promotion recommendation", row_order=RATING_ORDER,
                ), height=380),
                use_container_width=True,
            )
            st.caption("This heatmap cross-tabs performance rating against promotion recommendation for the current selection, to spot ratings where strong performers aren't being promoted.")

        st.divider()
        perf_group_label = st.selectbox(
            "Goal achievement score, broken down by", list(COMPENSATION_GROUP_OPTIONS.keys()), key="perf_group"
        )
        perf_group_col = COMPENSATION_GROUP_OPTIONS[perf_group_label]
        order = {"performance_rating": RATING_ORDER}.get(perf_group_col)
        st.plotly_chart(
            style_fig(box_by_group(
                full_f, perf_group_col, "goal_achievement_score",
                f"Goal achievement score by {perf_group_label}", order=order,
            ), height=440),
            use_container_width=True,
        )
        st.caption(f"This chart compares the spread of goal achievement scores across {perf_group_label.lower()} for the current selection — box = middle 50%, dashed line = mean.")

    # ------------------------------------------------------------ Compensation --
    with sub_comp:
        st.subheader("Compensation")
        st.caption(
            "Compensation compression for high-potential employees, noted in the "
            "FY2025 annual report."
        )
        col1, col2 = st.columns(2)

        with col1:
            fig = go.Figure()
            for flag, color, label in [(False, BLUE, "Not HiPo"), (True, ORANGE, "HiPo")]:
                subset = full_f.loc[full_f["hipo_flag"] == flag, "compa_ratio"].dropna()
                fig.add_trace(go.Box(y=subset, name=label, marker_color=color, boxmean=True))
            fig.update_layout(
                title="Compa-ratio: high-potential vs rest of workforce",
                yaxis_title="Compa-ratio (1.0 = at role midpoint)",
            )
            st.plotly_chart(style_fig(fig, height=420), use_container_width=True)
            hipo_compa = full_f.loc[full_f["hipo_flag"] == True, "compa_ratio"].mean()
            rest_compa = full_f.loc[full_f["hipo_flag"] == False, "compa_ratio"].mean()
            st.caption(
                f"This chart tests the report's \"7-8 point pay compression\" claim for the "
                f"current selection: HiPo employees average {hipo_compa:.2f} compa-ratio vs "
                f"{rest_compa:.2f} for the rest of the workforce."
                if hipo_compa == hipo_compa and rest_compa == rest_compa else
                "This chart compares compa-ratio spread between HiPo and non-HiPo employees."
            )

        with col2:
            bucket_counts = full_f["compa_bucket"].value_counts().reindex(COMPA_BUCKET_ORDER).dropna()
            st.plotly_chart(
                style_fig(count_bar(bucket_counts, "Compa-ratio bucket distribution", color=YELLOW), height=420),
                use_container_width=True,
            )
            st.caption("This chart shows how many employees in the current selection sit below, at, or above their role's pay band midpoint.")

        st.divider()
        comp_group_label = st.selectbox("Compa-ratio, broken down by", list(COMPENSATION_GROUP_OPTIONS.keys()), key="comp_group")
        comp_group_col = COMPENSATION_GROUP_OPTIONS[comp_group_label]
        order = {"performance_rating": RATING_ORDER}.get(comp_group_col)
        st.plotly_chart(
            style_fig(box_by_group(
                full_f, comp_group_col, "compa_ratio", f"Compa-ratio by {comp_group_label}", order=order,
            ), height=440),
            use_container_width=True,
        )
        st.caption(f"This chart compares compa-ratio spread across {comp_group_label.lower()} for the current selection — box = middle 50%, dashed line = mean.")

# --------------------------------------------------------------- Takeaways --
with tab_takeaways:

    # --- HiPo pay-compression hypothesis (matches the Hypothesis tab) ---
    hipo_h = full_f[full_f["hipo_flag"] == True]
    hipo_rates_h = attrition_rate(full_f, "hipo_flag")
    hipo_rate_h = hipo_rates_h.get(True, float("nan"))
    nonhipo_rate_h = hipo_rates_h.get(False, float("nan"))
    hipo_vs_nonhipo_lift = hipo_rate_h / nonhipo_rate_h if nonhipo_rate_h else float("nan")

    compa_by_hipo_h = full_f.groupby("hipo_flag")["compa_ratio"].mean()
    hipo_compa_h = compa_by_hipo_h.get(True, float("nan"))
    nonhipo_compa_h = compa_by_hipo_h.get(False, float("nan"))

    hipo_voluntary_h = full_f[
        full_f["attrited"] & (full_f["hipo_flag"] == True)
        & (full_f["exit_type"].astype(str).str.lower() == "voluntary")
    ]
    hipo_pull_h = hipo_voluntary_h[hipo_voluntary_h["pathway"].astype(str).str.contains("pull", case=False, na=False)]
    hipo_push_h = hipo_voluntary_h[hipo_voluntary_h["pathway"].astype(str).str.contains("push", case=False, na=False)]
    pull_compa_h = hipo_pull_h["compa_ratio"].mean() if len(hipo_pull_h) else float("nan")
    push_compa_h = hipo_push_h["compa_ratio"].mean() if len(hipo_push_h) else float("nan")

    departed_hipo_h = full_f[full_f["attrited"] & (full_f["hipo_flag"] == True)].copy()
    departed_hipo_h["is_regrettable"] = departed_hipo_h["regrettable_flag"] == "Yes"
    regrettable_hipo_h = departed_hipo_h[departed_hipo_h["is_regrettable"]]
    lo_h, hi_h = replacement_cost_range(regrettable_hipo_h) if len(regrettable_hipo_h) else (0.0, 0.0)

    below_band_h = departed_hipo_h[departed_hipo_h["compa_bucket"] == "<0.85 (below band)"]
    at_band_h = departed_hipo_h[departed_hipo_h["compa_bucket"] == "0.95-1.05 (at band)"]
    below_band_regret_rate = (below_band_h["regrettable_flag"] == "Yes").mean() * 100 if len(below_band_h) else float("nan")
    at_band_regret_rate = (at_band_h["regrettable_flag"] == "Yes").mean() * 100 if len(at_band_h) else float("nan")

    compa_attr_rates_hipo = attrition_rate(hipo_h, "compa_bucket") if len(hipo_h) else pd.Series(dtype=float)
    below_band_attr_rate = compa_attr_rates_hipo.get("<0.85 (below band)", float("nan"))
    at_band_attr_rate = compa_attr_rates_hipo.get("0.95-1.05 (at band)", float("nan"))

    # --- Entity_C / Non-Responder engagement gap (now the leading alternative) ---
    hipo_nonresp_h = full_f[(full_f["hipo_flag"] == True) & (full_f["response_category"] == "Non-Responder")]
    hipo_nonresp_rate_h = overall_attrition_rate(hipo_nonresp_h) if len(hipo_nonresp_h) else float("nan")
    hnr_lift_firm = hipo_nonresp_rate_h / overall_rate if overall_rate else float("nan")

    hnr_entity_lift = nonresponder_lift(hipo_h, "legacy_entity_code") if len(hipo_h) else None
    hnr_entity_c_share = (
        hnr_entity_lift.loc["Entity_C", "nonresponder_pct"]
        if hnr_entity_lift is not None and "Entity_C" in hnr_entity_lift.index else float("nan")
    )
    firm_entity_c_share = full_f["legacy_entity_code"].eq("Entity_C").mean() * 100 if len(full_f) else float("nan")

    st.markdown(f"""
**Problem statement.** High-potential (HiPo) employees are paid systematically below their role's
market band relative to everyone else, and that gap lines up with a higher exit rate for exactly the
group NovaCorp can least afford to lose. HiPo employees leave at **{hipo_rate_h:.1f}%** vs
**{nonhipo_rate_h:.1f}%** for the rest of the workforce ({hipo_vs_nonhipo_lift:.1f}x), and the loss is
sharpest among HiPo employees being actively recruited away (`pathway = pull`) and concentrated at
junior levels -- meaning NovaCorp is losing high-potential people early, before it has recouped much
investment in them.

**Evidence supporting it:**
- HiPo employees average a compa-ratio of **{hipo_compa_h:.2f}** vs **{nonhipo_compa_h:.2f}** for
  everyone else -- a real pay gap below the HiPo cohort's band midpoint, alongside a real attrition
  gap.
- The pathway split is the strongest single piece of evidence: HiPo employees poached by competitors
  (`pull`) average a **{pull_compa_h:.2f}** compa-ratio -- more underpaid than HiPo employees who leave
  for internal reasons (`push`, **{push_compa_h:.2f}**). It isn't just that HiPo employees are
  underpaid generally; the *most* underpaid HiPo employees are exactly the ones the market is picking
  off.
- Regrettable HiPo exits carry an estimated **\${lo_h:,.0f}-\${hi_h:,.0f}** replacement cost in this
  selection ({len(regrettable_hipo_h)} people, 50-200% of `salary_at_exit`) -- directly quantifiable
  against the \$42M annual estimate.
- Pay compression predicts *which* HiPo exits are regrettable: **{below_band_regret_rate:.0f}%** of
  departed HiPo employees below their pay band are flagged regrettable, vs **{at_band_regret_rate:.0f}%**
  for those at-band -- the underpaid group is disproportionately the preventable, high-value loss.
- The annual report's own "7-8 point compression" claim and its HiPo pay-band framing point directly
  at this pattern; this hypothesis is what the report's own data shows when pay and pathway are
  connected.

**Evidence against it / limitations:**
- The relationship isn't strictly monotonic: HiPo employees below band attrite at
  **{below_band_attr_rate:.1f}%** vs **{at_band_attr_rate:.1f}%** at-band in this selection --
  being underpaid predicts *how costly* a HiPo exit is more cleanly than it predicts *whether* the
  person leaves at all.
- Small sample: HiPo pull-exits in particular can be a small and depending on filters -- directionally
  strong, but treat point estimates cautiously and always check the current n before quoting a rate.
- We cannot yet separate "the market is pricing HiPo talent higher than NovaCorp's bands" from
  "NovaCorp's bands themselves are miscalibrated for this cohort" -- both produce the same
  underpaid-and-poached pattern, and they call for different fixes (Discover further before committing
  to a Develop-phase fix).

**Confounding variables:** role level and department mix (loss concentrates at junior levels and in
Risk & Compliance, Corporate Operations, and Technology), tenure, manager
quality/span of control (not in this dataset), and whether external market rates for these roles have
moved faster than NovaCorp's pay bands have been refreshed.

**Business impact:** every underpaid HiPo employee retained is a high-value, hard-to-replace employee
kept off a \${lo_h:,.0f}+ replacement-cost list, and closing the compa-ratio gap for the HiPo cohort
specifically is a targeted, bounded compensation fix rather than a firm-wide pay review.

**Recommended intervention:** (1) prioritise a compa-ratio review for HiPo employees below their pay
band, starting with junior levels and the departments with the highest `pull`-exit concentration;
(2) flag any HiPo employee with a pending promotion recommendation *and* a below-band compa-ratio for
an off-cycle pay adjustment; (3) track `pull` vs `push` pathway mix quarterly as a leading indicator --
a rising `pull` share signals the market is out-bidding NovaCorp before HR ever sees a resignation.

**KPIs to measure success:** HiPo compa-ratio gap vs the rest of the workforce (target: parity within
two review cycles); HiPo `pull`-pathway share trending down; regrettable HiPo attrition rate and its
replacement-cost total, tracked quarterly.

**Should this be the final project focus?** Yes, provisionally -- pending the one confirmation that
would sharpen it: whether the gap reflects NovaCorp's pay bands lagging a moving external market
(fixable with a band refresh) or a deeper internal miscalibration (slower, needs a job-architecture
review). That's the highest-value next step before committing further analysis time.
""")

    rate_by_cohort_all = attrition_rate(full_f, "legacy_entity_code")
    entity_b_takeaway = rate_by_cohort_all.get("Entity_B", float("nan"))
    origin_takeaway = rate_by_cohort_all.get("NovaCorp-Origin", float("nan"))

    with st.expander("Alternative hypotheses considered and rejected"):
        st.markdown(f"""
1. **"NovaCorp's engagement-survey coverage gap in Entity_C is hiding a compounding HiPo
   flight-risk segment."** Real and sharp: HiPo + Non-Responder employees leave at
   **{hipo_nonresp_rate_h:.1f}%** ({hnr_lift_firm:.1f}x the firm baseline), and Entity_C accounts for
   {hnr_entity_c_share:.0f}% of that segment vs only {firm_entity_c_share:.1f}% of the firm. Kept as a
   strong secondary finding -- it's a data-infrastructure story (survey coverage) rather than a
   compensation story, and it's harder to distinguish "broken survey system" from "genuinely
   disengaged talent" with what's in this dataset. The pay-compression pattern is broader,
   evidenced consistently across legacy entities, and ties more directly to the annual report's own
   "7-8 point compression" claim -- so it leads, with this as the next-highest-priority follow-up.
2. **"Entity_B is the primary attrition risk"** (the annual report's own framing). Real
   ({entity_b_takeaway:.1f}% vs {origin_takeaway:.1f}% for NovaCorp-Origin) but already stated
   explicitly in the FY2025 report -- not a new finding -- and its HiPo interaction is a flat +3pp
   rather than the pay-band-driven pattern seen in the pull/push split. Weaker as a *headline*
   finding, though still worth monitoring.
3. **"All survey non-responders are a flight risk"** (the CEO letter's literal claim). Too broad:
   non-responders overall are actually *less* likely to be flagged regrettable when they leave than
   responders are. Treating all ~500+ non-responders as equally high-value risk would misdirect a
   retention program at people who are, on average, not the preventable loss NovaCorp should be
   worried about.
""")

    st.divider()
    st.subheader("Supporting observations from the discovery pass")
    entity_b = rate_by_cohort_all.get("Entity_B", float("nan"))
    origin = rate_by_cohort_all.get("NovaCorp-Origin", float("nan"))

    rc_all = full_f[full_f["department"] == "Risk & Compliance"]
    rc_dept_rate = overall_attrition_rate(rc_all) if len(rc_all) else float("nan")
    rc_l4 = rc_all[rc_all["role_level"] == 4]
    rc_l4_rate = overall_attrition_rate(rc_l4) if len(rc_l4) else float("nan")

    resp_rates = attrition_rate(full_f, "low_responder")
    resp_rate_val = resp_rates.get(False, float("nan"))
    nonresp_rate_val = resp_rates.get(True, float("nan"))

    compa_by_hipo = full_f.groupby("hipo_flag")["compa_ratio"].mean()

    tenure_rates = attrition_rate(full_f, "tenure_bucket")
    first_year_rate = tenure_rates.get("<1y", float("nan"))
    hipo_rates = attrition_rate(full_f, "hipo_flag")
    hipo_rate_val = hipo_rates.get(True, float("nan"))

    nonresp_vs_resp_lift = nonresp_rate_val / resp_rate_val if resp_rate_val else float("nan")

    true_nonresp_f = full_f[full_f["response_category"] == "Non-Responder"]
    true_nonresp_rate = overall_attrition_rate(true_nonresp_f) if len(true_nonresp_f) else float("nan")
    true_nonresp_lift = true_nonresp_rate / overall_rate if overall_rate else float("nan")

    entity_lift_df = nonresponder_lift(full_f, "legacy_entity_code")
    if "Entity_C" in entity_lift_df.index:
        ec = entity_lift_df.loc["Entity_C"]
        entity_c_line = (
            f"Entity_C accounts for {ec['nonresponder_pct']:.1f}% of true non-responders vs "
            f"only {ec['firmwide_pct']:.1f}% of the firm ({ec['lift']:.1f}x over-representation)."
        )
    else:
        entity_c_line = "Not enough Entity_C non-responders in the current filter to assess."

    st.markdown(f"""
1. **Entity_B cohort:** ~{entity_b:.0f}% attrition compared to ~{origin:.0f}% in NovaCorp-Origin.
   Matches the annual report's "primary integration risk for FY2026."
2. **Risk & Compliance Director level (role_level 4):** spikes to ~{rc_l4_rate:.0f}%,
   vs ~{rc_dept_rate:.0f}% department-wide. Sharper than the report states — check sample size first
   ({len(rc_l4)} employees at that level in the current filter).
3. **Survey non-responders** leave at ~{nonresp_vs_resp_lift:.1f}x the rate of
   respondents ({nonresp_rate_val:.1f}% vs {resp_rate_val:.1f}%). A testable version of the
   CEO's "flight risk" claim.
4. **High-potential employees** show pay compression (compa-ratio {compa_by_hipo.get(True, float('nan')):.2f})
   vs the rest of the workforce ({compa_by_hipo.get(False, float('nan')):.2f}). Matches the
   report's "7-8 point compression" claim.
5. **Performance vs attrition** needs a clean read: are we losing low performers (managed exits)
   or high performers (regrettable loss)? Ties to `regrettable_flag`.
6. **Retention risk is concentrated, not uniform:** Entity_B ({entity_b:.1f}%), first-year tenure
   ({first_year_rate:.1f}%), true non-responders ({true_nonresp_rate:.1f}%), and HiPo employees
   ({hipo_rate_val:.1f}%) all sit above the {overall_rate:.1f}% firm baseline
   ({true_nonresp_lift:.1f}x lift for true non-responders specifically).
7. **Entity_C survey blind spot:** {entity_c_line} The annual report calls Entity_C
   "within normal range" and doesn't mention this — worth flagging as either an early
   warning sign or a data-quality gap in Entity_C's survey rollout.

**Questions to ask:**
- Which of these causes is worth committing to?
- Do the small-sample points (e.g. R&C Director level) hold up statistically?
- Is the current solution (People Investment Programme, \$47M) targeting the right areas?
""")

#--------------------------------------------------------------- Hypothesis --
with tab_hypothesis:
    render_hypothesis_tab(full_f, eng_f, style_fig, grouped_bar, CATEGORICAL)