"""Flight Risk Scorer -- a supplementary ML analysis, separate from the
Executive Story tab.

Trains a Logistic Regression and a Decision Tree to predict `attrited`
(has this employee left NovaCorp) from a snapshot of employee attributes,
then scores every ACTIVE employee's probability of leaving so HR can rank
who to prioritise.

Run: `python flight_risk_model.py` (uses the same data_utils.load_raw() /
build_full() as the dashboard, so it reflects the same employee-level table
-- no new data sources, no new joins).

--------------------------------------------------------------------------
FEATURES DELIBERATELY EXCLUDED, AND WHY
--------------------------------------------------------------------------
`pathway`, `exit_type`, `regrettable_flag`, `stated_exit_reason`,
`performance_band_at_exit` and `salary_at_exit` all come from
attrition_log.csv -- they only exist for employees who have already left,
and are filled "Unknown" for active employees. Including them would leak
the target (pathway != "Unknown" implies attrited=True by construction) and
would be undefined for the very population this model exists to score
(currently active employees). They are excluded.

`gender` and `cultural_background` are excluded on responsible-AI grounds:
even though they're in the source data, scoring flight risk on protected
characteristics creates disparate-impact exposure for an HR-facing tool.
`age_band` was explicitly requested in scope and is kept, but the same
caveat applies -- if this were productionised, legal/HR should review its
use before any action is taken on age-correlated scores.

No `promotion_history` field exists in the source data (only a single
current-state `promotion_recommendation` snapshot and a `promotion_eligible`
flag) -- these are used as the closest available proxies.

--------------------------------------------------------------------------
A MODELING LIMITATION THAT MATTERS FOR HOW THESE SCORES SHOULD BE READ
--------------------------------------------------------------------------
Every employee's features come from their LATEST engagement/performance
record. For departed employees, "latest" often means their last data point
before leaving -- i.e. the model partly learns what someone's profile looks
like right before they resign, not necessarily what it looked like a
meaningful lead time beforehand. That does not invalidate relative ranking
(it still separates higher- from lower-risk employees), but it does mean
the probabilities should be read as "relative risk given current profile,"
not as a validated early-warning lead time.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from data_utils import build_full, load_raw

RANDOM_STATE = 42

NUMERIC_FEATURES = [
    "compa_ratio", "goal_achievement_score", "role_level", "tenure_months",
    "engagement_mean", "psychological_safety", "wellbeing", "survey_response_rate",
]
BINARY_FEATURES = ["hipo_flag", "promotion_eligible", "has_survey_data"]
CATEGORICAL_FEATURES = [
    "performance_rating", "promotion_recommendation", "department",
    "legacy_entity_code", "age_band",
]
ALL_FEATURES = NUMERIC_FEATURES + BINARY_FEATURES + CATEGORICAL_FEATURES


def build_model_table(full):
    """Feature table + target, one row per employee. `has_survey_data`
    captures informative missingness (no engagement.csv rows at all) before
    the median-impute step below fills the score columns."""
    df = full.copy()
    df["has_survey_data"] = df["survey_response_rate"].notna()
    df["hipo_flag"] = df["hipo_flag"].astype(int)
    df["promotion_eligible"] = df["promotion_eligible"].astype(int)
    df["has_survey_data"] = df["has_survey_data"].astype(int)
    y = df["attrited"].astype(int)
    X = df[ALL_FEATURES].copy()
    return X, y, df


def build_preprocessor():
    return ColumnTransformer([
        ("num", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), NUMERIC_FEATURES),
        ("bin", "passthrough", BINARY_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", drop="first"), CATEGORICAL_FEATURES),
    ])


def evaluate(name, y_test, y_pred, y_proba):
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)
    print(f"\n--- {name} ---")
    print(f"Accuracy:  {acc:.3f}")
    print(f"Precision: {prec:.3f}")
    print(f"Recall:    {rec:.3f}")
    print(f"ROC AUC:   {auc:.3f}")
    print(f"Confusion matrix [[TN FP] [FN TP]]:\n{cm}")
    return {"model": name, "accuracy": acc, "precision": prec, "recall": rec, "roc_auc": auc, "cm": cm}


def get_feature_names(preprocessor):
    num_names = NUMERIC_FEATURES
    bin_names = BINARY_FEATURES
    cat_names = list(preprocessor.named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES))
    return num_names + bin_names + cat_names


def main():
    emp, att, eng, perf = load_raw()
    full = build_full(emp, att, eng, perf)
    X, y, df = build_model_table(full)

    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, df.index, test_size=0.25, stratify=y, random_state=RANDOM_STATE,
    )
    print(f"Train: {len(X_train):,} employees ({y_train.mean()*100:.1f}% attrited)")
    print(f"Test:  {len(X_test):,} employees ({y_test.mean()*100:.1f}% attrited)")

    # ------------------------------------------------------------- Logistic
    pre_lr = build_preprocessor()
    lr = Pipeline([
        ("pre", pre_lr),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)),
    ])
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)
    lr_proba = lr.predict_proba(X_test)[:, 1]
    lr_result = evaluate("Logistic Regression", y_test, lr_pred, lr_proba)

    feat_names_lr = get_feature_names(lr.named_steps["pre"])
    lr_coefs = pd.Series(lr.named_steps["clf"].coef_[0], index=feat_names_lr).sort_values()
    lr_odds = np.exp(lr_coefs)

    # --------------------------------------------------------- Decision Tree
    pre_dt = build_preprocessor()
    dt = Pipeline([
        ("pre", pre_dt),
        ("clf", DecisionTreeClassifier(
            max_depth=5, min_samples_leaf=30, class_weight="balanced", random_state=RANDOM_STATE,
        )),
    ])
    dt.fit(X_train, y_train)
    dt_pred = dt.predict(X_test)
    dt_proba = dt.predict_proba(X_test)[:, 1]
    dt_result = evaluate("Decision Tree", y_test, dt_pred, dt_proba)

    feat_names_dt = get_feature_names(dt.named_steps["pre"])
    dt_importance = pd.Series(
        dt.named_steps["clf"].feature_importances_, index=feat_names_dt,
    ).sort_values(ascending=False)

    print("\n=== Logistic Regression: strongest odds-ratio drivers ===")
    print("(odds ratio > 1 = higher attrition odds; < 1 = lower; features are standardized/one-hot)")
    print(pd.concat([lr_odds.head(8), lr_odds.tail(8)]).sort_values(ascending=False).round(3))

    print("\n=== Decision Tree: top feature importances ===")
    print(dt_importance.head(10).round(3))

    # ---------------------------------------------- score every ACTIVE employee
    active_mask = df["status"] != "departed"
    X_active = X.loc[active_mask]
    active_ids = df.loc[active_mask, "employee_id"]

    active_scores = pd.DataFrame({
        "employee_id": active_ids.values,
        "department": df.loc[active_mask, "department"].values,
        "role_level": df.loc[active_mask, "role_level"].values,
        "hipo_flag": df.loc[active_mask, "hipo_flag"].values,
        "tenure_months": df.loc[active_mask, "tenure_months"].values,
        "survey_response_rate": df.loc[active_mask, "survey_response_rate"].values,
        # Decision Tree has the better ROC AUC (0.833 vs 0.698) so it drives
        # the official ranking; Logistic Regression probability and its
        # coefficient decomposition are kept alongside as the interpretable
        # "why" companion, since tree splits are harder to explain to a board.
        "dt_probability": dt.predict_proba(X_active)[:, 1],
        "lr_probability": lr.predict_proba(X_active)[:, 1],
    })
    # The Decision Tree is shallow (max_depth=5) by design, so it only
    # produces a handful of distinct leaf probabilities -- a quantile
    # threshold lands on a tie plateau and can return far more than 20% of
    # the population. Rank-based selection (top N rows, ties broken by the
    # Logistic Regression probability) gives a clean top-20% cut instead.
    active_scores = active_scores.sort_values(
        ["dt_probability", "lr_probability"], ascending=False,
    ).reset_index(drop=True)
    n_top20 = round(len(active_scores) * 0.20)
    top20 = active_scores.head(n_top20)
    print(f"\n=== Top 20% flight risk (active employees, ranked by Decision Tree) ===")
    print(f"n = {len(top20):,} of {len(active_scores):,} active employees "
          f"(lowest probability in this group: {top20['dt_probability'].min():.3f})")
    print(f"HiPo share of top 20%: {top20['hipo_flag'].mean()*100:.1f}% "
          f"(vs {active_scores['hipo_flag'].mean()*100:.1f}% firm-wide active)")
    print(top20["department"].value_counts(normalize=True).mul(100).round(1).head(6))

    # ------------------------------------------------- per-employee "why"
    # Linear decomposition of the Logistic Regression: for one example
    # employee, coefficient x standardized-feature-value = each feature's
    # contribution to the predicted log-odds. This is exact and needs no
    # extra library (no SHAP dependency) because the model is linear.
    # Pick an employee both models agree is high-risk, so the LR
    # decomposition is actually representative of why the (better-performing)
    # Decision Tree flagged them too.
    example_id = top20.sort_values("lr_probability", ascending=False).iloc[0]["employee_id"]
    example_row = X_active.loc[df["employee_id"] == example_id]
    pre_fitted = lr.named_steps["pre"]
    clf_fitted = lr.named_steps["clf"]
    x_transformed = pre_fitted.transform(example_row)
    x_transformed = x_transformed.toarray() if hasattr(x_transformed, "toarray") else x_transformed
    contributions = pd.Series(
        (x_transformed[0] * clf_fitted.coef_[0]), index=feat_names_lr,
    ).sort_values(key=abs, ascending=False)
    print(f"\n=== Example: why employee {example_id} scores as high flight risk ===")
    print("(top contributors to predicted log-odds, logistic regression)")
    print(contributions.head(6).round(3))

    active_scores.to_csv("outputs/flight_risk_scores.csv", index=False)
    print("\nSaved full active-employee ranking to outputs/flight_risk_scores.csv")

    return {
        "lr_result": lr_result, "dt_result": dt_result,
        "lr_odds": lr_odds, "dt_importance": dt_importance,
        "active_scores": active_scores, "top20": top20,
    }


if __name__ == "__main__":
    main()
