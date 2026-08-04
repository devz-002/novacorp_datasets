"""Feature audit for the Flight Risk Scorer (flight_risk_model.py).

Answers: is the current feature set appropriate, and does the model's
feature importance actually support the Executive Story's hypothesis?
Run: `python flight_risk_audit.py`. Produces three PNGs in outputs/figures/
and prints the correlation/VIF/coefficient/backward-elimination tables this
file's docstring and the accompanying write-up are based on.

Two data-quality fixes applied here that flight_risk_model.py does not need
(that script only scores; this one does formal inference, which is more
sensitive to them):

1. `performance_rating_Unknown` and `promotion_recommendation_Unknown` are
   the exact same 109 employees (perfect overlap, confirmed by crosstab) --
   brand-new hires (avg tenure 2.7 months) with 0 of 109 attrited. Including
   both causes infinite VIF (perfect collinearity); including either alone
   still causes quasi-complete separation in statsmodels' Logit (a singular
   Hessian) because 0/109 is a deterministic outcome. They are excluded from
   the inferential (statsmodels) fit below and documented as an artifact,
   not a real predictor, in the feature audit.
2. `has_survey_data` has VIF=24.9 and is statistically non-identifiable once
   the above rows are removed (p=0.999, CI up to infinity) -- it is kept in
   flight_risk_model.py's operational scorer (where predictive ranking, not
   coefficient interpretation, is the goal) but flagged here as a removal
   candidate for any model used to interpret coefficients.
"""
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from statsmodels.stats.outliers_influence import variance_inflation_factor

from data_utils import build_full, load_raw
from flight_risk_model import (
    BINARY_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES, RANDOM_STATE,
    build_model_table, build_preprocessor, get_feature_names,
)

warnings.filterwarnings("ignore")
FIG_DIR = "outputs/figures"


