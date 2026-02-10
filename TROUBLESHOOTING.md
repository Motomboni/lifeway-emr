# Troubleshooting Guide

## Common Issues and Solutions

### 504 Gateway Timeout Error

**Symptom:** Frontend shows "504 Gateway Timeout" when trying to login or make API calls.

**Cause:** The Django backend server is not running or not accessible.

**Solution:**

1. **Start the Django backend server:**
   ```bash
   cd backend
   python manage.py runserver
   ```
   
   The server should start on `http://localhost:8000`

2. **Verify the server is running:**
   - Open `http://localhost:8000/api/v1/health/` in your browser
   - You should see a JSON response with health status

3. **Check for port conflicts:**
   - If port 8000 is already in use, you can use a different port:
     ```bash
     python manage.py runserver 8001
     ```
   - Then update `frontend/src/setupProxy.js` to use port 8001

4. **Verify CORS settings:**
   - Make sure `CORS_ALLOWED_ORIGINS` in `backend/core/settings.py` includes `http://localhost:3000`
   - Or ensure `CORS_ALLOW_ALL_ORIGINS = True` is set for development

5. **Check firewall/antivirus:**
   - Ensure your firewall or antivirus is not blocking localhost connections

### React Router Future Flag Warnings

**Symptom:** Console shows warnings about React Router future flags.

**Cause:** These are just warnings about upcoming React Router v7 changes.

**Solution:** These warnings are harmless and can be ignored. To suppress them, you can add future flags to your Router configuration in `App.tsx`:

```typescript
<BrowserRouter
  future={{
    v7_startTransition: true,
    v7_relativeSplatPath: true,
  }}
>
```

### Backend Not Starting

**Symptom:** `python manage.py runserver` fails.

**Common Causes and Solutions:**

1. **Database not migrated:**
   ```bash
   python manage.py migrate
   ```

2. **Missing dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Port already in use:**
   - Use a different port: `python manage.py runserver 8001`
   - Or kill the process using port 8000

4. **Settings errors:**
   ```bash
   python manage.py check
   ```

### Frontend Not Starting

**Symptom:** `npm start` fails.

**Common Causes and Solutions:**

1. **Missing dependencies:**
   ```bash
   npm install
   ```

2. **Port 3000 already in use:**
   - Use a different port: `PORT=3001 npm start`
   - Or kill the process using port 3000

3. **Proxy configuration issues:**
   - Restart the dev server after modifying `setupProxy.js`
   - Check that `setupProxy.js` is in `frontend/src/` directory

### Authentication Issues

**Symptom:** Login fails or tokens are not working.

**Solutions:**

1. **Clear browser storage:**
   - Open browser DevTools
   - Go to Application/Storage tab
   - Clear Local Storage
   - Refresh the page

2. **Check token format:**
   - Tokens should be stored as: `{"access": "...", "refresh": "..."}`
   - Check `localStorage.getItem('auth_tokens')` in console

3. **Verify backend authentication:**
   - Test login endpoint directly: `POST http://localhost:8000/api/v1/auth/login/`
   - Check backend logs for errors

### Database Issues

**Symptom:** Database errors or migration issues.

**Solutions:**

1. **Reset database (development only):**
   ```bash
   python manage.py flush
   python manage.py migrate
   python manage.py createsuperuser
   ```

2. **Check database connection:**
   - Verify database settings in `backend/core/settings.py`
   - For SQLite, ensure the file exists and is writable

3. **Recreate migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

### CORS Errors

**Symptom:** Browser console shows CORS errors.

**Solutions:**

1. **Check CORS settings in `backend/core/settings.py`:**
   ```python
   CORS_ALLOWED_ORIGINS = [
       "http://localhost:3000",
       "http://127.0.0.1:3000",
   ]
   ```

2. **For development, you can allow all origins:**
   ```python
   CORS_ALLOW_ALL_ORIGINS = True  # Only for development!
   ```

3. **Restart Django server after changing CORS settings**

### Module Not Found Errors

**Symptom:** Python/TypeScript errors about missing modules.

**Solutions:**

1. **Python:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Node.js:**
   ```bash
   npm install
   ```

3. **Check virtual environment:**
   - Ensure you're using the correct Python virtual environment
   - Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)

## Quick Start Checklist

Before reporting issues, ensure:

- [ ] Backend server is running on `http://localhost:8000`
- [ ] Frontend server is running on `http://localhost:3000`
- [ ] All dependencies are installed (both backend and frontend)
- [ ] Database migrations are applied
- [ ] CORS settings allow `http://localhost:3000`
- [ ] Browser console shows no blocking errors
- [ ] Network tab shows API requests reaching the backend

## Getting Help

If you're still experiencing issues:

1. Check the browser console for errors
2. Check the Django server logs for errors
3. Verify both servers are running
4. Check network tab to see if requests are reaching the backend
5. Review the error messages carefully - they often contain helpful information

## Development Server Commands

**Backend:**
```bash
cd backend
python manage.py runserver
```

**Frontend:**
```bash
cd frontend
npm start
```

Both should be running simultaneously for the app to work.
