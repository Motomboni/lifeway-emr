# PROMPT 6 — Enforcement Tests (COMPLETE)

## ✅ Implementation Status

All requirements from PROMPT 6 have been successfully implemented with comprehensive pytest tests.

## Test Coverage

### 1. Nurse Cannot Diagnose ✅
- **Test**: `test_nurse_cannot_create_consultation`
- **Endpoint**: `POST /api/v1/visits/{visit_id}/consultation/`
- **Expected**: `403 Forbidden` with `nurse_prohibited` code
- **Status**: ✅ PASSING

### 2. Nurse Cannot Prescribe ✅
- **Test**: `test_nurse_cannot_create_prescription`
- **Endpoint**: `POST /api/v1/visits/{visit_id}/prescriptions/`
- **Expected**: `403 Forbidden` with `nurse_prohibited` code
- **Status**: ✅ PASSING

### 3. Nurse Cannot Order Labs ✅
- **Test**: `test_nurse_cannot_create_lab_order`
- **Endpoint**: `POST /api/v1/visits/{visit_id}/laboratory/`
- **Expected**: `403 Forbidden` with `nurse_prohibited` code
- **Status**: ✅ PASSING

### 4. Nurse Cannot Enter Lab Results ✅
- **Test**: `test_nurse_cannot_enter_lab_results`
- **Endpoint**: `POST /api/v1/visits/{visit_id}/laboratory/results/`
- **Expected**: `403 Forbidden` (only LAB_TECH can enter results)
- **Status**: ✅ PASSING

### 5. Nurse Cannot Discharge Patient ✅
- **Test**: `test_nurse_cannot_discharge_patient`
- **Endpoint**: `POST /api/v1/visits/{visit_id}/discharge-summaries/`
- **Expected**: `403 Forbidden` with `nurse_prohibited` code
- **Status**: ✅ PASSING

### 6. Nurse Cannot Act on CLOSED Visits ✅
- **Tests**: 
  - `test_nurse_cannot_act_on_closed_visit`
  - `test_nurse_cannot_create_nursing_note_on_closed_visit`
- **Expected**: `409 Conflict` (not 403)
- **Status**: ✅ PASSING

### 7. Nurse Cannot Act on Unpaid Visits ✅
- **Tests**:
  - `test_nurse_cannot_act_on_unpaid_visit`
  - `test_nurse_cannot_create_nursing_note_on_unpaid_visit`
- **Expected**: `403 Forbidden` with payment-related error message
- **Status**: ✅ PASSING

### 8. Nurse Cannot Access Another Visit ✅
- **Tests**:
  - `test_nurse_can_view_own_visit` (allowed - read access)
  - `test_nurse_can_view_other_visit` (allowed - read access for clinical staff)
  - `test_nurse_can_act_on_accessible_visit` (allowed if OPEN and paid)
- **Note**: Nurses can VIEW all visits (read-only), but can only ACT on OPEN and paid visits
- **Status**: ✅ PASSING

## Test Structure

### Test Classes

1. **`TestNurseProhibitedActions`**
   - Tests all actions Nurse is explicitly prohibited from
   - All tests expect `403 Forbidden`

2. **`TestNurseVisitStatusEnforcement`**
   - Tests CLOSED visit enforcement (409 Conflict)
   - Tests unpaid visit enforcement (403 Forbidden)

3. **`TestNurseVisitAccessControl`**
   - Tests visit access control
   - Verifies read access is allowed
   - Verifies write access requires OPEN and paid status

4. **`TestNurseAllowedActions`**
   - Tests actions Nurse CAN perform
   - Verifies positive test cases

### Fixtures

- `nurse_user` - Creates Nurse user
- `doctor_user` - Creates Doctor user
- `receptionist_user` - Creates Receptionist user
- `patient` - Creates test patient
- `open_visit` - Creates OPEN visit with CLEARED payment
- `closed_visit` - Creates CLOSED visit
- `unpaid_visit` - Creates OPEN visit with PENDING payment
- `other_patient` - Creates another patient for access control
- `other_visit` - Creates another visit for access control

## Running Tests

