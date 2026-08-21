# Production Deployment Guide

This guide details the step-by-step instructions for deploying the Unified P&L AI Financial Intelligence Platform to Render (Backend & Database) and Vercel (Frontend).

---

## 1. Database Deployment (PostgreSQL on Render)
1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **PostgreSQL**.
3. Configure the database parameters:
   - **Name**: `unified-pl-db`
   - **Database Name**: `unified_pl`
   - **User**: `db_admin`
   - **Region**: Choose the closest region (e.g. `Oregon (US West)` or `Frankfurt (EU)`)
   - **Plan**: Select **Free** (or Starter/Standard for production loads)
4. Click **Create Database**.
5. Save the **Internal Database URL** and **External Database URL** (e.g. `postgresql://db_admin:password@host/unified_pl`).

---

## 2. Backend Service Deployment (FastAPI on Render)
1. Click **New +** and select **Web Service**.
2. Connect your Git repository.
3. Configure service settings:
   - **Name**: `unified-pl-backend`
   - **Language**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker --chdir backend main:app --bind 0.0.0.0:$PORT`
4. Add the following **Environment Variables**:
   - `DATABASE_URL`: Set to your **External Database URL** from the Render PostgreSQL configuration.
   - `GEMINI_API_KEY`: Your Google Gemini API Key.
   - `SECRET_KEY`: A secure random hash string (e.g. generated via `openssl rand -hex 32`).
   - `ACCESS_TOKEN_EXPIRE_MINUTES`: `60`
   - `REFRESH_TOKEN_EXPIRE_DAYS`: `7`
5. Click **Deploy Web Service**.
6. Note the public URL of your service (e.g. `https://unified-pl-backend.onrender.com`).

---

## 3. Applying Database Migrations in Production
Before accessing the platform, apply the database schema migration:
- Render runs build steps dynamically. You can append the migrations to the build command:
  ```bash
  pip install -r backend/requirements.txt && cd backend && alembic upgrade head
  ```
- Alternatively, trigger a one-time migration execution under Render **Shell** tab or run a release script command.

---

## 4. Frontend Deployment (Vercel)
The frontend is a static web application built using vanilla HTML, CSS, and JS.
1. Install the Vercel CLI locally or connect your Git repository in the [Vercel Dashboard](https://vercel.com).
2. Configure `vercel.json` in the project root:
   ```json
   {
     "cleanUrls": true,
     "trailingSlash": false,
     "rewrites": [
       { "source": "/(.*)", "destination": "/frontend_v2/$1" }
     ]
   }
   ```
3. Set the Backend API URL in the frontend script:
   - Modify the API URL variable at the top of [api.js](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/frontend_v2/js/api.js) (or configure environment variables if using a build system):
     ```javascript
     const BASE_URL = 'https://unified-pl-backend.onrender.com';
     ```
4. Deploy the project:
   ```bash
   vercel --prod
   ```
5. Note the deployment domain url (e.g. `https://unified-pl-frontend.vercel.app`).
