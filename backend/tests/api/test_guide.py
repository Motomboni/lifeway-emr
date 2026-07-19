"""Tests for guide API."""

import pytest
from rest_framework import status

from apps.guide.models import GuideEvent
from apps.organizations.models import OrganizationUser


@pytest.mark.django_db
class TestGuideAPI:
    def test_get_guide_progress_creates_record(self, api_client, doctor_user):
        client = api_client(user=doctor_user)
        response = client.get("/api/v1/guide/me/progress/")
        assert response.status_code == status.HTTP_200_OK
        assert "completed_steps" in response.data
        assert "role_launch_completed" in response.data
        assert "guide_modules" in response.data
        assert response.data["guide_modules"]["core"] is True

    def test_complete_guide_step(self, api_client, doctor_user):
        client = api_client(user=doctor_user)
        response = client.patch(
            "/api/v1/guide/me/progress/",
            {"step_id": "doctor-launch:open-visits"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "doctor-launch:open-visits" in response.data["completed_steps"]
        assert GuideEvent.objects.filter(event_type="role_launch_step").exists()

    def test_ask_guide_lab_query(self, api_client, doctor_user):
        client = api_client(user=doctor_user)
        response = client.post(
            "/api/v1/guide/me/ask/",
            {"query": "lab order"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["guide_target"] == "lab-inline"
        assert len(response.data["articles"]) >= 1
        assert GuideEvent.objects.filter(event_type="ask", article_id="lab-order").exists()

    def test_ask_guide_filters_disabled_module(self, api_client, doctor_user, test_org):
        test_org.guide_modules = {"laboratory": False}
        test_org.save(update_fields=["guide_modules"])

        client = api_client(user=doctor_user)
        response = client.post(
            "/api/v1/guide/me/ask/",
            {"query": "lab order"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["articles"] == []

    def test_log_guide_event(self, api_client, doctor_user):
        client = api_client(user=doctor_user)
        response = client.post(
            "/api/v1/guide/events/",
            {
                "event_type": "spotlight",
                "target_id": "lab-inline",
                "article_id": "lab-order",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert GuideEvent.objects.filter(event_type="spotlight").count() == 1

    def test_guide_analytics_admin(self, api_client, doctor_user, test_org):
        OrganizationUser.objects.filter(
            organization=test_org, user=doctor_user
        ).update(role="ADMIN")

        client = api_client(user=doctor_user)
        client.post(
            "/api/v1/guide/events/",
            {"event_type": "spotlight", "target_id": "lab-inline"},
            format="json",
        )
        response = client.get("/api/v1/guide/analytics/?days=30")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_events"] >= 1
        assert "spotlight" in response.data["totals"]

    def test_guide_analytics_denied_for_doctor(self, api_client, doctor_user):
        client = api_client(user=doctor_user)
        response = client.get("/api/v1/guide/analytics/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_visit_workflow_for_doctor(self, api_client, doctor_user, open_visit):
        client = api_client(user=doctor_user)
        response = client.get(f"/api/v1/guide/visits/{open_visit.id}/workflow/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["visit_id"] == open_visit.id
        pack_ids = [w["pack_id"] for w in response.data["workflows"]]
        assert "charting" in pack_ids

    def test_visit_workflow_for_receptionist(self, api_client, receptionist_user, open_visit):
        client = api_client(user=receptionist_user)
        response = client.get(f"/api/v1/guide/visits/{open_visit.id}/workflow/")
        assert response.status_code == status.HTTP_200_OK
        pack_ids = [w["pack_id"] for w in response.data["workflows"]]
        assert "intake" in pack_ids

    def test_visit_workflow_for_nurse(self, api_client, nurse_user, open_visit):
        client = api_client(user=nurse_user)
        response = client.get(f"/api/v1/guide/visits/{open_visit.id}/workflow/")
        assert response.status_code == status.HTTP_200_OK
        pack_ids = [w["pack_id"] for w in response.data["workflows"]]
        assert pack_ids == ["intake"]

    def test_visit_workflow_for_lab_tech(self, api_client, lab_tech_user, open_visit):
        client = api_client(user=lab_tech_user)
        response = client.get(f"/api/v1/guide/visits/{open_visit.id}/workflow/")
        assert response.status_code == status.HTTP_200_OK
        pack_ids = [w["pack_id"] for w in response.data["workflows"]]
        assert pack_ids == ["lab_fulfillment"]

    def test_visit_workflow_for_pharmacist(self, api_client, pharmacist_user, open_visit):
        client = api_client(user=pharmacist_user)
        response = client.get(f"/api/v1/guide/visits/{open_visit.id}/workflow/")
        assert response.status_code == status.HTTP_200_OK
        pack_ids = [w["pack_id"] for w in response.data["workflows"]]
        assert pack_ids == ["pharmacy_fulfillment"]

    def test_create_sandbox_visit(self, api_client, doctor_user, test_org):
        client = api_client(user=doctor_user)
        response = client.post("/api/v1/guide/sandbox-visit/", {}, format="json")
        assert response.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)
        assert "visit_id" in response.data

        repeat = client.post("/api/v1/guide/sandbox-visit/", {}, format="json")
        assert repeat.status_code == status.HTTP_200_OK
        assert repeat.data["visit_id"] == response.data["visit_id"]

    def test_org_settings_guide_modules(self, api_client, doctor_user, test_org):
        OrganizationUser.objects.filter(
            organization=test_org, user=doctor_user
        ).update(role="ADMIN")

        client = api_client(user=doctor_user)
        response = client.patch(
            f"/api/v1/organizations/{test_org.id}/settings/",
            {"guide_modules": {"telemedicine": False, "anc": False}},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["guide_modules"]["telemedicine"] is False
        assert response.data["guide_modules"]["anc"] is False
        assert response.data["guide_modules"]["core"] is True

        test_org.refresh_from_db()
        assert test_org.guide_modules["telemedicine"] is False
