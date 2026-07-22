import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Load datasets
emp = pd.read_csv('employees.csv')
attr = pd.read_csv('attrition_log.csv')
eng = pd.read_csv('engagement.csv')
perf = pd.read_csv('performance.csv')

# Convert dates
for df, cols in [
    (emp, ['hire_date', 'exit_date']),
    (attr, ['exit_date']),
    (eng, ['survey_date']),
    (perf, ['review_date'])
]:
    for c in cols:
        df[c] = pd.to_datetime(df[c], errors='coerce')

# Prepare one-row-per-employee summary
eng['response_flag'] = eng['response_flag'].astype(bool)
eng_latest = eng.sort_values('survey_date').groupby('employee_id').tail(1).copy()
eng_latest['response_rate'] = eng.groupby('employee_id')['response_flag'].mean().reindex(eng_latest['employee_id']).values
score_cols = ['manager_effectiveness', 'psychological_safety', 'recognition', 'career_development', 'senior_leadership_trust', 'purpose_meaning', 'wellbeing', 'confidence_in_role_future']
eng_latest['engagement_mean'] = eng_latest[score_cols].mean(axis=1)
perf_latest = perf.sort_values('review_date').groupby('employee_id').tail(1).copy()

full = emp.merge(attr[['employee_id', 'exit_type', 'regrettable_flag', 'salary_at_exit']], on='employee_id', how='left')
full = full.merge(eng_latest[['employee_id', 'response_flag', 'response_rate', 'engagement_mean'] + score_cols], on='employee_id', how='left')
full = full.merge(perf_latest[['employee_id', 'performance_rating', 'promotion_recommendation', 'goal_achievement_score']], on='employee_id', how='left')
full['attrited'] = full['exit_type'].notna()
full['tenure_bucket'] = pd.cut(full['tenure_months'], bins=[0,12,24,36,60,120,240,9999], labels=['<1y', '1-2y', '2-3y', '3-5y', '5-10y', '10-20y', '20+y'])

# Basic cohort stats
print('Overall attrition:', full['attrited'].mean())
print('Entity attrition:')
print(full.groupby('legacy_entity_code')['attrited'].mean().sort_values(ascending=False))
print('Department attrition:')
print(full.groupby('department')['attrited'].mean().sort_values(ascending=False))
print('HiPo attrition:')
print(full.groupby('hipo_flag')['attrited'].mean())
print('Response bias attrition:')
print(full.groupby('response_flag')['attrited'].mean())
print('Tenure bucket attrition:')
print(full.groupby('tenure_bucket')['attrited'].mean())
print('Regrettable exits:', attr['regrettable_flag'].sum(), 'of', len(attr))

# Visuals
sns.set_style('whitegrid')

plt.figure(figsize=(8, 5))
entity_plot = full.groupby('legacy_entity_code')['attrited'].mean().sort_values(ascending=False)
entity_plot.plot(kind='barh', color='#1f77b4')
plt.title('Attrition by Legacy Entity')
plt.xlabel('Attrition Rate')
plt.tight_layout()
plt.savefig('figures/attrition_by_entity.png', dpi=200)
plt.close()

plt.figure(figsize=(8, 5))
full.groupby('department')['attrited'].mean().sort_values(ascending=False).plot(kind='barh', color='#ff7f0e')
plt.title('Attrition by Department')
plt.xlabel('Attrition Rate')
plt.tight_layout()
plt.savefig('figures/attrition_by_department.png', dpi=200)
plt.close()

plt.figure(figsize=(8, 5))
full.groupby('tenure_bucket')['attrited'].mean().sort_values(ascending=False).plot(kind='barh', color='#2ca02c')
plt.title('Attrition by Tenure Bucket')
plt.xlabel('Attrition Rate')
plt.tight_layout()
plt.savefig('figures/attrition_by_tenure.png', dpi=200)
plt.close()

plt.figure(figsize=(8, 5))
full.groupby('response_flag')['attrited'].mean().plot(kind='bar', color='#d62728')
plt.title('Attrition by Survey Response Status')
plt.ylabel('Attrition Rate')
plt.xticks([0, 1], ['Non-responder', 'Responder'], rotation=0)
plt.tight_layout()
plt.savefig('figures/attrition_by_response.png', dpi=200)
plt.close()

plt.figure(figsize=(8, 5))
full.groupby('hipo_flag')['attrited'].mean().plot(kind='bar', color='#9467bd')
plt.title('Attrition by HiPo Status')
plt.ylabel('Attrition Rate')
plt.xticks([0, 1], ['Non-HiPo', 'HiPo'], rotation=0)
plt.tight_layout()
plt.savefig('figures/attrition_by_hipo.png', dpi=200)
plt.close()

# Engagement dimensions by attrition status
eng_summary = pd.DataFrame({
    'Active': full[~full['attrited']][score_cols].mean(),
    'Departed': full[full['attrited']][score_cols].mean()
})
eng_summary.plot(kind='bar', figsize=(12, 6))
plt.title('Engagement Dimensions by Attrition Status')
plt.ylabel('Average Score')
plt.tight_layout()
plt.savefig('figures/engagement_by_attrition.png', dpi=200)
plt.close()

print('Done. Figures saved to figures/.')
