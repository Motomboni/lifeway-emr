# EMR SaaS Conversion Summary

This document summarizes the multi-tenant SaaS conversion applied to the EMR project.

## What Was Implemented

### 1. Multi-Tenancy Foundation

- **Organization** model: Represents a clinic/hospital (tenant)
- **OrganizationUser** model: Links users to organizations (many-to-many); users can belong to multiple orgs
- **OrganizationMiddleware**: Resolves current organization from:
  - `X-Organization-Id` header
  - `X-Organization-Slug` header
  - JWT `organization_id` claim
  - User's default organization

### 2. SaaS Billing Models

- **Plan**: Subscription tiers (Starter, Professional, Enterprise) with limits and pricing
- **Subscription**: Organization's active plan, status, Stripe IDs, trial/period dates

### 3. Tenant-Scoped Data

- **Patient**: Added `organization` FK; `generate_patient_id()` scoped per organization
- **Visit**: Added `organization` FK; set from patient via signal
- **ServiceCatalog**: Added `organization` FK; org-specific + global templates

### 4. API Changes

- **Login**: Returns `organizations` (user's memberships) and JWT includes `organization_id`
- **Patients, Visits, ServiceCatalog**: Querysets filtered by `request.organization`
- **New endpoints**:
  - `GET /api/v1/organizations/` – List user's organizations
  - `GET /api/v1/organizations/me/` – Current organization
  - `GET /api/v1/organizations/memberships/` – User's memberships (tenant switcher)
  - `POST /api/v1/organizations/{id}/set-default/` – Set default org

### 5. Frontend Changes

- **apiClient**: Adds `X-Organization-Id` header when `organization_id` is in localStorage
- **AuthContext**: On login, sets `organization_id` from first/default membership
- **Organizations API**: `getOrganizationMemberships()`, `setDefaultOrganization()`

## Migration Path for Existing Data

1. Run `python manage.py migrate`
2. Migration `0002_create_default_org_and_assign`:
   - Creates "Default Clinic" organization
   - Creates "Starter" plan and subscription
   - Assigns all existing patients, visits, ServiceCatalog to default org
   - Adds all staff users to default org as members

## Phase 2 Additions (Completed)

- **Tenant switcher UI** in Dashboard header – shows current org, dropdown to switch when user has multiple orgs
- **Appointments** – filtered by `patient__organization`
- **Reports** – summary, visits-summary, payments-summary, consultations-summary, dashboard-stats, patient-statistics all scoped by organization

## Phase 3 Additions (Completed)

- **Plan limits enforcement** – `check_patient_limit()` in PatientCreateSerializer; `organizations/utils.py` with `check_patient_limit`, `check_user_limit`
- **Starter plan limits** – migration sets `max_users=10`, `max_patients=500` on Starter plan
- **Organization creation API** – `POST /organizations/create/` (admin only) creates org + subscription + adds creator as OWNER
- **Scoped views** – IVF (IVFCycle, SpermAnalysis), Antenatal (AntenatalRecord), Billing queue, Leak detection all filter by organization

## Phase 4 Additions (Completed)

- **Organization members API** – `GET/POST /organizations/{id}/members/` – list members, add member (with `check_user_limit`)
- **Reports clinical-statistics** – lab, radiology, prescription stats scoped by organization
- **Frontend API** – `createOrganization`, `getOrganizationMembers`, `addOrganizationMember`

## Phase 5 Additions (Completed)

- **Billing service** – `organizations/billing_service.py`: `get_usage_for_organization`, `get_subscription_status`, `create_stripe_checkout_session` (when STRIPE_SECRET_KEY set)
- **Subscription status API** – `GET /subscriptions/status/` returns plan, usage, limits
- **TenantSwitcher** – shows plan name and usage (patients/users) in badge and dropdown

## Phase 6 Additions (Completed)

- **Stripe webhook** – `POST /api/v1/subscriptions/stripe/webhook/` – handles `checkout.session.completed`, `customer.subscription.created/updated/deleted`; requires `STRIPE_WEBHOOK_SECRET`
- **Checkout API** – `POST /subscriptions/checkout/` – body: `{ plan_slug, success_url, cancel_url }`; returns `{ checkout_url }` for Stripe Checkout redirect
- **stripe** package added to `requirements.txt`

## Phase 7 Additions (Completed)

- **CORS** – `x-organization-id`, `x-organization-slug` added to `CORS_ALLOW_HEADERS` for frontend tenant header
- **EndOfDayReconciliation** – added `organization` FK; one reconciliation per org per day; migration `0022_add_organization_to_reconciliation`
- **Reconciliation service** – `create_reconciliation`, `_perform_reconciliation`, `get_reconciliation_for_date` all scope by `organization_id`
- **Leak detection** – `detect_all_leaks(organization_id)` scoped by organization
- **Reconciliation views** – queryset and create scoped by `request.organization`
- **Frontend Upgrade** – `createCheckoutSession` API; TenantSwitcher shows "Upgrade" button when at patient/user limit

## Phase 8 Additions (Completed)

- **Self-serve signup** – `POST /organizations/signup/` (public, when `ENABLE_ORG_SIGNUP=true`); creates org + owner user + Starter subscription; body: `{ name, slug, email?, phone?, username, password, first_name, last_name }`
- **Frontend** – `signupOrganization()` in organizations API

## Next Steps (Optional)

1. **Configure Stripe** – Add `stripe_price_id` to Plans in Django admin; set `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` in env
2. **Enable signup** – Set `ENABLE_ORG_SIGNUP=true` to allow public org creation
3. **Subdomain routing** (e.g. `clinic1.emr.app`) for tenant resolution

## Backward Compatibility

- Existing deployments: Data migration assigns everything to "Default Clinic"
- Users without OrganizationUser: Middleware falls back to first org; add memberships via admin
- API requests without `X-Organization-Id`: Backend uses JWT or default org
