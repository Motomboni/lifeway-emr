# Comprehensive Workflow Test Execution Guide

## Quick Start

### 1. Fix Backend Error First
There's a schema generation error in `ReportViewSet`. Let's fix it:

```bash
cd backend
python manage.py check
```

If you see the error about `revenue_by_method`, the methods need to be properly indented as `@action` methods in the ViewSet.

### 2. Run Backend Tests

```bash
# Run all tests
cd backend
python manage.py test

# Run specific test suites
python manage.py test apps.billing.tests_leak_detection
python manage.py test apps.billing.tests_reconciliation
python manage.py test apps.visits.tests_downstream_services
python manage.py test apps.core.tests_governance_rules

# Run with verbosity
python manage.py test --verbosity=2
```

### 3. Test PACS-lite Integration

```bash
cd backend
python manage.py test_pacs_lite
```

### 4. Frontend Build Check

```bash
cd frontend
npm run build
```

## Manual Workflow Tests

### Test Scenario 1: Complete Patient Journey

**Steps:**
1. **Start Backend:**
   ```bash
   cd backend
   python manage.py runserver
   ```

2. **Start Frontend:**
   ```bash
   cd frontend
   npm start
   ```

3. **Test Flow:**
   - Login as Receptionist
   - Register new patient
   - Create visit
   - Order services (Lab, Radiology, Pharmacy)
   - Process payment
   - Login as Doctor
   - Start consultation
   - Post lab results (as Lab Tech)
   - Upload radiology images (as Radiology Tech)
   - Dispense drugs (as Pharmacist)
   - Close visit

### Test Scenario 2: Payment & Lock System

**Steps:**
1. Create visit
2. Order service
3. Try to start consultation → Should show lock
4. Process payment
5. Try to start consultation → Should work
6. Order lab service
7. Try to post results → Should show lock
8. Process payment for lab
9. Post results → Should work

### Test Scenario 3: Reports & Analytics

**Steps:**
1. Create multiple visits with payments
2. Login as Admin
3. Navigate to `/reports`
4. Select date range
5. Verify:
   - Summary cards display
   - Revenue by method chart
   - Revenue trend chart
   - Visits by status chart

### Test Scenario 4: Revenue Leak Detection

**Steps:**
1. Create visit with unpaid service
2. Complete clinical action (post lab result without payment)
3. Login as Admin
4. Navigate to Revenue Leak Dashboard
5. Verify leak detected
6. Resolve leak

### Test Scenario 5: End-of-Day Reconciliation

**Steps:**
1. Create multiple visits with payments
2. Login as Admin or Receptionist
3. Navigate to `/reconciliation`
4. Review summary
5. Enter staff sign-off
6. Finalize day
7. Verify page becomes read-only

## API Testing with curl

### Test Reports API
```bash
# Get auth token first
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r '.access')

# Get summary
curl -X GET "http://localhost:8000/api/v1/reports/summary/?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer $TOKEN"

# Get revenue by method
curl -X GET "http://localhost:8000/api/v1/reports/revenue-by-method/?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer $TOKEN"
```

## Browser Testing Checklist

### Authentication
- [ ] Login works for all roles
- [ ] Logout works
- [ ] Token refresh works
- [ ] Unauthorized access blocked

### Patient Management
- [ ] Patient registration works
- [ ] Patient search works
- [ ] Patient details display correctly

### Visit Management
- [ ] Visit creation works
- [ ] Visit details display correctly
- [ ] Visit status updates correctly
- [ ] Visit closure works

### Service Ordering
- [ ] Service catalog accessible
- [ ] Services can be ordered
- [ ] Billing summary updates
- [ ] Multiple services work

### Payment Processing
- [ ] Cash payment works
- [ ] Paystack payment works
- [ ] Wallet payment works
- [ ] HMO payment works
- [ ] Receipt generation works

### Consultation
- [ ] Lock system works (before payment)
- [ ] Consultation starts after payment
- [ ] Consultation data saves
- [ ] Consultation closes correctly

### Lab Workflow
- [ ] Lab orders created
- [ ] Lock prevents results before payment
- [ ] Results post after payment
- [ ] Results visible in consultation

### Radiology Workflow
- [ ] Radiology orders created
- [ ] Image upload works
- [ ] Images viewable
- [ ] Reports post correctly

### Pharmacy Workflow
- [ ] Prescriptions created
- [ ] Lock prevents dispensing before payment
- [ ] Dispensing works after payment

### Reports
- [ ] Reports page loads
- [ ] Charts display correctly
- [ ] Date filtering works
- [ ] Data accurate

### Revenue Leak Detection
- [ ] Dashboard loads
- [ ] Leaks detected
- [ ] Filters work
- [ ] Resolution works

### Reconciliation
- [ ] Page loads
- [ ] Summary accurate
- [ ] Finalization works
- [ ] Immutability enforced

## Performance Checks

- [ ] Dashboard loads < 2 seconds
- [ ] Visit details loads < 1 second
- [ ] Reports page loads < 3 seconds
- [ ] API responses < 500ms

## Error Monitoring

### Check Browser Console
1. Open DevTools (F12)
2. Check Console for errors
3. Check Network for failed requests
4. Verify no 401/403/404/500 errors

### Check Backend Logs
1. Monitor Django server output
2. Check for exceptions
3. Verify database queries efficient

## Test Results Template

Create a file `TEST_RESULTS.md` and track:

```markdown
# Test Results - [Date]

## Environment
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Database: SQLite/PostgreSQL

## Test Results

| Category | Test | Status | Notes |
|----------|------|--------|-------|
| Auth | Login Admin | ✅/❌ | |
| Auth | Login Doctor | ✅/❌ | |
| Patient | Registration | ✅/❌ | |
| Visit | Creation | ✅/❌ | |
| Service | Ordering | ✅/❌ | |
| Payment | Processing | ✅/❌ | |
| Consultation | Workflow | ✅/❌ | |
| Lab | Order/Results | ✅/❌ | |
| Radiology | Order/Images | ✅/❌ | |
| Pharmacy | Dispensing | ✅/❌ | |
| Reports | Analytics | ✅/❌ | |
| Revenue Leak | Detection | ✅/❌ | |
| Reconciliation | EOD | ✅/❌ | |
| Timeline | Display | ✅/❌ | |
| Locks | System | ✅/❌ | |
| PACS | Integration | ✅/❌ | |

## Issues Found
1. [Issue description]
2. [Issue description]

## Next Steps
1. [Action item]
2. [Action item]
```

