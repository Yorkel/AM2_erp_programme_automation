# Hugging Face Spaces deployment — setup guide

Step-by-step for migrating the FastAPI classifier from Render to Hugging Face Spaces. Same Docker image, different hosting target.

## Prerequisites

- Hugging Face account ([signup](https://huggingface.co/join)) — free
- A Hugging Face access token with write permissions ([create one](https://huggingface.co/settings/tokens))
- The existing Dockerfile in the repo root (already PORT-aware, reads `${PORT:-8000}`)

## Step 1 — Create the Space

1. Go to <https://huggingface.co/new-space>
2. Settings:
   - **Owner:** your HF username (or an org if you have one)
   - **Space name:** `am2-classifier`
   - **License:** MIT (or whichever you prefer)
   - **SDK:** **Docker** ← important, not Streamlit / Gradio
   - **Hardware:** CPU Basic (free, 2 vCPU, 16GB RAM, no GPU)
   - **Visibility:** Public (free)
3. Click **Create Space**

The URL of your space will be: `https://huggingface.co/spaces/<owner>/am2-classifier`
The public API URL will be: `https://<owner>-am2-classifier.hf.space`

## Step 2 — Add HF README frontmatter

HF Spaces requires a specific YAML frontmatter in `README.md` at the repo root. The existing repo doesn't have one yet. Add this to the top of the (new) Space's README — note the SDK and port settings:

```yaml
---
title: AM2 Classifier
emoji: 📰
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
---
```

`app_port: 8000` matches our Dockerfile's default. (HF Spaces' Docker SDK uses port 7860 by default; this override keeps our existing Dockerfile working unchanged.)

## Step 3 — Add the HF Space as a Git remote

The Space is a Git repository. To deploy, push to it.

```bash
# In the repo root
git remote add hf https://huggingface.co/spaces/<owner>/am2-classifier

# Authenticate with your HF token (paste when prompted as password)
# Username can be anything; password is the token from huggingface.co/settings/tokens

# Or set a credential helper:
git config --global credential.helper store
```

## Step 4 — What to push

The Space repo needs:
- `Dockerfile` (existing, repo root)
- `README.md` (with the HF frontmatter)
- `requirements.txt` / `requirements-api.txt` (already in repo)
- `src/serving/` (FastAPI app)
- `models/runs/` (the classifier artefacts) ← bundle these in the Docker image OR mount via HF Hub
- Any other code referenced by `src/serving/`

The Dockerfile already handles all of this. You're just pushing the existing repo to a new remote.

## Step 5 — Push

```bash
# Push only the relevant subtree (avoids pushing the whole repo, which includes 
# data, notebooks, etc.). Simplest first attempt:
git push hf main:main
```

If the push is too large (`.git` history is heavy), consider a subtree push or a separate deployment branch. For first deploy, full push usually works.

After push, HF starts building the Docker image. Watch progress at:
`https://huggingface.co/spaces/<owner>/am2-classifier`

Build typically takes 3-8 minutes for first deploy.

## Step 6 — Verify

Once the Space shows "Running" status:

```bash
# Health check
curl https://<owner>-am2-classifier.hf.space/health

# Should return:
# {"status":"ok","run_id":"v1_2026-05-16","variant":"sbert_no_meta","n_classes":6,"classes":[...]}
```

Then run the pipeline against the new URL:

```bash
export CLASSIFIER_API_URL=https://<owner>-am2-classifier.hf.space
python -m src.inference.classify_via_api --batch-size 50   # 16GB RAM = no batch ceiling worry
```

## Step 7 — Cut over

When the HF deployment is stable:

1. Update `.env`:
   ```
   CLASSIFIER_API_URL=https://<owner>-am2-classifier.hf.space
   ```
2. Update `.github/workflows/classify.yml` to set the same env var (via repo secret or workflow env)
3. Decide whether to **retain Render as fallback** or retire it. (Retain during transition; retire once HF has been stable for 1-2 weeks.)
4. Update `render.yaml` and memory to reflect the new primary deployment.

## Step 8 — Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Build fails: "Dockerfile not found" | Pushed wrong subtree | Push from repo root |
| Build succeeds but service crashes on startup | Model artefacts not in image | Verify `models/runs/` is `COPY`ed in Dockerfile |
| /health returns 404 | App not bound to expected port | Check `app_port` in README frontmatter matches what FastAPI listens on |
| Cold start takes >2 min | First load after >24h idle | Hit `/health` ahead of any batch run (the wake_up_service helper in `classify_via_api.py` already does this) |
| `/predict` returns 500 | Sentence-transformer download from inside container | Pre-cache the model in the Docker build step (`RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`) |

## Step 9 — Optional improvements

- **Pin model in Docker image** — `RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"` in Dockerfile so the first /predict doesn't need to download the model. Adds ~90MB to image size but saves ~30s on cold starts.
- **Bigger batch size** — once 16GB is confirmed available, batch=100 or even batch=200 is fine; will dramatically speed up runs.
- **Add secrets** for any future Supabase calls from inside the API. Configure in the Space's **Settings → Repository secrets**.

## Cost

Free tier is sufficient for this workload (twice-weekly cron, ~100 articles per run). HF Spaces upgrade tiers exist (CPU Upgrade, GPU) but aren't needed.
