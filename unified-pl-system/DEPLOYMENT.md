# Deployment Guide

## Using Docker Compose (Local & Self-Hosted)
The simplest way to run the entire stack is via Docker Compose:
```bash
docker-compose up --build -d
```
This provisions a PostgreSQL database and the FastAPI backend automatically. The API will be available at `http://localhost:8000`.

## Cloud Deployment

### 1. Render (Backend API)
The backend is configured for easy deployment to [Render](https://render.com) using the `render.yaml` configuration.
- Connect your GitHub repository to Render.
- Render will automatically provision a PostgreSQL database and a Web Service for the FastAPI app.
- Ensure you set the `GEMINI_API_KEY` environment variable in the Render Dashboard.

### 2. Vercel (Frontend)
The frontend (`frontend_v2`) is configured as a static site and can be deployed directly to [Vercel](https://vercel.com).
- Connect your repository to Vercel.
- The root `vercel.json` maps routing automatically to `frontend_v2/index.html`.
- Vercel will build and deploy the application within seconds.
- Update the `API_BASE_URL` in `frontend_v2/js/api.js` to point to your new Render backend URL before pushing.
