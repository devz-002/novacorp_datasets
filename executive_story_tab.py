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


def _inject_style(accent):
    st.markdown(f"""
    <style>
    .exec-eyebrow {{
        font-size: 0.78rem; font-weight: 600; letter-spacing: 0.08em;
        text-transform: uppercase; color: {MUTED}; margin-bottom: 0.4rem;
    }}
    .exec-hero-title {{
        font-size: 2.5rem; font-weight: 700; line-height: 1.18;
        margin: 0 0 1.1rem 0; max-width: 900px;
    }}
    .exec-callout {{
        border-left: 4px solid {accent}; background: {accent}0f;
        padding: 0.9rem 1.25rem; border-radius: 4px; font-size: 1.05rem;
        line-height: 1.5; margin: 0 0 2.2rem 0; max-width: 820px;
    }}
    .exec-section-q {{
        font-size: 1.55rem; font-weight: 700; margin: 3.2rem 0 0.3rem 0;
    }}
    .exec-insight {{
        font-size: 1rem; color: #4b4a45; margin: 0.6rem 0 0 0; max-width: 760px;
        line-height: 1.5;
    }}
    .exec-card {{
        border-top: 3px solid {accent}; padding-top: 0.7rem; height: 100%;
    }}
    .exec-card h4 {{
        margin: 0 0 0.4rem 0; font-size: 0.78rem; letter-spacing: 0.06em;
        text-transform: uppercase; color: {MUTED};
    }}
    .exec-card p {{
        margin: 0; font-size: 1.08rem; font-weight: 500; line-height: 1.45;
    }}
    .exec-impact {{
        border-left: 4px solid {accent}; background: {accent}0f;
        padding: 0.9rem 1.25rem; border-radius: 4px; margin-top: 1.6rem;
        font-size: 1.1rem; max-width: 820px;
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

    hipo_voluntary = departed[
        (departed["hipo_flag"]) & (departed["exit_type"].astype(str).str.lower() == "voluntary")
    ]
    hipo_pull = hipo_voluntary[hipo_voluntary["pathway"].astype(str).str.contains("pull", case=False, na=False)]
    pull_attrition_pct = len(hipo_pull) / len(hipo) * 100 if len(hipo) else float("nan")

    avg_wellbeing = full["wellbeing"].mean()

    # =======================================================================
    # SECTION 1 — Executive Hook
    # =======================================================================
    st.markdown('<div class="exec-eyebrow">The project\'s primary hypothesis</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="exec-hero-title">We are losing the employees NovaCorp can least afford to lose.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="exec-callout">High-potential employees are paid systematically below market. '
        'That gap tracks a real attrition gap, and it is sharpest among the HiPos being poached '
        'by competitors — NovaCorp\'s hardest, most expensive people to replace.</div>',
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("HiPo compa-ratio", f"{avg_hipo_compa:.2f}", help=f"vs {avg_nonhipo_compa:.2f} for the rest of the workforce")
    k2.metric("HiPo attrition", f"{hipo_attrition:.1f}%", help=f"vs {nonhipo_attrition:.1f}% for the rest of the workforce")
    k3.metric("Pull attrition", f"{pull_attrition_pct:.1f}%", help="Share of HiPo employees poached by competitors (n=" + str(len(hipo_pull)) + ")")
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
        f'<div class="exec-insight">HiPo employees leave at {hipo_attrition / nonhipo_attrition:.1f}x '
        f'the rate of everyone else — the group NovaCorp has invested the most in developing.</div>',
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
        f'<div class="exec-insight">HiPo employees consistently earn below their market midpoint '
        f'(avg {avg_hipo_compa:.2f}), while the rest of the workforce sits close to parity '
        f'(avg {avg_nonhipo_compa:.2f}).</div>',
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
        '<div class="exec-insight">HiPo employees who go on to leave already show weaker engagement, '
        'wellbeing and survey participation while still employed — the signal appears before the exit.</div>',
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
        hovertemplate="%{y} · %{x}: %{z:.0f}%% of HiPo lost to pull (n=%{customdata})<extra></extra>",
    ))
    fig.update_layout(title="% of HiPo employees lost to competitors — department x role level")
    st.plotly_chart(style_fig(fig, height=440), use_container_width=True)

    mask = n_pivot >= 5
    valid = pivot.where(mask) if mask.values.any() else pivot
    top_dept, top_level = valid.stack().idxmax()
    top_val = valid.loc[top_dept, top_level]
    st.markdown(
        f'<div class="exec-insight">{top_dept} at Level {top_level} loses {top_val:.0f}% of its HiPo talent '
        f'to competitors — HR should intervene here first.</div>',
        unsafe_allow_html=True,
    )

    # =======================================================================
    # SECTION 6 — Recommendation
    # =======================================================================
    st.markdown('<div class="exec-section-q">Recommendation</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div class="exec-card"><h4>Immediate</h4>'
            '<p>Correct compa-ratio for HiPo employees below 0.90, starting with the junior levels most exposed to pull exits.</p></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="exec-card"><h4>Medium term</h4>'
            '<p>Stand up a targeted retention and pay-review track for every HiPo employee flagged as pull-pathway risk.</p></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="exec-card"><h4>Long term</h4>'
            '<p>Redesign the pay-band framework so HiPo compression cannot recur as tenure and promotions accumulate.</p></div>',
            unsafe_allow_html=True,
        )

    hipo_departed_records = departed[departed["hipo_flag"] == True].copy()
    regrettable_hipo = hipo_departed_records[hipo_departed_records["regrettable_flag"] == "Yes"]
    lo, hi = replacement_cost_range(regrettable_hipo) if len(regrettable_hipo) else (0.0, 0.0)
    st.markdown(
        f'<div class="exec-impact">Estimated <strong>${lo:,.0f}–${hi:,.0f}</strong> replacement cost currently at risk '
        f'from regrettable HiPo exits alone ({len(regrettable_hipo)} people) — the funding case for this programme.</div>',
        unsafe_allow_html=True,
    )
