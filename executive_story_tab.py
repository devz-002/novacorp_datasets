"""Executive Story tab — a scroll-only narrative built for a 3-minute pitch to
the CEO, CHRO and the Accenture judging panel.

Kept fully separate from app.py / data_utils.py / hypothesis_tabs.py so none
of the existing tabs need to change. render_executive_story_tab() re-presents
analysis already implemented in hypothesis_tabs.py (the HiPo pay-compression
hypothesis) as a single, always-on narrative — deliberately ignoring the
sidebar's global filters so the story never changes shape underneath the
audience mid-scroll.
"""
import plotly.graph_objects as go
import streamlit as st

from data_utils import replacement_cost_range

MUTED = "#898781"
SURFACE_TINT = "#f5f4ef"


def _hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _inject_style(accent):
    st.markdown(f"""
    <style>
    .exec-eyebrow {{
        font-size: 0.78rem; font-weight: 600; letter-spacing: 0.08em;
        text-transform: uppercase; color: {MUTED}; margin-bottom: 0.4rem;
    }}
    .exec-hero-title {{
        font-size: 2.5rem; font-weight: 700; line-height: 1.18;
        margin: 0 0 1.2rem 0; max-width: 900px;
    }}
    .exec-callout {{
        border-left: 4px solid {accent}; background: {accent}0f;
        padding: 1.1rem 1.4rem; border-radius: 4px; font-size: 1.05rem;
        line-height: 1.55; margin: 0 0 2.4rem 0; max-width: 820px;
    }}
    .exec-section-q {{
        font-size: 1.55rem; font-weight: 700; margin: 3.8rem 0 0.4rem 0;
    }}
    .exec-subhead {{
        font-size: 1.12rem; font-weight: 700; margin: 2.4rem 0 0.6rem 0;
    }}
    .exec-insight {{
        font-size: 1rem; color: #4b4a45; margin: 0.7rem 0 0.5rem 0; max-width: 760px;
        line-height: 1.55;
    }}
    .exec-card {{
        border-top: 3px solid {accent}; padding: 0.85rem 0 0 0; height: 100%;
    }}
    .exec-card h4 {{
        margin: 0 0 0.5rem 0; font-size: 0.78rem; letter-spacing: 0.06em;
        text-transform: uppercase; color: {MUTED};
    }}
    .exec-card p {{
        margin: 0 0 0.5rem 0; font-size: 1.05rem; font-weight: 500; line-height: 1.5;
    }}
    .exec-card p.why {{
        font-size: 0.92rem; font-weight: 400; color: #4b4a45;
    }}
    .exec-impact {{
        border-left: 4px solid {accent}; background: {accent}0f;
        padding: 1.1rem 1.4rem; border-radius: 4px; margin-top: 1.8rem;
        font-size: 1.12rem; line-height: 1.55; max-width: 820px;
    }}
    </style>
    """, unsafe_allow_html=True)


