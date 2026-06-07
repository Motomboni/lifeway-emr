# Workflow Test Execution Plan

## Current Status

### ✅ Completed
- Comprehensive test plan created (`COMPREHENSIVE_WORKFLOW_TEST.md`)
- Test execution guide created (`RUN_WORKFLOW_TESTS.md`)
- Backend test files identified
- Frontend test infrastructure exists

### ⚠️ Issues to Fix
1. **ReportViewSet Schema Error** - Need to verify new action methods are properly defined
2. **Backend Check** - Run `python manage.py check` to verify no errors

## Test Execution Steps

### Step 1: Fix Backend Issues
```bash
cd backend
python manage.py check
# Fix any errors found
```

### Step 2: Run Backend Unit Tests
```bash
cd backend

# Run all tests
python manage.py test

# Run specific suites
python manage.py test apps.billing.tests_leak_detection -v 2
python manage.py test apps.billing.tests_reconciliation -v 2
python manage.py test apps.visits.tests_downstream_services -v 2
python manage.py test apps.core.tests_governance_rules -v 2
```

### Step 3: Test PACS-lite Integration
```bash
cd backend
python manage.py test_pacs_lite
```

### Step 4: Start Servers
```bash
# Terminal 1 - Backend
cd backend
python manage.py runserver

# Terminal 2 - Frontend
cd frontend
npm start
```

### Step 5: Manual Workflow Testing

Follow the test scenarios in `COMPREHENSIVE_WORKFLOW_TEST.md`:

1. **Authentication & Authorization**
2. **Patient Registration & Visit Creation**
3. **Service Catalog & Ordering**
4. **Payment & Billing**
5. **Consultation Workflow**
6. **Lab Order & Results**
7. **Radiology Order & Results**
8. **Pharmacy & Prescription**
9. **Admission & Discharge**
10. **Reports & Analytics**
11. **Revenue Leak Detection**
12. **End-of-Day Reconciliation**
13. **Visit Timeline**
14. **Explainable Lock System**
15. **PACS-lite Integration**

## Quick Test Checklist

### Backend Health
- [ ] `python manage.py check` passes
- [ ] `python manage.py test` passes
- [ ] All migrations applied
- [ ] No import errors

### Frontend Health
- [ ] `npm run build` succeeds
- [ ] `npm start` runs without errors
- [ ] No console errors in browser
- [ ] All pages load

### API Endpoints
- [ ] Reports API endpoints accessible
- [ ] Lock system endpoints work
- [ ] Reconciliation endpoints work
- [ ] Revenue leak endpoints work

### Key Workflows
- [ ] Patient registration → Visit creation → Service ordering → Payment → Consultation
- [ ] Payment lock system works
- [ ] Reports display correctly
- [ ] Reconciliation works

## Test Results Tracking

Create a `TEST_RESULTS.md` file and track:

```markdown
# Test Results - [Date]

## Environment
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Database: SQLite

## Backend Tests
- [ ] All unit tests pass
- [ ] PACS-lite tests pass
- [ ] No system check errors

## Frontend Tests
- [ ] Build succeeds
- [ ] No compilation errors
- [ ] All pages load

## Workflow Tests
- [ ] Complete patient journey works
- [ ] Payment & lock system works
- [ ] Reports work
- [ ] Reconciliation works

## Issues Found
1. [Description]
2. [Description]

## Next Steps
1. [Action]
2. [Action]
```

## Automated Test Script

For future automation, consider:

1. **Playwright E2E Tests** - Already configured in `playwright.config.ts`
2. **API Integration Tests** - Use Django test client
3. **Frontend Component Tests** - Use React Testing Library

## Next Actions

1. Fix ReportViewSet schema error (if exists)
2. Run backend tests
3. Start servers
4. Execute manual workflow tests
5. Document results

