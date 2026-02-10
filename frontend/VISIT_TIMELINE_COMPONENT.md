# Visit Timeline Component

## Overview

The Visit Timeline component provides a comprehensive, chronological view of all events for a visit. It replaces traditional tab-heavy navigation with a single, scrollable timeline interface.

## Features

✅ **Read-only**: All events are immutable and cannot be edited
✅ **Visit-scoped**: Shows only events for the specified visit
✅ **Chronological**: Events displayed in chronological order
✅ **Vertical Timeline**: Clean vertical layout with connecting lines
✅ **Sticky Header**: Patient name and visit ID always visible
✅ **Expandable Items**: Click to expand for detailed information
✅ **Color Coding**: Department-based color coding for visual organization
✅ **Event Icons**: Unique icons for each event type
✅ **Role Display**: Shows who performed each action
✅ **Source Links**: Navigate to source objects (consultation, lab order, etc.)

## Event Types

The timeline supports all major event types:

- **Visit Created** - When visit was created
- **Consultation Started/Closed** - Consultation lifecycle
- **Service Selected** - Services ordered from catalog
- **Lab Ordered/Result Posted** - Laboratory workflow
- **Radiology Ordered/Report Posted** - Radiology workflow
- **Drug Dispensed** - Pharmacy dispensing
- **Payment Confirmed** - Payment processing
- **Procedure Ordered/Completed** - Clinical procedures
- **Admission Created/Discharged/Transferred** - Inpatient management
- **Vital Signs Recorded** - Nursing care
- **Nursing Note Added** - Documentation
- **Medication Administered** - Medication administration
- **Lab Sample Collected** - Sample collection
- **Document Uploaded** - Document management
- **Referral Created** - Referrals
- **Discharge Summary Created** - Discharge documentation

## Department Color Coding

Each department has a distinct color:

- **GENERAL**: Green (#4CAF50)
- **GOPD**: Blue (#2196F3)
- **LAB**: Purple (#9C27B0)
- **RADIOLOGY**: Cyan (#00BCD4)
- **PHARMACY**: Deep Orange (#FF5722)
- **BILLING**: Light Green (#8BC34A)
- **CLINICAL**: Blue Grey (#607D8B)
- **INPATIENT**: Brown (#795548)
- **NURSING**: Pink (#E91E63)
- **DOCUMENTS**: Grey (#757575)
- **REFERRALS**: Orange (#FF9800)
- **DISCHARGE**: Lime (#CDDC39)

## Usage

### Basic Usage

```tsx
import VisitTimeline from '../components/timeline/VisitTimeline';

<VisitTimeline visitId={123} />
```

### With Header

```tsx
<VisitTimeline visitId={123} showHeader={true} />
```

### With Custom Event Handler

```tsx
<VisitTimeline 
  visitId={123} 
  showHeader={true}
  onEventClick={(event) => {
    // Custom handling
    console.log('Event clicked:', event);
  }}
/>
```

## Component Props

- `visitId` (number, required): ID of the visit to display timeline for
- `showHeader` (boolean, optional): Show sticky header with patient info (default: true)
- `onEventClick` (function, optional): Custom handler for event clicks

## Sticky Header

The sticky header displays:
- Patient full name
- Visit ID
- Visit type
- Visit status (color-coded)

The header remains visible while scrolling through the timeline.

## Expandable Items

Each timeline item can be expanded to show:
- Full event information
- Timestamp details
- Actor information
- Additional metadata
- Link to source object

Click on any timeline item or the expand indicator to toggle details.

## Integration

The component is already integrated into `VisitDetailsPage.tsx`:

```tsx
<VisitTimeline visitId={visit.id} showHeader={true} />
```

## API Endpoint

The component uses:
- `GET /api/v1/visits/{visit_id}/timeline/` - Fetch timeline events

## Responsive Design

The component is fully responsive:
- Mobile: Stacked layout, smaller dots, compact cards
- Tablet: Optimized spacing
- Desktop: Full-width with optimal spacing

## Accessibility

- Keyboard navigation supported
- Screen reader friendly
- High contrast colors
- Clear visual hierarchy

