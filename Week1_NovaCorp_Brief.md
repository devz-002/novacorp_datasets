# NovaCorp Week 1 Mentor Check-In Brief

## Executive Summary

### Observed facts
- The employee master file has 13,403 rows and one row per employee.
- The attrition log contains 1,400 departed employees with complete exit records and no duplicate employee IDs.
- Engagement spans 55,971 survey rows across 5 waves for 13,096 unique employees; response rate is 79.6% at the employee level, but 307 employees have no engagement records at all.
- Performance contains 34,979 review rows across 3 review cycles for 13,294 unique employees.
- The overall employee attrition rate in the joined file is 10.45%.
- Voluntary attrition is 80.9% of all exits, while involuntary attrition is 19.1%.
- Of the 1,400 leavers, 153 are flagged regrettable, or 10.9% of all attrition events.

### Most important business signal
The strongest, most defensible hypothesis is that digital/operational integration pressure in Entity_B is the primary retention risk driver, particularly for high performers and employees who do not respond to pulse surveys. This is consistent with the annual report’s own language that Entity_B is in active stabilisation, with elevated engagement and attrition metrics, while the People Investment Programme already points to a management-capability, compensation-equity, and survey-response response path.

### Why this matters
- Entity_B has the highest attrition rate at 15.0%, compared with 10.3% for the rest of the company.
- HiPo employees leave at 14.96% versus 9.99% for non-HiPo employees.
- Employees with no survey response have attrition of 14.69% versus 7.53% for responders.
- New joiners are a notable retention risk: employees with less than one year of tenure show 24.2% attrition.

### Executive recommendation direction
Prioritise a targeted retention intervention for new-to-Entity_B employees and HiPo employees, with a fast-track risk engine that combines entity, response status, and manager quality. The intervention should not be a generic training programme. It should be a focused response on manager capability, compensation equity, and survey non-response follow-up.

---

## Part 1 — Data Understanding

### 1. Data dictionary

#### employees.csv
Shape: 13,403 rows × 24 columns

Column descriptions:
- employee_id: stable employee identifier, candidate primary key.
- name: employee name.
- hire_date: employee hire date.
- exit_date: exit date for departed employees; null for active employees.
- status: active/departed flag.
- department: 7 department categories.
- role_family: functional family classification.
- role_level: ordinal role level.
- job_title: job title.
- salary: annual salary.
- compa_ratio: salary relative to market benchmark.
- gender: demographic category.
- age_band: age band.
- cultural_background: cultural background.
- contract_type: full-time/part-time/contract status.
- hipo_flag: high-potential flag.
- promotion_eligible: promotion eligibility flag.
- manager_id: current manager identifier.
- hire_source: recruitment source.
- legacy_entity_code: source-system integration cohort.
- data_source_system: HR source system.
- days_to_fill: hiring cycle length.
- tenure_months: total tenure in months.
- acting_appointment: whether person is acting in a role.

Data types:
- Numeric: role_level, salary, compa_ratio, days_to_fill, tenure_months
- Boolean: hipo_flag, promotion_eligible, acting_appointment
- Object/string: all demographic and organisational fields

Missing value analysis:
- exit_date: 12,003 missing values, expected for active employees.
- manager_id: 1 missing value.

Duplicate analysis:
- 0 duplicate rows.

Invalid values:
- No negative salaries.
- No future hire dates.
- All department values are within the expected set.

Outlier summary:
- Salary range is $55k to $1,206,500, which is plausible for executive-level outliers.
- Compa ratio has a plausible range of 0.66–1.19.

Cardinality:
- 13,403 unique employee IDs.
- 13,403 unique names.
- 6,285 unique manager IDs.

Possible foreign keys:
- manager_id → employees.employee_id (self-referencing manager hierarchy)
- legacy_entity_code → integration cohort classification table (not provided)

Candidate primary key:
- employee_id

#### attrition_log.csv
Shape: 1,400 rows × 10 columns

Column descriptions:
- employee_id: departed employee identifier.
- exit_date: departure date.
- exit_type: voluntary or involuntary.
- stated_exit_reason: stated reason for exit.
- notice_period_served: whether notice was served.
- regrettable_flag: whether the exit is considered regrettable.
- performance_band_at_exit: performance band at exit.
- salary_at_exit: salary at departure.
- manager_id_at_exit: manager at exit.
- pathway: exit pathway classification.

Data types:
- Numeric: salary_at_exit
- Boolean: notice_period_served, regrettable_flag
- Object/string: all others

