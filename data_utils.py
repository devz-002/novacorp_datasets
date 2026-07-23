"""Data loading and aggregation for the NovaCorp attrition dashboard.

Mirrors the analysis in notebooks/01_EDA.ipynb. Only aggregated statistics
(counts, rates, means) are ever surfaced to the UI -- no per-employee rows
(names, salaries, etc.) are displayed.
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


@st.cache_data
def load_raw():
    emp = pd.read_csv(f"{DATA_DIR}/employees.csv", parse_dates=["hire_date", "exit_date"])
    att = pd.read_csv(f"{DATA_DIR}/attrition_log.csv", parse_dates=["exit_date"])
    eng = pd.read_csv(f"{DATA_DIR}/engagement.csv", parse_dates=["survey_date"])
    perf = pd.read_csv(f"{DATA_DIR}/performance.csv", parse_dates=["review_date"])

    # survey response rate + low-responder flag, joined onto employees
    resp_rate = eng.groupby("employee_id")["response_flag"].mean().rename("survey_response_rate")
    emp = emp.join(resp_rate, on="employee_id")
    emp["low_responder"] = emp["survey_response_rate"] < 0.5

    # most recent performance rating, joined onto employees
    latest_perf = perf.sort_values("review_date").groupby("employee_id").tail(1)
    emp = emp.join(
        latest_perf.set_index("employee_id")["performance_rating"], on="employee_id"
    )

    return emp, att, eng, perf


def filter_by_department(emp, att, eng, perf, departments):
    if departments:
        emp_f = emp[emp["department"].isin(departments)]
    else:
        emp_f = emp
    ids = set(emp_f["employee_id"])
    att_f = att[att["employee_id"].isin(ids)]
    eng_f = eng[eng["employee_id"].isin(ids)]
    perf_f = perf[perf["employee_id"].isin(ids)]
    return emp_f, att_f, eng_f, perf_f


def attrition_rate(df, group_col):
    return (
        df.groupby(group_col)["status"]
        .apply(lambda s: (s == "departed").mean() * 100)
        .sort_values(ascending=False)
    )


def overall_attrition_rate(emp):
    if len(emp) == 0:
        return 0.0
    return (emp["status"] == "departed").mean() * 100
