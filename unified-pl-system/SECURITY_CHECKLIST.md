# Security Checklist & Audit - Unified AI Financial Intelligence Platform

This security checklist documents the architecture and implementation configurations validating authentication controls, token policies, cross-origin parameters, role definitions, and transaction audit trails.

---

## 1. Authentication & Session Parameters

- [x] **Secure Hashing Algorithm**: Passwords are hashed using `bcrypt` (via `passlib.context.CryptContext` in `backend/core/security.py`), preventing plain-text storage in the database.
- [x] **Remember Me Configuration**: Configured in [login.js](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/frontend_v2/js/login.js) to store JWT tokens in `localStorage` if checked, or transient `sessionStorage` for basic browser window sessions.
- [x] **Token Lifespans Policy**:
  - **Access Tokens**: Expire in **30 minutes**, reducing exposure window.
  - **Refresh Tokens**: Expire in **7 days**, allowing seamless re-authorization.
- [x] **Auto-Refresh Fallback**: Mapped in [api.js](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/frontend_v2/js/api.js) to intercept HTTP `401 Unauthorized` responses and attempt to generate a new access token via `/api/v1/auth/refresh` before retrying failed requests.

---

## 2. API Security & Access Controls

- [x] **CORS Middleware**: Mounted in `backend/main.py` using `FastAPI`'s `CORSMiddleware`.
  - Allowed origins list: Loaded dynamically from `settings.ALLOWED_ORIGINS` (defaults to `http://localhost:3000,https://unified-pl.vercel.app` to restrict unauthorized domain scripts).
- [x] **Role-Based Access Control (RBAC)**:
  - Role definition field: User roles are declared inside the database model `User` using standard string categories (e.g. `Analyst`, `Supervisor`, `Administrator`).
  - Active check verification: Restricted endpoints call user credentials verification helper functions (`get_current_active_user`) inside `backend/core/security.py` to prevent session spoofing.
- [x] **Slowapi Rate Limiting**: Limit parameters configured in `backend/main.py` (using `slowapi.Limiter` to filter requests by IP origin, mitigating DDoS and brute-force vectors).

---

## 3. Transaction Audit Trail (RBAC Compliance)

- [x] **Automated Audit Logs**: The backend triggers database writes to `AuditLog` for critical state changes (e.g., executing user login, ingesting CSV documents, executing payment freezes).
- [x] **Audit Log Fields**:
  - `user_id`: Reference link of actor executing action.
  - `action`: Name of action executed (e.g., `user_login`, `pl_file_upload`, `anomaly_freeze`).
  - `resource`: Affected record link.
  - `timestamp`: UTC datetime log.
- [x] **Front-End Log Viewer**: Auditable history logs are displayed under the **Profile** view, providing supervisors with immediate context.
- [x] **Segregation of Duties (SOD)**:
  - Threshold rule: High-severity anomalies cannot be resolved or dismissed by the same Analyst who uploaded the file, satisfying corporate audit compliance requirements.
