from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0013_order_inventory_deducted"),
    ]

    operations = [
        migrations.CreateModel(
            name="FAQ",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.CharField(max_length=240, verbose_name="سوال")),
                ("answer", models.TextField(verbose_name="پاسخ")),
                ("position", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")),
            ],
            options={
                "verbose_name": "سوال پرتکرار",
                "verbose_name_plural": "سوالات پرتکرار",
                "ordering": ["position", "id"],
            },
        ),
    ]