Missing values:
- None.

Duplicate analysis:
- 0 duplicate employee IDs.

Invalid values:
- No impossible dates.
- No invalid exit types.

Outlier summary:
- Salary-at-exit range is reasonable and aligns with the salary distribution in the master file.

Cardinality:
- 1,400 unique employee IDs.

Possible foreign keys:
- employee_id → employees.employee_id
- manager_id_at_exit → employees.manager_id

Candidate primary key:
- employee_id

#### engagement.csv
Shape: 55,971 rows × 12 columns

Column descriptions:
- employee_id: employee identifier.
- wave_number: survey wave number from 1–5.
- survey_date: survey date.
- response_flag: whether the employee responded to that wave.
- manager_effectiveness, psychological_safety, recognition, career_development, senior_leadership_trust, purpose_meaning, wellbeing, confidence_in_role_future: survey dimensions.

Data types:
- Numeric: survey scale columns and wave_number
- Boolean: response_flag
- Object/string: employee_id, survey_date

Missing value analysis:
- 10,264 missing values in each of the eight engagement score columns. These are entirely consistent with non-response rows because response_flag is False.

Duplicate analysis:
- 0 duplicate rows.

Invalid values:
- No future dates.
- Scores are numeric and plausible.

Outlier summary:
- Engagement dimensions are bounded in practice, with no obvious numeric errors.

Cardinality:
- 13,096 unique employees, 5 survey waves, 55,971 rows.

Possible foreign keys:
- employee_id → employees.employee_id
- composite key (employee_id, wave_number) is a candidate business primary key

Candidate primary key:
- (employee_id, wave_number)

#### performance.csv
Shape: 34,979 rows × 7 columns

Column descriptions:
- employee_id, review_date, performance_rating, review_cycle, promotion_recommendation, goal_achievement_score, reviewer_id

Data types:
- Numeric: goal_achievement_score
- Boolean: promotion_recommendation
- Object/string: review rating and cycle fields

Missing value analysis:
- No missing values.

Duplicate analysis:
- 0 duplicate rows.

Invalid values:
- No invalid dates.
- Ratings are within the expected set of 5 categories.

Outlier summary:
- goal_achievement_score appears plausible and not structurally broken.

Cardinality:
- 13,294 unique employees and 3 review cycles.

Possible foreign keys:
- employee_id → employees.employee_id
- reviewer_id → employees.employee_id (if reviewer is an employee)

Candidate primary key:
- (employee_id, review_cycle)

---

## Part 2 — Data Quality Audit

### Audit summary

| Issue | Severity | Evidence | Business implication |
|---|---|---|---|
| Missing exit_date for active employees | Low | 12,003 missing in employees | Expected; not data quality issue |
| Missing manager_id in employees | Medium | 1 missing | Possible governance issue in manager hierarchy |
| Engagement score nulls in non-response rows | Low | 10,264 nulls in each survey dimension | Expected response bias, not random missingness |
| Duplicate rows | Low | 0 duplicates in all files | Data integrity is strong |
| Negative salaries | Low | 0 | Pay data is clean |
| Future dates | Low | 0 | Date handling is clean |
| Invalid departments | Low | 0 | Controlled dimension |
| Invalid ratings | Low | 0 | Controlled performance taxonomy |
| Date inconsistencies | Medium | No impossible dates, but employee date fields should be checked for chronology | Needs the join logic to be explicit |
| Unexpected categories | Medium | legacy_entity_code contains Entity_A/B/C and NovaCorp-Origin; this indicates integration source-system fragmentation | This is likely a core driver of behavioural differences |

### Audit notes
- The data quality baseline is strong. There are no major structural defects in the files.
- The most important “data issue” is not bad data; it is the intentional fragmentation across source systems and the non-response nature of the engagement file.

---

## Part 3 — Join Validation

### Inferred relationships
- employees.employee_id → attrition_log.employee_id: one-to-one at the employee level, with attrition being a left-joined extension of the employee master.
- employees.employee_id → engagement.employee_id: one-to-many; one employee can have many survey waves.
- employees.employee_id → performance.employee_id: one-to-many; one employee can have many review records.

### Join validation results

