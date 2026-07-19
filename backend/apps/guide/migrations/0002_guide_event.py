# Generated migration for GuideEvent model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0007_organization_guide_modules"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("guide", "0001_guide_and_sandbox_visit_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="GuideEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_role", models.CharField(max_length=50)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("ask", "Ask Guide query"),
                            ("article_open", "Article opened"),
                            ("spotlight", "Spotlight shown"),
                            ("hint_dismiss", "Hint dismissed"),
                            ("role_launch_step", "Role launch step"),
                            ("role_launch_complete", "Role launch complete"),
                            ("command_palette", "Command palette"),
                        ],
                        max_length=50,
                    ),
                ),
                ("article_id", models.CharField(blank=True, max_length=100)),
                ("target_id", models.CharField(blank=True, max_length=100)),
                ("hint_id", models.CharField(blank=True, max_length=100)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="guide_events",
                        to="organizations.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="guide_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Guide Event",
                "verbose_name_plural": "Guide Events",
                "db_table": "guide_events",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["organization", "created_at"], name="guide_event_org_created_idx"),
                    models.Index(fields=["event_type", "created_at"], name="guide_event_type_created_idx"),
                    models.Index(fields=["article_id"], name="guide_event_article_idx"),
                ],
            },
        ),
    ]
