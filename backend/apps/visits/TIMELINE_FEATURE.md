# Visit Timeline Feature

## Overview

The Visit Timeline feature provides an immutable, read-only chronological view of all significant events that occur during a patient's visit. Events are automatically logged via Django signals and cannot be manually created, edited, or deleted.

## Features

- **Visit-scoped**: All events are tied to a specific visit
- **Read-only**: Events are immutable once created
- **Auto-logged**: Events are automatically created via Django signals
- **Deduplication**: Prevents duplicate events using unique deduplication keys
- **Chronological**: Events are displayed in chronological order
- **Clickable links**: Events link to their source objects when available

## Event Types

The timeline tracks the following event types:

1. **VISIT_CREATED** - When a visit is created
2. **CONSULTATION_STARTED** - When a consultation begins
3. **CONSULTATION_CLOSED** - When a consultation is closed
4. **SERVICE_SELECTED** - When a service is selected from the catalog
5. **LAB_ORDERED** - When a lab order is placed
6. **LAB_RESULT_POSTED** - When a lab result is posted
7. **RADIOLOGY_ORDERED** - When a radiology study is ordered
8. **RADIOLOGY_REPORT_POSTED** - When a radiology report is posted
9. **DRUG_DISPENSED** - When a drug is dispensed
10. **PAYMENT_CONFIRMED** - When a payment is confirmed
11. **PROCEDURE_ORDERED** - When a procedure is ordered
12. **PROCEDURE_COMPLETED** - When a procedure is completed

## Backend Implementation

### Models

- **TimelineEvent** (`apps/visits/timeline_models.py`): The main model for timeline events
  - Immutable (prevents editing/deletion)
  - Auto-generates deduplication keys
  - Stores actor, timestamp, description, and metadata

### Signals

- **timeline_signals.py**: Django signals that automatically create timeline events
  - `log_visit_created`: Logs visit creation
  - `log_consultation_events`: Logs consultation started/closed
  - `log_lab_ordered`: Logs lab orders
  - `log_lab_result_posted`: Logs lab results
  - `log_radiology_ordered`: Logs radiology orders
  - `log_radiology_report_posted`: Logs radiology reports
  - `log_drug_dispensed`: Logs drug dispensing
  - `log_payment_confirmed`: Logs payment confirmations
  - `log_service_selected`: Logs service selections
  - `log_procedure_ordered`: Logs procedure orders
  - `log_procedure_completed`: Logs procedure completions

### API Endpoints

- **GET /api/v1/visits/{visit_id}/timeline/**: List all timeline events for a visit
  - Returns chronological list of events
  - Includes actor information, timestamps, descriptions, and source links

### Serializers

- **TimelineEventSerializer**: Serializes timeline events for API responses
  - Includes event type display names
  - Includes actor names and roles
  - Includes source URLs for clickable links

## Frontend Implementation

### Components

- **VisitTimeline** (`frontend/src/components/timeline/VisitTimeline.tsx`): Main timeline component
  - Vertical timeline layout
  - Color-coded event types
  - Icons for each event type
  - Relative timestamps (e.g., "2 hours ago")
  - Clickable links to source objects

### API Client

- **timeline.ts**: API client functions for fetching timeline events

### Integration

The timeline is integrated into the VisitDetailsPage and appears after the consultation section.

## Deduplication

Events are deduplicated using a unique `deduplication_key` field with the format:
```
{visit_id}:{event_type}:{source_id}
```

This ensures that:
- The same event is not logged multiple times
- Events are idempotent (safe to call signals multiple times)
- No duplicate events appear in the timeline

## Immutability

Timeline events are immutable:
- Cannot be edited after creation
- Cannot be deleted
- Can only be created via Django signals (not manually)

This ensures:
- Audit trail integrity
- No accidental data loss
- Complete visit history

## Usage

### Viewing Timeline

1. Navigate to a visit's details page
2. Scroll to the "Visit Timeline" section
3. View all events in chronological order

### Event Details

Each event shows:
- **Event Type**: What happened (e.g., "Lab Ordered")
- **Timestamp**: When it happened (relative or absolute)
- **Description**: Human-readable description
- **Actor**: Who performed the action (role and name)
- **Source Link**: Clickable link to view the source object (if available)

## Migration

To apply the timeline feature:

```bash
python manage.py makemigrations visits
python manage.py migrate
```

The signals will automatically start logging events for new actions. Existing visits will not have historical timeline events (only new events will be logged).

## Future Enhancements

Potential future enhancements:
- Filter events by type
- Search timeline events
- Export timeline as PDF
- Real-time updates via WebSocket
- Event grouping (e.g., group related events)
- Custom event types for specific workflows

