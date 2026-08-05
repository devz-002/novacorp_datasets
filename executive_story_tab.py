"""Executive Story tab — a scroll-only narrative built for a 3-minute pitch to
the CEO, CHRO and the Accenture judging panel.

Kept fully separate from app.py / data_utils.py / hypothesis_tabs.py so none
of the existing tabs need to change. render_executive_story_tab() re-presents
analysis already implemented in hypothesis_tabs.py, plus validated output
from the Flight Risk Model (flight_risk_model.py / flight_risk_audit.py), as
a single narrative. app.py passes the sidebar-filtered `full_f`/`eng_f`
dataframes here (not the unfiltered `full`), so every number, chart and
insight on this page reacts live to the sidebar's global filters. Every
computation below is therefore written to degrade gracefully on a small or
narrow filtered population (see the department/heatmap fallback logic)
rather than assume firm-wide sample sizes.

Narrative logic: structural pay compression does not independently predict
who leaves -- it is a severity multiplier that raises the cost of losses
driven by career progression gaps and department concentration, not the
trigger itself. The Flight Risk Model operationalises this: it independently
confirmed survey participation and tenure as the strongest predictors of
who to monitor, confirmed HiPo status as a real driver after controlling
for other factors, and confirmed compa ratio adds no independent predictive
power (consistent with the business-explanation finding above).

BUSINESS EXPLANATION vs PREDICTIVE SIGNALS -- kept deliberately separate:
"business explanation" (pay, career progression, department) answers why
these departures are strategically expensive; "predictive signals" (survey
participation, tenure, HiPo) answer which employees HR should monitor next.
They are not the same claim and this file never conflates them.

PERM_IMPORTANCE below is not recomputed on every page load: retraining and
permutation-testing two models on ~13k rows on every Streamlit render would
be slow and would make scikit-learn/statsmodels hard runtime dependencies of
the interactive dashboard. The values are copied from flight_risk_audit.py's
validated, reproducible output (run `python flight_risk_audit.py` to
regenerate them) -- the same pattern already used for the 50-200%
replacement-cost multiplier below, a cited assumption rather than a live
computation. ROC AUC, confusion matrices, precision/recall and the model
comparison live in flight_risk_model.py / flight_risk_audit.py and their
outputs/ artifacts -- this page shows business interpretation only.
"""
import plotly.graph_objects as go
import streamlit as st

from data_utils import replacement_cost_range

MUTED = "#898781"
SURFACE_TINT = "#f5f4ef"

