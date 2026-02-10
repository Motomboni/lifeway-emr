# E2E Billing Tests

End-to-end tests for the billing system using Playwright.

## Prerequisites

⚠️ **IMPORTANT**: The backend server MUST be running before running tests!

Before running the tests, ensure:

1. **Backend Server Running** (REQUIRED)
   ```bash
   cd backend
   python manage.py runserver
   ```
   
   The backend should be accessible at `http://localhost:8000`
   
   Verify it's running by visiting: `http://localhost:8000/api/v1/health/`

2. **Frontend Dev Server Running** (or Playwright will auto-start it)
   ```bash
   cd frontend
   npm start
   ```

3. **Test Users Created in Database**
   
   You need to create test users in the database. Run these Django commands:
   
   ```python
   # In Django shell: python manage.py shell
   from apps.users.models import User
   
   # Create test doctor
   User.objects.create_user(
       username='doctor@clinic.com',
       email='doctor@clinic.com',
       password='Doctor123!',
       first_name='Test',
       last_name='Doctor',
       role='DOCTOR')
   
   # Create test receptionist
   User.objects.create_user(
       username='receptionist@clinic.com',
       email='receptionist@clinic.com',
       password='Receptionist123!',
       first_name='Test',
       last_name='Receptionist',
       role='RECEPTIONIST')
   
   # Create test lab tech
   User.objects.create_user(
       username='labtech@clinic.com',
       email='labtech@clinic.com',
       password='LabTech123!',
       first_name='Test',
       last_name='Lab Tech',
       role='LAB_TECH')
   ```

4. **Lab Service Price List Configured**
   
   Create a lab service in the price list:
   
   ```python
   # In Django shell
   from apps.billing.price_lists import LabServicePriceList
   
   LabServicePriceList.objects.create(
       service_code='CBC-001',
       service_name='Complete Blood Count',
       amount=5000.00,
       description='Complete blood count test',
       is_active=True)
   ```

5. **Database Migrations Applied**
   ```bash
   cd backend
   python manage.py migrate
   ```

## Running Tests

### Run All Tests
```bash
npm run test:e2e
```

### Run Specific Test File
```bash
npx playwright test e2e/billing/billing.spec.ts
```

### Run Specific Test (by name pattern)
```bash
npx playwright test e2e/billing/billing.spec.ts -g "Cash visit"
```

### Run Specific Test (by line number)
```bash
# Run test at line 978 (Cash Visit Full Lifecycle)
npx playwright test e2e/billing/billing.spec.ts:978
```

### Run Tests in Specific Browser
```bash
# Chromium only
npx playwright test e2e/billing/billing.spec.ts --project=chromium

# Firefox only
npx playwright test e2e/billing/billing.spec.ts --project=firefox

# WebKit only
npx playwright test e2e/billing/billing.spec.ts --project=webkit
```

### List All Tests (without running)
```bash
npx playwright test --list
```

### Common Issues

**"No tests found" error:**
- Make sure you're in the `frontend` directory
- Use forward slashes in the path: `e2e/billing/billing.spec.ts` (not backslashes)
- Don't use quotes around the file path unless necessary
- Check that the file exists: `ls e2e/billing/billing.spec.ts` (Linux/Mac) or `dir e2e\billing\billing.spec.ts` (Windows)

### Run with UI Mode (Interactive)
```bash
npm run test:e2e:ui
```

### Run in Headed Mode (See Browser)
```bash
npm run test:e2e:headed
```

### Run in Debug Mode
```bash
npm run test:e2e:debug
```

## Test Structure

### Test Suites

1. **Billing System - Visit-Scoped Billing**
   - Visit creation and billing initialization
   - Automatic charge creation

2. **Billing System - Payment Processing**
   - Full cash payment
   - Partial payments
   - Payment validation

3. **Billing System - Insurance Visits**
   - Insurance visit creation
   - Invoice generation

