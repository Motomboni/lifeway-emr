from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0005_alter_plan_stripe_price_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="paystack_plan_code",
            field=models.CharField(
                blank=True,
                help_text="Paystack Plan code (PLN_xxx) for monthly auto-renew",
                max_length=64,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="auto_renew_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Whether Paystack auto-renewal is active for this subscription",
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="paystack_email_token",
            field=models.CharField(
                blank=True,
                help_text="Paystack subscription email_token (required to disable auto-renew)",
                max_length=64,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="paystack_customer_code",
            field=models.CharField(
                blank=True,
                help_text="Paystack Customer code (CUS_xxx)",
                max_length=64,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="paystack_subscription_code",
            field=models.CharField(
                blank=True,
                help_text="Paystack Subscription code (SUB_xxx)",
                max_length=64,
                null=True,
            ),
        ),
    ]
