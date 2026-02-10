"""
Nurse-specific API endpoints with exact URL patterns as required.

Endpoints:
- POST /api/v1/visits/{visit_id}/vitals/
- POST /api/v1/visits/{visit_id}/nursing-notes/
- POST /api/v1/visits/{visit_id}/medication-administration/
- POST /api/v1/visits/{visit_id}/lab-samples/
- GET equivalents where appropriate

All endpoints enforce:
- Visit must be OPEN (ACTIVE)
- Visit payment must be CLEARED
- Returns 409 Conflict for closed visits
- Nurse role required for creation
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError as DRFValidationError
from .models import NursingNote, MedicationAdministration, LabSampleCollection
from .serializers import (
    NursingNoteSerializer,
    NursingNoteCreateSerializer,
    MedicationAdministrationSerializer,
    MedicationAdministrationCreateSerializer,
    LabSampleCollectionSerializer,
    LabSampleCollectionCreateSerializer,
)
from .permissions import IsNurse, CanViewNursingRecords, IsVisitActiveAndPaid
from apps.visits.models import Visit
from apps.clinical.models import VitalSigns
from apps.clinical.serializers import VitalSignsSerializer, VitalSignsCreateSerializer
from apps.clinical.permissions import CanRecordVitalSigns


class NurseVitalSignsEndpoint(viewsets.ViewSet):
    """
    POST /api/v1/visits/{visit_id}/vitals/
    GET /api/v1/visits/{visit_id}/vitals/
    
    Nurse can record vital signs.
    Visit must be OPEN and payment CLEARED.
    """
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action == 'create':
            # Nurse can record vital signs (CanRecordVitalSigns allows Nurse)
            return [CanRecordVitalSigns(), IsVisitActiveAndPaid()]
        else:
            return [IsAuthenticated()]
    
    def get_visit(self):
        """Get visit from URL parameter."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        try:
            visit = Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            raise NotFound(detail=f"Visit with id {visit_id} not found.")
        
        self.request.visit = visit
        return visit
    
    def list(self, request, *args, **kwargs):
        """GET /api/v1/visits/{visit_id}/vitals/ - List vital signs."""
        try:
            visit = self.get_visit()
            vital_signs = VitalSigns.objects.filter(visit_id=visit.id).select_related(
                'visit', 'recorded_by'
            ).order_by('-recorded_at')
            
            # Serialize with error handling for each record
            vital_signs_data = []
            for vs in vital_signs:
                try:
                    serializer = VitalSignsSerializer(vs)
                    vital_signs_data.append(serializer.data)
                except Exception as e:
                    # Log error for this specific record but continue with others
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Error serializing vital signs {vs.id}: {str(e)}")
                    # Add a basic record without computed fields
                    vital_signs_data.append({
                        'id': vs.id,
                        'visit': vs.visit_id,
                        'recorded_by': vs.recorded_by_id if vs.recorded_by else None,
                        'recorded_by_name': getattr(vs.recorded_by, 'username', 'Unknown') if vs.recorded_by else 'Unknown',
                        'temperature': str(vs.temperature) if vs.temperature else None,
                        'systolic_bp': vs.systolic_bp,
                        'diastolic_bp': vs.diastolic_bp,
                        'pulse': vs.pulse,
                        'respiratory_rate': vs.respiratory_rate,
                        'oxygen_saturation': str(vs.oxygen_saturation) if vs.oxygen_saturation else None,
                        'weight': str(vs.weight) if vs.weight else None,
                        'height': str(vs.height) if vs.height else None,
                        'bmi': str(vs.bmi) if vs.bmi else None,
                        'notes': vs.notes,
                        'recorded_at': vs.recorded_at.isoformat(),
                        'abnormal_flags': [],
                    })
            
            return Response(vital_signs_data, status=status.HTTP_200_OK)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error listing vital signs for visit {kwargs.get('visit_id')}: {str(e)}", exc_info=True)
            return Response(
                {"detail": f"Error retrieving vital signs: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, *args, **kwargs):
        """POST /api/v1/visits/{visit_id}/vitals/ - Create vital signs."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Creating vital signs for visit {kwargs.get('visit_id')}, user: {request.user.username}")
            logger.debug(f"Request data: {request.data}")
            
            visit = self.get_visit()
            logger.debug(f"Visit retrieved: {visit.id}, status: {visit.status}")
            
            # Pass visit in context so serializer can check for duplicates
            serializer = VitalSignsCreateSerializer(
                data=request.data,
                context={'visit': visit, 'request': request}
            )
            
            if not serializer.is_valid():
                logger.error(f"Serializer validation failed: {serializer.errors}")
                raise DRFValidationError(serializer.errors)
            
            logger.debug("Serializer is valid, saving vital signs...")
            vital_signs = serializer.save(
                visit=visit,
                recorded_by=request.user
            )
            logger.info(f"Vital signs saved successfully with ID: {vital_signs.id}")
            
            # Check for abnormal values and create alerts
            try:
                from apps.clinical.models import ClinicalAlert
                abnormal_flags = vital_signs.get_abnormal_flags()
                if abnormal_flags:
                    for flag in abnormal_flags:
                        severity = 'CRITICAL' if flag in ['HYPOTENSION', 'HYPOXIA', 'FEVER'] else 'HIGH'
                        ClinicalAlert.objects.create(
                            visit=visit,
                            alert_type='VITAL_SIGNS',
                            severity=severity,
                            title=f"Abnormal Vital Sign: {flag}",
                            message=f"Vital signs recorded show {flag}. Please review.",
                            related_resource_type='vital_signs',
                            related_resource_id=vital_signs.id,
                        )
            except Exception as e:
                # Log but don't fail the vital signs creation if alert creation fails
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to create clinical alerts for vital signs {vital_signs.id}: {str(e)}")
            
            # Audit log - Nurse action
            try:
                from core.audit import log_nurse_action
                log_nurse_action(
                    user=request.user,
                    action='vital_signs.create',
                    visit_id=visit.id,
                    resource_type='vital_signs',
                    resource_id=vital_signs.id,
                    request=request,
                    metadata={
                        'systolic_bp': vital_signs.systolic_bp,
                        'diastolic_bp': vital_signs.diastolic_bp,
                        'pulse': vital_signs.pulse,
                        'temperature': vital_signs.temperature,
                    } if vital_signs else {}
                )
            except Exception as e:
                # Log but don't fail the vital signs creation if audit log fails
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to create audit log for vital signs {vital_signs.id}: {str(e)}")
            
            return Response(VitalSignsSerializer(vital_signs).data, status=status.HTTP_201_CREATED)
        except DRFValidationError as e:
            # Validation errors should return 400, not 500
            logger.error(f"Validation error creating vital signs: {str(e)}")
            return Response(
                {"detail": str(e), "errors": e.detail if hasattr(e, 'detail') else None},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating vital signs: {str(e)}", exc_info=True)
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Full traceback: {error_trace}")
            return Response(
                {"detail": f"Error creating vital signs: {str(e)}", "error_type": type(e).__name__},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NurseNursingNotesEndpoint(viewsets.ViewSet):
    """
    POST /api/v1/visits/{visit_id}/nursing-notes/
    GET /api/v1/visits/{visit_id}/nursing-notes/
    
    Nurse-only creation.
    Visit must be OPEN and payment CLEARED.
    """
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action == 'create':
            return [IsNurse(), IsVisitActiveAndPaid()]
        else:
            return [CanViewNursingRecords()]
    
    def get_visit(self):
        """Get visit from URL parameter."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        try:
            visit = Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            raise NotFound(detail=f"Visit with id {visit_id} not found.")
        
        self.request.visit = visit
        return visit
    
    def list(self, request, *args, **kwargs):
        """GET /api/v1/visits/{visit_id}/nursing-notes/ - List nursing notes."""
        visit = self.get_visit()
        notes = NursingNote.objects.filter(visit_id=visit.id).select_related(
            'visit', 'recorded_by'
        ).order_by('-recorded_at')
        serializer = NursingNoteSerializer(notes, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """POST /api/v1/visits/{visit_id}/nursing-notes/ - Create nursing note."""
        visit = self.get_visit()
        serializer = NursingNoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        note = serializer.save(
            visit=visit,
            recorded_by=request.user
        )
        
        # Audit log - Nurse action
        from core.audit import log_nurse_action
        log_nurse_action(
            user=request.user,
            action='nursing_note.create',
            visit_id=visit.id,
            resource_type='nursing_note',
            resource_id=note.id,
            request=request,
            metadata={
                'note_type': note.note_type,
                'patient_condition': 'recorded' if note.patient_condition else None,
            }
        )
        
        return Response(NursingNoteSerializer(note).data, status=status.HTTP_201_CREATED)


class NurseMedicationAdministrationEndpoint(viewsets.ViewSet):
    """
    POST /api/v1/visits/{visit_id}/medication-administration/
    GET /api/v1/visits/{visit_id}/medication-administration/
    
    Nurse-only creation.
    Visit must be OPEN and payment CLEARED.
    """
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action == 'create':
            return [IsNurse(), IsVisitActiveAndPaid()]
        else:
            return [CanViewNursingRecords()]
    
    def get_visit(self):
        """Get visit from URL parameter."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        try:
            visit = Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            raise NotFound(detail=f"Visit with id {visit_id} not found.")
        
        self.request.visit = visit
        return visit
    
    def list(self, request, *args, **kwargs):
        """GET /api/v1/visits/{visit_id}/medication-administration/ - List administrations."""
        visit = self.get_visit()
        administrations = MedicationAdministration.objects.filter(visit_id=visit.id).select_related(
            'visit', 'prescription', 'administered_by'
        ).order_by('-administration_time')
        serializer = MedicationAdministrationSerializer(administrations, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """POST /api/v1/visits/{visit_id}/medication-administration/ - Create administration."""
        visit = self.get_visit()
        serializer = MedicationAdministrationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Validate prescription belongs to same visit
        prescription = serializer.validated_data.get('prescription')
        if prescription and prescription.visit_id != visit.id:
            raise DRFValidationError("Prescription must belong to the same visit.")
        
        administration = serializer.save(
            visit=visit,
            administered_by=request.user
        )
        
        # Audit log - Nurse action
        from core.audit import log_nurse_action
        log_nurse_action(
            user=request.user,
            action='medication_administration.create',
            visit_id=visit.id,
            resource_type='medication_administration',
            resource_id=administration.id,
            request=request,
            metadata={
                'prescription_id': administration.prescription_id,
                'status': administration.status,
                'route': administration.route,
            }
        )
        
        return Response(MedicationAdministrationSerializer(administration).data, status=status.HTTP_201_CREATED)


class NurseLabSamplesEndpoint(viewsets.ViewSet):
    """
    POST /api/v1/visits/{visit_id}/lab-samples/
    GET /api/v1/visits/{visit_id}/lab-samples/
    
    Nurse-only creation.
    Visit must be OPEN and payment CLEARED.
    """
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action == 'create':
            return [IsNurse(), IsVisitActiveAndPaid()]
        else:
            return [CanViewNursingRecords()]
    
    def get_visit(self):
        """Get visit from URL parameter."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        try:
            visit = Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            raise NotFound(detail=f"Visit with id {visit_id} not found.")
        
        self.request.visit = visit
        return visit
    
    def list(self, request, *args, **kwargs):
        """GET /api/v1/visits/{visit_id}/lab-samples/ - List lab sample collections."""
        visit = self.get_visit()
        collections = LabSampleCollection.objects.filter(visit_id=visit.id).select_related(
            'visit', 'lab_order', 'collected_by'
        ).order_by('-collection_time')
        serializer = LabSampleCollectionSerializer(collections, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """POST /api/v1/visits/{visit_id}/lab-samples/ - Create lab sample collection."""
        visit = self.get_visit()
        serializer = LabSampleCollectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Validate lab_order belongs to same visit
        lab_order = serializer.validated_data.get('lab_order')
        if lab_order and lab_order.visit_id != visit.id:
            raise DRFValidationError("Lab order must belong to the same visit.")
        
        # Validate lab_order is in correct status
        if lab_order and lab_order.status not in ['ORDERED', 'SAMPLE_COLLECTED']:
            raise DRFValidationError("Can only collect samples for ORDERED or SAMPLE_COLLECTED lab orders.")
        
        collection = serializer.save(
            visit=visit,
            collected_by=request.user
        )
        
        # Update lab order status to SAMPLE_COLLECTED if successfully collected
        if collection.status == 'COLLECTED' and lab_order.status == 'ORDERED':
            lab_order.status = 'SAMPLE_COLLECTED'
            lab_order.save(update_fields=['status'])
        
        # Audit log - Nurse action
        from core.audit import log_nurse_action
        log_nurse_action(
            user=request.user,
            action='lab_sample_collection.create',
            visit_id=visit.id,
            resource_type='lab_sample_collection',
            resource_id=collection.id,
            request=request,
            metadata={
                'lab_order_id': collection.lab_order_id,
                'status': collection.status,
                'sample_type': collection.sample_type,
            }
        )
        
        return Response(LabSampleCollectionSerializer(collection).data, status=status.HTTP_201_CREATED)
