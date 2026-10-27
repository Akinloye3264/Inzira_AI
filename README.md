# Inzira AI

Inzira AI is a bilingual, privacy-conscious household vulnerability screening and opportunity-navigation tool developed for the NISR 2026 Big Data Hackathon. It turns 12 simple household question groups into 19 model inputs, runs a compact XGBoost model, and provides a cautious screening result, practical referrals and explainable opportunity matches.

The application is **decision support only**. It must never approve, deny or withdraw benefits, credit, insurance, jobs or public assistance without human review.

## Applications

- `app.py` — anonymous public screening and opportunity matching.
- `admin_app.py` — separate Firebase-authenticated referral administration dashboard.
- Firebase Email/Password Authentication verifies administrators.
- An administrator email allowlist provides a second authorization check.
- Neon PostgreSQL stores anonymous referrals, follow-ups and audit events.
- Public screening answers remain in the visitor's Streamlit session.
- Providers—not Inzira AI administrators—decide programme eligibility and acceptance.

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

The threshold is frozen at `0.49`. The locked test results must not be used for further tuning.

## Local setup

The model artifact is Linux-portable. Use Linux, WSL or Streamlit Community Cloud.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add the Neon, Firebase and administrator allowlist values to `.env`, then run either app:

```bash
streamlit run app.py
streamlit run admin_app.py --server.port 8502
```

Never commit `.env`, `.streamlit/secrets.toml`, administrator passwords or the Neon connection string.

## Streamlit secrets

The administrator deployment reads:

```toml
[neon]
database_url = "YOUR_COMPLETE_POOLED_NEON_URL"

[firebase]
api_key = "YOUR_FIREBASE_WEB_API_KEY"
project_id = "YOUR_FIREBASE_PROJECT_ID"

[admin]
allowed_emails = ["your-admin-email@example.com"]
```

## Deploy on Streamlit Community Cloud

Create two Streamlit apps from the same GitHub repository and branch:

1. Public app — main file `app.py`.
2. Admin app — main file `admin_app.py`.
3. Select Python 3.12 for both deployments.
4. Add Firebase, Neon and the administrator allowlist only to the admin app's Secrets settings.
5. Test one anonymous referral creation, follow-up update, CSV export and logout.

Community Cloud hibernates inactive applications. A visitor can wake a sleeping app from its sleep page. The public model bundle is cached with `st.cache_resource` to minimize repeated loading while its process is active.

## Verification

```bash
pip install -r requirements.txt pytest
python -m pytest -q
python scripts/smoke_inference.py
python scripts/smoke_ui.py
python scripts/smoke_opportunity_matcher.py
python scripts/smoke_impact_dashboard.py
python scripts/smoke_admin_login.py
python scripts/check_neon.py
```

## Repository structure

```text
app.py                              Public Streamlit application
admin_app.py                        Separate Firebase-protected admin application
src/inzira/admin_dashboard.py       Responsive referral operations workspace
src/inzira/case_store.py            Neon PostgreSQL persistence and audit trail
src/inzira/firebase_auth.py         Firebase email/password session client
src/inzira/impact_tracking.py       Anonymous referral schema and metrics
data/opportunities.json             Reviewed pathways, not a live vacancy feed
artifacts/inzira_lite_v1_*/         Verified model bundle and evidence
.streamlit/secrets.example.toml     Safe deployment configuration template
```

## Responsible use

- A positive result means a complete assessment may be helpful; it does not establish eligibility.
- A lower-risk result must never be described as “not vulnerable.”
- Suggested interventions are non-causal referral ideas, not automated prescriptions.
- Opportunity fit scores are relevance scores, not acceptance probabilities.
- Case records exclude names, telephone numbers, national IDs and free-text personal notes.
- Neon data requires an approved retention policy, backups and institutional governance before real field use.
- The Kinyarwanda copy requires native-speaker review before public field use.

The EICV7 2023–2024 data is provided by the National Institute of Statistics of Rwanda. Raw survey data is intentionally excluded from this repository.