# =============================================================================
# PART 1 -- feature audit (classification is reasoned from the evidence
# gathered in parts 2-4 below; this dict is the conclusion, not an assumption)
# =============================================================================
FEATURE_AUDIT = {
    "tenure_months":            ("Essential", "Dominant Gini (0.359) and permutation importance (0.091); "
                                  "significant in LR (OR=0.75, p=0.004). Caveat: measured at-exit for "
                                  "leavers vs. still-accumulating for actives -- a structural asymmetry, "
                                  "not clean leakage, but it inflates apparent predictive power somewhat."),
    "survey_response_rate":     ("Essential", "The single strongest predictor in every method tried: Gini "
                                  "0.478, permutation importance 0.200, LR OR=0.51 (95% CI 0.47-0.55, "
                                  "p<0.001, the tightest CI of any feature)."),
    "legacy_entity_code":       ("Essential", "Entity_C: OR=0.064 (95% CI 0.033-0.124, p<0.001) -- large, "
                                  "precise, and independently confirms the earlier Entity_C investigation. "
                                  "NovaCorp-Origin also significant (OR=1.39)."),
    "hipo_flag":                ("Essential", "The one hypothesis-relevant feature that survives full "
                                  "multivariate control: OR=1.60 (95% CI 1.26-2.03, p<0.001)."),
    "age_band":                 ("Potential bias", "Statistically the largest effect in the dataset "
                                  "(60+ = OR 2.48, monotonic, 4 of 8 bands significant) -- but it is a "
                                  "protected characteristic, checked and ruled out as a retirement artifact "
                                  "(no retirement exit-reason category exists), and its root cause is "
                                  "unexplained. Predictive power and appropriate use are in tension here."),
    "performance_rating":       ("Useful", "No individual category is significant in the LR table, but the "
                                  "feature contributes to Gini/permutation importance via its 'Unknown' "
                                  "level -- which is itself an artifact (see below). The known categories "
                                  "(Outstanding..Unsatisfactory) carry real if modest signal."),
    "compa_ratio":               ("Useful", "Not predictive (OR=0.96, 95% CI 0.89-1.04, p=0.33) -- but "
                                  "essential to KEEP in the model precisely to test the hypothesis, not "
                                  "because it helps predict."),
    "promotion_recommendation":  ("Useful", "Not significant (OR=0.92, p=0.50) -- kept for the same "
                                  "hypothesis-testing reason as compa_ratio."),
    "department":               ("Useful", "Not significant in the multivariate model (all CIs cross 1) "
                                  "and zero permutation importance -- but it's the operationally actionable "
                                  "grain the Executive Story recommends against, so it stays for that "
                                  "reason even though it adds no independent predictive power here."),
    "role_level":                ("Redundant", "OR=0.96, p=0.34, permutation importance 0.0000. No "
                                  "measurable contribution once tenure and department are present."),
    "promotion_eligible":        ("Redundant", "OR=1.04, p=0.67. Nearly identical role_level means between "
                                  "eligible/not-eligible groups (1.586 vs 1.573) -- carries almost no "
                                  "independent information."),
    "goal_achievement_score":    ("Redundant", "OR=1.05, p=0.45, permutation importance 0.0000."),
    "engagement_mean":           ("Redundant", "Mathematically the mean of 8 sub-scores including "
                                  "wellbeing and psychological_safety (r=0.59 with both) -- including it "
                                  "alongside its own components is a built-in redundancy, and it is not "
                                  "significant on its own (p=0.067)."),
    "psychological_safety":      ("Redundant", "A component of engagement_mean (r=0.59); OR=1.06, p=0.23."),
    "wellbeing":                 ("Redundant", "A component of engagement_mean (r=0.59); OR=1.01, p=0.81."),
    "has_survey_data":           ("Potential leakage", "VIF=24.9 (highest of any feature). Statistically "
                                  "non-identifiable once the Unknown-performance-rating rows are removed "
                                  "(p=0.999, CI extends to infinity). More importantly: we cannot rule out "
                                  "that missing survey data is a CONSEQUENCE of already being on an exit "
                                  "path (e.g. removed from distribution lists) rather than a cause of it -- "
                                  "flagged, not concluded, exactly like the Entity_C case."),
    "performance_rating_Unknown / promotion_recommendation_Unknown (category)":
                                 ("Potential leakage", "Perfectly collinear with each other (VIF=inf, "
                                  "identical 109-person population). Both are the same artifact: employees "
                                  "with ~2.7 months average tenure who haven't had a first review yet, "
                                  "0 of 109 attrited by construction. Recommend replacing with an explicit "
                                  "'new hire, no review yet' flag rather than an unlabeled 'Unknown' category."),
}


def build_correlation_and_vif(X_train, preprocessor_fitted, feat_names):
    corr = X_train[NUMERIC_FEATURES].corr()
    Xt = preprocessor_fitted.transform(X_train)
    Xt = Xt.toarray() if hasattr(Xt, "toarray") else Xt
    vif = pd.DataFrame({
        "feature": feat_names,
        "VIF": [variance_inflation_factor(Xt, i) for i in range(Xt.shape[1])],
    }).sort_values("VIF", ascending=False)
    return corr, vif


def fit_interpretable_logit(X, y):
    """statsmodels Logit with the perfect-separation artifact population
    excluded (see module docstring), for valid coefficients/CIs/p-values."""
    known_mask = X["performance_rating"] != "Unknown"
    Xk, yk = X.loc[known_mask], y.loc[known_mask]
    X_train, X_test, y_train, y_test = train_test_split(
        Xk, yk, test_size=0.25, stratify=yk, random_state=RANDOM_STATE,
    )
    pre = build_preprocessor()
    Xt_train = pre.fit_transform(X_train)
    Xt_train = Xt_train.toarray() if hasattr(Xt_train, "toarray") else Xt_train
    names = get_feature_names(pre)
    nonconstant = [i for i in range(Xt_train.shape[1]) if Xt_train[:, i].std() > 1e-8]
    Xt_clean = Xt_train[:, nonconstant]
    names_clean = [names[i] for i in nonconstant]

    result = sm.Logit(y_train.values, sm.add_constant(Xt_clean)).fit(disp=0, method="newton", maxiter=200)
    params, conf, pvals = result.params[1:], result.conf_int()[1:], result.pvalues[1:]
    table = pd.DataFrame({
        "feature": names_clean, "coef": params, "odds_ratio": np.exp(params),
        "ci_low": np.exp(conf[:, 0]), "ci_high": np.exp(conf[:, 1]), "p_value": pvals,
    }).sort_values("odds_ratio", ascending=False)
    table["significant_95"] = (table["ci_low"] > 1) | (table["ci_high"] < 1)
    return table, result.prsquared