| Join | Coverage | Lost rows | Duplicate rows | Unmatched IDs | Trustworthiness |
|---|---|---|---|---|---|
| employees ↔ attrition | 1,400 matched; 12,003 active employees remain on left-only | 0 | 0 | 0 unmatched on employee side | Trustworthy |
| employees ↔ engagement (employee-level) | 13,096 matched; 307 employees unmatched on employee side | 307 | 0 | 307 employees with no engagement records | Trustworthy but not complete |
| employees ↔ performance (employee-level) | 13,294 matched; 109 employees unmatched | 109 | 0 | 109 employees with no performance records | Trustworthy but not complete |

### Interpretation
The join logic is sound. The major caveat is that engagement and performance do not cover all employees; this is not a join failure, it is a coverage issue. That coverage gap is potentially important because employees who do not respond to surveys also show unusually high attrition.

---

## Part 4 — Exploratory Data Analysis

### 4.1 Demographics and workforce structure
Observed fact:
- The employee base is distributed across seven departments and four legacy entities.
- Most employees are in middle-aged cohorts, with the largest age bands being 30–39 and 25–29.
- The overall attrition rate is 10.45%.

Reasonable inference:
- The workforce is mature but not senior-heavy; the retention risk is less about age alone and more about integration cohort and first-year experience.

Business implication:
- A one-size-fits-all retention programme would miss the rising risk in new joiners and in the integration cohort.

### 4.2 Department and entity comparisons
Observed fact:
- Risk & Compliance has the highest attrition at 11.82%.
- Corporate Operations is close behind at 11.60%.
- Entity_B has the highest attrition among legacy entities at 15.02%.

Interpretation:
- A department-level story alone is incomplete; the sharper signal is the overlap of department and integration cohort.
- The annual report explicitly flagged Entity_B in stabilisation and Risk & Compliance under FAR pressure; the data supports that direction.

### 4.3 Tenure analysis
Observed fact:
- Employees with less than one year of tenure have a 24.17% attrition rate.
- Attrition then drops sharply in the 1–2 year and 2–3 year cohorts.

Interpretation:
- Early-career and integration-cycle churn is the most acute retention issue.
- The problem is therefore not simply broad employee disengagement; it is early-stage misfit, low manager quality, or integration disruption.

### 4.4 Salary and underpayment analysis
Observed fact:
- Salary distribution shows a large spread, but the median attrition salary is almost identical to the median active salary.
- The more interesting signal is that HiPo employees are not substantially paid more than non-HiPo employees on average, which creates a potential salary compression story.

Reasonable inference:
- If high performers are leaving despite relatively similar pay levels, compensation equity is not the only issue; but it may still be part of the root cause.

### 4.5 Performance and promotion patterns
Observed fact:
- HiPo attrition is 14.96%, versus 9.99% among non-HiPo employees.
- Promotion eligibility is not materially different in attrition rate; promotion recommendation also does not show a large exit effect.

Interpretation:
- This weakens a pure “promotion delay” explanation.
- It strengthens the hypothesis that high performers are leaving because the organisation does not adequately retain them through the integration and leadership environment, not just because they were blocked for promotion.

### 4.6 Engagement and response behaviour
Observed fact:
- Employees who responded to engagement surveys displayed lower attrition: 7.53% versus 14.69% for non-responders.
- The strongest survey dimensions between active and departed employees were senior leadership trust and career development.

Interpretation:
- Survey non-response is itself a retention risk indicator.
- The data supports the annual report statement that non-responders are a flight-risk population.

### 4.7 Missingness and response bias
Observed fact:
- The engagement file has 10,264 missing values in the eight score columns because responses are absent for some employees.
- The response-bias pattern is material and likely not random.

Reasonable inference:
- Employees who choose not to respond are not just “silent”; they are more likely to be at risk.

Business implication:
- A standard pulse survey that measures only respondents will miss the population most likely to leave.

### 4.8 Correlation matrix
Observed fact:
- The correlation matrix shows very weak association between engagement dimensions and pay outcome, which means pay is not a clean predictor on its own.
- There is a strong positive relationship between role level and salary, but not a strong direct organisational retention signal.

Interpretation:
- This suggests that compensation alone is not the sole explanation.
- The key signal sits in the interaction between entity, manager behaviour, survey response, and early tenure.

---

## Part 5 — Business Questions

### Responses

Who leaves?
- High performers, employees in their first year, and those in Entity_B and Risk & Compliance.

Why?
- The data supports a root-cause story around integration disruption, low trust in leadership, and likely under-managed early-stage experience. The precise causal reason is not fully observable in the data, so this remains an inference.

Which departments?
- Risk & Compliance and Corporate Operations carry the highest attrition risk.

Which grades?
- Role levels 1–4 are more exposed, with level 1 showing the highest risk among non-executive roles.

