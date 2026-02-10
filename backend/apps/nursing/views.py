"""
Views for nursing models.

Per EMR Rules:
- Visit-scoped endpoints
- Nurse-only creation
- Doctor and Nurse can view
- Immutable records after creation
- No diagnosis fields
"""
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError as DRFValidationError
from core.permissions import IsVisitOpen, IsVisitAccessible
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


class NursingNoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Nursing Notes.
    
    Rules enforced:
    - Visit-scoped
    - Nurse-only creation
    - Doctor and Nurse can view
    - Immutable after creation (no updates/deletes)
    """
    serializer_class = NursingNoteSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return [IsNurse(), IsVisitActiveAndPaid()]
        elif self.action == 'destroy':
            # Deletion not allowed - maintain audit trail
            return [IsAuthenticated()]
        else:
            # Read operations: Doctor and Nurse can view
            return [CanViewNursingRecords(), IsVisitAccessible()]
    
    def get_visit(self):
        """Get visit from middleware or URL parameter."""
        if hasattr(self.request, 'visit') and self.request.visit:
            return self.request.visit
        
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        try:
            visit = Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            raise NotFound(detail=f"Visit with id {visit_id} not found.")
        
        self.request.visit = visit
        return visit
    
    def get_queryset(self):
        """Get nursing notes for the visit."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return NursingNote.objects.none()
        
        return NursingNote.objects.filter(visit_id=visit_id).select_related(
            'visit', 'recorded_by'
        ).order_by('-recorded_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return NursingNoteCreateSerializer
        return NursingNoteSerializer
    
    def merge_with_patient_history(self, note, visit):
        """
        Merge nursing note into patient's medical history.
        
        This appends the nursing note to the patient's ongoing
        medical history record, creating a cumulative patient record.
        """
        from django.utils import timezone
        
        patient = visit.patient
        if not patient:
            return
        
        # Use note's recorded_at timestamp, or current time if not set
        timestamp = note.recorded_at if note.recorded_at else timezone.now()
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M')
        
        # Build nursing note entry with visit context
        note_entry = []
        note_entry.append(f"\n{'='*60}")
        note_entry.append(f"NURSING NOTE - Visit #{visit.id} - {timestamp_str}")
        note_entry.append(f"{'='*60}")
        note_entry.append(f"Note Type: {note.get_note_type_display()}")
        
        if note.note_content:
            note_entry.append(f"\nNOTE CONTENT:")
            note_entry.append(note.note_content)
        
        if note.patient_condition:
            note_entry.append(f"\nPATIENT CONDITION:")
            note_entry.append(note.patient_condition)
        
        if note.care_provided:
            note_entry.append(f"\nCARE PROVIDED:")
            note_entry.append(note.care_provided)
        
        if note.patient_response:
            note_entry.append(f"\nPATIENT RESPONSE:")
            note_entry.append(note.patient_response)
        
        note_entry.append(f"\nRecorded by: {note.recorded_by.get_full_name()}")
        note_entry.append(f"{'='*60}\n")
        
        # Append to patient's medical history
        new_entry = "\n".join(note_entry)
        if patient.medical_history:
            patient.medical_history += new_entry
        else:
            patient.medical_history = new_entry
        
        # Save patient (this updates the medical_history field)
        patient.save(update_fields=['medical_history'])
    
    def perform_create(self, serializer):
        """Create nursing note."""
        visit = self.get_visit()
        
        # Extract merge flag before saving (it's write_only, won't be saved to model)
        merge_with_patient = serializer.validated_data.pop('merge_with_patient_record', False)
        
        # Permissions already checked by IsVisitActiveAndPaid
        # Set visit and recorded_by
        note = serializer.save(
            visit=visit,
            recorded_by=self.request.user
        )
        
        # Merge with patient medical history if requested
        if merge_with_patient:
            self.merge_with_patient_history(note, visit)
        
        # Audit log - Nurse action
        from core.audit import log_nurse_action
        log_nurse_action(
            user=self.request.user,
            action='nursing_note.create',
            visit_id=visit.id,
            resource_type='nursing_note',
            resource_id=note.id,
            request=self.request,
            metadata={
                'note_type': note.note_type,
                'merged_with_patient_record': merge_with_patient,
            }
        )
    
    def perform_update(self, serializer):
        """Update nursing note."""
        note = self.get_object()
        visit = note.visit
        
        # Extract merge flag before saving
        merge_with_patient = serializer.validated_data.pop('merge_with_patient_record', False)
        
        # Update the note
        updated_note = serializer.save()
        
        # Merge with patient medical history if requested
        if merge_with_patient:
            self.merge_with_patient_history(updated_note, visit)
        
        # Audit log - Nurse action
        from core.audit import log_nurse_action
        log_nurse_action(
            user=self.request.user,
            action='nursing_note.update',
            visit_id=visit.id,
            resource_type='nursing_note',
            resource_id=updated_note.id,
            request=self.request,
            metadata={
                'note_type': updated_note.note_type,
                'merged_with_patient_record': merge_with_patient,
            }
        )
    
    def destroy(self, request, *args, **kwargs):
        """Prevent deletion - maintain audit trail."""
        raise PermissionDenied("Nursing notes cannot be deleted to maintain audit trail. Records are permanent.")


class MedicationAdministrationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Medication Administration.
    
    Rules enforced:
    - Visit-scoped
    - Requires existing Prescription
    - Nurse-only creation and updates
    - Doctor and Nurse can view
    - Can be updated (removed immutability)
    """
    serializer_class = MedicationAdministrationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return [IsNurse(), IsVisitActiveAndPaid()]
        elif self.action == 'destroy':
            # Deletion not allowed - maintain audit trail
            return [IsAuthenticated()]
        else:
            # Read operations: Doctor and Nurse can view
            return [CanViewNursingRecords(), IsVisitAccessible()]
    
    def get_visit(self):
        """Get visit from middleware or URL parameter."""
        if hasattr(self.request, 'visit') and self.request.visit:
            return self.request.visit
        
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        try:
            visit = Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            raise NotFound(detail=f"Visit with id {visit_id} not found.")
        
        self.request.visit = visit
        return visit
    
    def get_queryset(self):
        """Get medication administrations for the visit."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return MedicationAdministration.objects.none()
        
        return MedicationAdministration.objects.filter(visit_id=visit_id).select_related(
            'visit', 'prescription', 'administered_by'
        ).order_by('-administration_time')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return MedicationAdministrationCreateSerializer
        return MedicationAdministrationSerializer
    
    def merge_with_patient_history(self, administration, visit):
        """
        Merge medication administration into patient's medical history.
        """
        from django.utils import timezone
        
        patient = visit.patient
        if not patient:
            return
        
        timestamp = administration.administration_time if administration.administration_time else timezone.now()
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M')
        
        entry = []
        entry.append(f"\n{'='*60}")
        entry.append(f"MEDICATION ADMINISTRATION - Visit #{visit.id} - {timestamp_str}")
        entry.append(f"{'='*60}")
        entry.append(f"Medication: {administration.prescription.drug}")
        entry.append(f"Dose Administered: {administration.dose_administered}")
        entry.append(f"Route: {administration.get_route_display()}")
        entry.append(f"Status: {administration.get_status_display()}")
        
        if administration.site:
            entry.append(f"Site: {administration.site}")
        
        if administration.administration_notes:
            entry.append(f"\nNOTES:")
            entry.append(administration.administration_notes)
        
        if administration.reason_if_held:
            entry.append(f"\nREASON IF HELD:")
            entry.append(administration.reason_if_held)
        
        entry.append(f"\nAdministered by: {administration.administered_by.get_full_name()}")
        entry.append(f"{'='*60}\n")
        
        new_entry = "\n".join(entry)
        if patient.medical_history:
            patient.medical_history += new_entry
        else:
            patient.medical_history = new_entry
        
        patient.save(update_fields=['medical_history'])
    
    def perform_create(self, serializer):
        """Create medication administration record."""
        visit = self.get_visit()
        
        # Extract merge flag before saving
        merge_with_patient = serializer.validated_data.pop('merge_with_patient_record', False)
        
        # Permissions already checked by IsVisitActiveAndPaid
        # Validate prescription belongs to same visit
        prescription = serializer.validated_data.get('prescription')
        if prescription and prescription.visit_id != visit.id:
            raise DRFValidationError("Prescription must belong to the same visit.")
        
        # Set visit and administered_by
        administration = serializer.save(
            visit=visit,
            administered_by=self.request.user
        )
        
        # Merge with patient medical history if requested
        if merge_with_patient:
            self.merge_with_patient_history(administration, visit)
        
        # Audit log - Nurse action
        from core.audit import log_nurse_action
        log_nurse_action(
            user=self.request.user,
            action='medication_administration.create',
            visit_id=visit.id,
            resource_type='medication_administration',
            resource_id=administration.id,
            request=self.request,
            metadata={
                'prescription_id': administration.prescription_id,
                'status': administration.status,
                'route': administration.route,
                'merged_with_patient_record': merge_with_patient,
            }
        )
    
    def perform_update(self, serializer):
        """Update medication administration record."""
        administration = self.get_object()
        visit = administration.visit
        
        # Extract merge flag before saving
        merge_with_patient = serializer.validated_data.pop('merge_with_patient_record', False)
        
        # Update the administration
        updated_administration = serializer.save()
        
        # Merge with patient medical history if requested
        if merge_with_patient:
            self.merge_with_patient_history(updated_administration, visit)
        
        # Audit log - Nurse action
        from core.audit import log_nurse_action
        log_nurse_action(
            user=self.request.user,
            action='medication_administration.update',
            visit_id=visit.id,
            resource_type='medication_administration',
            resource_id=updated_administration.id,
            request=self.request,
            metadata={
                'prescription_id': updated_administration.prescription_id,
                'status': updated_administration.status,
                'merged_with_patient_record': merge_with_patient,
            }
        )
    
    def destroy(self, request, *args, **kwargs):
        """Prevent deletion - maintain audit trail."""
        raise PermissionDenied("Medication administration records cannot be deleted to maintain audit trail. Records are permanent.")


class LabSampleCollectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Lab Sample Collection.
    
    Rules enforced:
    - Visit-scoped
    - Requires existing LabOrder
    - Nurse-only creation and updates
    - Doctor and Nurse can view
    - Can be updated (removed immutability)
    """
    serializer_class = LabSampleCollectionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return [IsNurse(), IsVisitActiveAndPaid()]
        elif self.action == 'destroy':
            # Deletion not allowed - maintain audit trail
            return [IsAuthenticated()]
        else:
            # Read operations: Doctor and Nurse can view
            return [CanViewNursingRecords(), IsVisitAccessible()]
    
    def get_visit(self):
        """Get visit from middleware or URL parameter."""
        if hasattr(self.request, 'visit') and self.request.visit:
            return self.request.visit
        
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        try:
            visit = Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            raise NotFound(detail=f"Visit with id {visit_id} not found.")
        
        self.request.visit = visit
        return visit
    
    def get_queryset(self):
        """Get lab sample collections for the visit."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return LabSampleCollection.objects.none()
        
        return LabSampleCollection.objects.filter(visit_id=visit_id).select_related(
            'visit', 'lab_order', 'collected_by'
        ).order_by('-collection_time')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return LabSampleCollectionCreateSerializer
        return LabSampleCollectionSerializer
    
    def merge_with_patient_history(self, collection, visit):
        """
        Merge lab sample collection into patient's medical history.
        """
        from django.utils import timezone
        
        patient = visit.patient
        if not patient:
            return
        
        timestamp = collection.collection_time if collection.collection_time else timezone.now()
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M')
        
        entry = []
        entry.append(f"\n{'='*60}")
        entry.append(f"LAB SAMPLE COLLECTION - Visit #{visit.id} - {timestamp_str}")
        entry.append(f"{'='*60}")
        entry.append(f"Sample Type: {collection.sample_type}")
        entry.append(f"Status: {collection.get_status_display()}")
        
        if collection.collection_site:
            entry.append(f"Collection Site: {collection.collection_site}")
        
        if collection.sample_volume:
            entry.append(f"Sample Volume: {collection.sample_volume}")
        
        if collection.container_type:
            entry.append(f"Container Type: {collection.container_type}")
        
        if collection.collection_notes:
            entry.append(f"\nNOTES:")
            entry.append(collection.collection_notes)
        
        if collection.reason_if_failed:
            entry.append(f"\nREASON IF FAILED:")
            entry.append(collection.reason_if_failed)
        
        # Get lab order tests
        if collection.lab_order and collection.lab_order.tests_requested:
            tests = collection.lab_order.tests_requested
            if isinstance(tests, list):
                entry.append(f"\nTests: {', '.join(tests)}")
        
        entry.append(f"\nCollected by: {collection.collected_by.get_full_name()}")
        entry.append(f"{'='*60}\n")
        
        new_entry = "\n".join(entry)
        if patient.medical_history:
            patient.medical_history += new_entry
        else:
            patient.medical_history = new_entry
        
        patient.save(update_fields=['medical_history'])
    
    def perform_create(self, serializer):
        """Create lab sample collection record."""
        visit = self.get_visit()
        
        # Extract merge flag before saving
        merge_with_patient = serializer.validated_data.pop('merge_with_patient_record', False)
        
        # Permissions already checked by IsVisitActiveAndPaid
        # Validate lab_order belongs to same visit
        lab_order = serializer.validated_data.get('lab_order')
        if lab_order and lab_order.visit_id != visit.id:
            raise DRFValidationError("Lab order must belong to the same visit.")
        
        # Validate lab_order is in correct status
        if lab_order and lab_order.status not in ['ORDERED', 'SAMPLE_COLLECTED']:
            raise DRFValidationError("Can only collect samples for ORDERED or SAMPLE_COLLECTED lab orders.")
        
        # Set visit and collected_by
        collection = serializer.save(
            visit=visit,
            collected_by=self.request.user
        )
        
        # Update lab order status to SAMPLE_COLLECTED if successfully collected
        if collection.status == 'COLLECTED' and lab_order.status == 'ORDERED':
            lab_order.status = 'SAMPLE_COLLECTED'
            lab_order.save(update_fields=['status'])
        
        # Merge with patient medical history if requested
        if merge_with_patient:
            self.merge_with_patient_history(collection, visit)
        
        # Audit log - Nurse action
        from core.audit import log_nurse_action
        log_nurse_action(
            user=self.request.user,
            action='lab_sample_collection.create',
            visit_id=visit.id,
            resource_type='lab_sample_collection',
            resource_id=collection.id,
            request=self.request,
            metadata={
                'lab_order_id': collection.lab_order_id,
                'status': collection.status,
                'sample_type': collection.sample_type,
                'merged_with_patient_record': merge_with_patient,
            }
        )
    
    def perform_update(self, serializer):
        """Update lab sample collection record."""
        collection = self.get_object()
        visit = collection.visit
        
        # Extract merge flag before saving
        merge_with_patient = serializer.validated_data.pop('merge_with_patient_record', False)
        
        # Update the collection
        updated_collection = serializer.save()
        
        # Merge with patient medical history if requested
        if merge_with_patient:
            self.merge_with_patient_history(updated_collection, visit)
        
        # Audit log - Nurse action
        from core.audit import log_nurse_action
        log_nurse_action(
            user=self.request.user,
            action='lab_sample_collection.update',
            visit_id=visit.id,
            resource_type='lab_sample_collection',
            resource_id=updated_collection.id,
            request=self.request,
            metadata={
                'lab_order_id': updated_collection.lab_order_id,
                'status': updated_collection.status,
                'merged_with_patient_record': merge_with_patient,
            }
        )
    
    def destroy(self, request, *args, **kwargs):
        """Prevent deletion - maintain audit trail."""
        raise PermissionDenied("Lab sample collection records cannot be deleted to maintain audit trail. Records are permanent.")