def render_executive_story_tab(full, eng, style_fig, CATEGORICAL):
    """Everything for the Executive Story tab. Called from app.py inside a
    `with tab:` block.

    Args:
        full: the UNFILTERED employee-level dataframe from app.py's build_full()
            — deliberately not full_f, so this page ignores the sidebar filters.
        eng: the UNFILTERED engagement dataframe (kept for signature symmetry
            with the other tabs; the metrics used here all come from `full`).
        style_fig: the existing style_fig() function from app.py.
        CATEGORICAL: the existing color palette list from app.py.
    """
    BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = CATEGORICAL
    ACCENT = RED
    _inject_style(ACCENT)

    hipo = full[full["hipo_flag"] == True]
    non_hipo = full[full["hipo_flag"] == False]
    departed = full[full["attrited"]]

    if hipo.empty or departed.empty:
        st.info("Not enough data to build the executive story.")
        return

    hipo_active = hipo[~hipo["attrited"]]
    hipo_departed = hipo[hipo["attrited"]]

    avg_hipo_compa = hipo["compa_ratio"].mean()
    avg_nonhipo_compa = non_hipo["compa_ratio"].mean()
    hipo_attrition = (hipo["status"] == "departed").mean() * 100
    nonhipo_attrition = (non_hipo["status"] == "departed").mean() * 100
    attrition_ratio = hipo_attrition / nonhipo_attrition if nonhipo_attrition else float("nan")

    hipo_voluntary = departed[
        (departed["hipo_flag"]) & (departed["exit_type"].astype(str).str.lower() == "voluntary")
    ]
    hipo_pull = hipo_voluntary[hipo_voluntary["pathway"].astype(str).str.contains("pull", case=False, na=False)]
    pull_attrition_pct = len(hipo_pull) / len(hipo) * 100 if len(hipo) else float("nan")

    avg_wellbeing = full["wellbeing"].mean()

    # =======================================================================
    # SECTION 1 — Executive Hook
    # =======================================================================
    st.markdown('<div class="exec-eyebrow">Primary hypothesis</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="exec-hero-title">We are losing the employees NovaCorp can least afford to lose.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="exec-callout">High-potential employees earn below market, and attrition follows the same '
        'pattern. The sharpest losses come from competitors poaching underpaid HiPo talent.</div>',
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("HiPo compa-ratio", f"{avg_hipo_compa:.2f}", help=f"Rest of workforce averages {avg_nonhipo_compa:.2f}.")
    k2.metric("HiPo attrition", f"{hipo_attrition:.1f}%", help=f"Rest of workforce leaves at {nonhipo_attrition:.1f}%.")
    k3.metric("Pull attrition", f"{pull_attrition_pct:.1f}%", help=f"{len(hipo_pull)} HiPo employees poached by competitors.")
    k4.metric("Avg psychological wellbeing", f"{avg_wellbeing:.2f} / 5")

    # =======================================================================
    # SECTION 2 — Who are we losing?
    # =======================================================================
    st.markdown('<div class="exec-section-q">Who are we losing?</div>', unsafe_allow_html=True)

    fig = go.Figure()
    cats = ["Non-HiPo", "HiPo"]
    vals = [nonhipo_attrition, hipo_attrition]
    colors_map = [BLUE, RED]
    for cat, val, color in zip(cats, vals, colors_map):
        fig.add_trace(go.Scatter(
            x=[0, val], y=[cat, cat], mode="lines",
            line=dict(color="#c3c2b7", width=2), showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=[val], y=[cat], mode="markers+text", marker=dict(size=24, color=color),
            text=[f"{val:.1f}%"], textposition="middle right", textfont=dict(size=14),
            showlegend=False, hovertemplate=f"{cat}: %{{x:.1f}}%% departed<extra></extra>",
        ))
    fig.update_layout(
        title="Attrition rate: HiPo vs the rest of the workforce",
        xaxis_title="% departed", xaxis=dict(range=[0, max(vals) * 1.35]),
    )
    st.plotly_chart(style_fig(fig, height=280), use_container_width=True)
    st.markdown(
        f'<div class="exec-insight">HiPo employees leave at {attrition_ratio:.1f} times the rate of the rest '
        f'of the workforce. NovaCorp invests the most in developing this group.</div>',
        unsafe_allow_html=True,
    )

    # =======================================================================
    # SECTION 3 — Why are they leaving?
    # =======================================================================
    st.markdown('<div class="exec-section-q">Why are they leaving?</div>', unsafe_allow_html=True)

    fig = go.Figure()
    for flag, color, label in [(False, BLUE, "Non-HiPo"), (True, RED, "HiPo")]:
        subset = full.loc[full["hipo_flag"] == flag, "compa_ratio"].dropna()
        fig.add_trace(go.Violin(
            y=subset, name=label, line_color=color, fillcolor=color, opacity=0.45,
            box_visible=True, meanline_visible=True, points=False,
            hovertemplate=f"{label}<extra></extra>",
        ))
    fig.add_hline(y=1.0, line_dash="dash", line_color=MUTED, annotation_text="Market midpoint (1.00)")
    fig.update_layout(title="Compa-ratio distribution: HiPo vs rest of workforce", yaxis_title="Compa-ratio")
    st.plotly_chart(style_fig(fig, height=420, showlegend=True), use_container_width=True)
    st.markdown(
        f'<div class="exec-insight">HiPo employees earn below the market midpoint, averaging {avg_hipo_compa:.2f}. '
        f'The rest of the workforce averages {avg_nonhipo_compa:.2f}, close to parity.</div>',
        unsafe_allow_html=True,
    )

    # --- Promotion recommendation: does it compound the risk? -------------
    no_promo = hipo[hipo["promotion_recommendation"] == "No"]
    yes_promo = hipo[hipo["promotion_recommendation"] == "Yes"]
    no_total, yes_total = len(no_promo), len(yes_promo)
    no_departed = int((no_promo["status"] == "departed").sum())
    yes_departed = int((yes_promo["status"] == "departed").sum())
    no_active, yes_active = no_total - no_departed, yes_total - yes_departed
    no_rate = no_departed / no_total * 100 if no_total else float("nan")
    yes_rate = yes_departed / yes_total * 100 if yes_total else float("nan")
    pull_not_promoted = hipo_pull[hipo_pull["promotion_recommendation"] == "No"]
    pull_not_promoted_pct = len(pull_not_promoted) / len(hipo_pull) * 100 if len(hipo_pull) else float("nan")

    if no_total and yes_total:
        st.markdown('<div class="exec-subhead">Promotion denial compounds the risk</div>', unsafe_allow_html=True)

        labels = ["HiPo Employees", "Not Recommended", "Recommended", "Departed", "Active"]
        node_colors = [
            _hex_to_rgba(MUTED, 0.85), _hex_to_rgba(RED, 0.85), _hex_to_rgba(BLUE, 0.85),
            _hex_to_rgba(RED, 0.85), _hex_to_rgba(MUTED, 0.45),
        ]
        link_colors = [
            _hex_to_rgba(MUTED, 0.25), _hex_to_rgba(MUTED, 0.25),
            _hex_to_rgba(RED, 0.55), _hex_to_rgba(MUTED, 0.18),
            _hex_to_rgba(RED, 0.3), _hex_to_rgba(MUTED, 0.15),
        ]
        fig = go.Figure(go.Sankey(
            node=dict(
                label=labels, color=node_colors, pad=22, thickness=16,
                line=dict(color="white", width=0),
            ),
            link=dict(
                source=[0, 0, 1, 1, 2, 2],
                target=[1, 2, 3, 4, 3, 4],
                value=[no_total, yes_total, no_departed, no_active, yes_departed, yes_active],
                color=link_colors,
                hovertemplate="%{source.label} to %{target.label}: %{value}<extra></extra>",
            ),
        ))
        fig.update_layout(title="HiPo employees: promotion recommendation to attrition outcome", font=dict(size=13))
        st.plotly_chart(style_fig(fig, height=380), use_container_width=True)
        st.markdown(
            f'<div class="exec-insight">HiPo employees denied promotion leave at {no_rate:.1f}%, against '
            f'{yes_rate:.1f}% for those recommended. {pull_not_promoted_pct:.0f}% of HiPo employees poached '
            f'by competitors were denied promotion first.</div>',
            unsafe_allow_html=True,
        )

    # =======================================================================
    # SECTION 4 — Early warning signals
    # =======================================================================
    st.markdown('<div class="exec-section-q">Early warning signals</div>', unsafe_allow_html=True)

    groups = [("HiPo — Active", hipo_active), ("HiPo — Departed", hipo_departed)]
    metrics = ["Engagement", "Psychological Wellbeing", "Survey Participation"]
    z, text = [], []
    for _, grp in groups:
        eng_raw = grp["engagement_mean"].mean()
        well_raw = grp["wellbeing"].mean()
        resp_raw = grp["survey_response_rate"].mean() * 100
        z.append([eng_raw / 5 * 100, well_raw / 5 * 100, resp_raw])
        text.append([f"{eng_raw:.1f}/5", f"{well_raw:.1f}/5", f"{resp_raw:.0f}%"])

    fig = go.Figure(go.Heatmap(
        z=z, x=metrics, y=[g[0] for g in groups],
        text=text, texttemplate="%{text}", textfont=dict(size=14),
        colorscale=[[0, RED], [1, SURFACE_TINT]],
        showscale=False,
        hovertemplate="%{y} · %{x}: %{text}<extra></extra>",
    ))
    fig.update_layout(title="HiPo employees, active vs departed", height=300)
    st.plotly_chart(style_fig(fig, height=300), use_container_width=True)
    st.markdown(
        '<div class="exec-insight">HiPo leavers show weaker engagement and wellbeing before they exit. '
        'These signals surface early enough for HR to act.</div>',
        unsafe_allow_html=True,
    )

    # =======================================================================
    # SECTION 5 — Where is the risk concentrated?
    # =======================================================================
    st.markdown('<div class="exec-section-q">Where is the risk concentrated?</div>', unsafe_allow_html=True)

    hipo_total_dl = hipo.groupby(["department", "role_level"]).size()
    pull_dl = hipo_pull.groupby(["department", "role_level"]).size().reindex(hipo_total_dl.index, fill_value=0)
    pct_dl = (pull_dl / hipo_total_dl * 100)

    pivot = pct_dl.unstack(fill_value=0)
    n_pivot = hipo_total_dl.unstack(fill_value=0).reindex(index=pivot.index, columns=pivot.columns, fill_value=0)
    dept_order = pivot.sum(axis=1).sort_values(ascending=False).index
    pivot = pivot.loc[dept_order]
    n_pivot = n_pivot.loc[dept_order]
    col_order = sorted(pivot.columns)
    pivot = pivot[col_order]
    n_pivot = n_pivot[col_order]

    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=[f"Level {c}" for c in pivot.columns], y=list(pivot.index),
        customdata=n_pivot.values,
        colorscale=[[0, SURFACE_TINT], [1, RED]],
        hovertemplate="%{y} · %{x}: %{z:.0f}%% lost to competitors (n=%{customdata})<extra></extra>",
    ))
    fig.update_layout(title="% of HiPo employees lost to competitors, by department and role level")
    st.plotly_chart(style_fig(fig, height=440), use_container_width=True)

    mask = n_pivot >= 5
    valid = pivot.where(mask) if mask.values.any() else pivot
    top_dept, top_level = valid.stack().idxmax()
    top_val = valid.loc[top_dept, top_level]
    st.markdown(
        f'<div class="exec-insight">{top_dept} Level {top_level} should be HR\'s first intervention. '
        f'{top_val:.0f}% of its HiPo employees leave for competitors.</div>',
        unsafe_allow_html=True,
    )

    # =======================================================================
    # SECTION 6 — Recommendation
    # =======================================================================
    st.markdown('<div class="exec-section-q">Recommendation</div>', unsafe_allow_html=True)

    below_090_active = hipo_active[hipo_active["compa_ratio"] < 0.90]

    dept_hipo_total = hipo.groupby("department").size()
    dept_pull = hipo_pull.groupby("department").size().reindex(dept_hipo_total.index, fill_value=0)
    dept_pull_pct = (dept_pull / dept_hipo_total * 100).sort_values(ascending=False)
    risk_dept_1, risk_dept_2 = dept_pull_pct.index[0], dept_pull_pct.index[1]
    risk_pct_1, risk_pct_2 = dept_pull_pct.iloc[0], dept_pull_pct.iloc[1]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="exec-card"><h4>Immediate</h4>'
            f'<p>Reward teams should review pay for {len(below_090_active)} active HiPo employees below '
            f'a 0.90 compa ratio.</p>'
            f'<p class="why">Complete this before the next salary cycle, ahead of further losses to competitors.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="exec-card"><h4>Medium term</h4>'
            f'<p>Talent teams should mandate promotion and salary reviews for HiPo staff in '
            f'{risk_dept_1} and {risk_dept_2}.</p>'
            f'<p class="why">Start within two quarters: these two departments lose {risk_pct_1:.0f}% and '
            f'{risk_pct_2:.0f}% of HiPo talent to competitors.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="exec-card"><h4>Long term</h4>'
            '<p>Compensation design teams should rebuild HiPo pay bands to hold compa ratio above 0.90 '
            'after promotion.</p>'
            '<p class="why">Deliver this within the next planning cycle to remove the compression driving '
            "today's HiPo pull losses.</p>"
            '</div>',
            unsafe_allow_html=True,
        )

    hipo_departed_records = departed[departed["hipo_flag"] == True].copy()
    regrettable_hipo = hipo_departed_records[hipo_departed_records["regrettable_flag"] == "Yes"]
    lo, hi = replacement_cost_range(regrettable_hipo) if len(regrettable_hipo) else (0.0, 0.0)
    st.markdown(
        f'<div class="exec-impact">Replacing these {len(regrettable_hipo)} regrettable HiPo exits could cost '
        f'between ${lo / 1e6:.1f}M and ${hi / 1e6:.1f}M. Retaining a fraction of this group would fund the '
        f'entire intervention programme.</div>',
        unsafe_allow_html=True,
    )