Which entities?
- Entity_B is the clear outlier.

Who is regrettable?
- 153 employees, or about 10.9% of all exits. They are disproportionately senior and more likely to be in strategic risk or integration-heavy areas.

Who is high-performing?
- HiPo employees have materially higher attrition than non-HiPo employees.

Who is underpaid?
- Evidence is insufficient to say salary compression is a direct and general root cause, though the HiPo cohort is not materially better paid than the broader workforce.

Who is disengaged?
- Employees who did not respond to surveys are at materially higher attrition risk.

Who is promoted?
- Promotion recommendation does not materially separate attrition outcomes; therefore promotion design does not appear to be the primary driver.

Which engagement dimensions matter most?
- Senior leadership trust and career development are the most plausible differentiators in the attrition comparison.

Which variables appear associated with attrition?
- Entity_B, first-year tenure, survey non-response, HiPo status, and Risk & Compliance.

Which variables appear unrelated?
- Gender shows little difference in attrition rate.
- Promotion eligibility appears weakly related.

Which findings contradict expectations?
- Promotion delays do not appear to be the main cause.
- Rewarding performance does not obviously prevent voluntary attrition in this data.

Which findings support the annual report?
- The report explicitly says Entity_B is in active stabilisation with elevated engagement and attrition, which is consistent with the data.
- The report also says non-responders are disproportionately at flight risk, which is supported here.

Which findings challenge it?
- The annual report highlights compensation equity as a People Investment Programme area. The data does not prove compensation is the dominant driver of attrition, only that it is a probable contributing factor in the HiPo story.

---

## Part 6 — Hypothesis Generation

### Candidate hypotheses

1. Entity_B integration drives attrition.
   - Business rationale: Integration activity is materially disruptive to culture and confidence.
   - Evidence supporting: Entity_B attrition is 15.0% versus 10.3% company-wide.
   - Evidence against: Could also be a function of department mix or manager quality.
   - Confidence: High.
   - Required validation: Compare Entity_B vs other entities within the same department and manager cohort.

2. Engagement non-responders have higher attrition.
   - Business rationale: Silent employees may be flight-risk employees.
   - Evidence supporting: Non-responders show 14.69% attrition vs 7.53% for responders.
   - Evidence against: This could be a proxy for manager quality or low trust, not a direct cause.
   - Confidence: High.
   - Required validation: Control for entity, tenure, and department.

3. High performers leave because salary compression exists.
   - Business rationale: HiPo employees often leave when their market value is not reflected in pay.
   - Evidence supporting: HiPo attrition is elevated, and salary data is not meaningfully higher for HiPo employees.
   - Evidence against: Mean salary differences are small; the evidence is suggestive rather than conclusive.
   - Confidence: Medium.
   - Required validation: Compare compa ratio and role-level benchmark gap by HiPo and attrited status.

4. Manager quality predicts attrition.
   - Business rationale: Manager capability directly affects trust, career development, and sense of future.
   - Evidence supporting: Manager effectiveness is lower in attrition cases than in active cases.
   - Evidence against: Manager IDs are only partially interpretable without manager-level exposure data.
   - Confidence: Medium.
   - Required validation: Manager-level retention modelling and manager benchmark review.

5. Promotion delays increase exits.
   - Business rationale: Delayed promotion can trigger flight risk.
   - Evidence supporting: Some promotion-related friction is plausible.
   - Evidence against: Promotion recommendation and promotion eligibility do not show strong exit effects.
   - Confidence: Low.
   - Required validation: Use time-to-promotion and promotion-cycle sequencing.

6. Risk & Compliance suffers unique retention pressures under FAR.
   - Business rationale: FAR creates individual accountability obligations and makes senior regulatory talent scarce.
   - Evidence supporting: Risk & Compliance shows the strongest attrition among departments.
   - Evidence against: This could be a department mix issue rather than a unique FAR effect.
   - Confidence: Medium.
   - Required validation: Segment by seniority and entity; compare to external market benchmark if available.

### Ranked hypotheses
1. Entity_B integration drives attrition.
2. Engagement non-responders are at higher flight risk.
3. Manager quality predicts attrition.
4. High performers leave due to compensation compression.
5. Risk & Compliance retention pressure under FAR.
6. Promotion delay drives exits.

### Recommended hypothesis to pursue
Entity_B integration is the strongest single operating hypothesis because it is the single largest retention outlier, aligns with annual-report wording, and is measurable in a way that leaders can act on.

