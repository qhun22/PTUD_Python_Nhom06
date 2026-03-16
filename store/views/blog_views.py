"""
Blog Posts Views
"""
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required


@csrf_exempt
def blog_list(request):
    """Lấy danh sách tất cả bài viết blog - công khai"""
    from store.models import BlogPost

    try:
        blogs = BlogPost.objects.filter(is_active=True).order_by('-created_at')
        blog_data = []
        for blog in blogs:
            blog_data.append({
                'id': blog.id,
                'title': blog.title,
                'summary': blog.summary,
                'content': blog.content,
                'image_url': blog.image.url if blog.image else None,
                'is_active': blog.is_active,
                'created_at': blog.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': blog.updated_at.strftime('%Y-%m-%d %H:%M:%S') if blog.updated_at else None
            })
        return JsonResponse({'success': True, 'blogs': blog_data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)


@csrf_exempt
@login_required
def blog_add(request):
    """Thêm bài viết blog mới"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)

    from store.models import BlogPost

    try:
        title = request.POST.get('title', '').strip()
        summary = request.POST.get('summary', '').strip()
        content = request.POST.get('content', '').strip()
        image = request.FILES.get('image')
        is_active = request.POST.get('is_active', 'true').lower() == 'true'

        if not title:
            return JsonResponse({'success': False, 'message': 'Vui lòng nhập tiêu đề!'}, status=400)

        blog = BlogPost.objects.create(
            title=title,
            summary=summary,
            content=content,
            image=image,
            is_active=is_active
        )

        return JsonResponse({
            'success': True,
            'message': 'Đã thêm bài viết blog!',
            'blog': {
                'id': blog.id,
                'title': blog.title,
                'summary': blog.summary,
                'image_url': blog.image.url if blog.image else None,
                'is_active': blog.is_active,
                'created_at': blog.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)


@csrf_exempt
@login_required
def blog_update(request):
    """Cập nhật bài viết blog"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)

    from store.models import BlogPost

    try:
        blog_id = request.POST.get('blog_id')
        if not blog_id:
            return JsonResponse({'success': False, 'message': 'Thiếu ID bài viết!'}, status=400)

        blog = BlogPost.objects.get(id=blog_id)

        title = request.POST.get('title', '').strip()
        summary = request.POST.get('summary', '').strip()
        content = request.POST.get('content', '').strip()
        image = request.FILES.get('image')
        is_active = request.POST.get('is_active', '').lower() == 'true'

        if title:
            blog.title = title
        blog.summary = summary
        blog.content = content
        blog.is_active = is_active

        if image:
            if blog.image:
                old_path = blog.image.path
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass
            blog.image = image

        blog.save()

        return JsonResponse({
            'success': True,
            'message': 'Đã cập nhật bài viết blog!',
            'blog': {
                'id': blog.id,
                'title': blog.title,
                'summary': blog.summary,
                'image_url': blog.image.url if blog.image else None,
                'is_active': blog.is_active,
                'updated_at': blog.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except BlogPost.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Bài viết không tồn tại!'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)


@csrf_exempt
@login_required
def blog_delete(request):
    """Xóa bài viết blog"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Không có quyền!'}, status=403)

    from store.models import BlogPost

    try:
        blog_id = request.POST.get('blog_id')
        if not blog_id:
            return JsonResponse({'success': False, 'message': 'Thiếu ID bài viết!'}, status=400)

        blog = BlogPost.objects.get(id=blog_id)

        if blog.image:
            image_path = blog.image.path
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception:
                    pass

        blog_title = blog.title
        blog.delete()

        return JsonResponse({'success': True, 'message': f'Đã xóa bài viết "{blog_title}"!'})
    except BlogPost.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Bài viết không tồn tại!'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Lỗi: {str(e)}'}, status=500)
