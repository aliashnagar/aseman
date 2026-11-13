from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0012_sociallink"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="inventory_deducted",
            field=models.BooleanField(default=False, verbose_name="کسر موجودی انجام شده"),
        ),
    ]
