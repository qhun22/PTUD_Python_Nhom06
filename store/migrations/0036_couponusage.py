from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0035_customuser_is_student_verified_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CouponUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('used_at', models.DateTimeField(auto_now_add=True, verbose_name='Thời điểm dùng')),
                ('coupon', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='usages',
                    to='store.coupon',
                    verbose_name='Mã giảm',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='coupon_usages',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Người dùng',
                )),
            ],
            options={
                'verbose_name': 'Lịch sử dùng voucher',
                'verbose_name_plural': 'Lịch sử dùng voucher',
                'ordering': ['-used_at'],
            },
        ),
    ]
