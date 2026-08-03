"""Executive Story tab — a scroll-only narrative built for a 3-minute pitch to
the CEO, CHRO and the Accenture judging panel.

Kept fully separate from app.py / data_utils.py / hypothesis_tabs.py so none
of the existing tabs need to change. render_executive_story_tab() re-presents
analysis already implemented in hypothesis_tabs.py as a single, always-on
narrative that deliberately ignores the sidebar's global filters, so the
story never changes shape underneath the audience mid-scroll.

Narrative logic (revised after statistical review): structural pay
compression does not independently predict who leaves. It is presented here
as a severity multiplier that raises the cost of losses driven by career
progression gaps and department concentration, not as the trigger itself.
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
        border-left: 2px solid {accent}; padding: 0.2rem 0 0.2rem 1.1rem;
        font-size: 1.05rem; line-height: 1.55; margin: 0 0 2.6rem 0; max-width: 780px;
    }}
    .exec-section-q {{
        font-size: 1.5rem; font-weight: 700; margin: 4.2rem 0 0.5rem 0;
    }}
    .exec-subhead {{
        font-size: 1.05rem; font-weight: 700; margin: 2.6rem 0 0.6rem 0; color: #4b4a45;
    }}
    .exec-insight {{
        font-size: 1rem; color: #4b4a45; margin: 0.7rem 0 0.5rem 0; max-width: 720px;
        line-height: 1.5;
    }}
    .exec-card {{
        border-top: 2px solid {accent}; padding: 0.85rem 0 0 0; height: 100%;
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
        border-left: 2px solid {accent}; padding: 0.2rem 0 0.2rem 1.1rem;
        margin-top: 2rem; font-size: 1.1rem; line-height: 1.5; max-width: 780px;
    }}
    .exec-footnote {{
        font-size: 0.78rem; color: {MUTED}; margin-top: 0.8rem; line-height: 1.45;
        max-width: 720px;
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
            with the other tabs; unused after the early-warning section was
            removed on statistical review).
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

    # --- core figures, computed once and reused across sections -----------
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

    hipo_departed_records = departed[departed["hipo_flag"] == True].copy()
    regrettable_hipo = hipo_departed_records[hipo_departed_records["regrettable_flag"] == "Yes"]
    lo, hi = replacement_cost_range(regrettable_hipo) if len(regrettable_hipo) else (0.0, 0.0)

    dept_hipo_total = hipo.groupby("department").size()
    dept_pull = hipo_pull.groupby("department").size().reindex(dept_hipo_total.index, fill_value=0)
    dept_pull_pct = (dept_pull / dept_hipo_total * 100).sort_values(ascending=False)
    risk_dept_1, risk_dept_2 = dept_pull_pct.index[0], dept_pull_pct.index[1]
    risk_pct_1, risk_pct_2 = dept_pull_pct.iloc[0], dept_pull_pct.iloc[1]
    risk_n_1, risk_n_2 = dept_hipo_total[risk_dept_1], dept_hipo_total[risk_dept_2]

    no_promo = hipo[hipo["promotion_recommendation"] == "No"]
    yes_promo = hipo[hipo["promotion_recommendation"] == "Yes"]
    no_total, yes_total = len(no_promo), len(yes_promo)
    no_departed = int((no_promo["status"] == "departed").sum())
    yes_departed = int((yes_promo["status"] == "departed").sum())
    no_active, yes_active = no_total - no_departed, yes_total - yes_departed
    no_rate = no_departed / no_total * 100 if no_total else float("nan")
    yes_rate = yes_departed / yes_total * 100 if yes_total else float("nan")
    pull_not_promoted = hipo_pull[hipo_pull["promotion_recommendation"] == "No"]

    below_090_active = hipo_active[hipo_active["compa_ratio"] < 0.90]

    # =======================================================================
    # SECTION 1 — Executive Hook
    # =======================================================================
    st.markdown('<div class="exec-eyebrow">Primary hypothesis</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="exec-hero-title">We are losing the employees NovaCorp can least afford to lose.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="exec-callout">High-potential employees earn structurally below market. '
        'This raises the cost when competitors poach them.</div>',
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("HiPo compa-ratio", f"{avg_hipo_compa:.2f}", help=f"Rest of workforce averages {avg_nonhipo_compa:.2f}.")
    k2.metric("HiPo attrition", f"{hipo_attrition:.1f}%", help=f"Rest of workforce leaves at {nonhipo_attrition:.1f}%.")
    k3.metric("Pull attrition", f"{pull_attrition_pct:.1f}%", help=f"{len(hipo_pull)} of {len(hipo):,} HiPo employees poached by competitors.")
    k4.metric("Regrettable HiPo exits", f"{len(regrettable_hipo)}", help=f"Estimated ${lo/1e6:.1f}M-${hi/1e6:.1f}M replacement cost.")

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
        title="HiPo employees leave 1.5 times more often than the rest of the workforce.",
        xaxis_title="% departed", xaxis=dict(range=[0, max(vals) * 1.35]),
    )
    st.plotly_chart(style_fig(fig, height=280), use_container_width=True)
    st.markdown(
        f'<div class="exec-insight">HiPo employees leave at {attrition_ratio:.1f} times the rate of the '
        f'rest of the workforce.</div>',
        unsafe_allow_html=True,
    )

    # =======================================================================
    # SECTION 3 — How are they different?
    # =======================================================================
    st.markdown('<div class="exec-section-q">How are they different?</div>', unsafe_allow_html=True)

    fig = go.Figure()
    for flag, color, label in [(False, BLUE, "Non-HiPo"), (True, RED, "HiPo")]:
        subset = full.loc[full["hipo_flag"] == flag, "compa_ratio"].dropna()
        fig.add_trace(go.Violin(
            y=subset, name=label, line_color=color, fillcolor=color, opacity=0.45,
            box_visible=True, meanline_visible=True, points=False,
            hovertemplate=f"{label}<extra></extra>",
        ))
    fig.add_hline(y=1.0, line_dash="dash", line_color=MUTED, annotation_text="Market midpoint (1.00)")
    fig.update_layout(
        title="HiPo employees are consistently paid below their market midpoint.",
        yaxis_title="Compa-ratio",
    )
    st.plotly_chart(style_fig(fig, height=420, showlegend=True), use_container_width=True)
    st.markdown(
        f'<div class="exec-insight">HiPo employees average a {avg_hipo_compa:.2f} compa ratio. '
        f'The rest of the workforce averages {avg_nonhipo_compa:.2f}.</div>',
        unsafe_allow_html=True,
    )

    # =======================================================================
    # SECTION 4 — Where is the problem concentrated?
    # =======================================================================
    st.markdown('<div class="exec-section-q">Where is the problem concentrated?</div>', unsafe_allow_html=True)

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

    mask = n_pivot >= 5
    pivot_display = pivot.where(mask)  # cells with n<5 render blank, not colored

    fig = go.Figure(go.Heatmap(
        z=pivot_display.values, x=[f"Level {c}" for c in pivot.columns], y=list(pivot.index),
        customdata=n_pivot.values,
        colorscale=[[0, SURFACE_TINT], [1, RED]],
        hovertemplate="%{y} · %{x}: %{z:.0f}%% lost to competitors (n=%{customdata})<extra></extra>",
    ))
    fig.update_layout(
        title=f"{risk_dept_1} and {risk_dept_2} concentrate the highest HiPo losses to competitors.",
    )
    st.plotly_chart(style_fig(fig, height=440), use_container_width=True)
    st.caption("Cells with fewer than 5 HiPo employees are left blank.")

    valid = pivot.where(mask) if mask.values.any() else pivot
    top_dept, top_level = valid.stack().idxmax()
    top_val = valid.loc[top_dept, top_level]
    top_n = n_pivot.loc[top_dept, top_level]
    st.markdown(
        f'<div class="exec-insight">{top_dept} Level {top_level} shows the highest concentration of HiPo '
        f'losses. {top_val:.0f}% of its HiPo employees leave for competitors (n={top_n}).</div>',
        unsafe_allow_html=True,
    )

    # =======================================================================
    # SECTION 5 — What makes these losses expensive?
    # =======================================================================
    st.markdown('<div class="exec-section-q">What makes these losses expensive?</div>', unsafe_allow_html=True)

    if no_total and yes_total:
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
        fig.update_layout(
            title="Employees denied promotion leave more often, especially to competitors.",
            font=dict(size=13),
        )
        st.plotly_chart(style_fig(fig, height=380), use_container_width=True)
        st.markdown(
            f'<div class="exec-insight">HiPo employees denied promotion leave more often, '
            f'{no_rate:.0f}% versus {yes_rate:.0f}% (n={no_total}, n={yes_total}).</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="exec-insight">Competitors poached {len(pull_not_promoted)} of {len(hipo_pull)} '
            f'HiPo employees denied promotion first.</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="exec-impact">Reducing regrettable HiPo departures could offset an estimated '
        f'${lo/1e6:.1f}M-${hi/1e6:.1f}M in replacement costs, based on standard replacement-cost '
        f'assumptions.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="exec-footnote">Based on {len(regrettable_hipo)} HiPo exits HR classified as '
        'regrettable, costed at the industry-standard 50-200% of exit salary. Compensation is treated '
        'as a cost multiplier on departures that occur, not an independent predictor of who leaves.</div>',
        unsafe_allow_html=True,
    )

    # =======================================================================
    # SECTION 6 — Decision for NovaCorp
    # =======================================================================
    st.markdown('<div class="exec-section-q">Decision for NovaCorp</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="exec-card"><h4>Act now</h4>'
            f'<p>Target {risk_dept_1} and {risk_dept_2} for immediate HiPo retention reviews.</p>'
            f'<p class="why">These two departments lose {risk_pct_1:.0f}% (n={risk_n_1}) and '
            f'{risk_pct_2:.0f}% (n={risk_n_2}) of HiPo talent to competitors.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="exec-card"><h4>Improve career progression</h4>'
            f'<p>Introduce mandatory promotion reviews for HiPo employees before external offers '
            f'become attractive.</p>'
            f'<p class="why">Employees denied promotion leave more often, and most poached HiPo '
            f'employees were denied promotion first.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="exec-card"><h4>Strengthen compensation governance</h4>'
            f'<p>Review pay for {len(below_090_active)} active HiPo employees below a 0.90 compa ratio '
            f'this cycle.</p>'
            f'<p class="why">Compensation raises the cost of regrettable departures rather than '
            f'independently predicting them.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
