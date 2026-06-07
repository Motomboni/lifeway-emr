# Comprehensive Workflow Test Plan

## Overview
This document outlines comprehensive workflow tests for the Modern EMR application to ensure all features work correctly after recent implementations.

## Prerequisites
- Backend server running on `http://localhost:8000`
- Frontend server running on `http://localhost:3000` or `3001`
- Database with test data
- Admin user credentials
- Doctor user credentials
- Receptionist user credentials

## Test Categories

### 1. Authentication & Authorization Workflow
**Objective:** Verify user authentication and role-based access control

**Test Steps:**
1. ✅ Login as Admin
   - Navigate to `/login`
   - Enter admin credentials
   - Verify redirect to dashboard
   - Verify admin-specific features visible

2. ✅ Login as Doctor
   - Logout and login as doctor
   - Verify doctor dashboard loads
   - Verify doctor-specific features visible
   - Verify restricted features hidden

3. ✅ Login as Receptionist
   - Logout and login as receptionist
   - Verify receptionist dashboard loads
   - Verify receptionist-specific features visible

4. ✅ Token Refresh
   - Wait for token expiration (or manually expire)
   - Verify automatic token refresh
   - Verify no logout required

**Expected Results:**
- All login flows work correctly
- Role-based access enforced
- Token refresh works automatically

---

### 2. Patient Registration & Visit Creation Workflow
**Objective:** Verify patient registration and visit creation

**Test Steps:**
1. ✅ Register New Patient
   - Navigate to Patient Registration
   - Fill in patient details (name, DOB, gender, phone, address)
   - Submit form
   - Verify patient created successfully
   - Verify patient appears in patient list

2. ✅ Create Visit for Patient
   - Navigate to Create Visit
   - Select registered patient
   - Select visit type (GOPD, Emergency, etc.)
   - Create visit
   - Verify visit created with status "OPEN"
   - Verify visit appears in visit list

3. ✅ View Visit Details
   - Click on created visit
   - Verify visit details page loads
   - Verify all visit information displayed correctly

**Expected Results:**
- Patient registration works
- Visit creation works
- Visit details display correctly

---

### 3. Service Catalog & Ordering Workflow
**Objective:** Verify service-driven ordering system

**Test Steps:**
1. ✅ Access Service Catalog
   - Navigate to visit details
   - Click "Order Services from Catalog"
   - Verify service catalog modal opens
   - Verify services listed by category

2. ✅ Search and Order Service
   - Search for a service (e.g., "Lab Test")
   - Select service
   - Verify service added to bill
   - Verify billing summary updates

3. ✅ Order Multiple Services
   - Order lab service
   - Order radiology service
   - Order pharmacy service
   - Verify all services in billing summary

4. ✅ Verify Billing Line Items Created
   - Check backend: Verify `BillingLineItem` records created
   - Verify each service has corresponding billing line item
   - Verify amounts match service catalog prices

**Expected Results:**
- Service catalog accessible
- Services can be ordered
- Billing line items created correctly

---

### 4. Payment & Billing Workflow
**Objective:** Verify payment processing and billing

**Test Steps:**
1. ✅ View Billing Summary
   - Navigate to visit details
   - View billing section
   - Verify total amount calculated correctly
   - Verify breakdown by service

2. ✅ Process Payment (Cash)
   - Select payment method: CASH
   - Enter amount
   - Process payment
   - Verify payment recorded
   - Verify visit payment status updates

3. ✅ Process Payment (Paystack)
   - Select payment method: PAYSTACK
   - Enter amount
   - Process payment
   - Verify payment recorded

4. ✅ Process Payment (Wallet)
   - Select payment method: WALLET
   - Enter amount
   - Process payment
   - Verify payment recorded

5. ✅ Generate Invoice/Receipt
   - After payment, generate receipt
   - Verify PDF generated
   - Verify receipt contains correct information
   - Test print functionality

**Expected Results:**
- Billing summary accurate
- All payment methods work
- Receipts generate correctly

---

### 5. Consultation Workflow
**Objective:** Verify GOPD consultation workflow

**Test Steps:**
1. ✅ Start Consultation (Before Payment)
   - Navigate to visit with unpaid status
   - Try to start consultation
   - Verify lock indicator appears
   - Verify message explains payment required

2. ✅ Process Payment
   - Process payment for visit
   - Verify payment confirmed

3. ✅ Start Consultation (After Payment)
   - Try to start consultation again
   - Verify consultation starts
   - Verify consultation status: ACTIVE

4. ✅ Record Consultation Notes
   - Enter chief complaint
   - Enter history
   - Enter examination findings
   - Save consultation
   - Verify data saved

5. ✅ Close Consultation
   - Close consultation
   - Verify status: CLOSED
   - Verify consultation locked from further edits

**Expected Results:**
- Payment lock enforced
- Consultation starts after payment
- Consultation data saves correctly

---

