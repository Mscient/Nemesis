# Production Deployment Guide: Render + Vercel

This guide walks you through deploying your full-stack Hackathon starter to production:
- **Backend**: [Render](https://render.com) (Docker web service running `backend/Dockerfile.prod`)
- **Frontend**: [Vercel](https://vercel.com) (Static SPA hosting with Vite)

---

## Architecture

```
User Browser
    │
    ├─► https://your-project.vercel.app (React / Vite via Vercel Edge CDN)
    │     │
    │     ▼ (API requests + SSE streaming)
    └─► https://your-backend.onrender.com (FastAPI via Docker on Render)
          │
          ▼
        SQLite (/data/db.sqlite3) + Anthropic Claude API (or Mock AI)
```

---

## Prerequisites

1. Your code pushed to a **GitHub** repository.
2. A free account on [Render](https://render.com).
3. A free account on [Vercel](https://vercel.com).

---

## Step 1: Deploy Backend to Render

### Option A: One-Click Blueprint (`render.yaml`) — Recommended

Render natively supports Infrastructure-as-Code via the included `render.yaml`:

1. Go to the [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub repository.
4. Render will read `render.yaml` automatically and detect:
   - Service name: `hackathon-backend`
   - Runtime: `docker`
   - Dockerfile: `./backend/Dockerfile.prod`
   - Context: `./backend`
   - Health check path: `/api/health`
5. Fill in any required environment variables (e.g. `ANTHROPIC_API_KEY` or keep `USE_MOCK_AI=true`).
6. Click **Apply**.

---

### Option B: Manual Web Service Setup

If you prefer configuring via the web UI:

1. In Render Dashboard, click **New +** → **Web Service**.
2. Connect your GitHub repo.
3. Configure the service settings:
   - **Name**: `hackathon-backend`
   - **Region**: Closest to your users (e.g., Frankfurt or Oregon)
   - **Branch**: `main`
   - **Root Directory**: *(leave blank)*
   - **Runtime**: **Docker**
   - **Dockerfile Path**: `./backend/Dockerfile.prod`
   - **Docker Context**: `./backend`
   - **Instance Type**: **Free**
4. Expand **Advanced**:
   - **Health Check Path**: `/api/health`
5. Under **Environment Variables**, add:
   | Key | Value | Notes |
   |---|---|---|
   | `USE_MOCK_AI` | `true` | Set to `false` if using real Claude API key |
   | `ANTHROPIC_API_KEY` | `sk-ant-...` | Optional if `USE_MOCK_AI=true` |
   | `CORS_ORIGINS` | `http://localhost:5173` | We will update this with your Vercel URL in Step 3 |
   | `DATABASE_URL` | `sqlite:////data/db.sqlite3` | SQLite database file location |
6. Click **Create Web Service**.

Once deployed, note your Render backend URL:
```
https://<your-backend-name>.onrender.com
```

Test it in your browser or terminal:
```bash
curl https://<your-backend-name>.onrender.com/api/health
# Response: {"status":"ok","version":"0.1.0"}
```

---

## Step 2: Deploy Frontend to Vercel

1. Go to the [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New…** → **Project**.
3. Import your GitHub repository.
4. In the **Configure Project** screen:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select **`frontend`** *(Critical!)*
   - **Build Command**: `pnpm build` (or leave default Vite build)
   - **Output Directory**: `dist`
5. Expand **Environment Variables** and add:
   | Key | Value |
   |---|---|
   | `VITE_API_URL` | `https://<your-backend-name>.onrender.com` |
6. Click **Deploy**.

> **SPA Routing Note**: `frontend/vercel.json` already contains rewrites to `/index.html`. Direct visits to `/chat` or `/dashboard` will route correctly without 404 errors.

Once deployment finishes, copy your live Vercel URL:
```
https://<your-project>.vercel.app
```

---

## Step 3: Connect Frontend to Backend (CORS)

Now allow your Vercel frontend to make requests to your Render backend:

1. Open your **Render Dashboard** and select your `hackathon-backend` service.
2. Go to **Environment**.
3. Update `CORS_ORIGINS`:
   ```env
   CORS_ORIGINS=https://<your-project>.vercel.app,http://localhost:5173
   ```
   *(Multiple comma-separated origins are supported so local dev continues to work).*
4. Save Changes. Render will automatically apply the changes and restart the service.

---

## Step 4: Verification Checklist

- [ ] **Backend Health**: `https://<backend>.onrender.com/api/health` returns `{"status":"ok"}`.
- [ ] **API Swagger UI**: `https://<backend>.onrender.com/docs` opens the interactive API docs.
- [ ] **Frontend Loading**: `https://<project>.vercel.app` loads the homepage.
- [ ] **SPA Direct Link**: Refreshing `https://<project>.vercel.app/chat` loads without 404.
- [ ] **AI Chat**: Send a message in `/chat` and confirm streaming responses appear without CORS errors in DevTools Console (`F12`).

---

## Hackathon Pro-Tips

1. **Free Tier Cold Starts**: Render's free tier spins down after 15 minutes of inactivity. Send a quick request to `/api/health` 1-2 minutes before your pitch to ensure the backend is warm.
2. **Demo Backup**: Keep `USE_MOCK_AI=true` ready in Render environment variables. If you hit Anthropic rate limits or network issues during your demo, flip `USE_MOCK_AI=true` for an instant zero-failure fallback.
3. **Database Persistence**: On Render Free tier, the local container disk is ephemeral across redeploys. For hackathon demos, this is fine; for long-term storage, attach a Render Persistent Disk (Starter plan) or connect to a hosted PostgreSQL instance.
