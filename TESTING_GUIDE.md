# Testing Guide

## Overview

This guide provides instructions for testing all the newly implemented features.

## 1. Testing Explainable Lock System

### Test Consultation Lock
1. **Navigate to a visit** with unpaid status
2. **Check Visit Details Page** (`/visits/{id}`)
3. **Verify:**
   - Lock indicator appears with explanation
   - "Start Consultation" button is disabled
   - Message explains payment is required

### Test Radiology Upload Lock
1. **Navigate to Radiology Upload** component
2. **Select an unpaid radiology order**
3. **Verify:**
   - Lock indicator appears
   - Upload button is disabled
   - Message explains payment requirement

### Test Drug Dispense Lock
1. **Navigate to Prescriptions Page** (`/prescriptions`)
2. **Select a visit with unpaid prescription**
3. **Verify:**
   - Lock indicator appears for dispense button
   - Dispense button is disabled
   - Message explains payment requirement

### Test Lab Order Lock
1. **Navigate to Consultation Page** (`/visits/{id}/consultation`)
2. **Try to order a lab service**
3. **Verify:**
   - Lock indicator appears if visit payment not cleared
   - Service search button is disabled
   - Message explains requirement

## 2. Testing OHIF Viewer Integration

### Test Study/Series Browser
1. **Navigate to Radiology Orders Page** (`/radiology-orders`)
2. **Click on a radiology order** with uploaded images
3. **Verify:**
   - Order details modal opens
   - Study/Series browser displays
   - Images are grouped by series
   - Thumbnails are visible

### Test OHIF Viewer
1. **In Radiology Order Details**, click "OHIF Viewer" button
2. **Verify:**
   - Viewer loads in iframe
   - Images are accessible
   - Navigation works
   - Lock check prevents viewing if payment not cleared

### Test Lock for Viewing
1. **Try to view radiology images** for unpaid order
2. **Verify:**
   - Lock indicator appears
   - Viewer is blocked
   - Message explains payment requirement

## 3. Testing Reports API

### Test Summary Endpoint
```bash
# Get comprehensive summary
GET /api/v1/reports/summary/?start_date=2024-01-01&end_date=2024-12-31

# Expected response:
{
  "total_revenue": 1250000.0,
  "total_visits": 450,
  "total_patients": 320,
  "revenue_by_method": {
    "CASH": 500000.0,
    "PAYSTACK": 400000.0,
    "WALLET": 200000.0,
    "HMO": 150000.0
  },
  "visits_by_status": {
    "OPEN": 50,
    "CLOSED": 400
  },
  "revenue_trend": [...]
}
```

### Test Revenue by Method
```bash
GET /api/v1/reports/revenue-by-method/?start_date=2024-01-01&end_date=2024-12-31

# Expected: Object with payment methods as keys
```

### Test Revenue Trend
```bash
GET /api/v1/reports/revenue-trend/?start_date=2024-01-01&end_date=2024-01-07

# Expected: Array of {date, revenue} objects
```

### Test Visits by Status
```bash
GET /api/v1/reports/visits-by-status/?start_date=2024-01-01&end_date=2024-12-31

# Expected: Object with status counts
```

## 4. Testing Reports Page UI

### Test Charts Display
1. **Navigate to Reports Page** (`/reports`) as Admin
2. **Select date range**
3. **Verify:**
   - Summary cards display correctly
   - Pie chart shows revenue by payment method
   - Line chart shows revenue trend
   - Bar chart shows visits by status
   - All charts are responsive

### Test Date Range Selector
1. **Change start and end dates**
2. **Verify:**
   - Data refreshes automatically
   - Charts update with new data
   - Loading states display

### Test API Integration
1. **Check browser console** for API calls
2. **Verify:**
   - API calls are made correctly
   - Data is formatted properly
   - Fallback to mock data if API fails

## 5. Testing Radiology Order Details Integration

### Test Order Selection
1. **Navigate to Radiology Orders Page**
2. **Click on any radiology order**
3. **Verify:**
   - Modal opens with order details
   - Study/Series browser displays
   - Can toggle between browser and viewer

### Test Modal Functionality
1. **In order details modal:**
   - Click "Study Browser" button
   - Click "OHIF Viewer" button
   - Click "Close" button
2. **Verify:**
   - Views switch correctly
   - Modal closes properly
   - No errors in console

## 6. End-to-End Test Scenarios

### Scenario 1: Complete Radiology Workflow
1. Create a visit
2. Order radiology service
3. Process payment
4. Upload radiology images
5. View images in OHIF viewer
6. Post radiology report

**Expected:** All steps work, locks prevent actions before payment

### Scenario 2: Reports Generation
1. Create multiple visits with payments
2. Navigate to Reports page
3. Select date range
4. View all charts

**Expected:** All data displays correctly, charts render properly

### Scenario 3: Lock System Flow
1. Create visit without payment
2. Try to start consultation → Locked
3. Process payment
4. Try to start consultation → Unlocked
5. Try to order lab service → Works

**Expected:** Locks work correctly, unlock after payment

## 7. API Testing with curl

### Test Reports Summary
```bash
curl -X GET "http://localhost:8000/api/v1/reports/summary/?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Revenue by Method
```bash
curl -X GET "http://localhost:8000/api/v1/reports/revenue-by-method/?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Lock Evaluation
```bash
curl -X GET "http://localhost:8000/api/v1/locks/consultation/?visit_id=123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 8. Common Issues and Solutions

### Issue: Charts not displaying
**Solution:** Check browser console for errors, verify recharts is installed

### Issue: API returns 404
**Solution:** Verify URL patterns in `backend/apps/reports/urls.py`

### Issue: Lock not showing
**Solution:** Check browser console, verify lock API endpoint is accessible

### Issue: OHIF viewer not loading
**Solution:** Check OHIF viewer URL in settings, verify study has images

## 9. Performance Testing

### Test Report Loading
1. **Select large date range** (1 year)
2. **Measure load time**
3. **Verify:** Loads within reasonable time (< 5 seconds)

### Test Chart Rendering
1. **Load reports page**
2. **Measure chart render time**
3. **Verify:** Charts render quickly (< 2 seconds)

## 10. Browser Compatibility

Test in:
- Chrome (latest)
- Firefox (latest)
- Edge (latest)
- Safari (if available)

Verify:
- Charts render correctly
- Modals work properly
- Lock indicators display
- OHIF viewer loads

## Success Criteria

✅ All lock indicators display correctly
✅ All locks prevent actions when appropriate
✅ OHIF viewer loads and displays images
✅ Reports API returns correct data
✅ Charts display with real data
✅ Date range selector works
✅ Modal opens and closes properly
✅ No console errors
✅ All features work on mobile
