"""Flight Risk Model tab -- an operational decision-support tool for HR
Business Partners, separate from the Executive Story.

The Executive Story answers WHY NovaCorp has a regrettable-attrition
problem. This tab answers WHO to act on and HOW to find them -- its
centrepiece is the HR Watchlist (Section 3), a filterable, exportable,
ranked employee list. Nothing on this page repeats the Executive Story's
recommendations or its "how HR acts on a flagged employee" workflow --
that content lives there and only there.

ARCHITECTURE: this page reads pre-computed artifacts from outputs/ rather
than retraining scikit-learn/statsmodels models on every Streamlit page
load. That keeps the interactive dashboard's dependencies to
pandas/streamlit/plotly (the only import here) and keeps this page fast.
The artifacts are produced by flight_risk_model.py and flight_risk_audit.py
-- run `python flight_risk_model.py && python flight_risk_audit.py` to
regenerate them if the underlying data changes. Single headline numbers
(accuracy, precision, recall, ROC AUC, Gini/permutation importance) are
copied from that validated output as module-level constants below.

The Watchlist (Section 3) is the one place on this page that shows
employee_id -- deliberately, since this tab is an operational tool for HR
Business Partners who need to act on named individuals, unlike the
Executive Story's board-level, aggregate-only framing. IDs only, never
names or salaries, consistent with the rest of the app.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

MUTED = "#898781"
SURFACE_TINT = "#f5f4ef"
ACCENT = "#e34948"
BLUE = "#2a78d6"

# ---------------------------------------------------------------------------
# Validated, pre-computed model results (flight_risk_model.py, test set
# n=3,351, 25% holdout, stratified, random_state=42). Not recomputed live.
# ---------------------------------------------------------------------------
MODEL_METRICS = {
    "Logistic Regression": {
        "accuracy": 0.756, "precision": 0.224, "recall": 0.540, "roc_auc": 0.698,
        "cm": [[2346, 655], [161, 189]],
    },
    "Decision Tree": {
        "accuracy": 0.876, "precision": 0.434, "recall": 0.600, "roc_auc": 0.833,
        "cm": [[2727, 274], [140, 210]],
    },
}

# Four signals this page highlights (Compa Ratio and Promotion Recommendation
# are intentionally excluded from the chart -- near-zero permutation
# importance, they explain WHY not WHO, and stay in the Executive Story).
SIGNAL_FEATURES = ["Survey Participation", "Tenure", "HiPo", "Legacy Entity"]
GINI_BY_SIGNAL = {"Survey Participation": 0.478, "Tenure": 0.359, "HiPo": 0.000, "Legacy Entity": 0.059}
PERM_BY_SIGNAL = {"Survey Participation": 0.1995, "Tenure": 0.0908, "HiPo": 0.0000, "Legacy Entity": 0.0209}
PERM_OTHER = {"Compa Ratio": 0.0000, "Promotion Recommendation": 0.0000}

GINI_IMPORTANCE_FULL = [
    ("Survey Participation", 0.478), ("Tenure", 0.359), ("Has Survey Data", 0.064),
    ("Legacy Entity (Entity_C)", 0.059), ("Performance Rating (Unknown)", 0.039), ("Wellbeing", 0.002),
]

FINAL_FEATURES = ["Tenure", "Survey Participation", "Legacy Entity", "Performance Rating"]
FINAL_FEATURES_AUC = 0.835  # flight_risk_audit.py Part 5, Decision Tree, 4-feature set
FULL_FEATURES_AUC = 0.833   # same model, all 16 raw features


@st.cache_data
def _load_scores():
    scores = pd.read_csv("outputs/flight_risk_scores.csv")
    scores = scores.sort_values(
        ["dt_probability", "lr_probability"], ascending=False,
    ).reset_index(drop=True)
    n = len(scores)
    top20_cut, top50_cut = round(n * 0.20), round(n * 0.50)
    scores["Risk Tier"] = "Low"
    scores.loc[scores.index < top50_cut, "Risk Tier"] = "Medium"
    scores.loc[scores.index < top20_cut, "Risk Tier"] = "High"
    return scores


@st.cache_data
def _load_roc_curve():
    return pd.read_csv("outputs/flight_risk_roc_curve.csv")


@st.cache_data
def _load_lr_coefficients():
    return pd.read_csv("outputs/flight_risk_lr_coefficients.csv")


def _inject_style():
    st.markdown(f"""
    <style>
    .frm-hero {{
        font-size: 2rem; font-weight: 700; line-height: 1.2; margin: 0 0 0.6rem 0;
    }}
    .frm-sub {{
        font-size: 1.02rem; color: #4b4a45; line-height: 1.5; margin: 0 0 1.8rem 0;
        max-width: 780px;
    }}
    .frm-section {{
        font-size: 1.4rem; font-weight: 700; margin: 3rem 0 0.4rem 0;
    }}
    .frm-caption {{
        font-size: 0.95rem; color: #4b4a45; margin: 0.4rem 0 1.2rem 0; max-width: 760px;
        line-height: 1.5;
    }}
    .frm-signal-card {{
        border-top: 2px solid {ACCENT}; padding: 0.7rem 0.9rem 0.9rem 0; height: 100%;
    }}
    .frm-signal-card h4 {{
        margin: 0 0 0.3rem 0; font-size: 0.92rem; font-weight: 700;
    }}
    .frm-signal-card p {{
        margin: 0; font-size: 0.88rem; color: #4b4a45; line-height: 1.45;
    }}
    .frm-driver-box {{
        border-left: 2px solid {MUTED}; padding: 0.2rem 0 0.2rem 1rem; margin: 1.2rem 0 0 0;
        max-width: 780px; font-size: 0.9rem; color: #4b4a45; line-height: 1.5;
    }}
    </style>
    """, unsafe_allow_html=True)


def render_flight_risk_tab(full, style_fig, CATEGORICAL):
    """Everything for the Flight Risk Model tab. Called from app.py inside a
    `with tab:` block, immediately after the Executive Story tab.

    Args:
        full: the UNFILTERED employee-level dataframe from app.py's build_full()
            -- kept for signature symmetry; the Watchlist and charts here read
            from the pre-scored outputs/flight_risk_scores.csv instead, since
            that's the validated, already-ranked population.
        style_fig: the existing style_fig() function from app.py.
        CATEGORICAL: the existing color palette list from app.py (unused --
            this tab defines its own small palette so filter/tier colours
            stay stable regardless of the shared app palette's order).
    """
    _inject_style()
    scores = _load_scores()

    # =======================================================================
    # SECTION 1 -- Executive Summary
    # =======================================================================
    st.markdown('<div class="frm-hero">From Insight to Action</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="frm-sub">The Executive Story explains why NovaCorp loses employees. '
        'The Flight Risk Model shows HR who to prioritise next.</div>',
        unsafe_allow_html=True,
    )
    k1, k2 = st.columns(2)
    k1.metric("Active employees scored", f"{len(scores):,}")
    k2.metric("High risk employees", f"{(scores['Risk Tier'] == 'High').sum():,}")

    # =======================================================================
    # SECTION 2 -- What predicts flight risk?
    # =======================================================================
    st.markdown('<div class="frm-section">What predicts flight risk?</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="frm-caption">These signals show who to watch. They do not explain '
        'why people leave.</div>',
        unsafe_allow_html=True,
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=SIGNAL_FEATURES, y=[GINI_BY_SIGNAL[f] for f in SIGNAL_FEATURES],
        name="Gini importance", marker_color=MUTED,
        hovertemplate="%{x}: %{y:.3f}<extra>Gini</extra>",
    ))
    fig.add_trace(go.Bar(
        x=SIGNAL_FEATURES, y=[PERM_BY_SIGNAL[f] for f in SIGNAL_FEATURES],
        name="Permutation importance", marker_color=ACCENT,
        hovertemplate="%{x}: %{y:.3f}<extra>Permutation</extra>",
    ))
    fig.update_layout(title="Two ways to measure predictive strength agree", yaxis_title="Importance", barmode="group")
    st.plotly_chart(style_fig(fig, height=320, showlegend=True), use_container_width=True)

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(
            '<div class="frm-signal-card"><h4>Survey Participation</h4>'
            '<p>Flag employees whose survey response rate is dropping.</p></div>',
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            '<div class="frm-signal-card"><h4>Tenure</h4>'
            '<p>Watch new hires (26.9% leave) and 5+ year disengaged staff (48.0%).</p></div>',
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            '<div class="frm-signal-card"><h4>HiPo</h4>'
            '<p>Prioritise HiPo employees. Their departure costs the most.</p></div>',
            unsafe_allow_html=True,
        )
    with s4:
        st.markdown(
            '<div class="frm-signal-card"><h4>Legacy Entity</h4>'
            '<p>Deprioritise Entity_C, consistently low risk. Focus on Entity_B instead.</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="frm-driver-box">Compa ratio and promotion recommendation explain WHY, '
        'not WHO. See the Executive Story.</div>',
        unsafe_allow_html=True,
    )

    # =======================================================================
    # SECTION 3 -- HR Watchlist (the operational output)
    # =======================================================================
    st.markdown('<div class="frm-section">HR Watchlist</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="frm-caption">Filter, search and export employees to act on today.</div>',
        unsafe_allow_html=True,
    )

    watchlist = scores.copy()
    watchlist["Tenure (yrs)"] = (watchlist["tenure_months"] / 12).round(1)
    watchlist["HiPo"] = watchlist["hipo_flag"].map({1: "Yes", 0: "No"})
    watchlist["Predicted Flight Risk"] = (watchlist["dt_probability"] * 100).round(1)
    watchlist["Survey Participation"] = (watchlist["survey_response_rate"] * 100).round(0)
    watchlist = watchlist.rename(columns={
        "employee_id": "Employee ID", "department": "Department", "role_level": "Role Level",
    })
    display_cols = [
        "Employee ID", "Department", "Role Level", "HiPo", "Tenure (yrs)",
        "Predicted Flight Risk", "Risk Tier", "Survey Participation",
    ]
    watchlist = watchlist[display_cols]

    f1, f2, f3, f4 = st.columns([2, 1.6, 1, 2])
    with f1:
        dept_filter = st.multiselect("Department", sorted(watchlist["Department"].unique()), key="frm_dept")
    with f2:
        tier_filter = st.multiselect("Risk Tier", ["High", "Medium", "Low"], key="frm_tier")
    with f3:
        hipo_filter = st.selectbox("HiPo", ["All", "Yes", "No"], key="frm_hipo")
    with f4:
        search = st.text_input("Search Employee ID", key="frm_search", placeholder="e.g. E01234")

    filtered = watchlist.copy()
    if dept_filter:
        filtered = filtered[filtered["Department"].isin(dept_filter)]
    if tier_filter:
        filtered = filtered[filtered["Risk Tier"].isin(tier_filter)]
    if hipo_filter != "All":
        filtered = filtered[filtered["HiPo"] == hipo_filter]
    if search:
        filtered = filtered[filtered["Employee ID"].str.contains(search, case=False, na=False)]
    filtered = filtered.sort_values("Predicted Flight Risk", ascending=False)

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "Predicted Flight Risk": st.column_config.ProgressColumn(
                "Predicted Flight Risk", format="%.1f%%", min_value=0, max_value=100,
            ),
            "Survey Participation": st.column_config.NumberColumn("Survey Participation", format="%.0f%%"),
            "Tenure (yrs)": st.column_config.NumberColumn("Tenure (yrs)", format="%.1f yrs"),
        },
    )
    st.caption(f"{len(filtered):,} of {len(watchlist):,} active employees shown.")

    st.download_button(
        "Download CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="flight_risk_watchlist.csv",
        mime="text/csv",
    )

    # =======================================================================
    # Responsible AI Considerations
    # =======================================================================
    st.markdown("<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)
    with st.expander("Responsible AI Considerations"):
        st.markdown("""
- High scores are relative risk, not certainty. Use judgement.
- The model supports decisions. It does not replace managers.
- Age is statistically relevant but not for direct HR decisions.
- Read every score alongside real business context.
""")

    # =======================================================================
    # SECTION 4 -- Model Performance (technical detail, collapsed by default)
    # =======================================================================
    with st.expander("Model Performance (technical detail)"):
        st.markdown("**Evaluation metrics** (25% holdout test set, n=3,351)")
        mcol1, mcol2 = st.columns(2)
        for col, (name, m) in zip([mcol1, mcol2], MODEL_METRICS.items()):
            with col:
                st.markdown(f"**{name}**")
                st.markdown(
                    f"Accuracy {m['accuracy']:.3f} · Precision {m['precision']:.3f} · "
                    f"Recall {m['recall']:.3f} · ROC AUC {m['roc_auc']:.3f}"
                )
                cm = m["cm"]
                fig = go.Figure(go.Heatmap(
                    z=cm, x=["Predicted: stays", "Predicted: leaves"],
                    y=["Actual: stays", "Actual: leaves"],
                    text=cm, texttemplate="%{text}", colorscale=[[0, SURFACE_TINT], [1, ACCENT]],
                    showscale=False, hovertemplate="%{y} / %{x}: %{z}<extra></extra>",
                ))
                fig.update_layout(title="Confusion matrix", height=280)
                st.plotly_chart(style_fig(fig, height=280), use_container_width=True)

        st.markdown("**ROC curve**")
        roc_df = _load_roc_curve()
        fig = go.Figure()
        for model_name, color in [("Logistic Regression", BLUE), ("Decision Tree", ACCENT)]:
            sub = roc_df[roc_df["model"] == model_name]
            fig.add_trace(go.Scatter(
                x=sub["fpr"], y=sub["tpr"], mode="lines", name=model_name,
                line=dict(color=color, width=2),
                hovertemplate=f"{model_name}<extra></extra>",
            ))
        fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=MUTED, dash="dash", width=1),
                                  showlegend=False, hoverinfo="skip"))
        fig.update_layout(title="ROC curve", xaxis_title="False positive rate", yaxis_title="True positive rate")
        st.plotly_chart(style_fig(fig, height=380, showlegend=True), use_container_width=True)

        st.markdown("**Feature importance — Gini (Decision Tree)**")
        gini_labels = [g[0] for g in GINI_IMPORTANCE_FULL][::-1]
        gini_values = [g[1] for g in GINI_IMPORTANCE_FULL][::-1]
        fig = go.Figure(go.Bar(x=gini_values, y=gini_labels, orientation="h", marker_color=ACCENT,
                                text=[f"{v:.3f}" for v in gini_values], textposition="outside"))
        fig.update_layout(title="Gini importance", xaxis_title="Importance")
        st.plotly_chart(style_fig(fig, height=280), use_container_width=True)

        st.markdown("**Permutation importance — all features tested**")
        perm_all = {**PERM_BY_SIGNAL, **PERM_OTHER}
        perm_labels = list(perm_all.keys())[::-1]
        perm_values = list(perm_all.values())[::-1]
        fig = go.Figure(go.Bar(x=perm_values, y=perm_labels, orientation="h", marker_color=BLUE,
                                text=[f"{v:.3f}" for v in perm_values], textposition="outside"))
        fig.update_layout(title="Permutation importance (ROC AUC drop)", xaxis_title="Importance")
        st.plotly_chart(style_fig(fig, height=280), use_container_width=True)

        st.markdown("**Logistic Regression — odds ratios, 95% confidence intervals**")
        lr_table = _load_lr_coefficients()
        sig = lr_table[lr_table["significant_95"]].sort_values("odds_ratio")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sig["odds_ratio"], y=sig["feature"], mode="markers",
            marker=dict(size=9, color="#0b0b0b"),
            error_x=dict(
                type="data", symmetric=False,
                array=sig["ci_high"] - sig["odds_ratio"],
                arrayminus=sig["odds_ratio"] - sig["ci_low"],
                color=MUTED,
            ),
            hovertemplate="%{y}: OR=%{x:.2f}<extra></extra>",
        ))
        fig.add_vline(x=1.0, line_dash="dash", line_color=ACCENT)
        fig.update_layout(title="Statistically significant predictors only (CI excludes 1.0)", xaxis_title="Odds ratio (95% CI)")
        st.plotly_chart(style_fig(fig, height=max(300, len(sig) * 32)), use_container_width=True)

        st.markdown("**Feature selection**")
        st.markdown(
            f"The operational model uses {len(FINAL_FEATURES)} features "
            f"({', '.join(FINAL_FEATURES)}) after backward elimination, achieving "
            f"{FINAL_FEATURES_AUC:.3f} ROC AUC versus {FULL_FEATURES_AUC:.3f} for all 16 raw "
            f"features. No accuracy is lost by dropping the rest."
        )
        st.caption(
            "Full feature audit, correlation/VIF analysis and backward-elimination results are in "
            "flight_risk_audit.py and outputs/feature_audit.csv."
        )
