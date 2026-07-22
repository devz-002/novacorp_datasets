# NovaCorp Challenge — Student Guide
**UNSW Data SOC Challenge | Accenture Mentoring Program 2026**

---

## The Challenge in One Paragraph

NovaCorp is a 12,000-person Australian financial services firm losing an estimated $42M per year to preventable attrition, disengagement, and hiring inefficiency. You have been brought in as a data consulting team. Your job: choose the HR problem you believe matters most, dig into the data, form and test a hypothesis, build a business case, and pitch it — clearly, confidently, and backed by evidence — to NovaCorp's leadership team.

The organisation does not need another report. It needs your team to choose a problem, back a solution, and make the case for change.

---

## Your Datasets

| File | What it contains |
|---|---|
| `employees.csv` | One row per employee — demographics, tenure, role, grade band, department |
| `attrition_log.csv` | Every employee who has left — exit date, type, stated reason, regrettable flag, salary at exit |
| `engagement.csv` | Quarterly pulse survey scores across 8 dimensions, 5 waves |
| `performance.csv` | Performance ratings, promotion recommendations, goal achievement — 3 review cycles |

---

## Your Process: The Double Diamond

Great consulting work isn't just about the answer — it's about how you get there. Use the **Double Diamond** as your thinking framework throughout this challenge.

```
  DISCOVER ──► DEFINE ──► DEVELOP ──► DELIVER
  (diverge)   (converge)  (diverge)  (converge)
```

| Phase | What you do | In NovaCorp terms |
|---|---|---|
| **Discover** | Explore broadly. Don't anchor on a problem yet. Let the data surprise you. | Load all 4 datasets. Check distributions, nulls, joins. Find patterns you didn't expect. |
| **Define** | Synthesise. Choose the ONE problem that matters most. State a testable hypothesis. | "We believe the core issue is X, driven by Y, evidenced by Z." |
| **Develop** | Ideate on solutions. Generate 2–3 different approaches before committing to one. | What could NovaCorp actually do? Think broadly — tech, process, policy, culture. |
| **Deliver** | Converge on the best solution. Build the business case. Craft the story. | Prioritised recommendation with quantified impact, owner, timeline, and success metric. |

**The most common mistake:** Jumping from Discover straight to Deliver — finding one pattern and immediately recommending a solution without properly defining the problem or exploring alternatives. Judges will notice.

**Your goal for Week 1:** Complete a **draft pass through all four phases**. It doesn't have to be perfect — it has to be complete enough to pressure-test with your mentor.

---

## Weekly Milestones

Your work unfolds across three weeks. Each week has a milestone — bring it to your mentor check-in.

### Week 1 — Double Diamond Draft
**Check-in: 20–24 July | Bring: Draft pass through all 4 diamond phases**

The aim this week is breadth before depth. Get through the full diamond once — even roughly — so your mentor can validate your direction before you invest heavily in analysis.

| Diamond Phase | W1 Deliverable |
|---|---|
| **Discover** | Explored all 4 datasets (shapes, nulls, distributions, joins validated). Noted unexpected patterns. Not anchored on a solution yet. |
| **Define** | Chosen ONE priority HR problem with a clearly stated hypothesis. Can articulate what the data would look like if your hypothesis is wrong. |
| **Develop** | Identified 2–3 candidate solutions to the defined problem. Considered different types of interventions (not just "do more training"). |
| **Deliver** | Drafted a high-level story arc: Problem → Evidence → So What → Recommended direction. |

- [ ] Team plan submitted to your mentor (due **no later than 20 July**) — include chosen problem, approach, and who is doing what

> Your mentor will use this check-in to pressure-test your hypothesis and sharpen your focus. The question is not "is your analysis finished?" — it's "is your thinking going in the right direction?" Come with questions, not just answers.

---

### Week 2 — Analyse & Build
**Check-in: 28–30 July | Bring: Draft Presentation**

By your second check-in, you should have:
- [ ] Deepened your analysis — segmentation, correlation, or modelling that goes beyond surface stats
- [ ] Quantified the business impact of your findings ($ or headcount, not just %)
- [ ] Chosen your **output format**: slides, dashboard, interactive app, or narrated demo
- [ ] Drafted your presentation or prototype in your chosen format
- [ ] A clear recommendation the CHRO could act on by Monday morning

> Judges care about clarity and impact, not the medium. Choose the format that best tells your story — not the most technical one.

---