4. **Billing System - Wallet System**
   - Wallet payments
   - Balance validation

5. **Billing System - Paystack Integration**
   - Paystack payment initialization
   - Payment verification

6. **Billing System - Visit Closure Rules**
   - Visit closure validation
   - Payment requirements

7. **Billing System - Role-Based Access**
   - Permission enforcement
   - Role restrictions

8. **Billing System - Department Bill Item Generation**
   - Automatic bill item creation
   - Department-specific charges

9. **Billing System - Cash Visit Full Lifecycle**
   - Complete billing workflow from visit creation to closure

10. **Billing System - Error Handling**
    - Network error handling
    - Loading states

## Quick Start

1. **Start Backend Server** (Terminal 1)
   ```bash
   cd backend
   python manage.py runserver
   ```
   Verify: Visit `http://localhost:8000/api/v1/health/` - should return 200 OK

2. **Start Frontend Dev Server** (Terminal 2, optional - Playwright can auto-start it)
   ```bash
   cd frontend
   npm start
   ```

3. **Create Test Users** (Terminal 3)
   ```bash
   cd backend
   python manage.py shell
   ```
   Then run the Python code from the Prerequisites section above.

4. **Run Tests** (Terminal 4)
   ```bash
   cd frontend
   npm run test:e2e
   ```

## Troubleshooting

### ❌ "HTTP 504: Gateway Timeout" or "Backend server is not accessible"

**Problem**: Backend server is not running or not accessible.

**Solution**:
1. Verify backend is running: `curl http://localhost:8000/api/v1/health/`
2. Check backend logs for errors
3. Ensure backend is running on port 8000 (default Django port)
4. If using a different port, update `setupProxy.js` in frontend

### ❌ Tests Fail with "Cannot find element"

- Check that the frontend dev server is running
- Verify the selectors match the actual UI elements
- Check browser console for JavaScript errors
- View test screenshots in `test-results/` folder

### ❌ Tests Fail with "401 Unauthorized"

- Verify test users exist in the database
- Check that user credentials match test data
- Ensure JWT authentication is working
- Check backend logs for authentication errors

### ❌ Tests Fail with "404 Not Found"

- Verify backend server is running
- Check API endpoints are correct
- Ensure database migrations are applied
- Verify proxy configuration in `setupProxy.js`

### ❌ Tests Timeout

- Increase timeout values in test helpers
- Check network connectivity
- Verify servers are responding
- Check if backend is slow (database queries, etc.)

### ❌ Login Fails / "Login failed"

- Verify login form selectors are correct
- Check that button is enabled after filling fields
- Ensure username/password fields are filled correctly
- Check backend logs for login errors
- Verify test users exist and passwords are correct
- Check for error messages on the login page

### ❌ "page.waitForURL: Timeout exceeded"

- Backend is not responding (check backend server)
- Login is failing silently (check error messages)
- Network connectivity issues
- Frontend proxy not configured correctly

## Test Data

Test data is defined in the test file:

```typescript
const TEST_PATIENT = {
  first_name: 'John',
  last_name: 'Doe',
  date_of_birth: '1990-01-15',
  gender: 'MALE',
  phone: '+2348012345678',
  email: 'john.doe@example.com',
};

const TEST_DOCTOR = {
  email: 'doctor@clinic.com',
  password: 'Doctor123!',
  role: 'DOCTOR',
};
```

## Debugging

### View Test Report
After running tests, view the HTML report:
```bash
npx playwright show-report
```

### Screenshots and Videos
Failed tests automatically capture:
- Screenshots (in `test-results/`)
- Videos (in `test-results/`)
- Traces (if enabled)

### Debug Mode
Run tests in debug mode to step through:
```bash
npm run test:e2e:debug
```

## CI/CD Integration

For CI/CD, use:
```bash
npx playwright test --reporter=html
```

The HTML report will be generated in `playwright-report/`.