---

## Part 7 — Root Cause Analysis

### Selected hypothesis
Entity_B integration is materially associated with elevated attrition, particularly for employees who are new, high-performing, or not engaging in survey feedback.

### 5 Why analysis
1. Why are we losing employees? Because some employees leave voluntarily during the integration period.
2. Why do they leave during integration? Because the operating environment is unstable and trust in leadership is lower.
3. Why is trust lower? Because the integration programme is still stabilising and employee experience is not yet consistent across systems and leadership touchpoints.
4. Why does that lead to attrition? Because employees do not have confidence in the future, especially in the high-pressure functions.
5. Why is that urgent? Because the company has committed to integration completion and the cost of replacing these employees is meaningful.

### Fishbone reasoning
- People: new joiners in the integration cohort, HiPo employees, manager capability gaps.
- Process: survey response infrastructure, onboarding consistency, integration governance.
- Policy: compensation equity calibration, promotion track clarity.
- Systems: Entity_B source-system fragmentation and legacy operating model differences.

### Confounding variables
- Department mix within Entity_B is not uniform.
- Early tenure and employee age cohort may be correlated with integration risk.
- Manager quality may be a mediator rather than an independent cause.

### Alternative explanations
- Attrition could reflect a normal post-acquisition rebalancing pattern rather than a pure leadership problem.
- It could be a low-salary / market-competition story rather than one of integration disruption.

### Potential biases
- Survey non-response is itself a risk indicator and may create a response-bias sample.
- The data does not include employee-level reasons for exit beyond the stated reason field.
- Attrition data is retrospective and not longitudinal enough to establish causality.

### Limitations
- The dataset is observational, not experimental.
- We cannot prove causality without manager interviews, retention interviews, or a controlled intervention.
- The evidence is strong for association but not for a complete root-cause chain.

---

## Part 8 — Week 1 Deliverables

### Discover
Summary of EDA:
- The data has high integrity and valid joins.
- Entity_B is the leading outlier.
- Survey non-response is materially associated with attrition.
- HiPo attrition is elevated.
- New joiner attrition is especially high.

Unexpected findings:
- The “silent” population is a risk population.
- Promotion eligibility alone does not explain exits.
- Gender is not a major differentiator.

Interesting correlations:
- Engagement dimensions are broadly correlated with one another but have weak direct links to salary metrics.
- Senior leadership trust and career development are the clearest attrition-related engagement dimensions.

Data issues:
- Non-response is not a technical defect; it is a behavioural signal.
- Entity_B source-system integration is a data-structure reality that should be treated as a business variable, not just metadata.

### Define
Chosen problem:
- Entity_B integration-related attrition risk is materially higher than the rest of the firm, especially for HiPo employees and employees who do not respond to survey feedback.

Business importance:
- A continued integration drag would create preventable turnover and weaken delivery of strategic growth and operational scale.

Testable hypothesis:
- H1: Employees in Entity_B, especially those with low engagement response and/or HiPo status, are materially more likely to leave than comparable employees in other entities.

Null hypothesis:
- H0: There is no material attrition difference between Entity_B and other entities after controlling for tenure, department, and survey response behaviour.

What evidence would reject it:
- If the risk gap disappears after controlling for department, manager, and tenure, or if Entity_B is not in fact more volatile than the comparable cohorts.

### Develop
Intervention 1 — Targeted manager capability and onboarding reset for Entity_B
- Pros: High relevance, fast to launch, addresses trust and early-stage experience.
- Cons: Requires manager buy-in and performance tracking.
- Estimated cost: Medium.
- Expected impact: Moderate.
- Ease of implementation: Medium.
- Risk: Low-to-medium.

Intervention 2 — Compensation equity and retention review for HiPo employees in integration cohorts
- Pros: Directly addresses retention of critical talent.
- Cons: Budget-sensitive and can be difficult to calibrate fairly.
- Estimated cost: High.
- Expected impact: Moderate-to-high.
- Ease of implementation: Medium.
- Risk: Medium.

Intervention 3 — Engagement-response infrastructure redesign to capture non-responders
- Pros: Addresses the known flight-risk population and improves insight quality.
- Cons: Requires engineering and change management.
- Estimated cost: Medium.
- Expected impact: Moderate.
- Ease of implementation: Medium.
- Risk: Low.

### Deliver
Problem:
- NovaCorp is losing talent at an elevated rate in a critical integration period, with a measurable risk concentration in Entity_B, early-tenure employees, and the HiPo population.

