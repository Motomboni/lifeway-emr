from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_user_device_type_user_last_login_device_user_phone_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='specialization',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Clinical specialization for doctors (e.g., Gynaecologist)',
                max_length=120,
            ),
        ),
    ]
