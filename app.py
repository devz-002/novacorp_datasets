"""NovaCorp workforce analytics dashboard.

Interactive rebuild of notebooks/01_EDA.ipynb and the EDA.ipynb discovery
notebook: headcount & tenure, attrition patterns, engagement / non-responder
signals, and performance & compensation, all drillable through a shared set
of global filters. Run locally with `streamlit run app.py`.
"""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_utils import (
    AGE_BAND_ORDER, ATTRITION_GROUP_OPTIONS, COMPA_BUCKET_ORDER,
    COMPENSATION_GROUP_OPTIONS, ENGAGEMENT_GROUP_OPTIONS, FILTER_SPECS,
    RATING_ORDER, SCORE_COLS, TENURE_BUCKET_ORDER, apply_filters,
    apply_response_choice, attrition_rate, build_full, filter_options,
    load_raw, nonresponder_lift, overall_attrition_rate, slice_related,
)

from my_tabs import render_hypothesis_tab
 
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


def _select_all_toggle(ms_key, opts, all_key):
    st.session_state[ms_key] = list(opts) if st.session_state[all_key] else []


selections = {}
with st.sidebar:
    for label, col in FILTER_SPECS:
        if col == "role_level":
            opts = filter_options(full, col)
            fmt = lambda x: f"Level {x}"
        elif full[col].dtype == bool:
            opts = [False, True]
            fmt = lambda x: "Yes" if x else "No"
        elif col == "age_band":
            opts, fmt = filter_options(full, col, order=AGE_BAND_ORDER), str
        elif col == "tenure_bucket":
            opts, fmt = filter_options(full, col, order=TENURE_BUCKET_ORDER), str
        elif col == "compa_bucket":
            opts, fmt = filter_options(full, col, order=COMPA_BUCKET_ORDER), str
        elif col == "performance_rating":
            opts, fmt = filter_options(full, col, order=RATING_ORDER), str
        else:
            opts, fmt = filter_options(full, col), str

        ms_key, all_key = f"filter_{col}", f"filter_{col}_all"
        if ms_key not in st.session_state:
            st.session_state[ms_key] = opts

        c1, c2 = st.columns([3, 1])
        c1.markdown(f"**{label}**")
        c2.checkbox(
            "All", value=True, key=all_key, label_visibility="collapsed",
            help="Select all options", on_change=_select_all_toggle,
            args=(ms_key, opts, all_key),
        )
        selections[col] = st.multiselect(
            label, opts, key=ms_key, format_func=fmt, label_visibility="collapsed",
        )

response_choice = st.sidebar.radio(
    "Survey Response", ["All", "Responders", "Non-Responders"], horizontal=True,
    help="Non-Responders = employees who never answered a single engagement survey wave.",
)

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

tab_workforce, tab_attrition, tab_engagement, tab_perf, tab_comp, tab_takeaways, tab_hypothesis = st.tabs(
    ["Workforce", "Attrition", "Engagement", "Performance", "Compensation", "Takeaways", "Hypothesis"]
)
# --------------------------------------------------------------- Workforce --
with tab_workforce:
    st.subheader("Who works at NovaCorp")
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

    with col2:
        fig = px.histogram(
            full_f, x=full_f["tenure_months"] / 12, nbins=30,
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
        rate_by_dept = attrition_rate(full_f, "department")
        st.plotly_chart(
            style_fig(attrition_bar(rate_by_dept, "Attrition rate by department",
                                     color=RED, add_avg=overall_rate)),
            use_container_width=True,
        )

    with col2:
        rate_by_cohort = attrition_rate(full_f, "legacy_entity_code")
        st.plotly_chart(
            style_fig(attrition_bar(rate_by_cohort, "Attrition rate by acquisition cohort",
                                     color=ORANGE, add_avg=overall_rate)),
            use_container_width=True,
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
    else:
        if len(att_f):
            counts = att_f[group_col].astype(str).value_counts()
            st.plotly_chart(
                style_fig(count_bar(counts, f"{group_label} — distribution among leavers", color=AQUA), height=380),
                use_container_width=True,
            )
        else:
            st.info("No leavers in the current filter.")

    if len(att_f):
        st.plotly_chart(
            style_fig(heatmap_ct(att_f, "pathway", "exit_type", "Pathway vs exit type (leavers)"), height=340),
            use_container_width=True,
        )

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

# ------------------------------------------------------------- Performance --
with tab_perf:
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

    with col2:
        if len(att_f):
            counts = att_f["performance_band_at_exit"].value_counts().reindex(
                [r for r in RATING_ORDER if r in att_f["performance_band_at_exit"].unique()]
            )
            st.plotly_chart(
                style_fig(count_bar(counts, "Performance band at exit (leavers)", color=AQUA), height=420),
                use_container_width=True,
            )
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

# ------------------------------------------------------------ Compensation --
with tab_comp:
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

    with col2:
        bucket_counts = full_f["compa_bucket"].value_counts().reindex(COMPA_BUCKET_ORDER).dropna()
        st.plotly_chart(
            style_fig(count_bar(bucket_counts, "Compa-ratio bucket distribution", color=YELLOW), height=420),
            use_container_width=True,
        )

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

# --------------------------------------------------------------- Takeaways --
with tab_takeaways:
    st.subheader("Takeaways for initial mentor meeting")

    rate_by_cohort_all = attrition_rate(full_f, "legacy_entity_code")
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
3. **Survey non-responders** leave at ~{nonresp_rate_val / resp_rate_val:.1f}x the rate of
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
- Which of these causes is worth committing to for this project?
- Many of these causes are already outlined in the annual report by the CEO — is this a trap?
- Do the small-sample points (e.g. R&C Director level) hold up statistically?
- Is the current solution (People Investment Programme, $47M) targeting the right areas?
""")

#--------------------------------------------------------------- Hypothesis --
with tab_hypothesis:
    render_hypothesis_tab(full_f, eng_f, style_fig, grouped_bar, CATEGORICAL)
