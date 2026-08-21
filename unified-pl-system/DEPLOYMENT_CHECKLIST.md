# Deployment Checklist & Guide - Unified AI Financial Intelligence Platform

This deployment guide outlines the configuration settings and migration steps required to deploy the Unified AI platform to production hosting providers (Render for backend services and Vercel for frontend assets).

---

## 1. Production Hosting Setup

### Backend Deployment (Render)
Render uses the root [render.yaml](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/render.yaml) file to automatically provision a PostgreSQL instance and build the FastAPI web service using the backend `Dockerfile`:

1. Log in to your Render dashboard and click **New > Blueprint**.
2. Connect your repository clone link.
3. Render will parse `render.yaml` and provision:
   - **PostgreSQL Database**: `unified-pl-db` (Starter plan).
   - **Web Service**: `unified-pl-backend` (Docker environment, Ohio region, port 10000).
4. Render automatically populates the `DATABASE_URL` link property.
5. In the Render environment configuration panel for the Web Service, define the following variables manually:
   - `GEMINI_API_KEY`: The API key for Gemini AI explanations and Copilot interactions.
   - `ALLOWED_ORIGINS`: Set to your deployed Vercel frontend URL (e.g. `https://unified-pl.vercel.app`).
   - `SECRET_KEY`: Set a long random string for securing JWT tokens.

### Frontend Deployment (Vercel)
Vercel hosts the static HTML/CSS/JS frontend located inside the `frontend_v2` directory using the routing rules defined in [vercel.json](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/vercel.json):

1. Log in to your Vercel dashboard and click **Add New > Project**.
2. Select your repository.
3. In the **Project Settings** configuration panel:
   - **Framework Preset**: Select **Other** (since we use a vanilla static stack).
   - **Root Directory**: Leave empty or set to root directory (the project serves `frontend_v2` automatically as defined in `vercel.json`).
4. Click **Deploy**.
5. Once deployed, note down your production Vercel domain URL.
6. Open `frontend_v2/js/api.js` and update `API_BASE_URL` to match your Render production backend domain (e.g., `https://unified-pl-backend.onrender.com/api/v1`).

---

## 2. Database Migrations & Initial Seeding

When the backend container boots up, it automatically executes the shell command `alembic upgrade head && uvicorn main:app` to align the database structure with the latest model schema definitions:

### Manual Migration Check
If you need to verify or apply migrations manually on your database instance:

```bash
# Set database environment variable context
export DATABASE_URL="postgresql://user:password@localhost/unified_pl"

# Apply all pending Alembic schema migrations
alembic upgrade head
```

### Initial Data Seeding
To populate a fresh database with default admin/analyst users and initial ledger records, run the seed script:

```bash
# Run backend database seeding script
python backend/seed.py
```

This creates the default user account:
- **Username**: `testuser`
- **Password**: `testpass`
- **Email**: `test@test.com`

---

## 3. Local Docker Build Verification

To test the entire containerized orchestration suite locally before pushing to production:

```bash
# Build and run Postgres and FastAPI containers in detached mode
docker-compose up --build -d

# Verify both containers are running correctly
docker ps

# Check backend container logs
docker-compose logs backend

# Tear down services and clean up volumes
docker-compose down -v
```