def backward_elimination(X_train, X_test, y_train, y_test):
    def make_pre(num, binf, catf):
        parts = []
        if num:
            parts.append(("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), num))
        if binf:
            parts.append(("bin", "passthrough", binf))
        if catf:
            parts.append(("cat", OneHotEncoder(handle_unknown="ignore", drop="first"), catf))
        return ColumnTransformer(parts)

    def score(num, binf, catf, label):
        cols = num + binf + catf
        pre = make_pre(num, binf, catf)
        dt = Pipeline([("pre", pre), ("clf", DecisionTreeClassifier(
            max_depth=5, min_samples_leaf=30, class_weight="balanced", random_state=RANDOM_STATE))])
        dt.fit(X_train[cols], y_train)
        auc_dt = roc_auc_score(y_test, dt.predict_proba(X_test[cols])[:, 1])
        lr = Pipeline([("pre", make_pre(num, binf, catf)), ("clf", LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE))])
        lr.fit(X_train[cols], y_train)
        auc_lr = roc_auc_score(y_test, lr.predict_proba(X_test[cols])[:, 1])
        return {"step": label, "n_features": len(cols), "dt_auc": auc_dt, "lr_auc": auc_lr}

    steps = [
        score(NUMERIC_FEATURES, BINARY_FEATURES, CATEGORICAL_FEATURES, "Full set (16 raw features)"),
        score(["tenure_months", "survey_response_rate"], ["has_survey_data"],
              ["legacy_entity_code", "performance_rating"], "Drop zero-importance features (5)"),
        score(["tenure_months", "survey_response_rate"], [],
              ["legacy_entity_code", "performance_rating"], "Also drop has_survey_data (4)"),
        score(["tenure_months", "survey_response_rate"], [], ["legacy_entity_code"], "Also drop performance_rating (3)"),
        score(["tenure_months", "survey_response_rate"], [], [], "tenure + survey_response_rate only (2)"),
    ]
    return pd.DataFrame(steps)


def main():
    emp, att, eng, perf = load_raw()
    full = build_full(emp, att, eng, perf)
    X, y, df = build_model_table(full)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=RANDOM_STATE,
    )

    # ---------------------------------------------------------------- Part 1
    print("=" * 70, "\nPART 1 -- FEATURE AUDIT\n", "=" * 70, sep="")
    audit_df = pd.DataFrame(FEATURE_AUDIT).T.reset_index()
    audit_df.columns = ["feature", "classification", "reasoning"]
    print(audit_df.to_string(index=False))
    audit_df.to_csv("outputs/feature_audit.csv", index=False)

    # ---------------------------------------------------------------- Part 2
    print("\n" + "=" * 70, "\nPART 2 -- CORRELATION & VIF\n", "=" * 70, sep="")
    pre = build_preprocessor()
    pre.fit(X_train)
    names = get_feature_names(pre)
    corr, vif = build_correlation_and_vif(X_train, pre, names)
    print("\nNumeric correlation matrix:\n", corr.round(2))
    print("\nPairs with |r| > 0.5:")
    for i in range(len(NUMERIC_FEATURES)):
        for j in range(i + 1, len(NUMERIC_FEATURES)):
            r = corr.iloc[i, j]
            if abs(r) > 0.5:
                print(f"  {NUMERIC_FEATURES[i]} <-> {NUMERIC_FEATURES[j]}: r={r:.2f}")
    print("\nTop 10 VIF (post one-hot encoding):\n", vif.head(10).to_string(index=False))

    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1, ax=ax, square=True)
    ax.set_title("Numeric feature correlation matrix")
    plt.tight_layout()
    plt.savefig(f"{FIG_DIR}/flight_risk_correlation.png", dpi=150)
    plt.close()

    # ---------------------------------------------------------------- Part 3
    print("\n" + "=" * 70, "\nPART 3 -- GINI vs PERMUTATION IMPORTANCE\n", "=" * 70, sep="")
    dt = Pipeline([("pre", build_preprocessor()), ("clf", DecisionTreeClassifier(
        max_depth=5, min_samples_leaf=30, class_weight="balanced", random_state=RANDOM_STATE))])
    dt.fit(X_train, y_train)
    gini = pd.Series(dt.named_steps["clf"].feature_importances_, index=get_feature_names(dt.named_steps["pre"])).sort_values(ascending=False)
    perm = permutation_importance(dt, X_test, y_test, scoring="roc_auc", n_repeats=20, random_state=RANDOM_STATE, n_jobs=-1)
    perm_s = pd.Series(perm.importances_mean, index=X_test.columns).sort_values(ascending=False)
    print("\nGini importance (one-hot level, top 8):\n", gini.head(8).round(3))
    print("\nPermutation importance (semantic feature level, ROC AUC drop):\n", perm_s.round(4))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    gini.head(8).sort_values().plot.barh(ax=axes[0], color="#e34948")
    axes[0].set_title("Decision Tree: Gini importance (top 8)")
    perm_s[perm_s > 0].sort_values().plot.barh(ax=axes[1], color="#2a78d6")
    axes[1].set_title("Decision Tree: permutation importance (ROC AUC drop)")
    plt.tight_layout()
    plt.savefig(f"{FIG_DIR}/flight_risk_importance.png", dpi=150)
    plt.close()

    # ---------------------------------------------------------------- Part 4
    print("\n" + "=" * 70, "\nPART 4 -- LOGISTIC REGRESSION: COEFFICIENTS, ODDS RATIOS, 95% CI\n", "=" * 70, sep="")
    lr_table, pseudo_r2 = fit_interpretable_logit(X, y)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 160)
    print(lr_table.round(3).to_string(index=False))
    print(f"\nPseudo R-squared: {pseudo_r2:.3f}")
    lr_table.to_csv("outputs/flight_risk_lr_coefficients.csv", index=False)

    sig = lr_table[lr_table["significant_95"]].sort_values("odds_ratio")
    fig, ax = plt.subplots(figsize=(8, max(4, len(sig) * 0.4)))
    y_pos = np.arange(len(sig))
    ax.errorbar(
        sig["odds_ratio"], y_pos,
        xerr=[sig["odds_ratio"] - sig["ci_low"], sig["ci_high"] - sig["odds_ratio"]],
        fmt="o", color="#0b0b0b", ecolor="#898781", capsize=3,
    )
    ax.axvline(1.0, color="#e34948", linestyle="--", linewidth=1)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sig["feature"])
    ax.set_xlabel("Odds ratio (95% CI)")
    ax.set_title("Statistically significant predictors only (CI excludes 1.0)")
    plt.tight_layout()
    plt.savefig(f"{FIG_DIR}/flight_risk_odds_ratios.png", dpi=150)
    plt.close()

    # ---------------------------------------------------------------- Part 5
    print("\n" + "=" * 70, "\nPART 5 -- MODEL SIMPLIFICATION (BACKWARD ELIMINATION)\n", "=" * 70, sep="")
    elim = backward_elimination(X_train, X_test, y_train, y_test)
    print(elim.round(3).to_string(index=False))

    print("\nAll figures saved to outputs/figures/. Tables saved to outputs/.")
    return {"audit_df": audit_df, "corr": corr, "vif": vif, "gini": gini, "perm": perm_s,
            "lr_table": lr_table, "elim": elim}


if __name__ == "__main__":
    main()
