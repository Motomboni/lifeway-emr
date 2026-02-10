# Legacy RadiologyOrder / RadiologyResult Path (Quarantined)

## Current flow (Service Catalog)

- **RadiologyRequest** only: `GET /api/v1/visits/{visit_id}/radiology/`
- Reports: **PATCH** `/api/v1/visits/{visit_id}/radiology/{request_id}/` with `report`, `image_count`
- Billing: Created at order time (downstream_service_workflow) or ensured post-report (views._ensure_radiology_billing_for_visit)

## Legacy path (disabled by default)

- **RadiologyOrder** + **RadiologyResult** models
- Endpoint: `GET/POST /api/v1/visits/{visit_id}/radiology/results/`
- Controlled by `LEGACY_RADIOLOGY_RESULTS_ENABLED` in `result_views.py`

When `LEGACY_RADIOLOGY_RESULTS_ENABLED = False` (default):

- **POST** `/radiology/results/` → 403 (PermissionDenied)
- **GET** `/radiology/results/` → 410 Gone (with message to use RadiologyRequest + PATCH)

## Re-enabling legacy (read-only or migration)

1. Set `LEGACY_RADIOLOGY_RESULTS_ENABLED = True` in `result_views.py`.
2. Use only for migrating or viewing existing RadiologyResult data; do not create new results via this path for Service Catalog orders.

## Safe deletion (future)

To remove legacy code entirely:

1. Migrate any RadiologyResult data into RadiologyRequest report fields (if needed).
2. Remove or stub: `result_views.py`, `result_serializers.py`, and `RadiologyResult` / `RadiologyOrder` URL routes in `urls.py`.
3. Keep models/migrations for historical data or add a migration to archive/delete.
