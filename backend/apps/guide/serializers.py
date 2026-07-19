"""Serializers for guide API."""

from rest_framework import serializers

from .guide_modules import GUIDE_MODULE_KEYS, normalize_guide_modules
from .models import GuideEvent, UserGuideProgress, VisitWorkflowProgress


class UserGuideProgressSerializer(serializers.ModelSerializer):
    guide_modules = serializers.SerializerMethodField()

    class Meta:
        model = UserGuideProgress
        fields = [
            "completed_steps",
            "dismissed_hints",
            "role_launch_completed",
            "guide_preferences",
            "guide_modules",
            "updated_at",
        ]
        read_only_fields = ["updated_at", "guide_modules"]

    def get_guide_modules(self, obj) -> dict[str, bool]:
        org = self.context.get("organization")
        if org is None:
            from .guide_modules import DEFAULT_GUIDE_MODULES

            return dict(DEFAULT_GUIDE_MODULES)
        return normalize_guide_modules(getattr(org, "guide_modules", None))


class GuideProgressUpdateSerializer(serializers.Serializer):
    step_id = serializers.CharField(required=False, allow_blank=True)
    hint_id = serializers.CharField(required=False, allow_blank=True)
    role_launch_role = serializers.CharField(required=False, allow_blank=True)
    preferences = serializers.DictField(required=False)


class AskGuideSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500)


class VisitWorkflowSyncSerializer(serializers.Serializer):
    pack_id = serializers.CharField(max_length=50)
    step_id = serializers.CharField(max_length=50, required=False)
    action = serializers.ChoiceField(
        choices=["complete", "skip", "sync"],
        default="sync",
    )


class VisitWorkflowProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitWorkflowProgress
        fields = ["pack_id", "completed_steps", "skipped_steps", "updated_at"]


class GuideEventSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(choices=[c[0] for c in GuideEvent.EVENT_TYPES])
    article_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    target_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    hint_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    metadata = serializers.DictField(required=False)


class GuideModulesUpdateSerializer(serializers.Serializer):
    guide_modules = serializers.DictField()

    def validate_guide_modules(self, value):
        cleaned = {}
        for key in GUIDE_MODULE_KEYS:
            if key in value:
                cleaned[key] = bool(value[key])
        if not cleaned:
            raise serializers.ValidationError("Provide at least one guide module toggle.")
        return cleaned
