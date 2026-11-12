from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0010_sitesettings_telegram_order_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="footer_instagram_link",
            field=models.CharField(blank=True, max_length=200, verbose_name="لینک اینستاگرام"),
        ),
    ]
