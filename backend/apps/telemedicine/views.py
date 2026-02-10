"""
Telemedicine ViewSet - video consultation management.

Endpoint: /api/v1/telemedicine/

Enforcement:
1. Doctor-only access for creating sessions
2. Visit-scoped architecture
3. Audit logging mandatory
4. Twilio Video integration
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
    NotFound,
)
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse
from django.conf import settings
import uuid
import logging

logger = logging.getLogger(__name__)

from .models import TelemedicineSession, TelemedicineParticipant
from .serializers import (
    TelemedicineSessionSerializer,
    TelemedicineSessionCreateSerializer,
    TelemedicineTokenSerializer,
    CreateSessionSerializer,
)
from .permissions import CanManageTelemedicine, CanJoinTelemedicineSession
from .utils import (
    generate_twilio_access_token,
    create_twilio_room,
    end_twilio_room,
    get_room_recordings,
)
from .transcription import run_transcription
from .video_services import get_video_service
from apps.visits.models import Visit
from apps.appointments.models import Appointment
from core.audit import AuditLog


def log_telemedicine_action(
    user,
    action,
    session_id,
    visit_id=None,
    request=None,
    metadata=None
):
    """Log telemedicine action to audit log."""
    user_role = getattr(user, 'role', None) or \
               getattr(user, 'get_role', lambda: None)()
    if not user_role:
        user_role = 'UNKNOWN'
    
    AuditLog.log(
        user=user,
        role=user_role,
        action=f"TELEMEDICINE_{action}",
        visit_id=visit_id,
        resource_type="telemedicine_session",
        resource_id=session_id,
        request=request,
        metadata=metadata or {}
    )


class TelemedicineSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Telemedicine Sessions.
    
    Rules enforced:
    - Doctor-only access for creating sessions
    - Visit-scoped architecture
    - Twilio Video integration
    - Audit logging
    """
    
    queryset = TelemedicineSession.objects.all().select_related(
        'visit',
        'appointment',
        'doctor',
        'patient',
        'created_by'
    ).prefetch_related('participants__user')
    
    serializer_class = TelemedicineSessionSerializer
    permission_classes = [CanManageTelemedicine]
    pagination_class = None  # Disable pagination for telemedicine sessions
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create/Update/Delete: Doctor only (CanManageTelemedicine)
        - Read/Join: Doctor or Patient (CanJoinTelemedicineSession for join)
        """
        if self.action in ['create', 'create_session', 'update', 'partial_update', 'destroy', 'start_session', 'end_session', 'request_transcription']:
            permission_classes = [CanManageTelemedicine]
        elif self.action in ['get_access_token', 'leave_session', 'join']:
            # Join actions - use CanJoinTelemedicineSession
            from .permissions import CanJoinTelemedicineSession
            permission_classes = [CanJoinTelemedicineSession]
        else:
            # Read actions - allow authenticated users (filtered by queryset)
            from rest_framework.permissions import IsAuthenticated
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return TelemedicineSessionCreateSerializer
        if self.action == 'create_session':
            return CreateSessionSerializer
        return TelemedicineSessionSerializer
    
    def get_queryset(self):
        """Filter sessions based on user role."""
        user = self.request.user
        user_role = getattr(user, 'role', None) or \
                   getattr(user, 'get_role', lambda: None)()
        
        queryset = super().get_queryset()
        
        # Doctors see their own sessions
        if user_role == 'DOCTOR':
            queryset = queryset.filter(doctor=user)
        # Patients see sessions for their visits
        elif user_role == 'PATIENT':
            try:
                from apps.patients.models import Patient
                patient = Patient.objects.get(user=user, is_active=True)
                queryset = queryset.filter(patient=patient)
            except Patient.DoesNotExist:
                queryset = queryset.none()
        
        # Filter by visit if provided
        visit_id = self.request.query_params.get('visit_id')
        if visit_id:
            queryset = queryset.filter(visit_id=visit_id)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create telemedicine session with Twilio room."""
        visit = serializer.validated_data['visit']
        doctor = self.request.user
        
        # Ensure user is a doctor
        user_role = getattr(doctor, 'role', None) or \
                   getattr(doctor, 'get_role', lambda: None)()
        if user_role != 'DOCTOR':
            raise PermissionDenied("Only doctors can create telemedicine sessions.")
        
        # Get patient from visit
        patient = visit.patient
        
        # Generate unique room name
        room_name = f"visit-{visit.id}-{uuid.uuid4().hex[:8]}"
        recording_enabled = serializer.validated_data.get('recording_enabled', False)
        
        try:
            # Create Twilio room (with recording on if user enabled it for this session)
            room_info = create_twilio_room(
                room_name=room_name,
                max_participants=2,
                record_participants_on_connect=recording_enabled,
            )
            
            # Create session
            session = serializer.save(
                doctor=doctor,
                patient=patient,
                twilio_room_sid=room_info['room_sid'],
                twilio_room_name=room_info['room_name'],
                created_by=doctor,
                status='SCHEDULED'
            )
            
            # Audit log
            log_telemedicine_action(
                user=doctor,
                action='CREATED',
                session_id=session.id,
                visit_id=visit.id,
                request=self.request,
                metadata={
                    'room_sid': room_info['room_sid'],
                    'room_name': room_info['room_name'],
                }
            )
            
            return session
            
        except Exception as e:
            # Log error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create telemedicine session: {e}")
            raise DRFValidationError(f"Failed to create telemedicine session: {str(e)}")
    
    @action(detail=True, methods=['post'], url_path='start')
    def start_session(self, request, pk=None):
        """Start a telemedicine session."""
        session = self.get_object()
        
        if session.status != 'SCHEDULED':
            raise DRFValidationError(
                f"Cannot start session with status {session.status}."
            )
        
        session.status = 'IN_PROGRESS'
        session.actual_start = timezone.now()
        session.save()
        
        # Audit log
        log_telemedicine_action(
            user=request.user,
            action='STARTED',
            session_id=session.id,
            visit_id=session.visit_id,
            request=request
        )
        
        return Response(
            TelemedicineSessionSerializer(session).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], url_path='end')
    def end_session(self, request, pk=None):
        """End a telemedicine session. Optionally add a billing line item for the session."""
        session = self.get_object()
        
        if session.status != 'IN_PROGRESS':
            raise DRFValidationError(
                f"Cannot end session with status {session.status}."
            )
        
        add_billing = request.data.get('add_billing', False) if isinstance(request.data, dict) else False
        
        try:
            # End Twilio room (may return None if room already deleted/expired)
            room_result = end_twilio_room(session.twilio_room_sid)
            
            # Update session
            session.status = 'COMPLETED'
            session.actual_end = timezone.now()
            
            # Log if room was already gone
            if room_result is None:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Room {session.twilio_room_sid} was already deleted/expired when ending session {session.id}")
            
            if session.actual_start:
                duration = session.actual_end - session.actual_start
                session.duration_seconds = int(duration.total_seconds())
            
            # Get recordings if enabled
            if session.recording_enabled:
                try:
                    recordings = get_room_recordings(session.twilio_room_sid)
                    if recordings:
                        latest_recording = recordings[0]
                        session.recording_sid = latest_recording['sid']
                        session.recording_url = latest_recording.get('url', '')
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to get recordings: {e}")
            
            session.save()
            
            # Optional: add telemedicine session to visit bill
            billing_added = False
            if add_billing:
                billing_added = self._add_telemedicine_billing(session, request.user)
            
            # Audit log
            log_telemedicine_action(
                user=request.user,
                action='ENDED',
                session_id=session.id,
                visit_id=session.visit_id,
                request=request,
                metadata={
                    'duration_seconds': session.duration_seconds,
                    'add_billing': add_billing,
                    'billing_added': billing_added,
                }
            )
            
            response_data = TelemedicineSessionSerializer(session).data
            if add_billing:
                response_data['billing_added'] = billing_added
            
            return Response(
                response_data,
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to end telemedicine session: {e}")
            raise DRFValidationError(f"Failed to end session: {str(e)}")
    
    def _add_telemedicine_billing(self, session, user):
        """Add a billing line item for this telemedicine session if configured."""
        from django.conf import settings
        from apps.billing.service_catalog_models import ServiceCatalog
        from apps.billing.billing_line_item_service import create_billing_line_item_from_service
        from apps.consultations.models import Consultation
        
        service_code = getattr(settings, 'TELEMEDICINE_BILLING_SERVICE_CODE', None) or 'TELEMED-001'
        try:
            service = ServiceCatalog.objects.get(service_code=service_code, is_active=True)
        except ServiceCatalog.DoesNotExist:
            import logging
            logging.getLogger(__name__).info(
                f"Telemedicine billing skipped: service '{service_code}' not in ServiceCatalog. "
                "Add a service with this code (e.g. Telemedicine Consultation) to enable session billing."
            )
            return False
        
        visit = session.visit
        if visit.status != 'OPEN':
            return False
        # Telemedicine billing typically uses a standalone service (e.g. workflow_type OTHER);
        # link to visit's consultation if the service allows it, otherwise None
        consultation = Consultation.objects.filter(visit=visit).first()
        if service.workflow_type not in ('GOPD_CONSULT', 'LAB_ORDER', 'DRUG_DISPENSE', 'PROCEDURE', 'RADIOLOGY_STUDY'):
            consultation = None
        try:
            create_billing_line_item_from_service(
                service=service,
                visit=visit,
                consultation=consultation,
                created_by=user,
            )
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not add telemedicine billing: {e}")
            return False
    
    @action(detail=True, methods=['post'], url_path='request-transcription')
    def request_transcription(self, request, pk=None):
        """Request automatic transcription of the session recording (after session is completed)."""
        session = self.get_object()
        if session.status != 'COMPLETED':
            raise DRFValidationError(
                "Transcription can only be requested for completed sessions."
            )
        if session.transcription_status and session.transcription_status not in ('', 'FAILED'):
            raise DRFValidationError(
                f"Transcription already requested (status: {session.transcription_status})."
            )
        if not session.recording_url and not session.recording_sid:
            raise DRFValidationError(
                "No recording available for this session. Enable recording when creating the session."
            )
        session.transcription_requested_at = timezone.now()
        session.transcription_status = 'PENDING'
        session.save(update_fields=['transcription_requested_at', 'transcription_status'])
        run_transcription(session)
        session.refresh_from_db()
        log_telemedicine_action(
            user=request.user,
            action='TRANSCRIPTION_REQUESTED',
            session_id=session.id,
            visit_id=session.visit_id,
            request=request,
        )
        return Response(
            TelemedicineSessionSerializer(session).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], url_path='create-session')
    def create_session(self, request):
        """
        Create a telemedicine session from an appointment. Generate room and link to appointment.
        POST /api/v1/telemedicine/create-session/
        Body: { "appointment_id": 123, "recording_enabled": false }
        """
        serializer = CreateSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment_id = serializer.validated_data['appointment_id']
        recording_enabled = serializer.validated_data.get('recording_enabled', False)
        
        user = request.user
        user_role = getattr(user, 'role', None) or getattr(user, 'get_role', lambda: None)()
        if user_role != 'DOCTOR':
            raise PermissionDenied("Only doctors can create telemedicine sessions.")
        
        appointment = get_object_or_404(Appointment, id=appointment_id)
        if appointment.doctor != user:
            raise PermissionDenied("You can only create sessions for your own appointments.")
        if appointment.status not in ('SCHEDULED', 'CONFIRMED'):
            raise DRFValidationError("Appointment must be scheduled or confirmed.")
        
        patient = appointment.patient
        visit = appointment.visit
        if not visit:
            visit = Visit.objects.create(
                patient=patient,
                visit_type='CONSULTATION',
                chief_complaint=appointment.reason or 'Telemedicine consult',
                appointment=appointment,
                status='OPEN',
            )
            appointment.visit = visit
            appointment.save(update_fields=['visit'])
        elif visit.status != 'OPEN':
            raise DRFValidationError("Linked visit is not OPEN. Cannot start telemedicine.")
        
        room_name = f"visit-{visit.id}-{uuid.uuid4().hex[:8]}"
        try:
            room_info = create_twilio_room(
                room_name=room_name,
                max_participants=2,
                record_participants_on_connect=recording_enabled,
            )
        except Exception as e:
            logger.error(f"Failed to create Twilio room: {e}")
            raise DRFValidationError(f"Failed to create video room: {str(e)}")
        
        session = TelemedicineSession.objects.create(
            visit=visit,
            appointment=appointment,
            doctor=user,
            patient=patient,
            twilio_room_sid=room_info['room_sid'],
            twilio_room_name=room_info['room_name'],
            status='SCHEDULED',
            scheduled_start=timezone.now(),
            recording_enabled=recording_enabled,
            created_by=user,
        )
        
        base_url = getattr(settings, 'FRONTEND_URL', '').rstrip('/')
        meeting_link = f"{base_url}/telemedicine/room/{session.id}" if base_url else room_info['room_name']
        
        log_telemedicine_action(
            user=user,
            action='CREATED',
            session_id=session.id,
            visit_id=visit.id,
            request=request,
            metadata={'room_sid': room_info['room_sid'], 'from_appointment': appointment_id},
        )
        
        return Response(
            {
                **TelemedicineSessionSerializer(session).data,
                'meeting_link': meeting_link,
            },
            status=status.HTTP_201_CREATED,
        )
    
    @action(detail=True, methods=['get'], url_path='join')
    def join(self, request, pk=None):
        """
        Return meeting link (and token if Twilio) for joining the session.
        GET /api/v1/telemedicine/{id}/join/
        Patients and doctors only.
        """
        session = self.get_object()
        user = request.user
        user_role = getattr(user, 'role', None) or getattr(user, 'get_role', lambda: None)()
        
        if user_role == 'DOCTOR' and session.doctor != user:
            raise PermissionDenied("You are not the doctor for this session.")
        if user_role == 'PATIENT':
            try:
                from apps.patients.models import Patient
                patient = Patient.objects.get(user=user, is_active=True)
                if session.patient != patient:
                    raise PermissionDenied("You are not the patient for this session.")
            except Patient.DoesNotExist:
                raise PermissionDenied("Patient profile not found.")
        if user_role not in ('DOCTOR', 'PATIENT'):
            raise PermissionDenied("Only doctor or patient can join this session.")
        
        base_url = getattr(settings, 'FRONTEND_URL', '').rstrip('/')
        meeting_link = f"{base_url}/telemedicine/room/{session.id}" if base_url else session.twilio_room_name
        
        payload = {'meeting_link': meeting_link, 'session_id': session.id}
        try:
            token = generate_twilio_access_token(
                user=user,
                room_sid=session.twilio_room_sid,
                room_name=session.twilio_room_name,
            )
            payload['access_token'] = token
            payload['room_name'] = session.twilio_room_name
        except Exception as e:
            logger.warning(f"Twilio token not generated for join: {e}")
        
        return Response(payload, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='token')
    def get_access_token(self, request):
        """Get Twilio access token for joining a session."""
        serializer = TelemedicineTokenSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        session = serializer.context['session']
        
        # Check if user can join
        user = request.user
        user_role = getattr(user, 'role', None) or \
                   getattr(user, 'get_role', lambda: None)()
        
        if user_role == 'DOCTOR' and session.doctor != user:
            raise PermissionDenied("You are not authorized to join this session.")
        
        # Check patient access
        if user_role == 'PATIENT':
            try:
                from apps.patients.models import Patient
                patient = Patient.objects.get(user=user, is_active=True)
                if session.patient != patient:
                    raise PermissionDenied("You are not authorized to join this session.")
            except Patient.DoesNotExist:
                raise PermissionDenied("Patient profile not found.")
        
        # Generate access token
        try:
            # Use room SID if available (more reliable), otherwise use room name
            token = generate_twilio_access_token(
                user=user,
                room_sid=session.twilio_room_sid,
                room_name=session.twilio_room_name
            )
            
            # Track participant
            participant, created = TelemedicineParticipant.objects.get_or_create(
                session=session,
                user=user,
                defaults={
                    'joined_at': timezone.now(),
                }
            )
            
            if not created and not participant.joined_at:
                participant.joined_at = timezone.now()
                participant.save()
            
            # Audit log
            log_telemedicine_action(
                user=user,
                action='JOINED',
                session_id=session.id,
                visit_id=session.visit_id,
                request=request
            )
            
            return Response({
                'token': token,
                'room_name': session.twilio_room_name,
                'room_sid': session.twilio_room_sid,  # Also return SID for flexibility
                'session_id': session.id,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to generate access token: {e}")
            raise DRFValidationError(f"Failed to generate access token: {str(e)}")
    
    @action(detail=True, methods=['post'], url_path='leave')
    def leave_session(self, request, pk=None):
        """Leave a telemedicine session."""
        session = self.get_object()
        user = request.user
        
        try:
            participant = TelemedicineParticipant.objects.get(
                session=session,
                user=user
            )
            
            participant.left_at = timezone.now()
            participant.save()
            
            # Audit log
            log_telemedicine_action(
                user=user,
                action='LEFT',
                session_id=session.id,
                visit_id=session.visit_id,
                request=request
            )
            
            return Response({
                'message': 'Left session successfully'
            }, status=status.HTTP_200_OK)
            
        except TelemedicineParticipant.DoesNotExist:
            raise NotFound("You are not a participant in this session.")

    @action(detail=True, methods=['get'], url_path='recording', url_name='recording')
    def get_recording(self, request, pk=None):
        """
        Stream the session recording. Twilio Media subresource can return either:
        - HTTP 302 redirect to the media URL, or
        - HTTP 200 with JSON { "redirect_to": "<url>" }.
        We follow the media URL and stream the file to the client.
        GET /api/v1/telemedicine/{id}/recording/
        """
        session = self.get_object()
        if not session.recording_sid:
            raise NotFound("No recording available for this session.")
        try:
            import requests
            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            if not account_sid or not auth_token:
                raise NotFound("Recording service not configured.")
            auth = (account_sid, auth_token)
            media_resource_url = (
                f"https://video.twilio.com/v1/Recordings/{session.recording_sid}/Media"
            )
            # Do not follow redirects so we can handle 302 (Location) or 200 (JSON)
            media_resp = requests.get(
                media_resource_url, auth=auth, timeout=30, allow_redirects=False
            )
            redirect_to = None
            if media_resp.status_code == 302:
                redirect_to = media_resp.headers.get("Location")
            elif media_resp.status_code == 200:
                try:
                    data = media_resp.json()
                    redirect_to = data.get("redirect_to") or data.get("redirectTo")
                except (ValueError, TypeError):
                    # Response might be raw content in some edge cases
                    pass
            if not redirect_to:
                if media_resp.status_code == 404:
                    raise NotFound("Recording not found or still processing.")
                logger.warning(
                    "No media redirect for session %s: status=%s",
                    session.id,
                    media_resp.status_code,
                )
                raise DRFValidationError(
                    "Recording media not ready yet. Try again in a minute."
                )
            # Stream from the media URL (temporary; no auth needed)
            stream_resp = requests.get(redirect_to, timeout=120, stream=True)
            stream_resp.raise_for_status()
            content_type = stream_resp.headers.get(
                "Content-Type", "application/octet-stream"
            )
            response = StreamingHttpResponse(
                stream_resp.iter_content(chunk_size=8192),
                content_type=content_type,
            )
            disposition = stream_resp.headers.get("Content-Disposition")
            if disposition:
                response["Content-Disposition"] = disposition
            return response
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise NotFound("Recording not found or still processing.")
            logger.warning(f"Failed to proxy recording for session {session.id}: {e}")
            raise DRFValidationError(
                "Could not load recording. It may still be processing."
            )
        except NotFound:
            raise
        except DRFValidationError:
            raise
        except Exception as e:
            logger.warning(f"Failed to proxy recording for session {session.id}: {e}")
            raise DRFValidationError(
                "Could not load recording. It may still be processing."
            )
