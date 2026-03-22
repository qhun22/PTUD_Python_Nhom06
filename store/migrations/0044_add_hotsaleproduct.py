from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0043_add_userbrowselog'),
    ]

    operations = [
        migrations.CreateModel(
            name='HotSaleProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Thứ tự hiển thị')),
                ('is_active', models.BooleanField(default=True, verbose_name='Hiển thị')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='hot_sale_entries',
                    to='store.product',
                    verbose_name='Sản phẩm',
                )),
            ],
            options={
                'verbose_name': 'Sản phẩm Hot Sale',
                'verbose_name_plural': 'Sản phẩm Hot Sale',
                'ordering': ['sort_order', '-created_at'],
            },
        ),
    ]