# From flight_risk_audit.py Part 3 (permutation importance, ROC AUC drop,
# Decision Tree, test set n=3,351). HiPo's tree-based importance is ~0 even
# though it is independently significant in the Logistic Regression
# (OR=1.60, 95% CI 1.26-2.03, p<0.001) -- the two models capture different
# aspects of risk, and the chart below annotates that explicitly rather than
# hiding it.
PERM_IMPORTANCE = [
    ("Survey Participation", 0.1995),
    ("Tenure", 0.0908),
    ("HiPo", 0.0000),
    ("Legacy Entity", 0.0209),
    ("Compa Ratio", 0.0000),
    ("Promotion Recommendation", 0.0000),
]


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
    .exec-stage {{
        font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase;
        color: {MUTED}; margin: 4.2rem 0 0.5rem 0;
    }}
    .exec-stage-num {{
        color: {accent}; font-weight: 700; margin-right: 0.5rem;
    }}
    .exec-section-q {{
        font-size: 1.5rem; font-weight: 700; margin: 0.2rem 0 0.5rem 0;
    }}
    .exec-section-q.decision {{
        font-size: 1.85rem; color: {accent};
    }}
    .exec-closer {{
        font-size: 1.6rem; font-weight: 700; line-height: 1.3; margin: 3rem 0 1rem 0;
        max-width: 700px;
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
    .exec-window {{
        border-top: 2px solid {MUTED}; padding: 0.7rem 0 0 0; height: 100%;
    }}
    .exec-window h4 {{
        margin: 0 0 0.3rem 0; font-size: 0.78rem; letter-spacing: 0.06em;
        text-transform: uppercase; color: {MUTED};
    }}
    .exec-window .stat {{
        font-size: 2rem; font-weight: 700; color: {accent}; margin: 0 0 0.3rem 0;
    }}
    .exec-window p {{
        margin: 0; font-size: 0.92rem; color: #4b4a45; line-height: 1.45;
    }}
    .exec-flow-step {{
        border: 1px solid #d8d6cd; border-radius: 4px; padding: 0.6rem 1rem;
        max-width: 480px; margin: 0 auto; text-align: center; font-size: 0.95rem;
        font-weight: 500;
    }}
    .exec-flow-step.decision {{
        border-style: dashed; font-style: italic; color: #4b4a45; font-weight: 400;
    }}
    .exec-flow-step.action {{
        border-color: {accent}; font-weight: 600;
    }}
    .exec-flow-arrow {{
        text-align: center; color: {MUTED}; font-size: 1.1rem; line-height: 1;
        margin: 0.25rem auto;
    }}
    </style>
    """, unsafe_allow_html=True)


def _flow_step(text, kind="normal"):
    cls = f"exec-flow-step {kind}".strip()
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)
    st.markdown('<div class="exec-flow-arrow">↓</div>', unsafe_allow_html=True)


def render_executive_story_tab(full, eng, style_fig, CATEGORICAL):
    """Everything for the Executive Story tab. Called from app.py inside a
    `with tab:` block.

    Args:
        full: the employee-level dataframe for the CURRENT sidebar selection
            (app.py passes full_f) -- every stat on this page is computed
            from whatever is passed in, so this page is filter-responsive.
        eng: the engagement dataframe for the current selection (kept for
            signature symmetry with the other tabs; unused after the
            early-warning section was removed on statistical review).
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
    # Filters can narrow the population to a single department -- fall back
    # to repeating it rather than indexing past the end of a 1-row series.
    risk_dept_1 = dept_pull_pct.index[0]
    risk_dept_2 = dept_pull_pct.index[1] if len(dept_pull_pct) > 1 else risk_dept_1
    dept_phrase = risk_dept_1 if risk_dept_1 == risk_dept_2 else f"{risk_dept_1} and {risk_dept_2}"

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

    # tenure windows (bucketed observed rates, not the LR coefficient -- see
    # module docstring / flight_risk_audit.py Part 1 for why)
    window1 = full[full["tenure_bucket"] == "<1y"]
    window1_rate = window1["attrited"].mean() * 100
    window2 = full[(full["tenure_months"] >= 60) & (full["low_responder"])]
    window2_rate = window2["attrited"].mean() * 100
    baseline_5y = full[full["tenure_months"] >= 60]
    baseline_5y_rate = baseline_5y["attrited"].mean() * 100
    window2_lift = window2_rate / baseline_5y_rate if baseline_5y_rate else float("nan")

    # =======================================================================
    # SECTION 1 — Executive Hook
    # =======================================================================
    st.markdown('<div class="exec-eyebrow">Primary hypothesis</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="exec-hero-title">NovaCorp\'s most expensive talent losses are concentrated, not widespread.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="exec-callout">High-potential employees earn below market. '
        'Losing them to competitors costs more as a result.</div>',
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("HiPo compa-ratio", f"{avg_hipo_compa:.2f}", help=f"Rest of workforce averages {avg_nonhipo_compa:.2f}.")
    k2.metric("HiPo attrition", f"{hipo_attrition:.1f}%", help=f"Rest of workforce leaves at {nonhipo_attrition:.1f}%.")
    k3.metric("Pull attrition", f"{pull_attrition_pct:.1f}%", help=f"{len(hipo_pull)} of {len(hipo):,} HiPo employees poached by competitors.")
    k4.metric("Regrettable HiPo exits", f"{len(regrettable_hipo)}", help=f"Estimated ${lo/1e6:.1f}M-${hi/1e6:.1f}M replacement cost.")

    # =======================================================================
    # STAGE 01 — PROBLEM (descriptive: what happened)
    # =======================================================================
    st.markdown('<div class="exec-stage"><span class="exec-stage-num">01</span>Problem</div>', unsafe_allow_html=True)
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
        title=f"HiPo employees leave {attrition_ratio:.1f} times more often than the rest of the workforce.",
        xaxis_title="% departed", xaxis=dict(range=[0, max(vals) * 1.35]),
    )
    st.plotly_chart(style_fig(fig, height=280), use_container_width=True)
    st.markdown(
        '<div class="exec-insight">NovaCorp loses hard-to-replace talent faster than the rest of '
        'the business.</div>',
        unsafe_allow_html=True,
    )

    # =======================================================================
    # STAGE 02 — BUSINESS EXPLANATION (diagnostic: why it matters strategically)
    # =======================================================================
    st.markdown('<div class="exec-stage"><span class="exec-stage-num">02</span>Business explanation</div>', unsafe_allow_html=True)
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
        f'<div class="exec-insight">HiPo employees average a {avg_hipo_compa:.2f} compa ratio versus '
        f'{avg_nonhipo_compa:.2f} for peers. That gap widens the cost of every departure.</div>',
        unsafe_allow_html=True,
    )

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
        title=f"{dept_phrase} concentrate the highest HiPo losses to competitors."
        if risk_dept_1 != risk_dept_2 else
        f"{dept_phrase} concentrates the highest HiPo losses to competitors.",
    )
    st.plotly_chart(style_fig(fig, height=440), use_container_width=True)
    st.caption("Cells with fewer than 5 HiPo employees are left blank.")

    valid = pivot.where(mask) if mask.values.any() else pivot
    top_dept, top_level = valid.stack().idxmax()
    top_val = valid.loc[top_dept, top_level]
    top_n = n_pivot.loc[top_dept, top_level]
    st.markdown(
        f'<div class="exec-insight">{top_dept} Level {top_level} loses {top_val:.0f}% of its HiPo talent '
        f'to competitors (n={top_n}). Retention effort here returns the most.</div>',
        unsafe_allow_html=True,
    )

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
            title="Employees denied promotion leave more often than those recommended.",
            font=dict(size=13),
        )
        st.plotly_chart(style_fig(fig, height=380), use_container_width=True)
        st.markdown(
            f'<div class="exec-insight">Denied promotion, HiPo employees leave at {no_rate:.0f}% versus '
            f'{yes_rate:.0f}% (n={no_total}, n={yes_total}). Competitors poached {len(pull_not_promoted)} '
            f'of {len(hipo_pull)} of them first.</div>',
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
    # STAGE 03 — OPERATIONAL PREDICTION (predictive: who should HR monitor)
    # =======================================================================
    st.markdown('<div class="exec-stage"><span class="exec-stage-num">03</span>Operational prediction</div>', unsafe_allow_html=True)
    st.markdown('<div class="exec-section-q">Who should HR monitor first?</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="exec-insight">An independent model tested which signals predict departure. '
        'Some confirm the hypothesis. Others do not.</div>',
        unsafe_allow_html=True,
    )

    labels_perm = [p[0] for p in PERM_IMPORTANCE][::-1]
    values_perm = [p[1] for p in PERM_IMPORTANCE][::-1]
    bar_colors = [RED if v > 0 else "#d8d6cd" for v in values_perm]
    fig = go.Figure(go.Bar(
        x=values_perm, y=labels_perm, orientation="h",
        marker_color=bar_colors,
        text=[f"{v:.3f}" for v in values_perm], textposition="outside",
        hovertemplate="%{y}: %{x:.3f} ROC AUC drop<extra></extra>",
    ))
    fig.add_annotation(
        x=0.06, y="HiPo", text="significant in regression, p<0.001", showarrow=False,
        font=dict(size=11, color=MUTED), xanchor="left",
    )
    fig.update_layout(
        title="Survey participation and tenure predict departure more than pay or promotion.",
        xaxis_title="Permutation importance (ROC AUC drop)",
    )
    st.plotly_chart(style_fig(fig, height=340), use_container_width=True)
    st.markdown(
        '<div class="exec-insight">Compa ratio and promotion recommendation add almost nothing to '
        'prediction. They remain business explanations, not monitoring triggers.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="exec-insight">HiPo shows low tree-based importance but stays significant in '
        'regression, even after every control.</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="exec-subhead">Two tenure windows, not one</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="exec-insight">Tenure does not simply fall as risk falls. The data shows two '
        'separate danger windows.</div>',
        unsafe_allow_html=True,
    )

    tw1, tw2 = st.columns(2)
    with tw1:
        st.markdown(
            f'<div class="exec-window"><h4>Window 1 · First year</h4>'
            f'<div class="stat">{window1_rate:.1f}%</div>'
            f'<p>Attrition among employees under 12 months tenure (n={len(window1):,}). '
            f'An onboarding and role-fit problem.</p></div>',
            unsafe_allow_html=True,
        )
    with tw2:
        st.markdown(
            f'<div class="exec-window"><h4>Window 2 · 5+ years, disengaging</h4>'
            f'<div class="stat">{window2_rate:.1f}%</div>'
            f'<p>Attrition among 5+ year employees with declining survey participation '
            f'(n={len(window2):,}), {window2_lift:.1f}x the 5+ year baseline. A long-term '
            f'disengagement problem, not onboarding.</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="exec-subhead">Survey participation is a signal, not a cause</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="exec-insight">Participation measures whether employees respond, not how they '
        'feel. It differs from engagement score.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="exec-insight">Participation may not cause attrition. It is simply the earliest '
        'signal available before departure.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="exec-insight">HR should treat declining participation as a trigger for a '
        'proactive retention conversation.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="exec-callout">NovaCorp\'s highest-value attrition risk is concentrated among '
        'HiPo employees. The Flight Risk Model identifies survey participation and tenure as the '
        'earliest operational signals for identifying these employees before they leave, while '
        'career progression and structural pay compression guide where retention interventions '
        'should be prioritised.</div>',
        unsafe_allow_html=True,
    )

    # =======================================================================
    # STAGE 04 — DECISION (prescriptive: what NovaCorp should do next)
    # =======================================================================
    st.markdown('<div class="exec-stage"><span class="exec-stage-num">04</span>Decision</div>', unsafe_allow_html=True)
    st.markdown('<div class="exec-section-q decision">Decision for NovaCorp</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            '<div class="exec-card"><h4>Immediate · 0-12 months tenure</h4>'
            '<p>Strengthen onboarding, manager check-ins and role-fit reviews for new HiPo hires.</p>'
            '<p class="why">First-year attrition reaches '
            f'{window1_rate:.1f}%. Early intervention addresses the largest single risk window.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="exec-card"><h4>Medium term · critical career stage</h4>'
            '<p>Use survey participation, tenure and HiPo status to trigger career and retention '
            'conversations.</p>'
            '<p class="why">Act before employees start looking externally, not after they receive '
            'an offer.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="exec-card"><h4>Long term · governance</h4>'
            '<p>Integrate compensation benchmarking, career reviews, succession planning and the '
            'Flight Risk Model into annual talent governance.</p>'
            '<p class="why">No single lever fixes this. Governance ties pay, career and prediction '
            'together.</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="exec-subhead">How HR acts on a flagged employee</div>', unsafe_allow_html=True)
    _flow_step("Flight Risk Model flags an employee", "action")
    _flow_step("Top 20% highest-risk employees identified", "action")
    _flow_step("Is the employee HiPo?", "decision")
    _flow_step("Is survey participation declining?", "decision")
    _flow_step("Are they in a critical tenure window?", "decision")
    _flow_step("Manager holds a retention discussion", "action")
    _flow_step("Career progression review", "action")
    _flow_step("Compensation review, if appropriate", "action")
    st.markdown('<div class="exec-flow-step action">Retention plan agreed</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="exec-closer">The fix is narrow. The payoff is not.</div>',
        unsafe_allow_html=True,
    )
