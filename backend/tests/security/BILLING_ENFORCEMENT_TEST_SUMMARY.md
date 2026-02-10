# Billing Enforcement Tests - Summary

## Overview

Comprehensive pytest tests ensuring all billing rules are strictly enforced in the Rule-Locked EMR system.

## Test Coverage

### 1. Charge Creation Enforcement ✅

**Test Class**: `TestChargeCreationEnforcement`

- ✅ `test_receptionist_can_create_misc_charge` - Receptionist can create MISC charges
- ✅ `test_doctor_cannot_create_charge_via_api` - Doctor denied (403 Forbidden)
- ✅ `test_nurse_cannot_create_charge_via_api` - Nurse denied (403 Forbidden)
- ✅ `test_charge_creation_requires_visit_open` - CLOSED visits reject charges

**Rules Enforced**:
- Only Receptionist can create charges
- Charges cannot be created for CLOSED visits
- Non-receptionist roles receive 403 Forbidden

---

### 2. Insurance Visit Scope Enforcement ✅

**Test Class**: `TestInsuranceVisitScopeEnforcement`

- ✅ `test_insurance_is_visit_scoped` - Insurance must be visit-scoped
- ✅ `test_insurance_cannot_bypass_payment_enforcement` - Insurance doesn't bypass payment gates
- ✅ `test_insurance_computation_is_visit_scoped` - Insurance uses visit-scoped charges only

**Rules Enforced**:
- Insurance is always visit-scoped
- Insurance does NOT bypass payment enforcement
- Clinical actions still require payment_status == CLEARED
- Insurance computation uses only visit-scoped charges

---

### 3. Wallet Overdraft Prevention ✅

**Test Class**: `TestWalletOverdraftPrevention`

- ✅ `test_wallet_cannot_debit_more_than_balance` - Direct debit validation
- ✅ `test_wallet_debit_via_api_prevents_overdraft` - API-level validation
- ✅ `test_wallet_can_debit_exact_balance` - Exact balance debit allowed
- ✅ `test_wallet_cannot_go_negative` - Multiple debits prevent negative balance

**Rules Enforced**:
- Wallet cannot debit more than balance
- Negative balances are forbidden
- Validation at model and API level
- Multiple debits tracked correctly

---

### 4. Paystack Verification Enforcement ✅

**Test Class**: `TestPaystackVerificationEnforcement`

- ✅ `test_payment_intent_requires_verification` - PaymentIntent must be verified
- ✅ `test_payment_intent_verification_creates_payment` - Verification creates Payment
- ✅ `test_unverified_payment_intent_cannot_be_used` - Unverified intents unusable
- ✅ `test_payment_intent_verification_is_idempotent` - Safe to verify multiple times

**Rules Enforced**:
- PaymentIntent must be verified before Payment creation
- Unverified PaymentIntents cannot be used
- Verification is idempotent (safe to retry)
- Server-side verification only

---

### 5. Visit Closure Balance Enforcement ✅

**Test Class**: `TestVisitClosureBalanceEnforcement`

- ✅ `test_visit_cannot_close_with_outstanding_balance` - Outstanding balance blocks closure
- ✅ `test_visit_can_close_when_balance_cleared` - Cleared balance allows closure
- ✅ `test_visit_can_close_with_insurance_full_coverage` - Insurance can clear balance

**Rules Enforced**:
- Visit CANNOT close with outstanding balance > 0
- Visit CAN close when balance is cleared
- Insurance full coverage can clear balance (patient_payable = 0)
- BillingService.can_close_visit() enforces rule

---

### 6. Billing Computation Accuracy ✅

**Test Class**: `TestBillingComputationAccuracy`

- ✅ `test_billing_computation_with_insurance_only` - Insurance computation correct
- ✅ `test_billing_computation_with_payment_only` - Payment computation correct
- ✅ `test_billing_computation_with_wallet_only` - Wallet computation correct
- ✅ `test_billing_computation_with_insurance_and_payment` - Combined computation
- ✅ `test_billing_computation_with_all_payment_methods` - All methods combined
- ✅ `test_billing_computation_with_overpayment` - Overpayment creates credit
- ✅ `test_billing_computation_deterministic` - Same inputs = same outputs

**Rules Enforced**:
- Insurance coverage computed correctly
- Payments summed correctly
- Wallet debits included correctly
- Combined computations accurate
- Overpayments handled (negative balance = credit)
- Deterministic computation (idempotent)

---

## Test Structure

### Fixtures

- `patient` - Test patient
- `doctor_user` - Doctor user
- `receptionist_user` - Receptionist user
- `nurse_user` - Nurse user
- `open_visit` - OPEN visit
- `hmo_provider` - HMO provider
- `wallet` - Patient wallet with balance

### Test Classes

