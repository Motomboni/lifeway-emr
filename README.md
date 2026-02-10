# Modern EMR System

A comprehensive Electronic Medical Record (EMR) system built with strict adherence to EMR RULE LOCK principles.

## Overview

This EMR system enforces visit-scoped architecture, role-based access control, payment enforcement, and comprehensive audit logging. All clinical actions are visit-scoped and follow a strict workflow: `Visit → Consultation → (Lab | Radiology) → Prescription → Closure`.

## Technology Stack

### Backend
- **Django 4.x** - Web framework
- **Django REST Framework** - API framework
- **djangorestframework-simplejwt** - JWT authentication
- **PostgreSQL** (recommended) / SQLite (development)
- **Pytest** - Testing framework

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **React Router** - Routing
- **CSS Modules** - Styling

## Key Features

### ✅ Completed Features

1. **Authentication & Authorization**
   - JWT-based authentication
   - Role-based access control (Doctor, Receptionist, Lab Tech, Radiology Tech, Pharmacist, Patient)
   - Account lockout after failed attempts
   - Token refresh mechanism
   - Multi-role registration page

2. **Patient Management**
   - Patient registration (Receptionist)
   - Patient search and management
   - PHI data protection

3. **Visit Management**
   - Visit creation (Receptionist)
   - Visit listing with advanced filters
   - Visit details view
   - Visit closure (Doctor only)

4. **Consultation**
   - Single-screen consultation workspace
   - Visit-scoped consultation creation/editing
   - Payment enforcement
   - Close visit functionality

5. **Lab Orders & Results**
   - Lab order creation (Doctor)
   - Lab result entry (Lab Tech)
   - Visit-scoped and consultation-dependent

6. **Radiology Orders & Results**
   - Radiology order creation (Doctor)
   - Radiology report entry (Radiology Tech)
   - Visit-scoped and consultation-dependent

7. **Prescriptions & Dispensing**
   - Prescription creation (Doctor)
   - Prescription dispensing (Pharmacist)
   - Visit-scoped and consultation-dependent

8. **Payment Processing**
   - Payment creation and clearing (Receptionist)
   - Multiple payment methods
   - Automatic visit payment status update

9. **Audit Logging**
   - Comprehensive audit log viewer
   - All actions logged with user, role, timestamp, IP
   - Read-only access for compliance

10. **Notifications**
    - Real-time notifications for pending orders
    - Role-specific notifications
    - Notification bell component

11. **Export & Print**
    - Visit summary printing
    - Visit summary export (text)
    - Formatted reports

12. **Advanced Features**
    - Advanced search and filtering
    - Pagination for large lists
    - Keyboard shortcuts
    - Error handling utilities
    - Form validation utilities

13. **System Health & Monitoring**
    - Health check endpoints (database, cache, application)
    - Health status dashboard
    - System information display
    - Real-time status monitoring

14. **Error Handling & Logging**
    - React Error Boundary for crash prevention
    - Centralized logging utility
    - 404 Not Found page
    - Improved error messages

15. **Patient Portal**
    - Patient self-registration with automatic Patient record creation
    - Patient account verification by Receptionist (required before portal access)
    - Email notifications when account is verified
    - Patient dashboard with quick stats and recent activity
    - View visits, appointments, lab results, radiology results, prescriptions
    - Comprehensive medical history view
    - Telemedicine session access
    - Read-only access to own records only
    - Secure authentication and audit logging

## EMR Rule Compliance

✅ **Visit-Scoped Architecture**: All clinical APIs nested under `/api/v1/visits/{visit_id}/`  
✅ **Consultation-Centric Flow**: Mandatory consultation before orders/prescriptions  
✅ **Payment Enforcement**: Payment must be CLEARED before clinical actions  
✅ **Closed Visit Immutability**: CLOSED visits cannot be modified  
✅ **Role-Based Access**: Strict separation of duties  
✅ **Audit Logging**: All actions logged for compliance  
✅ **Error Handling**: Comprehensive error boundaries and logging  
✅ **Health Monitoring**: System health checks and status monitoring  
✅ **Data Minimization**: Role-based data visibility  
✅ **PHI Protection**: Patient data properly protected  

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+
- PostgreSQL (optional, SQLite works for development)

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

The frontend will run on `http://localhost:3000` (or next available port) and proxy API requests to `http://localhost:8000`.

## API Documentation

