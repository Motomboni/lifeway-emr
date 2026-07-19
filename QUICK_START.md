# Quick Start Guide

## Starting the Application

### 1. Start the Backend Server

**Important:** The backend must be running before the frontend can make API calls.

```bash
# Navigate to backend directory
cd backend

# Start Django development server
python manage.py runserver
```

The backend should start on `http://localhost:8000`

**Verify it's running:**
- Open `http://localhost:8000/api/v1/health/` in your browser
- You should see a JSON response

### 2. Start the Frontend Server

**In a new terminal window:**

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start React development server
npm start
```

The frontend should start on `http://localhost:3000` (or another port if 3000 is taken)

### 3. Troubleshooting

#### 504 Gateway Timeout Error

**Symptom:** Frontend shows "504 Gateway Timeout" when trying to login.

**Causes:**
1. Backend server is not running
2. Backend is running on a different port
3. Database connection issues

**Solutions:**

1. **Check if backend is running:**
   ```bash
   # In backend directory
   python manage.py runserver
   ```
   
   You should see:
   ```
   Starting development server at http://127.0.0.1:8000/
   ```

2. **Check backend port:**
   - Default is port 8000
   - If using a different port, update `frontend/src/setupProxy.js`:
     ```javascript
     target: 'http://localhost:8001', // Change to your port
     ```

3. **Check database:**
   ```bash
   cd backend
   python manage.py migrate
   ```

4. **Check for port conflicts:**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Linux/Mac
   lsof -i :8000
   ```

#### React Router Warnings

These are harmless warnings about future React Router changes. They can be ignored or suppressed by adding future flags to your Router configuration.

#### Backend Not Starting

**Common issues:**

1. **Database not migrated:**
   ```bash
   cd backend
   python manage.py migrate
   ```

2. **Missing dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Port already in use:**
   ```bash
   python manage.py runserver 8001
   ```

## Local test before deployment (Windows)

Use the project venv (Python 3.11 via `uv`), not MSYS `python`.

```powershell
# One-time
.\scripts\setup-backend-venv.ps1

# Fresh local DB + test users + NHIA tariffs (SQLite — easiest)
.\scripts\prepare-local.ps1 -UseSqlite -ResetDb

# Terminal 1 — API (must use same SQLite env as prepare)
.\scripts\start-local-backend.ps1 -UseSqlite

# Terminal 2 — UI
cd frontend
npm install
npm start
```

Open **http://localhost:3000** and log in:

| Role | Email | Password |
|------|-------|----------|
| Doctor | doctor@clinic.com | Doctor123! |
| Receptionist | receptionist@clinic.com | Receptionist123! |

**Manual v2.1 checklist**

1. Register patient → create visit → pay registration (receptionist)
2. Open consultation as doctor → **Clinical AI Scribe** → generate → **Apply to consultation**
3. Confirm NHIA validation badges and form fields filled
4. Save consultation → confirm ICD-11 codes appear

**Automated checks**

```powershell
.\scripts\run-backend-tests.ps1
# optional E2E (backend must be running):
cd frontend
npx playwright test e2e/workflows/visit-pay-consult.spec.ts --project=chromium
```

For Postgres instead of SQLite, omit `-UseSqlite` and ensure `backend/.env` DB settings match a running local Postgres.

---

## Development Workflow

1. **Always start backend first** - The frontend depends on it
2. **Check console logs** - Both frontend and backend logs show useful debugging info
3. **Restart after config changes** - Restart both servers after changing proxy or settings

## Port Configuration

- **Backend:** `http://localhost:8000` (default)
- **Frontend:** `http://localhost:3000` (default, React will use next available if taken)
- **Proxy:** Frontend proxies `/api/*` requests to `http://localhost:8000/api/*`

## Environment Variables

### Backend (.env file in backend/ directory)

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
```

### Frontend

No environment variables required for basic development. The proxy is configured in `setupProxy.js`.
