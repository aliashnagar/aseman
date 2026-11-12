from django.db import migrations, models
import django.db.models.deletion


def migrate_footer_social_links(apps, schema_editor):
    SiteSettings = apps.get_model("store", "SiteSettings")
    SocialLink = apps.get_model("store", "SocialLink")

    for site in SiteSettings.objects.all():
        links = (
            (site.footer_channel_label.rstrip(":：") or "کانال تلگرام", "telegram", site.footer_channel_link),
            (site.footer_order_text or "ثبت سفارش", "telegram", site.footer_order_link),
            ("اینستاگرام", "instagram", site.footer_instagram_link),
        )
        for position, (label, icon, url) in enumerate(links):
            if url:
                SocialLink.objects.create(
                    site_id=site.pk,
                    label=label,
                    icon=icon,
                    url=url,
                    position=position,
                )


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0011_sitesettings_footer_instagram_link"),
    ]

    operations = [
        migrations.CreateModel(
            name="SocialLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "label",
                    models.CharField(max_length=60, verbose_name="عنوان"),
                ),
                (
                    "icon",
                    models.CharField(
                        choices=[
                            ("telegram", "تلگرام"),
                            ("instagram", "اینستاگرام"),
                            ("whatsapp", "واتساپ"),
                            ("facebook", "فیسبوک"),
                            ("x", "ایکس (X)"),
                            ("youtube", "یوتیوب"),
                            ("tiktok", "تیک‌تاک"),
                            ("link", "لینک عمومی"),
                        ],
                        default="link",
                        max_length=16,
                        verbose_name="آیکون",
                    ),
                ),
                ("url", models.URLField(max_length=500, verbose_name="لینک")),
                ("position", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="social_links",
                        to="store.sitesettings",
                    ),
                ),
            ],
            options={
                "verbose_name": "شبکه اجتماعی فوتر",
                "verbose_name_plural": "شبکه‌های اجتماعی فوتر",
                "ordering": ["position", "id"],
            },
        ),
        migrations.RunPython(migrate_footer_social_links, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="sitesettings",
            name="footer_instagram_link",
        ),
    ]
