# API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication

All API endpoints (except `/auth/login/` and `/auth/refresh/`) require JWT authentication.

Include the token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## Endpoints

### Authentication

#### Login
```http
POST /auth/login/
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access": "string",
  "refresh": "string",
  "user": {
    "id": 1,
    "username": "string",
    "first_name": "string",
    "last_name": "string",
    "role": "DOCTOR"
  }
}
```

#### Refresh Token
```http
POST /auth/refresh/
Content-Type: application/json

{
  "refresh": "string"
}
```

#### Get Current User
```http
GET /auth/me/
Authorization: Bearer <token>
```

### Patients

#### List Patients
```http
GET /patients/?search=<query>
```

#### Get Patient
```http
GET /patients/{id}/
```

#### Create Patient
```http
POST /patients/
Content-Type: application/json

{
  "first_name": "string",
  "last_name": "string",
  "date_of_birth": "YYYY-MM-DD",
  "gender": "MALE|FEMALE|OTHER|PREFER_NOT_TO_SAY",
  "phone": "string",
  "email": "string",
  "address": "string",
  "national_id": "string",
  "blood_group": "A+|A-|B+|B-|AB+|AB-|O+|O-",
  "allergies": "string",
  "medical_history": "string"
}
```

### Visits

#### List Visits
```http
GET /visits/?status=OPEN&payment_status=CLEARED&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&search=<query>&page=1&page_size=20
```

#### Create Visit
```http
POST /visits/
Content-Type: application/json

{
  "patient": 1,
  "payment_status": "PENDING|CLEARED"
}
```

#### Get Visit
```http
GET /visits/{id}/
```

#### Close Visit
```http
POST /visits/{id}/close/
```
**Doctor only**

### Consultation

#### Get Consultation
```http
GET /visits/{visit_id}/consultation/
```

#### Create Consultation
```http
POST /visits/{visit_id}/consultation/
Content-Type: application/json

{
  "history": "string",
  "examination": "string",
  "diagnosis": "string",
  "clinical_notes": "string"
}
```
**Doctor only, payment must be CLEARED**

#### Update Consultation
```http
PATCH /visits/{visit_id}/consultation/
Content-Type: application/json

{
  "history": "string",
  "examination": "string",
  "diagnosis": "string",
  "clinical_notes": "string"
}
```
**Doctor only, visit must be OPEN**

### Lab Orders

#### List Lab Orders
```http
GET /visits/{visit_id}/laboratory/
```

#### Create Lab Order
```http
POST /visits/{visit_id}/laboratory/
Content-Type: application/json

{
  "consultation": 1,
  "tests_requested": ["test1", "test2"],
  "clinical_indication": "string"
}
```
**Doctor only**

#### List Lab Results
```http
GET /visits/{visit_id}/laboratory/results/
```

#### Create Lab Result
```http
POST /visits/{visit_id}/laboratory/results/
Content-Type: application/json

{
  "lab_order": 1,
  "result_data": "string",
  "abnormal_flag": "NORMAL|ABNORMAL|CRITICAL"
}
```
**Lab Tech only**

### Radiology Orders

#### List Radiology Orders
```http
GET /visits/{visit_id}/radiology/
```

#### Create Radiology Order
```http
POST /visits/{visit_id}/radiology/
Content-Type: application/json

{
  "consultation": 1,
  "imaging_type": "XRAY|CT|MRI|US",
  "body_part": "string",
  "clinical_indication": "string",
  "priority": "ROUTINE|URGENT"
}
```
**Doctor only**

#### List Radiology Results
```http
GET /visits/{visit_id}/radiology/results/
```

#### Create Radiology Result
```http
POST /visits/{visit_id}/radiology/results/
Content-Type: application/json

{
  "radiology_order": 1,
  "report": "string",
  "finding_flag": "NORMAL|ABNORMAL|CRITICAL",
  "image_count": 0,
  "image_metadata": {}
}
```
**Radiology Tech only**

### Prescriptions

#### List Prescriptions
```http
GET /visits/{visit_id}/prescriptions/
```

#### Create Prescription
```http
POST /visits/{visit_id}/prescriptions/
Content-Type: application/json

{
  "consultation": 1,
  "drug": "string",
  "dosage": "string",
  "frequency": "string",
  "duration": "string",
  "quantity": 0,
  "instructions": "string"
}
```
**Doctor only**

#### Dispense Prescription
```http
POST /visits/{visit_id}/pharmacy/dispense/
Content-Type: application/json

{
  "prescription_id": 1,
  "dispensing_notes": "string"
}
```
**Pharmacist only**

### Payments

#### List Payments
```http
GET /visits/{visit_id}/payments/
```

#### Create Payment
```http
POST /visits/{visit_id}/payments/
Content-Type: application/json

{
  "amount": "10.00",
  "payment_method": "CASH|CARD|BANK_TRANSFER|MOBILE_MONEY|INSURANCE",
  "transaction_reference": "string",
  "notes": "string",
  "status": "PENDING|CLEARED"
}
```
**Receptionist only**

#### Clear Payment
```http
POST /visits/{visit_id}/payments/{id}/clear/
Content-Type: application/json

{
  "transaction_reference": "string",
  "notes": "string"
}
```
**Receptionist only**

### Audit Logs

#### List Audit Logs
```http
GET /audit-logs/?visit_id=1&action=consultation&resource_type=consultation&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&page=1&page_size=50
```
**Read-only**

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Error message"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 409 Conflict
```json
{
  "detail": "Visit is closed and cannot be modified."
}
```

## Pagination

Paginated responses follow this format:
```json
{
  "count": 100,
  "next": "http://localhost:8000/api/v1/visits/?page=2",
  "previous": null,
  "results": [...]
}
```

## Filtering

Most list endpoints support filtering via query parameters:
- `status` - Filter by status
- `payment_status` - Filter by payment status
- `date_from` - Filter from date (YYYY-MM-DD)
- `date_to` - Filter to date (YYYY-MM-DD)
- `search` - Search query
- `page` - Page number
- `page_size` - Items per page