### Authentication
- `POST /api/v1/auth/login/` - Login
- `POST /api/v1/auth/refresh/` - Refresh token
- `POST /api/v1/auth/logout/` - Logout
- `GET /api/v1/auth/me/` - Get current user

### Visits
- `GET /api/v1/visits/` - List visits (with filters)
- `POST /api/v1/visits/` - Create visit
- `GET /api/v1/visits/{id}/` - Get visit details
- `POST /api/v1/visits/{id}/close/` - Close visit (Doctor only)

### Visit-Scoped Endpoints
All clinical actions are nested under visits:

- `/api/v1/visits/{visit_id}/consultation/` - Consultation CRUD
- `/api/v1/visits/{visit_id}/laboratory/` - Lab orders
- `/api/v1/visits/{visit_id}/laboratory/results/` - Lab results
- `/api/v1/visits/{visit_id}/radiology/` - Radiology orders
- `/api/v1/visits/{visit_id}/radiology/results/` - Radiology results
- `/api/v1/visits/{visit_id}/prescriptions/` - Prescriptions
- `/api/v1/visits/{visit_id}/pharmacy/dispense/` - Dispensing
- `/api/v1/visits/{visit_id}/payments/` - Payments

### Audit Logs
- `GET /api/v1/audit-logs/` - List audit logs (read-only)

### Patient Portal (Read-Only for Patients)
- `GET /api/v1/patient-portal/profile/` - Get patient's own profile
- `GET /api/v1/patient-portal/visits/` - Get patient's visits
- `GET /api/v1/patient-portal/visits/{visit_id}/` - Get visit details
- `GET /api/v1/patient-portal/appointments/` - Get patient's appointments
- `GET /api/v1/patient-portal/lab-results/` - Get patient's lab results
- `GET /api/v1/patient-portal/radiology-results/` - Get patient's radiology results
- `GET /api/v1/patient-portal/prescriptions/` - Get patient's prescriptions
- `GET /api/v1/patient-portal/medical-history/` - Get comprehensive medical history

## User Roles

- **DOCTOR**: Create consultations, orders, prescriptions; close visits
- **RECEPTIONIST**: Register patients, create visits, process payments, verify patient portal accounts
- **LAB_TECH**: View and process lab orders, create lab results
- **RADIOLOGY_TECH**: View and process radiology orders, create reports
- **PHARMACIST**: View and dispense prescriptions

## Keyboard Shortcuts

- `Ctrl+N` - Create new visit (Receptionist)
- `Ctrl+V` - View visits list
- `Ctrl+P` - View patients
- `Ctrl+D` - Go to dashboard
- `Ctrl+Shift+L` - Logout
- `Escape` - Go back

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Project Structure

```
Modern EMR/
├── backend/
│   ├── apps/
│   │   ├── users/          # Authentication & user management
│   │   ├── patients/       # Patient management
│   │   ├── visits/          # Visit management
│   │   ├── consultations/  # Consultation domain
│   │   ├── laboratory/      # Lab orders & results
│   │   ├── radiology/       # Radiology orders & results
│   │   ├── pharmacy/        # Prescriptions & dispensing
│   │   ├── billing/         # Payment processing
│   │   └── offline/         # Offline support models
│   └── core/                # Core utilities, audit, middleware
├── frontend/
│   ├── src/
│   │   ├── api/             # API clients
│   │   ├── components/      # React components
│   │   ├── contexts/        # React contexts
│   │   ├── hooks/           # Custom hooks
│   │   ├── pages/           # Page components
│   │   ├── styles/          # CSS modules
│   │   ├── types/           # TypeScript types
│   │   └── utils/           # Utility functions
│   └── public/
└── README.md
```

## Deployment

### Backend
1. Set `DEBUG=False` in `settings.py`
2. Configure `ALLOWED_HOSTS`
3. Set up PostgreSQL database
4. Run migrations
5. Collect static files: `python manage.py collectstatic`
6. Use a production WSGI server (e.g., Gunicorn)

### Frontend
1. Build for production: `npm run build`
2. Serve the `build/` directory with a web server (e.g., Nginx)

## Security Considerations

- All API endpoints require JWT authentication
- Role-based access control enforced at API level
- Payment enforcement via middleware
- Audit logging for all actions
- PHI data protection
- Account lockout mechanism
- Token blacklisting on logout

## License

[Specify your license here]

## Support

For issues or questions, please [create an issue](link-to-issues).
