# Quick Test Guide - Start Here

## 🚀 Quick Start (5 minutes)

### 1. Start Servers
```bash
# Terminal 1 - Backend
cd backend
python manage.py runserver

# Terminal 2 - Frontend  
cd frontend
npm start
```

### 2. Quick Smoke Tests

**Test 1: Login (30 seconds)**
- Open http://localhost:3000
- Login as Admin
- Verify dashboard loads

**Test 2: Create Visit (1 minute)**
- Register new patient
- Create visit
- Verify visit created

**Test 3: Order Service (1 minute)**
- Navigate to visit
- Order service from catalog
- Verify service added to bill

**Test 4: Process Payment (1 minute)**
- Process payment
- Verify payment recorded
- Verify visit payment status: PAID

**Test 5: Start Consultation (1 minute)**
- Try to start consultation
- Should work (payment cleared)
- Enter consultation notes
- Save

**Test 6: View Reports (1 minute)**
- Navigate to Reports page
- Verify charts display
- Change date range
- Verify data updates

## ✅ If All Quick Tests Pass

Proceed to comprehensive tests in `COMPREHENSIVE_WORKFLOW_TEST.md`

## ❌ If Tests Fail

1. Check browser console for errors
2. Check backend logs
3. Verify database migrations applied
4. Check API endpoints accessible

## Next Steps

1. Run backend unit tests
2. Execute full workflow scenarios
3. Test all features systematically
4. Document results

