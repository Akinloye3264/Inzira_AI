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
- Google-authenticated admin workspace with an explicit email allowlist
- Anonymous referral creation, structured follow-up and an admin audit trail
- MongoDB-backed referral dashboard for applications, outcomes and overdue follow-ups
- Reviewed opportunity directory plus schema-validated CSV export and restore
- Versioned FastAPI inference service with health checks, request validation and optional API-key protection
- Streamlit-to-FastAPI integration with automatic local-model fallback for demo reliability

## Architecture

The repository supports two deployment modes:

1. **Single-service demo:** Streamlit loads the verified model and performs inference in-process. This is the simplest hackathon deployment.
2. **Separated production path:** Streamlit is the frontend and calls the FastAPI service over HTTPS. FastAPI owns model loading and inference. If the configured API is temporarily unavailable, the Streamlit app safely falls back to the same local model.

FastAPI exposes:

- `GET /health`
- `GET /v1/model-info`
- `POST /v1/screenings`
- Interactive API documentation at `/docs`

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

Run the API in another terminal:

```bash
pip install -r requirements-api.txt
export INZIRA_API_KEY="replace-with-a-long-random-value"
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Then add this to local `.streamlit/secrets.toml`:

```toml
[api]
url = "http://localhost:8000"
key = "replace-with-the-same-long-random-value"
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
pip install -r requirements-dev.txt
python -m pytest -q
python scripts/smoke_inference.py
python scripts/smoke_ui.py
python scripts/smoke_opportunity_matcher.py
python scripts/smoke_impact_dashboard.py
```

The smoke test loads both joblib artifacts, creates all 19 raw model inputs, transforms them into 49 processed predictors, and performs a real probability prediction.

## Admin authentication and MongoDB

The public screening remains anonymous and session-only. The protected Admin page uses Streamlit's native Google OIDC login, an administrator email allowlist and MongoDB Atlas for persistent anonymous referral records.

1. Create a Google Cloud OAuth 2.0 web client.
2. Add `https://YOUR-APP.streamlit.app/oauth2callback` as an authorized redirect URI.
3. Create a MongoDB Atlas database user with read/write access only to the `inzira_ai` database.
4. Copy `.streamlit/secrets.example.toml`, replace every placeholder, and paste it into **Streamlit Community Cloud → App settings → Secrets**.
5. Put only approved Google account addresses in `admin.allowed_emails`.

Generate the cookie secret locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never commit `.streamlit/secrets.toml`, the Google client secret or the MongoDB URI. The repository already ignores the local secrets file.

## Deploy the FastAPI backend

`render.yaml` provides a deployable Render Blueprint. Connect this repository in Render and create the `inzira-ai-api` web service. When Render asks for `INZIRA_API_KEY`, enter a long random value. Put that same value in the Streamlit `[api].key` secret and set `[api].url` to the API's HTTPS `onrender.com` URL.

You can also build `Dockerfile.api` on any container host:

```bash
docker build -f Dockerfile.api -t inzira-ai-api .
docker run -p 8000:8000 -e INZIRA_API_KEY="your-secret" inzira-ai-api
```

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub. Do not add the EICV7 raw data or internal test predictions.
2. Open [share.streamlit.io](https://share.streamlit.io/).
3. Select the repository and set the main file to `app.py`.
4. Select Python 3.12 if the deployment settings offer a version choice.
5. Add the Google OIDC, admin allowlist and MongoDB values in the app's Secrets settings.
6. Optionally add the deployed FastAPI URL and matching API key under `[api]`. Without these values, local inference remains active.
7. Deploy, then complete one English and one Kinyarwanda assessment and one authenticated referral journey.

## Repository structure

```text
app.py                         Streamlit interface
api/main.py                    Versioned FastAPI model service
src/inzira/                    Features, inference, referrals and opportunity ranking
src/inzira/api_client.py       Streamlit-to-FastAPI client with local fallback
src/inzira/case_store.py       MongoDB referral persistence and admin audit trail
data/opportunities.json        Reviewed official pathway catalogue (not a live vacancy feed)
tests/                         Unit tests
scripts/smoke_inference.py     End-to-end artifact check
scripts/smoke_impact_dashboard.py  Caseworker workflow check
artifacts/inzira_lite_v1_*/    Verified deployment bundle and model evidence
.streamlit/config.toml         Theme and privacy-oriented settings
.streamlit/secrets.example.toml  Safe configuration template; contains no real secrets
requirements-core.txt          Shared model runtime dependencies
requirements.txt               Streamlit frontend dependencies
requirements-api.txt           FastAPI backend dependencies
requirements-dev.txt           Combined verification dependencies
render.yaml                    Render backend deployment blueprint
Dockerfile.api                 Portable API container
```

## Responsible use

- A positive result means a complete assessment may be helpful; it does not establish eligibility.
- A lower-risk result must never be described as “not vulnerable.”
- The model has lower vulnerable-household recall for households with 1–3 members, so the interface always recommends professional assessment for this group.
- Suggested interventions are non-causal referral ideas, not automated prescriptions.
- Opportunity fit scores are relevance scores, not acceptance probabilities. Providers decide eligibility and availability.
- Case records intentionally exclude names, telephone numbers, national IDs and free-text personal notes.
- Screening answers remain in the visitor's Streamlit session and are not written to MongoDB. Only an authenticated, allowlisted admin can create a persistent anonymous referral.
- MongoDB records still require an approved retention policy, database backups and institutional governance before real field deployment.
- The Kinyarwanda copy is a draft and requires native-speaker review before public field use.

The EICV7 2023–2024 data is provided by the National Institute of Statistics of Rwanda. The raw survey data is intentionally excluded from this repository.
