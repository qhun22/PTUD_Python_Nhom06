from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0044_add_hotsaleproduct'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='cost_price',
            field=models.DecimalField(
                blank=True,
                decimal_places=0,
                max_digits=15,
                null=True,
                verbose_name='Giá vốn nhập hàng (VNĐ)',
            ),
        ),
    ]
