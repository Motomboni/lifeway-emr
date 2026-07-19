"""
Telemedicine ViewSet - video consultation management.

Endpoint: /api/v1/telemedicine/

Enforcement:
1. Doctor-only access for creating sessions
2. Visit-scoped architecture
3. Audit logging mandatory
4. Video provider integration (Twilio Video or LiveKit)
"""

import logging
import uuid

from django.conf import settings
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
)
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
)
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from apps.appointments.models import Appointment
from apps.visits.models import Visit
from core.audit import AuditLog
from core.tenant import assert_visit_in_organization, filter_by_visit_organization

from .access import (
    ACTIVE_INVITE_STATUSES,
    INVITABLE_STAFF_ROLES,
    VIRTUAL_CLINIC_MAX_PARTICIPANTS,
    default_clinic_role_for_user,
    get_active_invite,
    is_session_host,
    is_session_patient,
    user_can_invite_staff,
    user_can_join_session,
    user_can_view_session,
    user_role as resolve_user_role,
)
from .models import TelemedicineParticipant, TelemedicineSession
from .notifications import (
    build_meeting_link,
    notify_patient_telemedicine_invite,
    notify_staff_telemedicine_invite,
)
from .payment_gates import enforce_telemedicine_payment_gates
from .visit_access import assert_telemedicine_visit_access
from .permissions import CanManageTelemedicine
from .serializers import (
    CreateSessionSerializer,
    TelemedicineInviteResponseSerializer,
    TelemedicineInviteSerializer,
    TelemedicineParticipantSerializer,
    TelemedicineSessionCreateSerializer,
    TelemedicineSessionSerializer,
    TelemedicineTokenSerializer,
)
from .tasks import schedule_auto_transcription
from .transcription import run_transcription
from .video_providers import (
    create_video_room,
    end_video_room,
    ensure_virtual_clinic_capacity,
    generate_video_access_token,
    get_active_video_provider,
    get_public_video_config,
    get_room_recordings_for_session,
    refresh_session_recording,
    resolve_session_video_provider,
)


def _video_join_payload(session, token):
    provider = resolve_session_video_provider(session)
    payload = {
        "token": token,
        "room_name": session.twilio_room_name,
        "room_sid": session.twilio_room_sid,
        "session_id": session.id,
        "video_provider": provider,
    }
    payload.update(get_public_video_config(provider))
    return payload


def log_telemedicine_action(
    user, action, session_id, visit_id=None, request=None, metadata=None
):
    """Log telemedicine action to audit log."""
    user_role = getattr(user, "role", None) or getattr(user, "get_role", lambda: None)()
    if not user_role:
        user_role = "UNKNOWN"

    AuditLog.log(
        user=user,
        role=user_role,
        action=f"TELEMEDICINE_{action}",
        visit_id=visit_id,
        resource_type="telemedicine_session",
        resource_id=session_id,
        request=request,
        metadata=metadata or {},
    )


def _ensure_host_participant(session, doctor):
    """Ensure the host doctor is tracked as a virtual clinic participant."""
    TelemedicineParticipant.objects.update_or_create(
        session=session,
        user=doctor,
        defaults={
            "clinic_role": "HOST",
            "invite_status": "ACCEPTED",
            "invited_by": doctor,
            "invited_at": timezone.now(),
        },
    )


def _mark_participant_joined(session, user):
    """Create/update participant row and accept pending invites on join."""
    invite = get_active_invite(user, session)
    defaults = {
        "joined_at": timezone.now(),
        "left_at": None,
    }
    if invite:
        defaults["invite_status"] = "ACCEPTED"
        defaults["clinic_role"] = invite.clinic_role
    elif is_session_host(user, session):
        defaults["clinic_role"] = "HOST"
        defaults["invite_status"] = "ACCEPTED"
    elif is_session_patient(user, session):
        defaults["clinic_role"] = "PATIENT"
        defaults["invite_status"] = "ACCEPTED"
    else:
        defaults["clinic_role"] = default_clinic_role_for_user(user)
        defaults["invite_status"] = "ACCEPTED"

    participant, created = TelemedicineParticipant.objects.get_or_create(
        session=session,
        user=user,
        defaults=defaults,
    )
    if not created:
        participant.joined_at = timezone.now()
        participant.left_at = None
        if participant.invite_status == "PENDING":
            participant.invite_status = "ACCEPTED"
        if not participant.clinic_role:
            participant.clinic_role = defaults.get("clinic_role", "STAFF")
        participant.save()
    return participant


class TelemedicineSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Telemedicine Sessions.

    Rules enforced:
    - Doctor-only access for creating sessions
    - Visit-scoped architecture
    - Twilio Video integration
    - Audit logging
    """

    queryset = (
        TelemedicineSession.objects.all()
        .select_related("visit", "appointment", "doctor", "patient", "created_by")
        .prefetch_related("participants__user")
    )

    serializer_class = TelemedicineSessionSerializer
    permission_classes = [CanManageTelemedicine]
    pagination_class = None  # Disable pagination for telemedicine sessions

    def get_permissions(self):
        """
        Return appropriate permissions based on action.

        - Create/Update/Delete: Doctor only (CanManageTelemedicine)
        - Pricing: Admin
        - Read/Join: Doctor, patient, or invited staff
        """
        from rest_framework.permissions import IsAuthenticated

        from .permissions import CanJoinTelemedicineSession

        if self.action in [
            "create",
            "create_session",
            "update",
            "partial_update",
            "destroy",
            "start_session",
            "end_session",
            "request_transcription",
            "save_live_transcript",
            "invite_staff",
            "revoke_invite",
            "invitable_staff",
        ]:
            permission_classes = [CanManageTelemedicine]
        elif self.action == "pricing":
            # GET: any authenticated user; PUT/PATCH checked inside the action
            permission_classes = [IsAuthenticated]
        elif self.action in [
            "get_access_token",
            "leave_session",
            "join",
            "get_recording",
            "respond_invite",
        ]:
            permission_classes = [CanJoinTelemedicineSession]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return TelemedicineSessionCreateSerializer
        if self.action == "create_session":
            return CreateSessionSerializer
        return TelemedicineSessionSerializer

    def get_queryset(self):
        """Filter sessions based on user role (host, patient, or invited staff)."""
        from django.db.models import Q

        user = self.request.user
        user_role = resolve_user_role(user)

        queryset = super().get_queryset()

        if user_role == "DOCTOR":
            queryset = queryset.filter(
                Q(doctor=user)
                | Q(
                    participants__user=user,
                    participants__invite_status__in=ACTIVE_INVITE_STATUSES,
                )
            ).distinct()
        elif user_role == "PATIENT":
            try:
                from apps.patients.models import Patient

                patient = Patient.objects.get(user=user, is_active=True)
                queryset = queryset.filter(patient=patient)
            except Patient.DoesNotExist:
                queryset = queryset.none()
        elif user_role in INVITABLE_STAFF_ROLES:
            queryset = queryset.filter(
                participants__user=user,
                participants__invite_status__in=ACTIVE_INVITE_STATUSES,
            ).distinct()
        else:
            queryset = queryset.none()

        # Filter by visit if provided
        visit_id = self.request.query_params.get("visit_id")
        if visit_id:
            queryset = queryset.filter(visit_id=visit_id)

        return filter_by_visit_organization(queryset, self.request)

    def perform_create(self, serializer):
        """Create telemedicine session with configured video provider."""
        visit = serializer.validated_data["visit"]
        doctor = self.request.user

        # Ensure user is a doctor
        user_role = (
            getattr(doctor, "role", None) or getattr(doctor, "get_role", lambda: None)()
        )
        if user_role != "DOCTOR":
            raise PermissionDenied("Only doctors can create telemedicine sessions.")

        # Get patient from visit
        patient = visit.patient

        enforce_telemedicine_payment_gates(visit, doctor, for_create=True)
        assert_telemedicine_visit_access(visit, doctor, self.request)

        recording_enabled = serializer.validated_data.get("recording_enabled", False)
        consent_ack = serializer.validated_data.pop(
            "recording_consent_acknowledged", False
        )
        if recording_enabled and not consent_ack:
            raise DRFValidationError(
                {
                    "recording_consent_acknowledged": [
                        "Patient recording consent is required when recording is enabled."
                    ]
                }
            )

        # Generate unique room name
        room_name = f"visit-{visit.id}-{uuid.uuid4().hex[:8]}"

        try:
            room_info = create_video_room(
                room_name=room_name,
                max_participants=VIRTUAL_CLINIC_MAX_PARTICIPANTS,
                record_participants_on_connect=recording_enabled,
            )

            consent_kwargs = {}
            if recording_enabled and consent_ack:
                consent_kwargs = {
                    "recording_consent_at": timezone.now(),
                    "recording_consent_by": doctor,
                }

            # Create session
            session = serializer.save(
                doctor=doctor,
                patient=patient,
                twilio_room_sid=room_info["room_sid"],
                twilio_room_name=room_info["room_name"],
                video_provider=room_info.get("video_provider", get_active_video_provider()),
                created_by=doctor,
                status="SCHEDULED",
                **consent_kwargs,
            )

            _ensure_host_participant(session, doctor)

            notify_patient_telemedicine_invite(session, created_by=doctor)

            # Audit log
            log_telemedicine_action(
                user=doctor,
                action="CREATED",
                session_id=session.id,
                visit_id=visit.id,
                request=self.request,
                metadata={
                    "room_sid": room_info["room_sid"],
                    "room_name": room_info["room_name"],
                },
            )

            return session

        except Exception as e:
            # Log error
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create telemedicine session: {e}")
            raise DRFValidationError(f"Failed to create telemedicine session: {str(e)}")

    @action(detail=True, methods=["post"], url_path="start")
    def start_session(self, request, pk=None):
        """Start a telemedicine session."""
        session = self.get_object()

        if session.status != "SCHEDULED":
            raise DRFValidationError(
                f"Cannot start session with status {session.status}."
            )

        enforce_telemedicine_payment_gates(
            session.visit,
            request.user,
            for_doctor_encounter=True,
        )

        session.status = "IN_PROGRESS"
        session.actual_start = timezone.now()
        session.save()

        notify_patient_telemedicine_invite(session, created_by=request.user, event="started")

        # Audit log
        log_telemedicine_action(
            user=request.user,
            action="STARTED",
            session_id=session.id,
            visit_id=session.visit_id,
            request=request,
        )

        return Response(
            TelemedicineSessionSerializer(session).data, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"], url_path="end")
    def end_session(self, request, pk=None):
        """End a telemedicine session. Optionally add a billing line item for the session."""
        session = self.get_object()

        if session.status != "IN_PROGRESS":
            raise DRFValidationError(
                f"Cannot end session with status {session.status}."
            )

        add_billing = (
            request.data.get("add_billing", False)
            if isinstance(request.data, dict)
            else False
        )

        try:
            provider = resolve_session_video_provider(session)
            room_result = end_video_room(
                session.twilio_room_sid,
                room_name=session.twilio_room_name,
                provider=provider,
            )

            # Update session
            session.status = "COMPLETED"
            session.actual_end = timezone.now()

            # Log if room was already gone
            if room_result is None:
                import logging

                logger = logging.getLogger(__name__)
                logger.info(
                    f"Room {session.twilio_room_sid} was already deleted/expired when ending session {session.id}"
                )

            if session.actual_start:
                duration = session.actual_end - session.actual_start
                session.duration_seconds = int(duration.total_seconds())

            if session.recording_enabled and provider == "twilio":
                try:
                    recordings = get_room_recordings_for_session(session)
                    if recordings:
                        latest_recording = recordings[0]
                        session.recording_sid = latest_recording["sid"]
                        session.recording_url = (
                            latest_recording.get("media_url")
                            or latest_recording.get("url")
                            or ""
                        )
                except Exception as e:
                    logger.warning(f"Failed to get recordings: {e}")

            session.save()

            # Automatic transcription when recording is enabled
            if session.recording_enabled:
                session.transcription_requested_at = timezone.now()
                session.transcription_status = "PENDING"
                session.save(
                    update_fields=[
                        "transcription_requested_at",
                        "transcription_status",
                    ]
                )
                schedule_auto_transcription(session.id)

            # Optional: add telemedicine session to visit bill
            billing_added = False
            if add_billing:
                billing_added = self._add_telemedicine_billing(session, request.user)

            # Audit log
            log_telemedicine_action(
                user=request.user,
                action="ENDED",
                session_id=session.id,
                visit_id=session.visit_id,
                request=request,
                metadata={
                    "duration_seconds": session.duration_seconds,
                    "add_billing": add_billing,
                    "billing_added": billing_added,
                },
            )

            response_data = TelemedicineSessionSerializer(session).data
            if add_billing:
                response_data["billing_added"] = billing_added

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to end telemedicine session: {e}")
            raise DRFValidationError(f"Failed to end session: {str(e)}")

    def _add_telemedicine_billing(self, session, user):
        """Add a billing line item for this telemedicine session if configured."""
        from apps.billing.billing_line_item_service import (
            create_billing_line_item_from_service,
        )
        from apps.consultations.models import Consultation
        from .pricing import get_telemedicine_billing_service

        org = getattr(session.visit, "organization", None) or getattr(
            self.request, "organization", None
        )
        service = get_telemedicine_billing_service(organization=org)
        if not service or not service.is_active:
            import logging

            logging.getLogger(__name__).info(
                "Telemedicine billing skipped: no active telemedicine service in catalog. "
                "Admin can set the price under Virtual Clinic → Telemedicine pricing."
            )
            return False

        visit = session.visit
        if visit.status != "OPEN":
            return False
        consultation = Consultation.objects.filter(visit=visit).first()
        if service.workflow_type not in (
            "GOPD_CONSULT",
            "LAB_ORDER",
            "DRUG_DISPENSE",
            "PROCEDURE",
            "RADIOLOGY_STUDY",
        ):
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

            logging.getLogger(__name__).warning(
                f"Could not add telemedicine billing: {e}"
            )
            return False

    @action(detail=False, methods=["get", "put", "patch"], url_path="pricing")
    def pricing(self, request):
        """
        Get or update telemedicine consultation price (ServiceCatalog).

        GET  /api/v1/telemedicine/pricing/
        PUT/PATCH /api/v1/telemedicine/pricing/
        Body (write): { amount, name?, is_active?, description? }
        """
        from decimal import Decimal, InvalidOperation

        from .permissions import CanManageTelemedicinePricing
        from .pricing import (
            get_or_create_telemedicine_billing_service,
            get_telemedicine_billing_service,
            serialize_telemedicine_pricing,
        )

        org = getattr(request, "organization", None)
        role = resolve_user_role(request.user)
        is_admin = (
            role == "ADMIN"
            or getattr(request.user, "is_staff", False)
            or getattr(request.user, "is_superuser", False)
        )

        if request.method in ("PUT", "PATCH"):
            if not CanManageTelemedicinePricing().has_permission(request, self):
                return Response(
                    {"detail": "Only administrators can update telemedicine pricing."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            service, _ = get_or_create_telemedicine_billing_service(organization=org)

            amount_raw = request.data.get("amount", None)
            if amount_raw is None:
                raise DRFValidationError({"amount": ["Amount is required."]})
            try:
                amount = Decimal(str(amount_raw))
            except (InvalidOperation, TypeError, ValueError):
                raise DRFValidationError({"amount": ["Enter a valid amount."]})
            if amount < 0:
                raise DRFValidationError({"amount": ["Amount cannot be negative."]})

            service.amount = amount
            if "name" in request.data and request.data.get("name"):
                service.name = str(request.data.get("name")).strip()[:255]
            if "description" in request.data:
                service.description = str(request.data.get("description") or "")
            if "is_active" in request.data:
                service.is_active = bool(request.data.get("is_active"))
            service.save()

            log_telemedicine_action(
                user=request.user,
                action="PRICING_UPDATED",
                session_id=0,
                visit_id=None,
                request=request,
                metadata={
                    "service_code": service.service_code,
                    "amount": str(service.amount),
                    "is_active": service.is_active,
                },
            )

            payload = serialize_telemedicine_pricing(service)
            payload["configured"] = True
            payload["can_edit"] = True
            return Response(payload)

        if is_admin:
            service, created = get_or_create_telemedicine_billing_service(
                organization=org
            )
        else:
            service = get_telemedicine_billing_service(organization=org)
            created = False
            if not service:
                return Response(
                    {
                        "configured": False,
                        "detail": "Telemedicine pricing is not configured yet.",
                    },
                    status=status.HTTP_200_OK,
                )

        payload = serialize_telemedicine_pricing(service)
        payload["configured"] = True
        payload["created"] = created
        payload["can_edit"] = is_admin
        return Response(payload)

    @action(detail=True, methods=["post"], url_path="request-transcription")
    def request_transcription(self, request, pk=None):
        """Request automatic transcription of the session recording (after session is completed)."""
        session = self.get_object()
        if session.status != "COMPLETED":
            raise DRFValidationError(
                "Transcription can only be requested for completed sessions."
            )
        if session.transcription_status and session.transcription_status not in (
            "",
            "FAILED",
        ):
            raise DRFValidationError(
                f"Transcription already requested (status: {session.transcription_status})."
            )
        if not session.recording_url and not session.recording_sid:
            refresh_session_recording(session)
            session.refresh_from_db()
        if not session.recording_url and not session.recording_sid:
            raise DRFValidationError(
                "No recording available for this session. Enable recording when creating the session."
            )
        session.transcription_requested_at = timezone.now()
        session.transcription_status = "PENDING"
        session.save(
            update_fields=["transcription_requested_at", "transcription_status"]
        )
        run_transcription(session)
        session.refresh_from_db()
        log_telemedicine_action(
            user=request.user,
            action="TRANSCRIPTION_REQUESTED",
            session_id=session.id,
            visit_id=session.visit_id,
            request=request,
        )
        return Response(
            TelemedicineSessionSerializer(session).data, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"], url_path="save-live-transcript")
    def save_live_transcript(self, request, pk=None):
        """
        Save browser live speech-to-text captured during the video call.
        Doctor-only. Does not overwrite an existing completed recording transcription.
        """
        session = self.get_object()
        transcript = (request.data.get("transcript") or "").strip()
        if not transcript:
            raise DRFValidationError({"transcript": ["Transcript text is required."]})
        if session.transcription_status == "COMPLETED" and session.transcription_text:
            return Response(
                TelemedicineSessionSerializer(session).data,
                status=status.HTTP_200_OK,
            )
        session.transcription_text = transcript
        session.transcription_status = "COMPLETED"
        session.transcription_completed_at = timezone.now()
        if not session.transcription_requested_at:
            session.transcription_requested_at = timezone.now()
        session.save(
            update_fields=[
                "transcription_text",
                "transcription_status",
                "transcription_completed_at",
                "transcription_requested_at",
            ]
        )
        log_telemedicine_action(
            user=request.user,
            action="LIVE_TRANSCRIPT_SAVED",
            session_id=session.id,
            visit_id=session.visit_id,
            request=request,
            metadata={"chars": len(transcript), "source": "browser_stt"},
        )
        return Response(
            TelemedicineSessionSerializer(session).data, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"], url_path="create-session")
    def create_session(self, request):
        """
        Create a telemedicine session from an appointment. Generate room and link to appointment.
        POST /api/v1/telemedicine/create-session/
        Body: { "appointment_id": 123, "recording_enabled": false }
        """
        serializer = CreateSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment_id = serializer.validated_data["appointment_id"]
        recording_enabled = serializer.validated_data.get("recording_enabled", False)
        consent_ack = serializer.validated_data.get("recording_consent_acknowledged", False)

        user = request.user
        user_role = (
            getattr(user, "role", None) or getattr(user, "get_role", lambda: None)()
        )
        if user_role != "DOCTOR":
            raise PermissionDenied("Only doctors can create telemedicine sessions.")

        appointment = get_object_or_404(Appointment, id=appointment_id)
        if appointment.doctor != user:
            raise PermissionDenied(
                "You can only create sessions for your own appointments."
            )
        if appointment.status not in ("SCHEDULED", "CONFIRMED"):
            raise DRFValidationError("Appointment must be scheduled or confirmed.")

        patient = appointment.patient
        visit = appointment.visit
        if not visit:
            visit = Visit.objects.create(
                patient=patient,
                visit_type="CONSULTATION",
                chief_complaint=appointment.reason or "Telemedicine consult",
                appointment=appointment,
                status="OPEN",
            )
            appointment.visit = visit
            appointment.save(update_fields=["visit"])
        elif visit.status != "OPEN":
            raise DRFValidationError(
                "Linked visit is not OPEN. Cannot start telemedicine."
            )

        enforce_telemedicine_payment_gates(visit, user, for_create=True)
        assert_visit_in_organization(visit, request)

        room_name = f"visit-{visit.id}-{uuid.uuid4().hex[:8]}"
        try:
            room_info = create_video_room(
                room_name=room_name,
                max_participants=VIRTUAL_CLINIC_MAX_PARTICIPANTS,
                record_participants_on_connect=recording_enabled,
            )
        except Exception as e:
            logger.error(f"Failed to create video room: {e}")
            raise DRFValidationError(f"Failed to create video room: {str(e)}")

        session = TelemedicineSession.objects.create(
            visit=visit,
            appointment=appointment,
            doctor=user,
            patient=patient,
            twilio_room_sid=room_info["room_sid"],
            twilio_room_name=room_info["room_name"],
            video_provider=room_info.get("video_provider", get_active_video_provider()),
            status="SCHEDULED",
            scheduled_start=timezone.now(),
            recording_enabled=recording_enabled,
            created_by=user,
            **(
                {
                    "recording_consent_at": timezone.now(),
                    "recording_consent_by": user,
                }
                if recording_enabled and consent_ack
                else {}
            ),
        )

        _ensure_host_participant(session, user)

        meeting_link = build_meeting_link(session.id) or room_info["room_name"]

        notify_patient_telemedicine_invite(session, created_by=user)

        log_telemedicine_action(
            user=user,
            action="CREATED",
            session_id=session.id,
            visit_id=visit.id,
            request=request,
            metadata={
                "room_sid": room_info["room_sid"],
                "from_appointment": appointment_id,
            },
        )

        return Response(
            {
                **TelemedicineSessionSerializer(session).data,
                "meeting_link": meeting_link,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="join")
    def join(self, request, pk=None):
        """
        Return meeting link (and access token) for joining the session.
        GET /api/v1/telemedicine/{id}/join/
        Host doctor, patient, or invited staff.
        """
        session = self.get_object()
        user = request.user

        if not user_can_join_session(user, session):
            raise PermissionDenied("You are not authorized to join this session.")

        enforce_telemedicine_payment_gates(
            session.visit,
            user,
            for_doctor_encounter=is_session_host(user, session),
        )

        meeting_link = build_meeting_link(session.id) or session.twilio_room_name

        payload = {"meeting_link": meeting_link, "session_id": session.id}
        try:
            provider = resolve_session_video_provider(session)
            token = generate_video_access_token(
                user=user,
                room_sid=session.twilio_room_sid,
                room_name=session.twilio_room_name,
                provider=provider,
            )
            join_data = _video_join_payload(session, token)
            payload["access_token"] = token
            payload["room_name"] = join_data["room_name"]
            payload["video_provider"] = join_data["video_provider"]
            if join_data.get("livekit_url"):
                payload["livekit_url"] = join_data["livekit_url"]
        except Exception as e:
            logger.warning(f"Video token not generated for join: {e}")

        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="token")
    def get_access_token(self, request):
        """Get video access token for joining a session (Twilio or LiveKit)."""
        serializer = TelemedicineTokenSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        session = serializer.context["session"]
        user = request.user

        if not user_can_join_session(user, session):
            raise PermissionDenied("You are not authorized to join this session.")

        enforce_telemedicine_payment_gates(
            session.visit,
            user,
            for_doctor_encounter=is_session_host(user, session),
        )

        try:
            provider = resolve_session_video_provider(session)
            token = generate_video_access_token(
                user=user,
                room_sid=session.twilio_room_sid,
                room_name=session.twilio_room_name,
                provider=provider,
            )

            _mark_participant_joined(session, user)

            log_telemedicine_action(
                user=user,
                action="JOINED",
                session_id=session.id,
                visit_id=session.visit_id,
                request=request,
            )

            return Response(
                _video_join_payload(session, token),
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to generate access token: {e}")
            raise DRFValidationError(f"Failed to generate access token: {str(e)}")

    @action(detail=True, methods=["get"], url_path="invitable-staff")
    def invitable_staff(self, request, pk=None):
        """List staff who can be invited into this virtual clinic room."""
        from apps.users.models import User
        from apps.users.serializers import UserSerializer

        session = self.get_object()
        if not user_can_invite_staff(request.user, session):
            raise PermissionDenied("Only the host doctor can invite staff.")

        already_invited = set(
            session.participants.exclude(invite_status="REVOKED").values_list(
                "user_id", flat=True
            )
        )
        already_invited.add(session.doctor_id)

        qs = User.objects.filter(
            is_active=True, role__in=INVITABLE_STAFF_ROLES
        ).exclude(id__in=already_invited)

        org = getattr(request, "organization", None)
        if org is not None:
            from apps.organizations.models import OrganizationUser

            member_ids = OrganizationUser.objects.filter(organization=org).values_list(
                "user_id", flat=True
            )
            qs = qs.filter(id__in=member_ids)

        role_filter = request.query_params.get("role")
        if role_filter:
            qs = qs.filter(role=role_filter.upper())

        qs = qs.order_by("role", "first_name", "last_name")[:100]
        return Response(UserSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="invite")
    def invite_staff(self, request, pk=None):
        """Invite a nurse or other clinical staff into the virtual clinic."""
        from apps.users.models import User

        session = self.get_object()
        if not user_can_invite_staff(request.user, session):
            raise PermissionDenied("Only the host doctor can invite staff.")

        if session.status in ("COMPLETED", "CANCELLED", "FAILED"):
            raise DRFValidationError("Cannot invite staff to a closed session.")

        ensure_virtual_clinic_capacity(session)

        serializer = TelemedicineInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invitee = get_object_or_404(User, id=serializer.validated_data["user_id"])
        if not invitee.is_active:
            raise DRFValidationError("Cannot invite an inactive user.")
        if resolve_user_role(invitee) not in INVITABLE_STAFF_ROLES:
            raise DRFValidationError(
                "Only clinical staff roles can be invited to the virtual clinic."
            )
        if invitee.id == session.doctor_id:
            raise DRFValidationError("Host doctor is already in this clinic.")

        active_count = session.participants.filter(
            invite_status__in=ACTIVE_INVITE_STATUSES
        ).count()
        # Reserve slots for host + patient identity
        if active_count >= VIRTUAL_CLINIC_MAX_PARTICIPANTS:
            raise DRFValidationError(
                f"Virtual clinic is full (max {VIRTUAL_CLINIC_MAX_PARTICIPANTS})."
            )

        clinic_role = serializer.validated_data.get("clinic_role") or default_clinic_role_for_user(
            invitee
        )
        message = (serializer.validated_data.get("message") or "").strip()

        participant, created = TelemedicineParticipant.objects.get_or_create(
            session=session,
            user=invitee,
            defaults={
                "clinic_role": clinic_role,
                "invite_status": "PENDING",
                "invited_by": request.user,
                "invited_at": timezone.now(),
                "invite_message": message,
            },
        )
        if not created:
            if participant.invite_status in ACTIVE_INVITE_STATUSES:
                raise DRFValidationError("This staff member is already invited.")
            participant.clinic_role = clinic_role
            participant.invite_status = "PENDING"
            participant.invited_by = request.user
            participant.invited_at = timezone.now()
            participant.invite_message = message
            participant.joined_at = None
            participant.left_at = None
            participant.save()

        log_telemedicine_action(
            user=request.user,
            action="STAFF_INVITED",
            session_id=session.id,
            visit_id=session.visit_id,
            request=request,
            metadata={
                "invitee_id": invitee.id,
                "clinic_role": clinic_role,
            },
        )

        try:
            notify_staff_telemedicine_invite(
                session,
                invitee,
                created_by=request.user,
                clinic_role=clinic_role,
                message=message,
            )
        except Exception as e:
            logger.warning("Staff telemedicine SMS invite failed: %s", e)

        return Response(
            TelemedicineParticipantSerializer(participant).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"invites/(?P<participant_id>[^/.]+)/revoke",
    )
    def revoke_invite(self, request, pk=None, participant_id=None):
        """Revoke a staff invite."""
        session = self.get_object()
        if not user_can_invite_staff(request.user, session):
            raise PermissionDenied("Only the host doctor can revoke invites.")

        participant = get_object_or_404(
            TelemedicineParticipant, id=participant_id, session=session
        )
        if participant.clinic_role == "HOST" or participant.user_id == session.doctor_id:
            raise DRFValidationError("Cannot revoke the host doctor.")
        if participant.clinic_role == "PATIENT":
            raise DRFValidationError("Cannot revoke the patient from the session.")

        participant.invite_status = "REVOKED"
        participant.left_at = timezone.now()
        participant.save(update_fields=["invite_status", "left_at"])

        log_telemedicine_action(
            user=request.user,
            action="STAFF_INVITE_REVOKED",
            session_id=session.id,
            visit_id=session.visit_id,
            request=request,
            metadata={"participant_id": participant.id, "user_id": participant.user_id},
        )
        return Response(TelemedicineParticipantSerializer(participant).data)

    @action(detail=True, methods=["post"], url_path="respond-invite")
    def respond_invite(self, request, pk=None):
        """Accept or decline a pending virtual clinic invite."""
        session = self.get_object()
        serializer = TelemedicineInviteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        participant = TelemedicineParticipant.objects.filter(
            session=session, user=request.user
        ).first()
        if not participant or participant.invite_status not in ("PENDING", "ACCEPTED"):
            raise PermissionDenied("No pending invite found for this session.")

        if serializer.validated_data["accept"]:
            participant.invite_status = "ACCEPTED"
            action_name = "STAFF_INVITE_ACCEPTED"
        else:
            participant.invite_status = "DECLINED"
            participant.left_at = timezone.now()
            action_name = "STAFF_INVITE_DECLINED"
        participant.save()

        log_telemedicine_action(
            user=request.user,
            action=action_name,
            session_id=session.id,
            visit_id=session.visit_id,
            request=request,
        )
        return Response(TelemedicineParticipantSerializer(participant).data)

    @action(detail=True, methods=["post"], url_path="leave")
    def leave_session(self, request, pk=None):
        """Leave a telemedicine session."""
        session = self.get_object()
        user = request.user

        try:
            participant = TelemedicineParticipant.objects.get(
                session=session, user=user
            )

            participant.left_at = timezone.now()
            participant.save()

            # Audit log
            log_telemedicine_action(
                user=user,
                action="LEFT",
                session_id=session.id,
                visit_id=session.visit_id,
                request=request,
            )

            return Response(
                {"message": "Left session successfully"}, status=status.HTTP_200_OK
            )

        except TelemedicineParticipant.DoesNotExist:
            raise NotFound("You are not a participant in this session.")

    @action(detail=True, methods=["get"], url_path="recording", url_name="recording")
    def get_recording(self, request, pk=None):
        """
        Stream the session recording. Twilio Media subresource can return either:
        - HTTP 302 redirect to the media URL, or
        - HTTP 200 with JSON { "redirect_to": "<url>" }.
        We follow the media URL and stream the file to the client.
        GET /api/v1/telemedicine/{id}/recording/
        """
        session = self.get_object()
        log_telemedicine_action(
            user=request.user,
            action="RECORDING_VIEWED",
            session_id=session.id,
            visit_id=session.visit_id,
            request=request,
            metadata={"recording_sid": session.recording_sid},
        )
        if not session.recording_sid:
            raise NotFound("No recording available for this session.")
        try:
            import requests

            account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
            auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
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
