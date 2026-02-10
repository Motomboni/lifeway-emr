# Test Execution Script

## Quick Test Commands

### 1. Backend Health Check
```bash
cd backend
python manage.py check
python manage.py migrate
```

### 2. Run Backend Tests
```bash
cd backend

# Run all tests
python manage.py test

# Run specific test suites
python manage.py test apps.billing.tests_leak_detection -v 2
python manage.py test apps.billing.tests_reconciliation -v 2
python manage.py test apps.visits.tests_downstream_services -v 2
python manage.py test apps.core.tests_governance_rules -v 2
```

### 3. Test PACS-lite
```bash
cd backend
python manage.py test_pacs_lite
```

### 4. Frontend Build
```bash
cd frontend
npm run build
```

## Manual Workflow Test Scenarios

### Scenario 1: Complete Patient Journey (15-20 minutes)

**Objective:** Test end-to-end patient workflow

**Steps:**
1. **Receptionist Actions:**
   - Login as Receptionist
   - Register new patient (John Doe, DOB: 1990-01-01, Phone: 08012345678)
   - Create visit (GOPD, Emergency)
   - Order services:
     - Lab: CBC (₦5,000)
     - Radiology: Chest X-Ray (₦10,000)
     - Pharmacy: Paracetamol (₦2,000)
   - Process payment: Cash, ₦17,000
   - Verify payment status: PAID

2. **Doctor Actions:**
   - Login as Doctor
   - Navigate to visit
   - Start consultation (should work now - payment cleared)
   - Enter:
     - Chief Complaint: "Fever and cough"
     - History: "3 days duration"
     - Examination: "Temp 38.5°C, Chest clear"
     - Diagnosis: "Upper respiratory tract infection"
   - Save consultation
   - Verify consultation saved

3. **Lab Tech Actions:**
   - Login as Lab Tech
   - Navigate to Lab Orders
   - Select visit
   - Post lab results:
     - WBC: 7.5
     - RBC: 4.5
     - Platelets: 250
   - Verify results posted

4. **Radiology Tech Actions:**
   - Login as Radiology Tech
   - Navigate to Radiology Orders
   - Select visit
   - Upload test image (use sample file)
   - Post radiology report: "Normal chest X-ray"
   - Verify report posted

5. **Pharmacist Actions:**
   - Login as Pharmacist
   - Navigate to Prescriptions
   - Select visit
   - Dispense drugs
   - Enter dispensing notes
   - Verify dispensing recorded

6. **Doctor Actions (Final):**
   - Login as Doctor
   - Review all results
   - Close consultation
   - Close visit
   - Verify visit status: CLOSED

**Expected Results:**
- ✅ All steps complete successfully
- ✅ Payment locks work correctly
- ✅ All data saved correctly
- ✅ Visit closes successfully

---

### Scenario 2: Payment & Lock System (10 minutes)

**Objective:** Verify explainable lock system

**Steps:**
1. Create visit
2. Order consultation service
3. Try to start consultation → **Should show lock with message**
4. Process payment
5. Try to start consultation → **Should work**
6. Order lab service
7. Try to post lab results → **Should show lock**
8. Process payment for lab
9. Post lab results → **Should work**

**Expected Results:**
- ✅ Locks appear before payment
- ✅ Lock messages clear and helpful
- ✅ Actions work after payment

---

### Scenario 3: Reports & Analytics (5 minutes)

**Objective:** Verify reports functionality

**Steps:**
1. Create 5-10 visits with payments (various amounts, methods)
2. Login as Admin
3. Navigate to `/reports`
4. Select date range (last 30 days)
5. Verify:
   - Summary cards display correctly
   - Revenue by method pie chart
   - Revenue trend line chart
   - Visits by status bar chart
6. Change date range
7. Verify data refreshes

**Expected Results:**
- ✅ All charts display
- ✅ Data accurate
- ✅ Date filtering works

---

### Scenario 4: Revenue Leak Detection (5 minutes)

**Objective:** Verify leak detection works

**Steps:**
1. Create visit
2. Order lab service
3. **Don't process payment**
4. Login as Lab Tech
5. Post lab results (should work - emergency override or test mode)
6. Login as Admin
7. Navigate to Revenue Leak Dashboard
8. Verify leak detected
9. Click on leak
10. View details
11. Resolve leak with notes
12. Verify leak marked as resolved

**Expected Results:**
- ✅ Leak detected
- ✅ Dashboard displays correctly
- ✅ Resolution works

---

### Scenario 5: End-of-Day Reconciliation (10 minutes)

**Objective:** Verify daily reconciliation

**Steps:**
1. Create multiple visits with payments (Cash, Paystack, Wallet, HMO)
2. Login as Admin
3. Navigate to `/reconciliation`
4. Review summary:
   - Total revenue
   - Revenue by method
   - Outstanding items
   - Revenue leaks
5. Enter staff name
6. Check confirmation checkbox
7. Click "Finalize Day"
8. Confirm finalization
9. Verify:
   - Page becomes read-only
   - Summary locked
   - Cannot edit

**Expected Results:**
- ✅ Summary accurate
- ✅ Finalization works
- ✅ Immutability enforced

---

### Scenario 6: Visit Timeline (5 minutes)

**Objective:** Verify timeline feature

**Steps:**
1. Navigate to visit with activity
2. Scroll to timeline section
3. Verify timeline displays
4. Verify events in chronological order:
   - Visit created
   - Payment confirmed
   - Consultation started
   - Service selected
   - Lab result posted
   - Consultation closed
5. Click on event
6. Verify details expand
7. Click "View Source Details"
8. Verify navigation works

**Expected Results:**
- ✅ Timeline displays
- ✅ All events logged
- ✅ Details expandable
- ✅ Links work

---

### Scenario 7: PACS-lite Integration (10 minutes)

**Objective:** Verify radiology image viewing

**Steps:**
1. Create radiology order
2. Process payment
3. Login as Radiology Tech
4. Upload test image
5. Navigate to radiology order details
6. Click to view images
7. Verify study/series browser displays
8. Click "OHIF Viewer" (if configured)
9. Verify viewer loads

**Expected Results:**
- ✅ Images upload
- ✅ Study browser works
- ✅ Viewer loads (if configured)

---

## Test Execution Checklist

### Pre-Test Setup
- [ ] Backend server running
- [ ] Frontend server running
- [ ] Database accessible
- [ ] Test users created (Admin, Doctor, Receptionist, Lab Tech, Radiology Tech, Pharmacist)

### Backend Tests
- [ ] `python manage.py check` passes
- [ ] `python manage.py test` passes
- [ ] PACS-lite test passes

### Frontend Tests
- [ ] `npm run build` succeeds
- [ ] No console errors
- [ ] All pages load

### Workflow Tests
- [ ] Complete patient journey
- [ ] Payment & lock system
- [ ] Reports & analytics
- [ ] Revenue leak detection
- [ ] End-of-day reconciliation
- [ ] Visit timeline
- [ ] PACS-lite integration

## Test Results Template

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

## Workflow Tests
| Scenario | Status | Notes |
|----------|--------|-------|
| Complete Patient Journey | ✅/❌ | |
| Payment & Lock System | ✅/❌ | |
| Reports & Analytics | ✅/❌ | |
| Revenue Leak Detection | ✅/❌ | |
| End-of-Day Reconciliation | ✅/❌ | |
| Visit Timeline | ✅/❌ | |
| PACS-lite Integration | ✅/❌ | |

## Issues Found
1. [Description]
2. [Description]

## Next Steps
1. [Action]
2. [Action]
```

