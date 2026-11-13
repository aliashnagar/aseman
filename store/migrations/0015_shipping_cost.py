from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0014_faq"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="shipping_cost",
            field=models.PositiveIntegerField(default=0, verbose_name="هزینه ارسال (تومان)"),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_cost",
            field=models.PositiveIntegerField(default=0, verbose_name="هزینه ارسال (تومان)"),
        ),
    ]
