"""
Service Catalog API for the unified service catalog system.

Provides API endpoints for browsing, searching, and ordering services
from the ServiceCatalog model. Create/update/delete restricted to admin (is_staff).

For PHARMACY/DRUG services, includes drug availability and expiry date from DrugInventory
to help doctors make prescribing decisions.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from django.db.models import Q
from django.utils import timezone
from apps.billing.service_catalog_models import ServiceCatalog


class IsStaffOrAdminReadOnly(BasePermission):
    """Allow read for any authenticated user; allow create/update/delete for staff or role ADMIN."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        if getattr(request.user, 'is_staff', False):
            return True
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        return user_role == 'ADMIN'


def _get_drug_inventory_info(service):
    """
    Get drug availability and expiry for PHARMACY/DRUG services.
    Returns dict with drug_availability, drug_expiry_date, drug_unit, is_out_of_stock, is_low_stock.
    Returns None for non-drug services.
    """
    if service.department != 'PHARMACY' or service.category != 'DRUG':
        return None
    try:
        from apps.pharmacy.models import Drug, DrugInventory
        # Resolve Drug from ServiceCatalog: match by name (service.name = drug.name from sync)
        drug = Drug.objects.filter(name=service.name, is_active=True).first()
        if not drug:
            return {
                'drug_availability': None,
                'drug_expiry_date': None,
                'drug_unit': None,
                'is_out_of_stock': None,
                'is_low_stock': None,
            }
        # DrugInventory is OneToOne with Drug
        inv = getattr(drug, 'inventory', None)
        if not inv:
            return {
                'drug_availability': 0,
                'drug_expiry_date': None,
                'drug_unit': 'units',
                'is_out_of_stock': True,
                'is_low_stock': True,
            }
        today = timezone.now().date()
        expiry = inv.expiry_date
        is_expired = expiry is not None and expiry < today
        stock = float(inv.current_stock) if inv.current_stock is not None else 0
        return {
            'drug_availability': stock,
            'drug_expiry_date': expiry.isoformat() if expiry else None,
            'drug_unit': inv.unit or 'units',
            'is_out_of_stock': stock <= 0 or is_expired,
            'is_low_stock': stock <= float(inv.reorder_level or 0) and stock > 0,
        }
    except Exception:
        return None


class ServiceCatalogSerializer:
    """Simple serializer for ServiceCatalog (avoiding DRF ModelSerializer for simplicity)."""

    @staticmethod
    def serialize(service):
        """Convert ServiceCatalog instance to dict."""
        result = {
            'id': service.id,
            'department': service.department,
            'service_code': service.service_code,
            'name': service.name,
            'amount': str(service.amount),
            'description': service.description or '',
            'category': service.category,
            'workflow_type': service.workflow_type,
            'requires_visit': service.requires_visit,
            'requires_consultation': service.requires_consultation,
            'auto_bill': service.auto_bill,
            'bill_timing': service.bill_timing,
            'restricted_service_flag': service.restricted_service_flag,
            'allowed_roles': service.allowed_roles,
            'is_active': service.is_active,
            'created_at': service.created_at.isoformat() if service.created_at else None,
            'updated_at': service.updated_at.isoformat() if service.updated_at else None,
            'display': f"{service.department} - {service.name} ({service.service_code}) - ₦{service.amount:,.2f}",
        }
        # Add drug inventory info for PHARMACY/DRUG services
        drug_info = _get_drug_inventory_info(service)
        if drug_info:
            result.update(drug_info)
        return result


class ServiceCatalogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ServiceCatalog.
    
    Endpoints:
    - GET    /api/v1/billing/service-catalog/ - List all services (paginated)
    - POST   /api/v1/billing/service-catalog/ - Create service (admin only)
    - GET    /api/v1/billing/service-catalog/{id}/ - Get specific service
    - PUT    /api/v1/billing/service-catalog/{id}/ - Update service (admin only)
    - PATCH  /api/v1/billing/service-catalog/{id}/ - Partial update (admin only)
    - DELETE /api/v1/billing/service-catalog/{id}/ - Delete service (admin only)
    - GET    /api/v1/billing/service-catalog/choices/ - Get department/workflow choices
    """
    permission_classes = [IsAuthenticated, IsStaffOrAdminReadOnly]
    queryset = ServiceCatalog.objects.all()
    
    def list(self, request):
        """
        List all services with optional filters.
        
        Query Parameters:
        - search: Search term (searches in service_code, name, description)
        - department: Filter by department (CONSULTATION, LAB, PHARMACY, RADIOLOGY, PROCEDURE)
        - category: Filter by category
        - active_only: true/false (default: true)
        - page: Page number (default: 1)
        - page_size: Items per page (default: 50, max: 200)
        """
        queryset = self.get_queryset()
        
        # Get query parameters
        search_term = request.query_params.get('search', '').strip()
        department = request.query_params.get('department', '').strip().upper()
        category = request.query_params.get('category', '').strip().upper()
        active_only = request.query_params.get('active_only', 'true').lower() == 'true'
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 50)), 200)
        
        # Apply filters
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        if department:
            queryset = queryset.filter(department=department)
        
        if category:
            queryset = queryset.filter(category=category)
        
        if search_term:
            queryset = queryset.filter(
                Q(service_code__icontains=search_term) |
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        
        # Order by name
        queryset = queryset.order_by('name')
        
        # Manual pagination
        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        services = queryset[start:end]
        
        # Serialize
        results = [ServiceCatalogSerializer.serialize(s) for s in services]
        
        return Response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'results': results,
        })
    
    def retrieve(self, request, pk=None):
        """Get a specific service by ID."""
        try:
            service = self.get_queryset().get(pk=pk)
            return Response(ServiceCatalogSerializer.serialize(service))
        except ServiceCatalog.DoesNotExist:
            return Response(
                {'error': f'Service with ID {pk} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Quick search endpoint for autocomplete/dropdown.
        
        Query Parameters:
        - q: Search query (required)
        - limit: Maximum results (default: 20, max: 50)
        - department: Filter by department (optional)
        - category: Filter by category (optional)
        
        Returns results sorted by relevance and name.
        """
        query = request.query_params.get('q', '').strip()
        limit = min(int(request.query_params.get('limit', 20)), 50)
        department = request.query_params.get('department', '').strip().upper()
        category = request.query_params.get('category', '').strip().upper()
        
        if not query:
            return Response({'results': []})
        
        queryset = self.get_queryset().filter(is_active=True)
        
        # Apply department filter
        if department:
            queryset = queryset.filter(department=department)
        
        # Apply category filter
        if category:
            queryset = queryset.filter(category=category)
        
        # Apply search
        queryset = queryset.filter(
            Q(service_code__icontains=query) |
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).order_by('name')[:limit]
        
        results = [ServiceCatalogSerializer.serialize(s) for s in queryset]
        
        return Response({'results': results})
    
    @action(detail=False, methods=['get'])
    def by_department(self, request):
        """
        Get services grouped by department.
        
        Query Parameters:
        - department: Department code (required)
        - active_only: true/false (default: true)
        """
        department = request.query_params.get('department', '').strip().upper()
        active_only = request.query_params.get('active_only', 'true').lower() == 'true'
        
        if not department:
            return Response(
                {'error': 'department parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(department=department)
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        queryset = queryset.order_by('name')
        
        results = [ServiceCatalogSerializer.serialize(s) for s in queryset]
        
        return Response({
            'department': department,
            'count': len(results),
            'services': results,
        })
    
    @action(detail=False, methods=['get'])
    def departments(self, request):
        """
        Get list of available departments with service counts.
        """
        departments = ServiceCatalog.objects.values('department').distinct()
        
        result = []
        for dept in departments:
            dept_name = dept['department']
            count = ServiceCatalog.objects.filter(
                department=dept_name,
                is_active=True
            ).count()
            
            result.append({
                'code': dept_name,
                'name': dict(ServiceCatalog.DEPARTMENT_CHOICES).get(dept_name, dept_name),
                'count': count,
            })
        
        return Response({'departments': result})
    
    @action(detail=False, methods=['get'], url_path='choices')
    def choices(self, request):
        """
        Get choices for department, category, and workflow_type (for admin forms).
        """
        return Response({
            'departments': [{'value': c[0], 'label': c[1]} for c in ServiceCatalog.DEPARTMENT_CHOICES],
            'categories': [{'value': c[0], 'label': c[1]} for c in ServiceCatalog.CATEGORY_CHOICES],
            'workflow_types': [{'value': c[0], 'label': c[1]} for c in ServiceCatalog.WORKFLOW_TYPE_CHOICES],
            'bill_timing': [{'value': c[0], 'label': c[1]} for c in ServiceCatalog.BILL_TIMING_CHOICES],
        })
    
    def _department_default_category(self, department):
        """Default category for a department."""
        m = {
            'CONSULTATION': 'CONSULTATION',
            'LAB': 'LAB',
            'PHARMACY': 'DRUG',
            'RADIOLOGY': 'RADIOLOGY',
            'PROCEDURE': 'PROCEDURE',
        }
        return m.get(department, 'CONSULTATION')
    
    def _parse_request_data(self, data, instance=None):
        """Parse and validate request body for create/update. Returns dict for model."""
        department = (data.get('department') or (instance.department if instance else '')).strip().upper()
        service_code = (data.get('service_code') or (instance.service_code if instance else '')).strip()
        name = (data.get('name') or (instance.name if instance else '')).strip()
        amount = data.get('amount')
        if amount is not None:
            try:
                amount = str(amount).strip()
                amount = round(float(amount), 2) if amount else None
            except (TypeError, ValueError):
                amount = None
        if instance and amount is None:
            amount = float(instance.amount)
        if not service_code:
            raise ValueError("Service code is required.")
        if not name:
            raise ValueError("Name is required.")
        if amount is None or amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        
        category = (data.get('category') or '').strip().upper() or self._department_default_category(department)
        workflow_type = (data.get('workflow_type') or (instance.workflow_type if instance else 'OTHER')).strip().upper()
        if not workflow_type:
            workflow_type = 'OTHER'
        
        allowed_roles = data.get('allowed_roles')
        if allowed_roles is None and instance:
            allowed_roles = instance.allowed_roles
        if not allowed_roles or not isinstance(allowed_roles, list):
            allowed_roles = ['ADMIN', 'RECEPTIONIST']
        
        return {
            'department': department,
            'service_code': service_code,
            'name': name,
            'amount': amount,
            'description': (data.get('description') or (instance.description if instance else '') or '')[:5000],
            'category': category,
            'workflow_type': workflow_type,
            'requires_visit': data.get('requires_visit', True if not instance else instance.requires_visit),
            'requires_consultation': data.get('requires_consultation', False if not instance else instance.requires_consultation),
            'auto_bill': data.get('auto_bill', True if not instance else instance.auto_bill),
            'bill_timing': (data.get('bill_timing') or (instance.bill_timing if instance else 'AFTER')).strip() or 'AFTER',
            'restricted_service_flag': data.get('restricted_service_flag', False if not instance else instance.restricted_service_flag),
            'allowed_roles': allowed_roles,
            'is_active': data.get('is_active', True if not instance else instance.is_active),
        }
    
    def create(self, request):
        """Create a new service (admin only)."""
        try:
            data = self._parse_request_data(request.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        if ServiceCatalog.objects.filter(service_code=data['service_code']).exists():
            return Response(
                {'error': f"A service with code '{data['service_code']}' already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            service = ServiceCatalog.objects.create(**data)
            return Response(ServiceCatalogSerializer.serialize(service), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, pk=None):
        """Full update (admin only)."""
        try:
            service = self.get_queryset().get(pk=pk)
        except ServiceCatalog.DoesNotExist:
            return Response({'error': 'Service not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            data = self._parse_request_data(request.data, instance=service)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        other = ServiceCatalog.objects.filter(service_code=data['service_code']).exclude(pk=pk).first()
        if other:
            return Response(
                {'error': f"A service with code '{data['service_code']}' already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
        for key, value in data.items():
            setattr(service, key, value)
        try:
            service.save()
            return Response(ServiceCatalogSerializer.serialize(service))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None):
        """Partial update (admin only)."""
        try:
            service = self.get_queryset().get(pk=pk)
        except ServiceCatalog.DoesNotExist:
            return Response({'error': 'Service not found.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            data = self._parse_request_data(request.data, instance=service)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        other = ServiceCatalog.objects.filter(service_code=data['service_code']).exclude(pk=pk).first()
        if other:
            return Response(
                {'error': f"A service with code '{data['service_code']}' already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
        for key, value in data.items():
            setattr(service, key, value)
        try:
            service.save()
            return Response(ServiceCatalogSerializer.serialize(service))
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        """Delete a service (admin only)."""
        try:
            service = self.get_queryset().get(pk=pk)
        except ServiceCatalog.DoesNotExist:
            return Response({'error': 'Service not found.'}, status=status.HTTP_404_NOT_FOUND)
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)