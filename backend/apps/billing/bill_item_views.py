"""
API endpoints for adding bill items.

Per EMR Rules:
- Validate visit is OPEN
- Validate consultation exists (for consultation-dependent services)
- Create appropriate workflow object (Prescription, LabOrder, etc.)
- Create BillingLineItem
- Attach to visit
- Mark as UNPAID or INSURANCE
- Prices fetched automatically from ServiceCatalog
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import (
    NotFound,
    ValidationError as DRFValidationError,
    PermissionDenied
)
from django.core.exceptions import ValidationError
from decimal import Decimal

from apps.visits.models import Visit
from apps.consultations.models import Consultation
from apps.billing.service_catalog_models import ServiceCatalog
from apps.visits.downstream_service_workflow import order_downstream_service
from apps.billing.billing_line_item_service import create_billing_line_item_from_service
from apps.consultations.gopd_workflow_service import initiate_gopd_consultation_workflow
from .permissions import CanAddServicesFromCatalog
from core.audit import AuditLog


class AddBillItemView(APIView):
    """
    POST /api/billing/add-item/
    
    Add a bill item to a visit's bill.
    
    Payload:
    {
        "visit_id": 1,
        "department": "LAB",
        "service_code": "CBC-001"
    }
    
    Behavior:
    - Validate visit is OPEN
    - Fetch price from price list
    - Create BillItem
    - Attach to visit bill
    - Mark item as UNPAID or INSURANCE (based on visit payment_type)
    
    Permissions:
    - Receptionist: Can add services from catalog (billing workflow)
    - Doctor: Can order services from catalog (clinical workflow)
    - Services added by doctors will reflect in patient's account in Receptionist dashboard
    """
    permission_classes = [IsAuthenticated, CanAddServicesFromCatalog]
    
    def post(self, request):
        """
        Add service to visit using NEW ServiceCatalog system.
        
        This creates:
        1. Appropriate workflow object (Prescription, LabOrder, RadiologyRequest, ProcedureTask)
        2. BillingLineItem for billing
        
        Validates:
        1. Visit exists and is OPEN
        2. Service exists in ServiceCatalog
        3. User has permission
        4. Consultation exists (if service requires it)
        
        Note: This endpoint now uses the Service-Driven EMR architecture.
        Services automatically create the correct workflow objects and billing.
        """
        try:
            visit_id = request.data.get('visit_id')
            department = request.data.get('department')
            service_code = request.data.get('service_code')
            
            # Validate required fields
            if not visit_id:
                raise DRFValidationError("visit_id is required.")
            
            if not service_code:
                raise DRFValidationError("service_code is required.")
            
            # Convert visit_id to integer if it's a string
            try:
                visit_id = int(visit_id)
            except (ValueError, TypeError):
                raise DRFValidationError(f"visit_id must be a valid integer. Got: {visit_id}")
            
            # Validate visit exists and is OPEN
            try:
                visit = Visit.objects.get(id=visit_id)
            except Visit.DoesNotExist:
                raise NotFound(f"Visit with id {visit_id} not found.")
            
            if visit.status != 'OPEN':
                raise DRFValidationError(
                    f"Cannot add services to a {visit.status} visit. Visit must be OPEN."
                )
            
            # Get service from ServiceCatalog
            try:
                service = ServiceCatalog.objects.get(
                    service_code=service_code,
                    is_active=True
                )
            except ServiceCatalog.DoesNotExist:
                raise NotFound(
                    f"Service with code '{service_code}' not found in ServiceCatalog or is inactive."
                )
        
            # Check if this is a consultation service (GOPD_CONSULT)
            # Consultation services create consultations, they don't require existing ones
            is_consultation_service = (
                service.workflow_type == 'GOPD_CONSULT' or
                service.department == 'CONSULTATION' or
                service.service_code.upper().startswith('CONS-') or
                'FOLLOW UP' in (service.name or '').upper() or
                'FOLLOW-UP' in (service.name or '').upper() or
                'FOLLOWUP' in (service.name or '').upper() or
                'CONSULTATION' in (service.name or '').upper() or
                'CONSULT' in (service.name or '').upper()
            )
            
            # Handle consultation services differently - they create consultations
            if is_consultation_service:
                # For consultation services, create a Consultation if one doesn't exist
                try:
                    # Check if consultation already exists (check all statuses first)
                    consultation = Consultation.objects.filter(visit=visit).first()
                    
                    # If consultation exists but is CLOSED, we might want to create a new one
                    # For now, use existing consultation regardless of status
                    if consultation and consultation.status == 'CLOSED':
                        # Don't create a new consultation if one exists (even if closed)
                        # The downstream services will handle this appropriately
                        pass
                    
                    # If no consultation exists, create one
                    if not consultation:
                        # Determine consultation status and created_by based on user role
                        is_doctor = request.user.role == 'DOCTOR'
                        consultation_status = 'ACTIVE' if is_doctor else 'PENDING'
                        consultation_created_by = request.user if is_doctor else None
                        
                        # If service has GOPD_CONSULT workflow_type, use the GOPD workflow service
                        if service.workflow_type == 'GOPD_CONSULT':
                            try:
                                _, consultation, consultation_created = initiate_gopd_consultation_workflow(
                                    patient=visit.patient,
                                    service=service,
                                    user=request.user,
                                    payment_type='CASH',  # Default, can be enhanced later
                                    chief_complaint=None,
                                )
                                # If consultation wasn't created (e.g., bill_timing=BEFORE and payment not cleared),
                                # create one anyway for billing purposes
                                if not consultation:
                                    consultation = Consultation.objects.create(
                                        visit=visit,
                                        created_by=consultation_created_by,
                                        status=consultation_status,
                                    )
                            except ValidationError as e:
                                # If GOPD workflow fails (e.g., consultation already exists), try to get it
                                consultation = Consultation.objects.filter(visit=visit).first()
                                if not consultation:
                                    # Create basic consultation if still doesn't exist
                                    consultation = Consultation.objects.create(
                                        visit=visit,
                                        created_by=consultation_created_by,
                                        status=consultation_status,
                                    )
                        else:
                            # For consultation services without GOPD_CONSULT workflow_type,
                            # create a basic consultation
                            consultation = Consultation.objects.create(
                                visit=visit,
                                created_by=consultation_created_by,
                                status=consultation_status,
                            )
                    
                    # Ensure consultation is ACTIVE or PENDING for downstream services
                    # Only set to ACTIVE if we have a doctor assigned
                    if consultation.status == 'CLOSED':
                        if consultation.created_by:
                            consultation.status = 'ACTIVE'
                            consultation.save(update_fields=['status'])
                        else:
                            # If no doctor assigned, set to PENDING
                            consultation.status = 'PENDING'
                            consultation.save(update_fields=['status'])
                    
                    # Create billing line item and link to consultation
                    # Only link consultation if service is GOPD_CONSULT (per validation rules)
                    consultation_to_link = consultation if service.workflow_type == 'GOPD_CONSULT' else None
                    billing_line_item = create_billing_line_item_from_service(
                        service=service,
                        visit=visit,
                        consultation=consultation_to_link,
                        created_by=request.user,
                    )
                    domain_object = consultation  # Return consultation as domain object
                except ValidationError as e:
                    raise DRFValidationError(str(e))
            else:
                # For downstream services (LAB, PHARMACY, PROCEDURE, RADIOLOGY), use downstream workflow
                # Get consultation if service requires it
                consultation = None
                if service.requires_consultation:
                    # First check for any consultation on this visit (regardless of status)
                    consultation = Consultation.objects.filter(visit=visit).first()
                    
                    # If consultation exists but is CLOSED, reactivate it
                    # Only if we have a doctor assigned, otherwise set to PENDING
                    if consultation and consultation.status == 'CLOSED':
                        if consultation.created_by:
                            consultation.status = 'ACTIVE'
                            consultation.save(update_fields=['status'])
                        else:
                            # If no doctor assigned, set to PENDING
                            consultation.status = 'PENDING'
                            consultation.save(update_fields=['status'])
                    
                    # If no consultation exists, try to find one with PENDING or ACTIVE status
                    if not consultation:
                        consultation = Consultation.objects.filter(
                            visit=visit,
                            status__in=['PENDING', 'ACTIVE']
                        ).first()
                    
                    # If still no consultation exists, create one automatically
                    # This ensures downstream services can always be ordered
                    if not consultation:
                        # Determine consultation status and created_by based on user role
                        is_doctor = request.user.role == 'DOCTOR'
                        consultation_status = 'ACTIVE' if is_doctor else 'PENDING'
                        consultation_created_by = request.user if is_doctor else None
                        
                        consultation = Consultation.objects.create(
                            visit=visit,
                            created_by=consultation_created_by,
                            status=consultation_status,
                        )
                    else:
                        # Auto-activate PENDING consultation when first service is ordered
                        # Only if we have a doctor assigned
                        if consultation.status == 'PENDING' and consultation.created_by:
                            consultation.status = 'ACTIVE'
                            consultation.save(update_fields=['status'])
                        # If consultation is PENDING and no doctor assigned, try to assign current user if they're a doctor
                        elif consultation.status == 'PENDING' and not consultation.created_by and request.user.role == 'DOCTOR':
                            consultation.created_by = request.user
                            consultation.status = 'ACTIVE'
                            consultation.save(update_fields=['created_by', 'status'])
                
                # Order the service using the downstream workflow system
                # This will create the appropriate object (Prescription, LabOrder, etc.) and billing
                try:
                    domain_object, billing_line_item = order_downstream_service(
                        service=service,
                        visit=visit,
                        consultation=consultation,
                        user=request.user,
                        additional_data=request.data.get('additional_data', {})
                    )
                except ValidationError as e:
                    raise DRFValidationError(str(e))
                except Exception as e:
                    # Catch any other exceptions and provide a more informative error
                    import traceback
                    error_trace = traceback.format_exc()
                    raise DRFValidationError(
                        f"Failed to order service '{service.service_code}': {str(e)}. "
                        f"Please check the service configuration and try again."
                    )
            
            # Validate that we have the required objects
            if not billing_line_item:
                raise DRFValidationError(
                    f"Failed to create billing line item for service '{service.service_code}'. "
                    "Please try again or contact support."
                )
            
            # Audit log (with error handling)
            try:
                user_role = getattr(request.user, 'role', None)
                AuditLog.log(
                    user=request.user,
                    role=user_role,
                    action="SERVICE_ORDERED",
                    visit_id=visit.id,
                    resource_type="service_order",
                    resource_id=getattr(domain_object, 'id', None) if domain_object else None,
                    request=request,
                    metadata={
                        'department': service.department,
                        'service_code': service.service_code,
                        'service_name': service.name,
                        'workflow_type': service.workflow_type,
                        'amount': str(service.amount),
                        'domain_object_type': type(domain_object).__name__ if domain_object else None,
                    }
                )
            except Exception as e:
                # Log audit failure but don't fail the request
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create audit log for service order: {e}")
            
            # Return response with details (with safe attribute access)
            return Response(
                {
                    'id': getattr(billing_line_item, 'id', None),
                    'visit_id': visit.id,
                    'department': service.department,
                    'service_code': service.service_code,
                    'service_name': service.name,
                    'amount': str(service.amount),
                    'workflow_type': service.workflow_type,
                    'domain_object_id': getattr(domain_object, 'id', None) if domain_object else None,
                    'domain_object_type': type(domain_object).__name__ if domain_object else None,
                    'billing_line_item_id': getattr(billing_line_item, 'id', None),
                    'bill_status': getattr(billing_line_item, 'bill_status', None),
                    'created_at': billing_line_item.created_at.isoformat() if billing_line_item and hasattr(billing_line_item, 'created_at') else None,
                },
                status=status.HTTP_201_CREATED
            )
        except DRFValidationError:
            # Re-raise DRF validation errors as-is
            raise
        except Exception as e:
            # Catch any other unexpected exceptions and return a 500 with details
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            error_trace = traceback.format_exc()
            logger.error(f"Unexpected error in AddBillItemView: {e}\n{error_trace}")
            raise DRFValidationError(
                f"An unexpected error occurred while adding the service: {str(e)}. "
                "Please try again or contact support if the problem persists."
            )


class ListServicesView(APIView):
    """
    GET /api/billing/services/?department=LAB
    
    List all services for a department from price list.
    
    Query Parameters:
    - department: LAB, PHARMACY, RADIOLOGY, or PROCEDURE
    - active_only: true/false (default: true)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List services for a department."""
        department = request.query_params.get('department')
        active_only = request.query_params.get('active_only', 'true').lower() == 'true'
        
        if not department:
            raise DRFValidationError("department query parameter is required.")
        
        try:
            services = ServicePriceListManager.list_services(
                department=department,
                active_only=active_only
            )
        except ValidationError as e:
            raise DRFValidationError(str(e))
        
        return Response(
            {
                'department': department.upper(),
                'count': len(services),
                'services': services,
            },
            status=status.HTTP_200_OK
        )


class GetServicePriceView(APIView):
    """
    GET /api/billing/service-price/?department=LAB&service_code=CBC-001
    
    Get price for a specific service.
    
    Query Parameters:
    - department: LAB, PHARMACY, RADIOLOGY, or PROCEDURE
    - service_code: Service code/identifier
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get service price."""
        department = request.query_params.get('department')
        service_code = request.query_params.get('service_code')
        
        if not department:
            raise DRFValidationError("department query parameter is required.")
        
        if not service_code:
            raise DRFValidationError("service_code query parameter is required.")
        
        try:
            service_info = ServicePriceListManager.get_price(department, service_code)
        except ValidationError as e:
            raise DRFValidationError(str(e))
        
        return Response(service_info, status=status.HTTP_200_OK)