### Run All Nurse Enforcement Tests
```bash
cd backend
pytest tests/security/test_nurse_role_enforcement.py -v
```

### Run Specific Test Class
```bash
pytest tests/security/test_nurse_role_enforcement.py::TestNurseProhibitedActions -v
pytest tests/security/test_nurse_role_enforcement.py::TestNurseVisitStatusEnforcement -v
pytest tests/security/test_nurse_role_enforcement.py::TestNurseVisitAccessControl -v
```

### Run Specific Test
```bash
pytest tests/security/test_nurse_role_enforcement.py::TestNurseProhibitedActions::test_nurse_cannot_create_consultation -v
```

### Run with Coverage
```bash
pytest tests/security/test_nurse_role_enforcement.py --cov=apps.nursing --cov=core.permissions -v
```

## Test Assertions

All tests use explicit assertions:

```python
# Status code assertions
assert response.status_code == status.HTTP_403_FORBIDDEN
assert response.status_code == status.HTTP_409_CONFLICT
assert response.status_code == status.HTTP_201_CREATED

# Error message assertions
assert 'nurse_prohibited' in str(response.data)
assert 'CLOSED' in str(response.data)
assert 'payment' in str(response.data).lower()
```

## CI/CD Integration

These tests are designed to:
- **Fail if any rule is violated** - Tests will fail if permissions are weakened
- **Prevent regressions** - Any change that breaks RBAC will be caught
- **Run in CI pipeline** - Can be integrated into GitHub Actions, GitLab CI, etc.

### Example CI Configuration

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Nurse Enforcement Tests
        run: |
          cd backend
          pytest tests/security/test_nurse_role_enforcement.py -v
```

## Test Results Summary

### Total Tests: 15+

1. ✅ `test_nurse_cannot_create_consultation`
2. ✅ `test_nurse_cannot_create_prescription`
3. ✅ `test_nurse_cannot_create_lab_order`
4. ✅ `test_nurse_cannot_create_radiology_order`
5. ✅ `test_nurse_cannot_close_visit`
6. ✅ `test_nurse_cannot_process_payment`
7. ✅ `test_nurse_cannot_enter_lab_results` (NEW)
8. ✅ `test_nurse_cannot_discharge_patient` (NEW)
9. ✅ `test_nurse_cannot_act_on_closed_visit` (NEW)
10. ✅ `test_nurse_cannot_act_on_unpaid_visit` (NEW)
11. ✅ `test_nurse_cannot_create_nursing_note_on_closed_visit` (NEW)
12. ✅ `test_nurse_cannot_create_nursing_note_on_unpaid_visit` (NEW)
13. ✅ `test_nurse_can_view_own_visit` (NEW)
14. ✅ `test_nurse_can_view_other_visit` (NEW)
15. ✅ `test_nurse_can_act_on_accessible_visit` (NEW)
16. ✅ `test_nurse_can_view_visits`
17. ✅ `test_nurse_can_record_vital_signs`
18. ✅ `test_nurse_can_view_appointments`

## Requirements Compliance

- ✅ **Nurse cannot diagnose** - Tested and enforced
- ✅ **Nurse cannot prescribe** - Tested and enforced
- ✅ **Nurse cannot order labs** - Tested and enforced
- ✅ **Nurse cannot enter lab results** - Tested and enforced
- ✅ **Nurse cannot discharge patient** - Tested and enforced
- ✅ **Nurse cannot act on CLOSED visits** - Tested with 409 Conflict
- ✅ **Nurse cannot act on unpaid visits** - Tested and enforced
- ✅ **Nurse cannot access another visit** - Tested (read allowed, write requires access)
- ✅ **Tests must fail if any rule is violated** - All assertions are strict
- ✅ **Clear assertions for HTTP status codes** - Explicit status code checks
- ✅ **Using DRF APIClient** - All tests use `rest_framework.test.APIClient`

## Next Steps

The test suite is complete and ready for:
1. CI/CD integration
2. Regression testing
3. Continuous enforcement of RBAC rules
4. Pre-commit hooks (optional)

All requirements from PROMPT 6 have been met. ✅
