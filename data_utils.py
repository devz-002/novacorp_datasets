"""Data loading and aggregation for the NovaCorp attrition dashboard.

Mirrors the analysis in notebooks/01_EDA.ipynb and EDA.ipynb (discovery
notebook): employee-level joins against attrition/engagement/performance,
plus the derived buckets and non-responder analysis used across the app.
Only aggregated statistics (counts, rates, means) are ever surfaced to the
UI -- no per-employee rows (names, salaries, etc.) are displayed.
"""
import pandas as pd
import streamlit as st

DATA_DIR = "data/raw"

SCORE_COLS = [
    "manager_effectiveness", "psychological_safety", "recognition",
    "career_development", "senior_leadership_trust", "purpose_meaning",
    "wellbeing", "confidence_in_role_future",
]

RATING_ORDER = [
    "Unsatisfactory", "Below Expectations", "Meets Expectations",
    "High Performer", "Outstanding",
]

AGE_BAND_ORDER = [
    "18-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60+",
]

TENURE_BUCKET_ORDER = ["<1y", "1-2y", "2-3y", "3-5y", "5-10y", "10-20y", "20+y"]

COMPA_BUCKET_ORDER = [
    "<0.85 (below band)", "0.85-0.95", "0.95-1.05 (at band)", "1.05-1.15",
    ">1.15 (above band)",
]

# label -> column in `full` for every sidebar "Global Filters" multiselect
FILTER_SPECS = [
    ("Department", "department"),
    ("Legacy Entity Code", "legacy_entity_code"),
    ("Role Level", "role_level"),
    ("Gender", "gender"),
    ("Employment Status", "status"),
    ("HiPo Flag", "hipo_flag"),
    ("Performance Rating", "performance_rating"),
    ("Promotion Recommendation", "promotion_recommendation"),
    ("Exit Type", "exit_type"),
    ("Exit Reason", "stated_exit_reason"),
    ("Regrettable Exit", "regrettable_flag"),
    ("Tenure Bucket", "tenure_bucket"),
    ("Age Bucket", "age_band"),
    ("Compa Ratio Bucket", "compa_bucket"),
]

# Filters shown by default in the sidebar (reduces clutter); everything else
# in FILTER_SPECS lives inside the "Advanced filters" expander.
PRIMARY_FILTER_COLS = ["department", "legacy_entity_code", "hipo_flag", "status"]

# label -> column, for "Group By" drill-down dropdowns. "rate" columns are
# defined for the whole population (attrition rate by group); "count"
# columns only exist for leavers (distribution among departed employees).
ATTRITION_GROUP_OPTIONS = {
    "Department": ("rate", "department"),
    "Legacy Entity": ("rate", "legacy_entity_code"),
    "Role Level": ("rate", "role_level"),
    "Gender": ("rate", "gender"),
    "Age Bucket": ("rate", "age_band"),
    "Tenure Bucket": ("rate", "tenure_bucket"),
    "Performance Rating": ("rate", "performance_rating"),
    "Promotion Recommendation": ("rate", "promotion_recommendation"),
    "HiPo": ("rate", "hipo_flag"),
    "Pathway": ("count", "pathway"),
    "Regrettable Exit": ("count", "regrettable_flag"),
    "Exit Reason": ("count", "stated_exit_reason"),
    "Exit Type": ("count", "exit_type"),
}

ENGAGEMENT_GROUP_OPTIONS = {
    "Department": "department",
    "Legacy Entity": "legacy_entity_code",
    "Role Level": "role_level",
    "Gender": "gender",
    "Age Bucket": "age_band",
}

COMPENSATION_GROUP_OPTIONS = {
    "HiPo Flag": "hipo_flag",
    "Department": "department",
    "Legacy Entity": "legacy_entity_code",
    "Role Level": "role_level",
    "Performance Rating": "performance_rating",
}


@st.cache_data
def load_raw():
    emp = pd.read_csv(f"{DATA_DIR}/employees.csv", parse_dates=["hire_date", "exit_date"])
    att = pd.read_csv(f"{DATA_DIR}/attrition_log.csv", parse_dates=["exit_date"])
    eng = pd.read_csv(f"{DATA_DIR}/engagement.csv", parse_dates=["survey_date"])
    perf = pd.read_csv(f"{DATA_DIR}/performance.csv", parse_dates=["review_date"])
    return emp, att, eng, perf


def _fill_unknown(series):
    # left-merging a boolean column upcasts it to `object` dtype wherever
    # NaN gets introduced (e.g. actives with no attrition/perf record), so
    # check actual values rather than dtype to still catch True/False here.
    non_null = series.dropna()
    if len(non_null) and set(non_null.unique()) <= {True, False}:
        return series.map({True: "Yes", False: "No"}).fillna("Unknown")
    return series.astype("object").fillna("Unknown")