### Week 3 — Present & Win
**Final submission to mentors: 5 August | Selection: 6 August | Presentation Day: 7 August**

By final submission, you should have:
- [ ] A polished, executive-ready output in your chosen format
- [ ] A compelling narrative: Hook → Story → Method → Impact → Recommend
- [ ] Every insight linked to a specific, prioritised action
- [ ] Practised your delivery — 10–15 min pitch, 10 min Q&A with an Accenture judge panel

> Three groups will be selected on 6 August to present to the panel. Selection is based on the full rubric — technical quality and professional behaviours combined.

---

## How You Are Evaluated

Your submission is assessed across **two parts**. Both matter for selection.

---

### Part A — Technical Rubric (100 points)

#### 1. Problem Framing & Hypothesis — 15 pts

| Score | What it looks like |
|---|---|
| 13–15 | One specific HR problem chosen; testable hypothesis stated before analysis; linked to the $42M; revisited when data surprised you |
| 9–12 | Broad problem area; some business link; hypothesis implicit |
| 5–8 | No clear problem statement; feels like a data dump |
| 0–4 | Findings disconnected from the brief |

**Ask yourself:** What is the one thing you believe is most wrong at NovaCorp, and why? If you were wrong, what would the data look like — did you check?

---

#### 2. Data Exploration & Rigour — 20 pts

| Score | What it looks like |
|---|---|
| 17–20 | All 4 datasets explored; joins validated; missing data acknowledged; multi-system fragmentation noted; filters documented |
| 12–16 | ≥3 datasets used; joins done but not validated; some attention to quality |
| 7–11 | 1–2 datasets; no join validation; distributions not checked |
| 0–6 | Single dataset used; conclusions drawn on raw unexamined data |

**Things rigorous teams check:**
- `engagement.csv` has ~18% non-response — do non-responders attrite at a different rate?
- `performance.csv` has 3 review cycles — take the most recent rating per person before joining
- `legacy_entity_code` flags 4 source systems — do patterns hold across all entities?
- After joining employees + attrition, your row count should be exactly 1,400 matched rows

---

#### 3. Analytical Depth & Evidence — 25 pts

| Score | What it looks like |
|---|---|
| 21–25 | Segmentation across ≥2 dimensions simultaneously; trend over time; voluntary vs involuntary vs regrettable distinguished; explains WHY not just WHAT; bonus for predictive model or flight-risk score |
| 15–20 | Clear segmentation on 1 dimension; trends identified; 2-level depth |
| 8–14 | Surface-level stats; no segmentation; no exit type distinction |
| 0–7 | Descriptive counts/means only |

**Great analysts ask 'why' at least 3 times before accepting an answer.** A stat without context is just a number — link every finding to a business outcome.

---

#### 4. Insight Quality & Business Impact — 25 pts

| Score | What it looks like |
|---|---|
| 21–25 | 2–3 root causes with evidence; every insight quantified ($, %, headcount); non-obvious findings; links back to $42M |
| 15–20 | Root causes identified with evidence; ≥1 quantified impact |
| 8–14 | Findings stated without business translation |
| 0–7 | Obvious observations with no evidence or business context |

**How to quantify:** `salary_at_exit` is in `attrition_log.csv`. Replacement cost is typically 50–200% of annual salary. Multiply by regrettable exits. Link to the $42M.

---

#### 5. Communication & Recommendation — 15 pts

| Score | What it looks like |
|---|---|
| 13–15 | Hook → Story → Method → Impact → Recommend; no jargon; 1–2 bold, specific actions with owner, timeline, and success metric |
| 9–12 | Clear narrative; recommendations slightly generic; some jargon |
| 5–8 | Data presented but not told as a story; vague recommendations |
| 0–4 | No narrative; no actionable recommendations |

**Recommendation quality test:** Can a CHRO issue a calendar invite Monday morning based on what you've told them? Who owns it? How will they know in 6 months if it worked?

**Output checklist:**
- [ ] No raw statistical output visible to the audience
- [ ] Every chart has a headline insight, not just a title (e.g. "High Performers Leave 39% Faster" — not "Attrition by hipo_flag")
- [ ] Visualisations are readable without narration
- [ ] Recommendation slide answers: What / Who / By When / How We Measure

---

### Part B — Professional Behaviours (scored 1–10 per dimension)

These are observed continuously by your mentor — not just at submission. They reflect the behaviours that make a great consultant, not just a great analyst.