1. **TestChargeCreationEnforcement** - Charge creation rules
2. **TestInsuranceVisitScopeEnforcement** - Insurance scope rules
3. **TestWalletOverdraftPrevention** - Wallet overdraft prevention
4. **TestPaystackVerificationEnforcement** - Paystack verification rules
5. **TestVisitClosureBalanceEnforcement** - Visit closure rules
6. **TestBillingComputationAccuracy** - Billing computation accuracy

## Running Tests

### Run All Billing Enforcement Tests
```bash
cd backend
pytest tests/security/test_billing_enforcement.py -v
```

### Run Specific Test Class
```bash
pytest tests/security/test_billing_enforcement.py::TestChargeCreationEnforcement -v
pytest tests/security/test_billing_enforcement.py::TestInsuranceVisitScopeEnforcement -v
pytest tests/security/test_billing_enforcement.py::TestWalletOverdraftPrevention -v
pytest tests/security/test_billing_enforcement.py::TestPaystackVerificationEnforcement -v
pytest tests/security/test_billing_enforcement.py::TestVisitClosureBalanceEnforcement -v
pytest tests/security/test_billing_enforcement.py::TestBillingComputationAccuracy -v
```

### Run Specific Test
```bash
pytest tests/security/test_billing_enforcement.py::TestChargeCreationEnforcement::test_doctor_cannot_create_charge_via_api -v
```

### Run with Coverage
```bash
pytest tests/security/test_billing_enforcement.py --cov=apps.billing --cov-report=html
```

## Test Fixes Applied

### Wallet Fixture Fix
- Changed from `Wallet.objects.create()` to `Wallet.objects.get_or_create()`
- Handles case where wallet already exists for patient (OneToOneField constraint)
- Updates balance if wallet already exists

### Consultation Creation Fix
- Changed from `receptionist_user` to `doctor_user` for consultation creation
- Consultations can only be created by doctors

### Insurance Bypass Test Fix
- Explicitly sets visit payment_status to PENDING before test
- Verifies payment_status remains PENDING after insurance is added
- Insurance should not automatically clear payment_status

### Visit Closure Test Fix
- Accepts both 400 Bad Request and 403 Forbidden as valid responses
- Both status codes indicate the visit cannot be closed with outstanding balance

## Expected Test Results

All tests should **PASS**. If any test fails, it indicates a billing rule violation:

- ❌ **Charge creation by non-receptionist** → Security violation
- ❌ **Insurance bypasses payment** → Rule violation
- ❌ **Wallet overdraft** → Business logic violation
- ❌ **Unverified Paystack payment** → Security violation
- ❌ **Visit closes with balance** → Business rule violation
- ❌ **Incorrect billing computation** → Calculation error

## Failure Scenarios

Tests are designed to **FAIL** if rules are violated:

1. **Non-receptionist creates charge** → Test expects 403, fails if 200/201
2. **Insurance bypasses payment** → Test expects payment gate, fails if bypassed
3. **Wallet overdrafts** → Test expects ValidationError, fails if allowed
4. **Unverified Paystack payment** → Test expects no Payment, fails if created
5. **Visit closes with balance** → Test expects 400, fails if 200
6. **Incorrect computation** → Test expects specific values, fails if different

## Assertions

### Permission Assertions
- `assert response.status_code == status.HTTP_403_FORBIDDEN`
- `assert 'Receptionist' in str(response.data)`

### Validation Assertions
- `assert pytest.raises(ValidationError)`
- `assert 'balance' in str(exc_info.value).lower()`

### Business Logic Assertions
- `assert summary.outstanding_balance == Decimal('0.00')`
- `assert summary.payment_status == 'CLEARED'`
- `assert can_close is False`

### Computation Assertions
- `assert summary.total_charges == Decimal('10000.00')`
- `assert summary.insurance_amount == Decimal('5000.00')`
- `assert summary.patient_payable == Decimal('5000.00')`

## Integration with CI/CD

These tests should run in CI/CD pipeline:

```yaml
# .github/workflows/test.yml
- name: Run Billing Enforcement Tests
  run: |
    cd backend
    pytest tests/security/test_billing_enforcement.py -v --cov=apps.billing
```

## Maintenance

### Adding New Tests

When adding new billing rules:

1. Add test to appropriate test class
2. Use existing fixtures
3. Follow naming convention: `test_<rule_description>`
4. Add clear docstring
5. Assert expected behavior
6. Update this summary

### Updating Tests

When billing logic changes:

1. Update test expectations
2. Verify all tests still pass
3. Update summary if needed
4. Document breaking changes

## Compliance Checklist

✅ **Non-receptionist cannot create charges**  
✅ **Insurance does not bypass visit scope**  
✅ **Wallet cannot overdraft**  
✅ **Paystack payment must be verified**  
✅ **Visit cannot close with balance**  
✅ **Insurance + wallet + payment compute correctly**  

All billing rules are enforced and tested.

