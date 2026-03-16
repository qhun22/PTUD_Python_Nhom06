# Data migration: thêm 1 bài blog mẫu nếu chưa có

from django.db import migrations


def create_sample_blog(apps, schema_editor):
    BlogPost = apps.get_model('store', 'BlogPost')
    if BlogPost.objects.exists():
        return
    BlogPost.objects.create(
        title='Chào mừng đến với Blog công nghệ',
        summary='Cập nhật tin tức, mẹo sử dụng và ưu đãi sản phẩm điện thoại, laptop từ QHUN22.',
        content='Đây là bài viết mẫu. Bạn có thể chỉnh sửa hoặc xóa từ Dashboard > BLOG SẢN PHẨM. Thêm các bài viết mới để hiển thị trên trang chủ.',
        is_active=True,
    )


def remove_sample_blog(apps, schema_editor):
    BlogPost = apps.get_model('store', 'BlogPost')
    BlogPost.objects.filter(
        title='Chào mừng đến với Blog công nghệ',
        summary__startswith='Cập nhật tin tức',
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0041_blogpost'),
    ]

    operations = [
        migrations.RunPython(create_sample_blog, remove_sample_blog),
    ]
