"""Custom tab(s) — your own data and visualizations.

Kept fully separate from app.py / data_utils.py so the existing dashboard
code never needs to change. render_hypothesis_tab() converts the analysis
from my_analysis.ipynb (HiPo pay-compression hypothesis) into Plotly charts
that respect the same global filters as the rest of the app.
"""
import pandas as pd
import plotly.graph_objects as go 
import streamlit as st

from data_utils import SCORE_COLS, RATING_ORDER

HIPO_LABEL = {True: "HiPo", False: "Non-HiPo"}


def _hipo_pct_by(full_f, departed_subset, group_col, label_fmt=str):
    """% of HiPo employees lost (in departed_subset) vs all HiPo employees, by group_col."""
    hipo_total = full_f[full_f["hipo_flag"]][group_col].value_counts()
    hipo_left = departed_subset[group_col].value_counts()
    pct = (hipo_left / hipo_total * 100).dropna()
    return pct


def _promo_colors(columns, BLUE, RED, GREY="#b0aea6"):
    """Map promotion_recommendation values to colors by name (Yes=blue, No=red,
    anything else e.g. 'Unknown'=grey) instead of by position -- grouped_bar()
    assigns colors positionally, which breaks once there are more categories
    (Yes/No/Unknown) than colors supplied."""
    mapping = {"Yes": BLUE, "No": RED}
    return [mapping.get(str(c), GREY) for c in columns]