#### Engagement
| Score | What it looks like |
|---|---|
| 9–10 | Proactively reaching out every 1–2 days; sharing progress, questions, or blockers without being asked |
| 6–8 | Regular communication; responds promptly; occasional check-ins |
| 3–5 | Communicates when prompted; slow to respond |
| 1–2 | Only responds when directly asked; effectively silent between sessions |

#### Creativity
| Score | What it looks like |
|---|---|
| 9–10 | Analysis goes beyond the obvious; explores angles others wouldn't think to check; output format or framing is genuinely novel |
| 6–8 | Some original thinking; mostly follows expected analytical paths with a few interesting detours |
| 3–5 | Competent but predictable; analysis could have been generated by a prompt with no data |
| 1–2 | Work is indistinguishable from a generic LLM output; no original insight grounded in this specific dataset |

#### Collaboration
| Score | What it looks like |
|---|---|
| 9–10 | Every team member visibly contributing; communication within the team is clear, frequent, and evident in the work |
| 6–8 | Most members contributing; occasional imbalance; work product feels cohesive |
| 3–5 | Uneven contributions; one or two people carrying the work |
| 1–2 | Work produced by effectively one person; team dynamics absent |

#### Accountability & Punctuality
| Score | What it looks like |
|---|---|
| 9–10 | Team plan submitted to mentor by 20 July; milestone deliverables met on time or communicated proactively ahead of any delay |
| 6–8 | Minor delays but communicated in advance; plan submitted close to deadline |
| 3–5 | Milestones missed without prior communication; plan submitted late |
| 1–2 | Last-minute plan or no plan; ghosting on milestone check-ins |

> **Note on 20 July:** Your team plan is due to your mentor by end of day 20 July. A plan passed by this date scores 9–10 on Accountability. A plan submitted at the last minute or after a missed check-in scores 1–3.

---

## Using AI Well

AI tools can help you go faster — but they cannot look at your data. Any insight an LLM could have generated without seeing the actual numbers will score poorly on insight quality. Judges will recognise generic analysis immediately.

**7 ways to use AI well:**

1. **Hypothesis generation** — Paste the dataset column names and ask for 5 testable hypotheses before you start. Use it to pressure-test your instincts, not replace them.

2. **Boilerplate code** — Describe what you need in plain English (*"Join employees.csv to attrition_log.csv, calculate voluntary attrition by department and hipo_flag"*). Get working code in seconds. Spend your time on interpretation.

3. **Sanity-check your logic** — After forming a conclusion, ask: *"What's wrong with this reasoning? What confounding variables am I missing?"*

4. **Chart headline writing** — Never label a chart "Attrition by Department." Paste your finding and ask for 5 executive-ready headline options.

5. **Translate for a non-technical audience** — Paste any analysis section and ask: *"Rewrite this for an HR leader who has 3 minutes to read it."*

6. **Stress-test your recommendation** — Ask: *"What would a sceptical CFO say? What evidence would counter the top 3 objections?"*

7. **Build a flight-risk scorer** — A logistic regression or decision tree that flags the top 20% at-risk employees is a genuine "consultant move" — ask an LLM to help you write it, then interpret the results yourself.

**The rule:** Use AI to go faster. Use the data to go deeper.

---

## Weekly Self-Assessment

Answer these before each check-in. Your mentor will ask.

### Before Week 1 Check-in
_One question per diamond phase — you should be able to answer all four._

- **Discover:** What was the most surprising thing the data showed you when you explored it with no assumptions?
- **Define:** What is the ONE HR problem we believe matters most — and what would the data look like if we were wrong?
- **Develop:** What are 2–3 genuinely different solutions we considered? Why did we rule out the ones we didn't choose?
- **Deliver:** What is our draft story arc — Problem → Evidence → So What → Recommended direction?

### Before Week 2 Check-in
- What is our strongest finding, and what number quantifies its business impact?
- What did the data show us that we didn't expect?
- Why did we choose our output format, and how does it serve the audience?
- What is our #1 recommendation, and who at NovaCorp would own it?

### Before Week 3 (Final Submission)
- Can a CHRO understand and act on this in under 5 minutes?
- Have we removed all jargon and p-values from the executive-facing output?
- What would we do differently if we had one more week?
- Are we ready for 10 minutes of hostile Q&A from a judge who read the data themselves?

---

*Guide prepared by Accenture AI & Data | UNSW Data SOC Challenge 2026*