@st.cache_data
def build_full(emp, att, eng, perf):
    """Employee-level analytics table -- mirrors EDA.ipynb's `full` dataframe.

    One row per employee, joined with their latest engagement wave, latest
    performance review, and (if departed) their attrition_log record.
    """
    eng = eng.copy()
    eng["response_flag"] = eng["response_flag"].astype(bool)
    eng_latest = eng.sort_values("survey_date").groupby("employee_id").tail(1).copy()
    resp_rate = eng.groupby("employee_id")["response_flag"].mean()
    eng_latest["response_rate"] = eng_latest["employee_id"].map(resp_rate)
    eng_latest["engagement_mean"] = eng_latest[SCORE_COLS].mean(axis=1)

    perf_latest = perf.sort_values("review_date").groupby("employee_id").tail(1).copy()

    full = emp.merge(
        att[[
            "employee_id", "exit_type", "pathway", "regrettable_flag",
            "stated_exit_reason", "performance_band_at_exit", "salary_at_exit",
        ]],
        on="employee_id", how="left",
    )
    full = full.merge(
        eng_latest[["employee_id", "response_flag", "response_rate", "engagement_mean"] + SCORE_COLS],
        on="employee_id", how="left",
    )
    full = full.merge(
        perf_latest[["employee_id", "performance_rating", "promotion_recommendation", "goal_achievement_score"]],
        on="employee_id", how="left",
    )

    full["attrited"] = full["status"] == "departed"

    full["tenure_bucket"] = pd.cut(
        full["tenure_months"], bins=[-0.01, 12, 24, 36, 60, 120, 240, 9999],
        labels=TENURE_BUCKET_ORDER,
    ).astype("object")
    full["compa_bucket"] = pd.cut(
        full["compa_ratio"], bins=[0, 0.85, 0.95, 1.05, 1.15, 99],
        labels=COMPA_BUCKET_ORDER,
    ).astype("object")

    # non-responder analysis: response_rate == 0 means the employee has at
    # least one engagement.csv row and never once answered (this is
    # EDA.ipynb's "true non-responder" population, 506 employees). NaN means
    # the employee has NO engagement.csv rows at all -- never administered a
    # survey wave in the first place, a different population (307 employees)
    # that must NOT be folded into "Non-Responder" or it silently inflates
    # the count to 813.
    def _response_category(rate):
        if pd.isna(rate):
            return "No Survey Data"
        if rate == 0:
            return "Non-Responder"
        if rate < 0.5:
            return "Low Responder"
        return "Responder"

    full["response_category"] = full["response_rate"].apply(_response_category)
    full["survey_response_rate"] = full["response_rate"]
    full["low_responder"] = full["response_rate"].fillna(1) < 0.5

    for col in [
        "performance_rating", "promotion_recommendation", "exit_type",
        "pathway", "regrettable_flag", "stated_exit_reason",
        "performance_band_at_exit", "tenure_bucket", "compa_bucket",
    ]:
        full[col] = _fill_unknown(full[col])

    return full


def filter_options(full, column, order=None):
    values = list(full[column].dropna().unique())
    if order:
        values = [v for v in order if v in values] + sorted(
            [v for v in values if v not in order], key=str
        )
    else:
        values = sorted(values, key=str)
    return values


def apply_filters(full, selections):
    """selections: {column: list_of_selected_values}. Empty list = no rows match,
    so callers should default every multiselect to "all options selected"."""
    mask = pd.Series(True, index=full.index)
    for col, values in selections.items():
        if values is not None:
            mask &= full[col].isin(values)
    return full[mask]


def apply_response_choice(full, choice):
    if choice == "Responders":
        return full[full["response_category"].isin(["Low Responder", "Responder"])]
    if choice == "Non-Responders":
        return full[full["response_category"] == "Non-Responder"]
    return full


def slice_related(att, eng, perf, employee_ids):
    ids = set(employee_ids)
    att_f = att[att["employee_id"].isin(ids)]
    eng_f = eng[eng["employee_id"].isin(ids)]
    perf_f = perf[perf["employee_id"].isin(ids)]
    return att_f, eng_f, perf_f


def attrition_rate(df, group_col):
    return (
        df.groupby(group_col, observed=True)["status"]
        .apply(lambda s: (s == "departed").mean() * 100)
        .sort_values(ascending=False)
    )


def overall_attrition_rate(emp):
    if len(emp) == 0:
        return 0.0
    return (emp["status"] == "departed").mean() * 100


def nonresponder_lift(full, group_col):
    """Compare the group-column distribution of true non-responders against
    the firm-wide distribution -- the Entity_C over-representation analysis
    from EDA.ipynb (cells 18-21)."""
    nonresp = full[full["response_category"] == "Non-Responder"]
    if len(nonresp) == 0 or len(full) == 0:
        return pd.DataFrame(columns=["nonresponder_pct", "firmwide_pct", "lift"])
    nonresp_dist = nonresp[group_col].value_counts(normalize=True) * 100
    firm_dist = full[group_col].value_counts(normalize=True) * 100
    out = pd.DataFrame({"nonresponder_pct": nonresp_dist, "firmwide_pct": firm_dist}).fillna(0)
    out["lift"] = (out["nonresponder_pct"] / out["firmwide_pct"].replace(0, pd.NA)).astype(float)
    return out.sort_values("lift", ascending=False)


def replacement_cost_range(df, low_mult=0.5, high_mult=2.0):
    """Estimated replacement-cost range for a set of leavers, from
    salary_at_exit -- industry rule of thumb is 50-200% of salary."""
    total_salary = df["salary_at_exit"].sum()
    return total_salary * low_mult, total_salary * high_mult