### 6. Lab Order & Results Workflow
**Objective:** Verify lab ordering and result posting

**Test Steps:**
1. ✅ Order Lab Service
   - From consultation, order lab service via Service Catalog
   - Verify `LabOrder` created
   - Verify billing line item created
   - Verify lock check: Can't post results before payment

2. ✅ Process Payment
   - Process payment for lab service
   - Verify payment confirmed

3. ✅ Post Lab Results
   - Navigate to lab orders page (as Lab Tech)
   - Select lab order
   - Enter test results
   - Post results
   - Verify results saved
   - Verify results visible in consultation

4. ✅ Verify Lock System
   - Try to post results before payment
   - Verify lock message appears
   - Verify action blocked

**Expected Results:**
- Lab orders created correctly
- Payment required before results
- Results post correctly after payment

---

### 7. Radiology Order & Results Workflow
**Objective:** Verify radiology ordering and imaging

**Test Steps:**
1. ✅ Order Radiology Service
   - From consultation, order radiology service
   - Verify `RadiologyRequest` created
   - Verify billing line item created

2. ✅ Process Payment
   - Process payment for radiology service
   - Verify payment confirmed

3. ✅ Upload Radiology Images
   - Navigate to radiology upload page
   - Upload images (test with sample files)
   - Verify upload session created
   - Verify images sync to server

4. ✅ View Radiology Images
   - Navigate to radiology order details
   - Click to view images
   - Verify OHIF viewer loads (if configured)
   - Verify images display correctly

5. ✅ Post Radiology Report
   - Enter radiology findings
   - Post report
   - Verify report saved
   - Verify report visible in consultation

**Expected Results:**
- Radiology orders work
- Image upload works
- Images viewable
- Reports post correctly

---

### 8. Pharmacy & Prescription Workflow
**Objective:** Verify prescription and drug dispensing

**Test Steps:**
1. ✅ Create Prescription
   - From consultation, order pharmacy service
   - Verify prescription created
   - Verify billing line item created

2. ✅ Process Payment
   - Process payment for prescription
   - Verify payment confirmed

3. ✅ Dispense Drugs
   - Navigate to prescriptions page (as Pharmacist)
   - Select prescription
   - Enter dispensing details
   - Dispense drugs
   - Verify dispensing recorded

4. ✅ Verify Lock System
   - Try to dispense before payment
   - Verify lock message appears
   - Verify action blocked

**Expected Results:**
- Prescriptions created
- Payment required before dispensing
- Dispensing works after payment

---

### 9. Admission & Discharge Workflow
**Objective:** Verify inpatient admission/discharge

**Test Steps:**
1. ✅ View Available Wards/Beds
   - Navigate to Inpatients page
   - Verify wards and beds listed
   - Verify bed availability status

2. ✅ Admit Patient
   - From visit details, click "Admit Patient"
   - Select ward and bed
   - Enter admission details
   - Submit admission
   - Verify admission created
   - Verify bed marked as unavailable

3. ✅ View Inpatients
   - Navigate to Inpatients page
   - Verify admitted patient listed
   - Verify admission details displayed

4. ✅ Discharge Patient
   - Select admitted patient
   - Click discharge
   - Enter discharge date
   - Confirm discharge
   - Verify bed marked as available
   - Verify admission status: DISCHARGED

**Expected Results:**
- Admission works
- Bed management works
- Discharge works
- Bed availability updates correctly

---

### 10. Reports & Analytics Workflow
**Objective:** Verify reporting functionality

**Test Steps:**
1. ✅ Access Reports Page
   - Login as Admin
   - Navigate to Reports page
   - Verify page loads

2. ✅ View Summary Cards
   - Verify total revenue displayed
   - Verify total visits displayed
   - Verify total patients displayed

3. ✅ View Charts
   - Select date range
   - Verify revenue by payment method chart
   - Verify revenue trend chart
   - Verify visits by status chart

4. ✅ Test Date Range Filter
   - Change start date
   - Change end date
   - Verify data refreshes
   - Verify charts update

**Expected Results:**
- Reports page loads
- All charts display correctly
- Date filtering works
- Data accurate

---

### 11. Revenue Leak Detection Workflow
**Objective:** Verify revenue leak detection

**Test Steps:**
1. ✅ Access Revenue Leak Dashboard
   - Login as Admin
   - Navigate to Revenue Leak Dashboard
   - Verify page loads

2. ✅ View Leak Summary
   - Verify total potential leaked revenue
   - Verify number of leak incidents
   - Verify resolved/unresolved counts

3. ✅ View Leak Table
   - Verify leaks listed
   - Verify filters work (department, status, date)
   - Verify high-value leaks highlighted

4. ✅ Resolve Leak
   - Select a leak
   - Add resolution notes
   - Resolve leak
   - Verify leak marked as resolved

**Expected Results:**
- Dashboard loads
- Leaks detected correctly
- Resolution works

---

