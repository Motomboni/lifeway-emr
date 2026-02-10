# Automated Workflow Test Script

## Quick Test Commands

### Backend Health Check
```bash
# Check Django setup
cd backend
python manage.py check

# Run all tests
python manage.py test

# Run specific test suites
python manage.py test apps.billing.tests_leak_detection
python manage.py test apps.billing.tests_reconciliation
python manage.py test apps.visits.tests
```

### Frontend Health Check
```bash
# Check build
cd frontend
npm run build

# Check for linting errors
npm run lint  # if configured

# Start dev server
npm start
```

### Database Check
```bash
# Verify migrations
cd backend
python manage.py showmigrations

# Check for pending migrations
python manage.py makemigrations --dry-run
```

## Manual Test Scenarios

### Scenario 1: Complete Patient Journey
1. Register new patient
2. Create visit
3. Order services (Lab, Radiology, Pharmacy)
4. Process payment
5. Start consultation
6. Post lab results
7. Upload radiology images
8. Dispense drugs
9. Close visit

### Scenario 2: Payment & Lock Flow
1. Create visit
2. Order service
3. Try to start consultation → Should be locked
4. Process payment
5. Try to start consultation → Should work
6. Order lab service
7. Try to post results → Should be locked
8. Process payment for lab
9. Post results → Should work

### Scenario 3: Reports & Analytics
1. Create multiple visits with payments
2. Navigate to Reports page
3. Select date range
4. Verify all charts display
5. Verify data accuracy

### Scenario 4: Revenue Leak Detection
1. Create visit with unpaid service
2. Complete clinical action (post lab result)
3. Navigate to Revenue Leak Dashboard
4. Verify leak detected
5. Resolve leak

### Scenario 5: End-of-Day Reconciliation
1. Create multiple visits with payments
2. Navigate to Reconciliation page
3. Review summary
4. Enter staff sign-off
5. Finalize day
6. Verify immutability

## API Endpoint Tests

### Test Reports API
```bash
# Get summary
curl -X GET "http://localhost:8000/api/v1/reports/summary/?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get revenue by method
curl -X GET "http://localhost:8000/api/v1/reports/revenue-by-method/?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Lock System
```bash
# Check consultation lock
curl -X GET "http://localhost:8000/api/v1/locks/consultation/?visit_id=123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Reconciliation
```bash
# Create reconciliation
curl -X POST "http://localhost:8000/api/v1/billing/reconciliation/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reconciliation_date": "2024-01-15"}'
```

## Browser Console Checks

### Check for Errors
1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Check Network tab for failed requests
4. Check for 401/403/404/500 errors

### Check API Calls
1. Open Network tab
2. Filter by XHR/Fetch
3. Verify all API calls return 200/201
4. Check response data structure

## Performance Checks

### Page Load Times
- Dashboard: < 2 seconds
- Visit Details: < 1 second
- Reports Page: < 3 seconds

### API Response Times
- GET requests: < 500ms
- POST requests: < 1 second
- Complex queries: < 2 seconds

## Security Checks

1. ✅ Verify authentication required for all API calls
2. ✅ Verify role-based access enforced
3. ✅ Verify CORS configured correctly
4. ✅ Verify sensitive data not exposed
5. ✅ Verify SQL injection protection
6. ✅ Verify XSS protection

## Data Integrity Checks

1. ✅ Verify billing amounts match service catalog
2. ✅ Verify payment totals accurate
3. ✅ Verify visit status transitions correct
4. ✅ Verify bed availability updates
5. ✅ Verify timeline events logged