Evidence:
- Entity_B attrition is 15.0% vs 10.3% company-wide.
- HiPo attrition is 15.0% vs 10.0% for non-HiPo.
- Non-responders show 14.7% attrition, versus 7.5% for responders.
- First-year tenure has 24.2% attrition.

Business impact:
- Observed payroll at exit is $175.8M across 1,400 exits.
- At an assumed replacement cost of 90% of annual salary, the full-cost attrition envelope is roughly $158.2M.
- A 5% reduction in the number of exits would save about $8.8M, or about $17.6M for a 10% reduction and $26.4M for a 15% reduction.

Recommendation direction:
- Make retention an integration and leadership problem, not a generic HR problem.
- Prioritise manager capability, compensation equity, and survey-response infrastructure as the first-wave actions.

Key numbers:
- 14,003 employees matched in the master file? No — 13,403 employees.
- 1,400 exits.
- 153 regrettable exits.
- 10.45% overall attrition.
- 15.0% Entity_B attrition.
- 24.2% first-year attrition.
- 14.7% attrition among survey non-responders.

Suggested charts:
- Attrition by entity.
- Attrition by tenure bucket.
- Attrition by department.
- Attrition by survey response status.
- HiPo vs non-HiPo attrition.

---

## Part 9 — Business Impact

### Assumptions
- Replacement cost is assumed at 90% of annual salary at exit.
- This is a conservative estimate aligned with the brief’s 50–200% range.
- A 5%/10%/15% reduction in exits is treated as a proportional reduction in the total cost envelope.

### Estimated cost envelope
- Average exit salary: $125,558
- Total exit salary cost across the 1,400 exits: $175.8M
- Replacement cost assumption: 90% × average annual salary = $113,003 per exit
- Total replacement-cost envelope: $158.2M
- Regrettable exits: 153
- Regrettable-cost estimate: 153 × $113,003 ≈ $17.3M

### Potential savings
| Attrition reduction | Potential savings |
|---|---:|
| 5% | $8.8M |
| 10% | $17.6M |
| 15% | $26.4M |

---

## Part 10 — Presentation Recommendations

### Best storyline
Problem → Integration cohort risk → Silent population risk → HiPo retention risk → Targeted action.

### Slide order
1. Executive summary of the business problem.
2. Attrition concentration by entity and tenure.
3. High performers and survey non-responders as the most at-risk cohorts.
4. Root-cause interpretation using the annual report context and the data.
5. Recommended intervention set and impact estimate.

### Best charts
- Horizontal bar chart: attrition by entity.
- Horizontal bar chart: attrition by tenure bucket.
- Horizontal bar chart: attrition by department.
- Lollipop chart: attrition by survey response status.
- Back-to-back bar chart: HiPo vs non-HiPo attrition.

### Strong executive titles
- Entity_B is NovaCorp’s most visible attrition hotspot.
- The silent employee population is more likely to leave.
- High performers are leaving faster than the company average.
- Early-tenure turnover is the most urgent retention lever.

### Weak titles to avoid
- Attrition by department.
- Performance score distribution.
- Exploratory analysis of workforce demographics.

### Key messages
- Do not start with “the company needs more training”.
- Start with the fact that integration risk is geographically and organisationally concentrated.
- The highest-cost risk is not broad attrition; it is a concentrated loss of critical, high-potential employees in the integration phase.

---

## Part 11 — Next Week Analysis

Recommended deeper analyses:
- Predictive flight-risk scoring using logistic regression or tree-based models.
- Survival analysis for time-to-exit by integration cohort.
- Segment-level analysis of Entity_B vs other entities across manager and department interactions.
- Compensation equity analysis by role level and HiPo flag.
- SHAP or feature importance analysis on the final flight-risk model.

---

## Part 12 — Output Format

1. Executive summary — included.
2. Detailed EDA report — included.
3. Markdown tables — included.
4. Python code — provided in the companion script.
5. Visualisations — to be saved in the visuals folder.
6. Business insights — included.
7. Week 1 deliverables — included.
8. Recommended hypothesis — included.
9. Recommended next analyses — included.
10. Appendix — see notes below.

### Appendix
- Annual report notes: the People Investment Programme includes manager capability, compensation equity for the high-potential cohort, and a redesigned engagement infrastructure.
- This matters because the data shows the same three signals emerging from the raw HR data.
- The strongest operational recommendation is not to “improve engagement overall”; it is to reach the silent population and protect critical talent in the integration cohort.