### 12. End-of-Day Reconciliation Workflow
**Objective:** Verify daily reconciliation

**Test Steps:**
1. ✅ Access Reconciliation Page
   - Login as Admin or Receptionist
   - Navigate to Reconciliation page
   - Verify page loads

2. ✅ View Summary
   - Verify total revenue
   - Verify revenue by payment method
   - Verify outstanding items
   - Verify revenue leaks

3. ✅ Staff Sign-off
   - Enter staff name
   - Check confirmation
   - Verify sign-off recorded

4. ✅ Finalize Day
   - Click "Finalize Day"
   - Confirm finalization
   - Verify reconciliation finalized
   - Verify page becomes read-only

**Expected Results:**
- Reconciliation page works
- Summary accurate
- Finalization works
- Immutability enforced

---

### 13. Visit Timeline Workflow
**Objective:** Verify timeline feature

**Test Steps:**
1. ✅ View Timeline
   - Navigate to visit details
   - Scroll to timeline section
   - Verify timeline displays

2. ✅ Verify Events
   - Verify visit created event
   - Verify payment events
   - Verify consultation events
   - Verify service order events
   - Verify lab/radiology events

3. ✅ Expand Event Details
   - Click on timeline event
   - Verify details expand
   - Verify source links work

**Expected Results:**
- Timeline displays correctly
- All events logged
- Details expandable
- Links functional

---

### 14. Explainable Lock System Workflow
**Objective:** Verify lock system across all actions

**Test Steps:**
1. ✅ Test Consultation Lock
   - Try to start consultation before payment
   - Verify lock indicator appears
   - Verify message explains why locked

2. ✅ Test Lab Order Lock
   - Try to order lab service before payment
   - Verify lock indicator appears

3. ✅ Test Radiology Lock
   - Try to upload images before payment
   - Verify lock indicator appears

4. ✅ Test Drug Dispense Lock
   - Try to dispense before payment
   - Verify lock indicator appears

5. ✅ Test After Payment
   - Process payment
   - Verify locks removed
   - Verify actions now allowed

**Expected Results:**
- All locks work correctly
- Messages clear and helpful
- Locks removed after payment

---

### 15. PACS-lite Integration Workflow
**Objective:** Verify radiology image viewing

**Test Steps:**
1. ✅ Upload Images
   - Upload radiology images
   - Verify images stored
   - Verify study/series created

2. ✅ View Study Browser
   - Navigate to radiology order
   - Click to view images
   - Verify study/series browser displays
   - Verify images grouped by series

3. ✅ View in OHIF Viewer
   - Click "OHIF Viewer" button
   - Verify viewer loads
   - Verify images accessible
   - Verify navigation works

**Expected Results:**
- Images upload correctly
- Study browser works
- OHIF viewer loads (if configured)

---

## Test Execution Checklist

### Backend Tests
- [ ] Run Django tests: `python manage.py test`
- [ ] Check for any test failures
- [ ] Verify all migrations applied: `python manage.py migrate`
- [ ] Check for any model validation errors

### Frontend Tests
- [ ] Verify build succeeds: `npm run build`
- [ ] Check for console errors in browser
- [ ] Verify all API calls work
- [ ] Test responsive design

### Integration Tests
- [ ] Test complete patient journey
- [ ] Test payment flow end-to-end
- [ ] Test consultation workflow
- [ ] Test service ordering workflow

## Common Issues to Watch For

1. **API Errors**
   - Check browser console for 404/500 errors
   - Verify API endpoints correct
   - Check authentication tokens

2. **Type Errors**
   - Check TypeScript compilation
   - Verify all types correct

3. **State Management**
   - Verify data refreshes after actions
   - Check for stale data

4. **Permissions**
   - Verify role-based access works
   - Check unauthorized access blocked

## Test Results Template

```
Test Date: ___________
Tester: ___________
Environment: ___________

Category | Test | Status | Notes
---------|------|--------|------
Auth | Login Admin | ✅/❌ | 
Auth | Login Doctor | ✅/❌ | 
Patient | Registration | ✅/❌ | 
Visit | Creation | ✅/❌ | 
Service | Ordering | ✅/❌ | 
Payment | Processing | ✅/❌ | 
Consultation | Workflow | ✅/❌ | 
Lab | Order/Results | ✅/❌ | 
Radiology | Order/Images | ✅/❌ | 
Pharmacy | Dispensing | ✅/❌ | 
Admission | Workflow | ✅/❌ | 
Reports | Analytics | ✅/❌ | 
Revenue Leak | Detection | ✅/❌ | 
Reconciliation | EOD | ✅/❌ | 
Timeline | Display | ✅/❌ | 
Locks | System | ✅/❌ | 
PACS | Integration | ✅/❌ | 
```

## Next Steps

1. Execute tests systematically
2. Document any issues found
3. Fix critical issues
4. Re-test after fixes
5. Create automated test suite (future)

