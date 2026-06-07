# Nurse Prescription Dispensed Notification

## Problem

When a pharmacist dispenses a prescription, nurses need to be notified so they can administer the drugs to patients. Previously, there was no notification system for nurses when prescriptions were dispensed.

## Solution

Added notification system for nurses that alerts them when prescriptions are dispensed and ready for administration.

## Implementation Details

### Frontend: Notification Context

**File**: `frontend/src/contexts/NotificationContext.tsx`

Added nurse-specific notification checking for dispensed prescriptions:

1. **Updated Notification Interface**:
   - Added `'prescription_dispensed'` to notification types

2. **Added Nurse Notification Logic**:
   - Checks all open visits with cleared payment status
   - Fetches prescriptions for each visit
   - Filters for prescriptions with `status === 'DISPENSED'`
   - Creates notifications for dispensed prescriptions

```typescript
if (user.role === 'NURSE') {
  // Dispensed prescriptions notification - nurses need to administer drugs
  const visitsResponse = await fetchVisits({ status: 'OPEN' });
  const allVisits = Array.isArray(visitsResponse) ? visitsResponse : (visitsResponse as PaginatedResponse<Visit>).results || [];
  // Include PARTIALLY_PAID as cleared payment status (allows clinical actions)
  const openVisits = allVisits.filter((v: Visit) => 
    v.payment_status === 'PAID' || 
    v.payment_status === 'SETTLED' || 
    v.payment_status === 'PARTIALLY_PAID'
  );
  for (const visit of openVisits) {
    try {
      const prescriptions = await fetchPrescriptions(visit.id.toString());
      // Filter for dispensed prescriptions that need administration
      const dispensedPrescriptions = prescriptions.filter(p => p.status === 'DISPENSED');
      if (dispensedPrescriptions.length > 0) {
        newNotifications.push({
          id: `prescription-dispensed-${visit.id}`,
          type: 'prescription_dispensed',
          message: `${dispensedPrescriptions.length} dispensed prescription(s) ready for administration - Visit #${visit.id}`,
          visitId: visit.id,
          count: dispensedPrescriptions.length,
          timestamp: new Date(),
        });
      }
    } catch (error) {
      // Skip if error fetching prescriptions
    }
  }
}
```

### Frontend: Notification Bell Component

**File**: `frontend/src/components/common/NotificationBell.tsx`

Added navigation handling for `prescription_dispensed` notifications:

```typescript
case 'prescription_dispensed':
  // Navigate to visit details page for nurses to administer drugs
  if (notification.visitId > 0) {
    navigate(`/visits/${notification.visitId}#prescriptions-section`);
  } else {
    navigate('/visits');
  }
  break;
```

## How It Works

### Notification Flow

1. **Pharmacist Dispenses Prescription**:
   - Prescription status changes to `'DISPENSED'`
   - Prescription is saved with `dispensed=True`, `dispensed_by`, `dispensed_date`

2. **Nurse Notification Check** (every 30 seconds):
   - System checks all open visits
   - Fetches prescriptions for each visit
   - Filters for `status === 'DISPENSED'`
   - Creates notification if dispensed prescriptions found

3. **Nurse Sees Notification**:
   - Notification appears in notification bell
   - Shows count of dispensed prescriptions per visit
   - Clicking notification navigates to visit details

4. **Nurse Administers Drugs**:
   - Nurse navigates to visit
   - Views dispensed prescriptions
   - Administers drugs to patient
   - Records administration (if tracking implemented)

## User Experience

### For Nurses

1. **Notification Bell** → Shows count of dispensed prescriptions
2. **Click Notification** → Navigates to visit details page
3. **View Prescriptions** → See all dispensed prescriptions for the visit
4. **Administer Drugs** → Administer medications to patient

### Notification Message

- **Format**: `"{count} dispensed prescription(s) ready for administration - Visit #{visitId}"`
- **Example**: `"3 dispensed prescription(s) ready for administration - Visit #236"`

## Benefits

1. **Real-time Notifications** → Nurses are immediately aware when drugs are dispensed
2. **Efficient Workflow** → Nurses can quickly navigate to the correct visit
3. **Patient Safety** → Ensures timely drug administration
4. **Automatic Updates** → Notifications refresh every 30 seconds
5. **Role-Specific** → Only nurses see these notifications

## Testing Checklist

- [ ] Pharmacist dispenses prescription → Status changes to DISPENSED
- [ ] Nurse sees notification → Notification appears in bell
- [ ] Notification shows correct count → Count matches dispensed prescriptions
- [ ] Click notification → Navigates to correct visit
- [ ] Multiple visits → Shows separate notifications per visit
- [ ] Notification refreshes → Updates every 30 seconds
- [ ] Other roles → Don't see nurse notifications

## Files Modified

1. **`frontend/src/contexts/NotificationContext.tsx`**
   - Added `'prescription_dispensed'` to Notification type
   - Added nurse-specific notification checking for dispensed prescriptions

2. **`frontend/src/components/common/NotificationBell.tsx`**
   - Added navigation handling for `prescription_dispensed` notifications
   - Navigates to visit details page with prescriptions section

## Future Enhancements

Potential improvements:
1. Add backend notification creation when prescription is dispensed (push notifications)
2. Add administration tracking (mark prescription as administered)
3. Add administration notes (record when/how drug was given)
4. Add reminders for scheduled administrations
5. Add alerts for overdue administrations

## Related Features

This complements:
- **Prescription Dispensing** → Pharmacists dispense medications
- **Prescription Viewing** → Nurses can view prescriptions
- **Visit Management** → Nurses manage patient visits
- **Notification System** → Role-based notifications for all staff