def render_hypothesis_tab(full_f, eng_f, style_fig, grouped_bar, CATEGORICAL):
    """Everything for the Hypothesis tab. Called from app.py inside a `with tab:` block.

    Args:
        full_f: the filtered employee-level dataframe app.py already computes.
        eng_f: the filtered engagement dataframe (all survey waves) app.py already computes.
        style_fig: the existing style_fig() function from app.py (consistent chart styling).
        grouped_bar: the existing grouped_bar() function from app.py (side-by-side bars).
        CATEGORICAL: the existing color palette list from app.py.
    """
    BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = CATEGORICAL

    st.subheader("Hypothesis: HiPo Pay Compression Drives Attrition")
    st.markdown(
        "High-potential (HiPo) employees are paid systematically below their role's "
        "market band relative to everyone else, and that gap lines up with a higher "
        "exit rate for exactly the group the company can least afford to lose — most "
        "sharply among HiPos being actively recruited away (`pathway = pull`) and "
        "concentrated at junior levels."
    )

    departed = full_f[full_f["attrited"]]
    if departed.empty:
        st.info("No departed employees in the current filter to analyse.")
        return

    sub_pay, sub_pathway, sub_entity, sub_perf = st.tabs(
        ["Pay Gap & Attrition", "Exit Pathway Deep-Dive", "Legacy Entity & Engagement", "Performance & Promotion"]
    )

    # =======================================================================
    # SUB-TAB 1: Pay Gap & Attrition
    # =======================================================================
    with sub_pay:
        st.info(
            "**Why this matters:** HiPo employees average a compa-ratio of ~0.88 vs ~0.95 "
            "for everyone else — roughly a 7-point gap below their pay band's midpoint. "
            "That pay gap lines up with a real attrition gap: 15% of HiPo employees have "
            "left vs 10% of Non-HiPo employees, about 1.5x the exit rate. The charts below "
            "establish this baseline before the rest of the tab digs into why."
        )
        col1, col2 = st.columns(2)

        with col1:
            counts = departed["hipo_flag"].map(HIPO_LABEL).value_counts()
            fig = go.Figure(go.Bar(
                x=counts.index, y=counts.values,
                marker_color=[RED if c == "HiPo" else BLUE for c in counts.index],
                hovertemplate="%{x}: %{y} departed<extra></extra>",
            ))
            fig.update_layout(title="Employees who left, by HiPo status", yaxis_title="Departed")
            st.plotly_chart(style_fig(fig, height=360), use_container_width=True)

        with col2:
            total_by_hipo = full_f["hipo_flag"].value_counts()
            left_by_hipo = departed["hipo_flag"].value_counts()
            pct = (left_by_hipo / total_by_hipo * 100).reindex([True, False]).dropna()
            fig = go.Figure(go.Bar(
                x=[HIPO_LABEL[i] for i in pct.index], y=pct.values,
                marker_color=[RED if i else BLUE for i in pct.index],
                hovertemplate="%{x}: %{y:.1f}%% departed<extra></extra>",
            ))
            fig.update_layout(title="% of employees who left, by HiPo status", yaxis_title="% departed")
            st.plotly_chart(style_fig(fig, height=360), use_container_width=True)

        col3, col4 = st.columns(2)

        with col3:
            compa_by_hipo = departed.groupby("hipo_flag")["compa_ratio"].mean().reindex([True, False]).dropna()
            fig = go.Figure(go.Bar(
                x=[HIPO_LABEL[i] for i in compa_by_hipo.index], y=compa_by_hipo.values,
                marker_color=[RED if i else BLUE for i in compa_by_hipo.index],
                hovertemplate="%{x}: %{y:.3f}<extra></extra>",
            ))
            fig.update_layout(title="Avg compa-ratio among departed employees, by HiPo status",
                               yaxis_title="Compa-ratio")
            st.plotly_chart(style_fig(fig, height=360), use_container_width=True)

        with col4:
            pathway_compa = departed.groupby(["hipo_flag", "pathway"])["compa_ratio"].mean().unstack()
            if not pathway_compa.empty:
                fig = grouped_bar(
                    [HIPO_LABEL[i] for i in pathway_compa.index],
                    {str(p): pathway_compa[p].values for p in pathway_compa.columns},
                    "Compa-ratio by HiPo status and exit pathway", yaxis_title="Compa-ratio",
                    colors=[ORANGE, VIOLET],
                )
                st.plotly_chart(style_fig(fig, height=360, showlegend=True), use_container_width=True)
            else:
                st.info("No pathway data for the current filter.")

        perf_band_compa = departed.groupby(["hipo_flag", "performance_band_at_exit"])["compa_ratio"].mean().unstack()
        if not perf_band_compa.empty:
            bands = [b for b in RATING_ORDER if b in perf_band_compa.columns]
            fig = grouped_bar(
                [HIPO_LABEL[i] for i in perf_band_compa.index],
                {b: perf_band_compa[b].values for b in bands},
                "Compa-ratio by HiPo status and performance band at exit", yaxis_title="Compa-ratio",
            )
            st.plotly_chart(style_fig(fig, height=420, showlegend=True), use_container_width=True)

        hipo_departed = departed[departed["hipo_flag"]]
        if len(hipo_departed):
            regret_counts = hipo_departed["regrettable_flag"].astype(str).value_counts(normalize=True) * 100
            fig = go.Figure(go.Bar(
                x=regret_counts.index, y=regret_counts.values,
                marker_color=[GREEN if v == "No" else RED for v in regret_counts.index],
                hovertemplate="%{x}: %{y:.1f}%%<extra></extra>",
            ))
            fig.update_layout(title="Regrettable exits among departed HiPo employees", yaxis_title="% of HiPo exits")
            st.plotly_chart(style_fig(fig, height=380), use_container_width=True)
        else:
            st.info("No departed HiPo employees in the current filter.")

    # =======================================================================
    # SUB-TAB 2: Exit Pathway Deep-Dive (push vs pull, department & role level)
    # =======================================================================
    with sub_pathway:
        st.info(
            "**Why this matters:** the pathway split is the strongest evidence for the "
            "hypothesis. HiPo employees poached by competitors (`pull`) are the single "
            "most underpaid group in the dataset (~0.86 compa-ratio) — even more "
            "underpaid than HiPo employees who leave for internal reasons (`push`, ~0.92). "
            "It isn't just that HiPos are underpaid generally; the *most* underpaid HiPos "
            "are exactly the ones the market is picking off. That loss also concentrates "
            "at junior levels (role level 1-2) and in Risk & Compliance, Corporate "
            "Operations, and Technology — meaning the company is losing high-potential "
            "people early, before it has recouped much investment in them."
        )
        st.markdown("**Where HiPo employees leave by pathway** — `pull` = poached by competitors, `push` = left for internal reasons")

        hipo_voluntary = departed[(departed["hipo_flag"]) & (departed["exit_type"].astype(str).str.lower() == "voluntary")]
        hipo_pull = hipo_voluntary[hipo_voluntary["pathway"].astype(str).str.contains("pull", case=False, na=False)]
        hipo_push = hipo_voluntary[hipo_voluntary["pathway"].astype(str).str.contains("push", case=False, na=False)]

        col1, col2 = st.columns(2)
        with col1:
            pct_dept_pull = _hipo_pct_by(full_f, hipo_pull, "department")
            if len(pct_dept_pull):
                fig = go.Figure(go.Bar(
                    x=pct_dept_pull.sort_values(ascending=False).index, y=pct_dept_pull.sort_values(ascending=False).values,
                    marker_color=RED, hovertemplate="%{x}: %{y:.1f}%%<extra></extra>",
                ))
                fig.update_layout(title="% of HiPo employees lost — Pull, by department", yaxis_title="%")
                st.plotly_chart(style_fig(fig, height=400), use_container_width=True)
            else:
                st.info("No HiPo pull-exits in the current filter.")

        with col2:
            pct_dept_push = _hipo_pct_by(full_f, hipo_push, "department")
            if len(pct_dept_push):
                fig = go.Figure(go.Bar(
                    x=pct_dept_push.sort_values(ascending=False).index, y=pct_dept_push.sort_values(ascending=False).values,
                    marker_color=ORANGE, hovertemplate="%{x}: %{y:.1f}%%<extra></extra>",
                ))
                fig.update_layout(title="% of HiPo employees lost — Push, by department", yaxis_title="%")
                st.plotly_chart(style_fig(fig, height=400), use_container_width=True)
            else:
                st.info("No HiPo push-exits in the current filter.")

        col3, col4 = st.columns(2)
        with col3:
            pct_level_pull = _hipo_pct_by(full_f, hipo_pull, "role_level").sort_index()
            if len(pct_level_pull):
                fig = go.Figure(go.Bar(
                    x=[f"Level {i}" for i in pct_level_pull.index], y=pct_level_pull.values,
                    marker_color=RED, hovertemplate="%{x}: %{y:.1f}%%<extra></extra>",
                ))
                fig.update_layout(title="% of HiPo employees lost — Pull, by role level", yaxis_title="%")
                st.plotly_chart(style_fig(fig, height=400), use_container_width=True)
            else:
                st.info("No HiPo pull-exits in the current filter.")

        with col4:
            pct_level_push = _hipo_pct_by(full_f, hipo_push, "role_level").sort_index()
            if len(pct_level_push):
                fig = go.Figure(go.Bar(
                    x=[f"Level {i}" for i in pct_level_push.index], y=pct_level_push.values,
                    marker_color=ORANGE, hovertemplate="%{x}: %{y:.1f}%%<extra></extra>",
                ))
                fig.update_layout(title="% of HiPo employees lost — Push, by role level", yaxis_title="%")
                st.plotly_chart(style_fig(fig, height=400), use_container_width=True)
            else:
                st.info("No HiPo push-exits in the current filter.")

        st.divider()

        dept_compa = hipo_voluntary.groupby(["department", "pathway"])["compa_ratio"].mean().unstack()
        if not dept_compa.empty:
            fig = grouped_bar(
                list(dept_compa.index),
                {str(p): dept_compa[p].values for p in dept_compa.columns},
                "Mean compa-ratio for HiPo voluntary leavers, by department and pathway",
                yaxis_title="Compa-ratio", colors=[VIOLET, ORANGE],
            )
            st.plotly_chart(style_fig(fig, height=440, showlegend=True), use_container_width=True)

        level_compa = hipo_voluntary.groupby(["role_level", "pathway"])["compa_ratio"].mean().unstack()
        if not level_compa.empty:
            fig = grouped_bar(
                [f"Level {i}" for i in level_compa.index],
                {str(p): level_compa[p].values for p in level_compa.columns},
                "Mean compa-ratio for HiPo voluntary leavers, by role level and pathway",
                yaxis_title="Compa-ratio", colors=[VIOLET, ORANGE],
            )
            st.plotly_chart(style_fig(fig, height=420, showlegend=True), use_container_width=True)

        if len(hipo_push):
            reason_counts = hipo_push["stated_exit_reason"].astype(str).value_counts()
            fig = go.Figure(go.Bar(
                x=reason_counts.index, y=reason_counts.values, marker_color=ORANGE,
                hovertemplate="%{x}: %{y}<extra></extra>",
            ))
            fig.update_layout(title="Stated exit reason — HiPo employees, Push pathway", yaxis_title="Employees")
            st.plotly_chart(style_fig(fig, height=380), use_container_width=True)

    # =======================================================================
    # SUB-TAB 3: Legacy Entity & Engagement
    # =======================================================================
    with sub_entity:
        st.info(
            "**Why this matters:** the pay gap and attrition pattern established so far "
            "could either be a company-wide HiPo problem, or an artifact of one particular "
            "legacy entity from the integration. This section checks whether the HiPo "
            "compa-ratio gap and the HiPo exit rate hold up within every legacy entity, "
            "or whether they're really concentrated in one acquired cohort — which would "
            "point to an integration-specific pay-band issue rather than a firm-wide policy "
            "problem. It also shows that HiPo employees who go on to depart already report " \
            "lower Recognition and Wellbeing scores than everyone else while they're still " \
            "employed, well before their exit."
        )

        eng_all = eng_f.merge(full_f[["employee_id", "hipo_flag", "legacy_entity_code"]], on="employee_id", how="inner")
        eng_departed = eng_all[eng_all["employee_id"].isin(departed["employee_id"])]

        if len(eng_all):
            metric_names = [c.replace("_", " ").title() for c in SCORE_COLS]
            fig = go.Figure()
            combos = [("All Employees", eng_all, BLUE), ("Departed", eng_departed, RED)]
            for group_name, df, base_color in combos:
                for hipo_val, dash in [(True, "solid"), (False, "dot")]:
                    subset = df[df["hipo_flag"] == hipo_val]
                    if subset.empty:
                        continue
                    means = subset[SCORE_COLS].mean()
                    fig.add_trace(go.Scatter(
                        x=metric_names, y=means.values, mode="lines+markers",
                        name=f"{HIPO_LABEL[hipo_val]} ({group_name})",
                        line=dict(color=base_color, dash=dash, width=2),
                        hovertemplate="%{y:.2f}<extra>" + f"{HIPO_LABEL[hipo_val]} ({group_name})" + "</extra>",
                    ))
            fig.update_layout(
                title="Engagement metrics profile: HiPo status x attrition status",
                yaxis_title="Mean score (1-5)", hovermode="x unified",
            )
            st.plotly_chart(style_fig(fig, height=460, showlegend=True), use_container_width=True)
        else:
            st.info("No engagement survey data for the current filter.")

        st.divider()

        hipo_voluntary_all = departed[(departed["hipo_flag"]) & (departed["exit_type"].astype(str).str.lower() == "voluntary")]
        pct_by_entity = _hipo_pct_by(full_f, hipo_voluntary_all, "legacy_entity_code").sort_values(ascending=False)
        if len(pct_by_entity):
            fig = go.Figure(go.Bar(
                x=pct_by_entity.index, y=pct_by_entity.values, marker_color=RED,
                hovertemplate="%{x}: %{y:.1f}%%<extra></extra>",
            ))
            fig.update_layout(title="% of HiPo employees who left (voluntary), by legacy entity", yaxis_title="%")
            st.plotly_chart(style_fig(fig, height=420), use_container_width=True)
        else:
            st.info("No HiPo voluntary leavers in the current filter.")

        col1, col2 = st.columns(2)

        with col1:
            departed_entity_compa = departed.groupby(["legacy_entity_code", "hipo_flag"])["compa_ratio"].mean().unstack()
            if not departed_entity_compa.empty:
                fig = grouped_bar(
                    list(departed_entity_compa.index),
                    {HIPO_LABEL[c]: departed_entity_compa[c].values for c in departed_entity_compa.columns},
                    "Mean compa-ratio by legacy entity — departed employees", yaxis_title="Compa-ratio",
                    colors=[RED, BLUE],
                )
                st.plotly_chart(style_fig(fig, height=440, showlegend=True), use_container_width=True)
            else:
                st.info("No departed employees in the current filter.")

        with col2:
            full_entity_compa = full_f.groupby(["legacy_entity_code", "hipo_flag"])["compa_ratio"].mean().unstack()
            if not full_entity_compa.empty:
                fig = grouped_bar(
                    list(full_entity_compa.index),
                    {HIPO_LABEL[c]: full_entity_compa[c].values for c in full_entity_compa.columns},
                    "Mean compa-ratio by legacy entity — all employees", yaxis_title="Compa-ratio",
                    colors=[RED, BLUE],
                )
                st.plotly_chart(style_fig(fig, height=440, showlegend=True), use_container_width=True)
            else:
                st.info("No employees in the current filter.")

    # =======================================================================
    # SUB-TAB 4: Performance & Promotion
    # =======================================================================
    with sub_perf:
        st.info(
            "**Why this matters:** if HiPo pay compression were just a side-effect of "
            "middling performance, high performers wouldn't be affected. Instead, HiPo "
            "employees rated \"Outstanding\" at exit average a compa-ratio of ~0.87 — "
            "lower than Non-HiPo employees rated \"Below Expectations\" (~0.94). The "
            "best-performing high-potential people are paid worse than the worst-performing "
            "ordinary employees, which rules out \"they're just underperforming\" as the explanation."
        )

        st.markdown("**Compa-ratio by performance rating and promotion recommendation** (all employees)")
        col1, col2 = st.columns(2)
        for col, hipo_val in [(col1, True), (col2, False)]:
            with col:
                pop = full_f[full_f["hipo_flag"] == hipo_val]
                pivot = pop.groupby(["performance_rating", "promotion_recommendation"])["compa_ratio"].mean().unstack()
                if not pivot.empty:
                    ratings = [r for r in RATING_ORDER if r in pivot.index]
                    fig = grouped_bar(
                        ratings,
                        {str(p): pivot.loc[ratings, p].values for p in pivot.columns},
                        f"{HIPO_LABEL[hipo_val]} employees", yaxis_title="Mean compa-ratio",
                        colors=_promo_colors(pivot.columns, BLUE, RED),
                    )
                    st.plotly_chart(style_fig(fig, height=420, showlegend=True), use_container_width=True)
                else:
                    st.info(f"No data for {HIPO_LABEL[hipo_val]} employees in the current filter.")

        st.markdown("**Compa-ratio by performance band at exit and promotion recommendation** (departed employees)")
        col3, col4 = st.columns(2)
        for col, hipo_val in [(col3, True), (col4, False)]:
            with col:
                pop = departed[departed["hipo_flag"] == hipo_val]
                pivot = pop.groupby(["performance_band_at_exit", "promotion_recommendation"])["compa_ratio"].mean().unstack()
                if not pivot.empty:
                    bands = [b for b in RATING_ORDER if b in pivot.index]
                    fig = grouped_bar(
                        bands,
                        {str(p): pivot.loc[bands, p].values for p in pivot.columns},
                        f"{HIPO_LABEL[hipo_val]} departed employees", yaxis_title="Mean compa-ratio",
                        colors=_promo_colors(pivot.columns, BLUE, RED),
                    )
                    st.plotly_chart(style_fig(fig, height=420, showlegend=True), use_container_width=True)
                else:
                    st.info(f"No departed {HIPO_LABEL[hipo_val]} employees in the current filter.")
