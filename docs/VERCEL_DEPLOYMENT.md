# Vercel Deployment Guide — Literature Intelligence Platform

This guide explains how to deploy the **Literature Intelligence Platform** directly to **Vercel** as a full-stack application (FastAPI backend + Vite React frontend).

---

## Architecture on Vercel

```
Incoming Request
      │
      ├───► /api/(.*)  ──► api/index.py (FastAPI Serverless Function via @vercel/python)
      │
      └───► /(.*)      ──► frontend/dist/ (Vite React SPA via @vercel/static-build)
```

- **Backend:** Serves all REST endpoints from `api/index.py` using Python 3.10/3.11/3.12 Serverless Functions.
- **Frontend:** Automatically built via `frontend/package.json` (`npm run build`) and served globally via Vercel Edge Network.
- **Storage:** Dynamic serverless storage automatically uses `/tmp/literature.db` and `/tmp/chroma` to respect Vercel's read-only filesystem constraints.

---

## Step-by-Step Vercel Deployment

### Option 1: Deploy from GitHub (Recommended)
1. Push your repository to GitHub (or extract the zip into your Git repository).
2. Go to your [Vercel Dashboard](https://vercel.com/dashboard) and click **"Add New..."** -> **"Project"**.
3. Import your GitHub repository (`Literature-Intelligence-Platform`).
4. **Project Settings:**
   - **Framework Preset:** `Other` (or `Vite`)
   - **Root Directory:** `./` (Leave as default root)
   - **Build Command:** Leave default (`vercel.json` automatically manages builds)
   - **Output Directory:** Leave default
5. Click **"Deploy"**.

---

### Option 2: Deploy Using Vercel CLI
If deploying directly from your terminal:

```bash
# 1. Install Vercel CLI globally
npm i -g vercel

# 2. Login to your Vercel account
vercel login

# 3. Deploy to preview
vercel

# 4. Deploy to production
vercel --prod
```

---

## Environment Variables on Vercel (Optional)

In your Vercel Project Settings -> **Environment Variables**, you can configure:

| Variable Name | Default Value | Description |
|:---|:---|:---|
| `ENVIRONMENT` | `production` | Deployment environment flag |
| `DEBUG` | `False` | Disables debug logs in production |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Point to a public/tunnel Ollama endpoint (e.g. via Ngrok) if remote inference is desired |
| `OPENALEX_EMAIL` | `researcher@academic.edu` | Email for courteous OpenAlex discovery rate limits |

> **Note on Local LLMs on Cloud:** Vercel serverless functions do not bundle local GPU/CPU model weights. The platform's built-in non-blocking fallback engine automatically activates on Vercel, providing deterministic L2-normalized 768-dimensional embeddings, semantic retrieval, cross-paper comparison matrices, and grounded literature review generation with exact citations without needing local Ollama.

---

## Included Vercel Configuration Files

- **`vercel.json`:** Coordinates `@vercel/python` for `api/index.py` and `@vercel/static-build` for `frontend/package.json`.
- **`api/index.py`:** Canonical FastAPI entrypoint resolving `app` for Vercel's Python runtime.
- **`api/requirements.txt`:** Serverless dependency manifest.
- **`pyproject.toml`:** Explicit entrypoint declaration for Vercel.
- **`package.json` (Root):** Monorepo build orchestrator.

