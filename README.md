# Inzira AI

Inzira AI is a bilingual, privacy-conscious household vulnerability screening and opportunity-navigation tool developed for the NISR 2026 Big Data Hackathon. It turns 12 simple household question groups into 19 model inputs, runs a compact XGBoost model, and provides a cautious screening result, practical referrals and explainable opportunity matches.

The application is **decision support only**. It must never approve, deny, or withdraw benefits, credit, insurance, or public assistance without human review.

## What is included

- Kinyarwanda-first and English user interface
- Guided six-step assessment with an “I don't know” option
- No names, ID numbers, telephone numbers, or other direct identifiers
- Missing-answer handling and a 60% minimum completeness rule
- Additional warning for households with 1–3 members
- Suggested support pathways requiring professional review
- Locked-test metrics, model card, and fairness limitations inside the app
- Downloadable, non-identifying result summary
- Standalone opportunity matcher for jobs, internships, vocational training, agriculture and enterprise support
- Transparent fit score with the reasons, eligibility checks, current-status warning and official application route
- Downloadable opportunity plan and shortlist; the vulnerability score is never used to rank opportunities
- Anonymous referral creation and structured caseworker follow-up
- Impact dashboard for referrals, applications, progress outcomes and overdue follow-ups
- Session-only case storage with schema-validated CSV export and restore for the competition demo

## Model evidence

The deployed **Compact XGBoost** model was evaluated once on a locked test set of 2,259 households.

| Metric | Locked-test result |
|---|---:|
| Accuracy | 0.7734 |
| Balanced accuracy | 0.6783 |
| Macro F1 | 0.6815 |
| Vulnerable recall | 0.4972 |
| ROC AUC | 0.7933 |
| Average precision | 0.5466 |

The threshold is frozen at `0.49`. The test results must not be used for additional tuning.

## Run locally

The XGBoost joblib artifact was exported from Google Colab and is Linux-portable. Run the deployment on Linux, WSL, or Streamlit Community Cloud.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On WSL from this repository:

```bash
wsl
cd /mnt/c/Users/AKINLOYE/Documents/Inzira_AI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Verify before deployment

```bash
python -m pytest -q
python scripts/smoke_inference.py
python scripts/smoke_ui.py
python scripts/smoke_opportunity_matcher.py
python scripts/smoke_impact_dashboard.py
```

The smoke test loads both joblib artifacts, creates all 19 raw model inputs, transforms them into 49 processed predictors, and performs a real probability prediction.

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub. Do not add the EICV7 raw data or internal test predictions.
2. Open [share.streamlit.io](https://share.streamlit.io/).
3. Select the repository and set the main file to `app.py`.
4. Select Python 3.12 if the deployment settings offer a version choice.
5. Deploy, then complete one English and one Kinyarwanda assessment on a phone-sized screen.

No API, database, or secret is required for this competition release.

## Repository structure

```text
app.py                         Streamlit interface
src/inzira/                    Features, inference, referrals and opportunity ranking
data/opportunities.json        Reviewed official pathway catalogue (not a live vacancy feed)
tests/                         Unit tests
scripts/smoke_inference.py     End-to-end artifact check
scripts/smoke_impact_dashboard.py  Caseworker workflow check
artifacts/inzira_lite_v1_*/    Verified deployment bundle and model evidence
.streamlit/config.toml         Theme and privacy-oriented settings
requirements.txt               Deployment dependencies
```

## Responsible use

- A positive result means a complete assessment may be helpful; it does not establish eligibility.
- A lower-risk result must never be described as “not vulnerable.”
- The model has lower vulnerable-household recall for households with 1–3 members, so the interface always recommends professional assessment for this group.
- Suggested interventions are non-causal referral ideas, not automated prescriptions.
- Opportunity fit scores are relevance scores, not acceptance probabilities. Providers decide eligibility and availability.
- Case records intentionally exclude names, telephone numbers, national IDs and free-text personal notes.
- Browser-session storage is suitable for this demonstration, not production case management. Production use requires approved identity, access, encryption and retention controls.
- The Kinyarwanda copy is a draft and requires native-speaker review before public field use.

The EICV7 2023–2024 data is provided by the National Institute of Statistics of Rwanda. The raw survey data is intentionally excluded from this repository.
