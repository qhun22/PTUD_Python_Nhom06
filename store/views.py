"""
Views cho ứng dụng store - QHUN22
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


def home(request):
    """
    Trang chủ của cửa hàng QHUN22
    """
    return render(request, 'store/home.html')


def product_search(request):
    """
    Tìm kiếm sản phẩm
    """
    query = request.GET.get('q', '')
    context = {
        'query': query,
    }
    return render(request, 'store/search.html', context)


def cart_detail(request):
    """
    Chi tiết giỏ hàng
    """
    return render(request, 'store/cart.html')


def order_tracking(request):
    """
    Tra cứu đơn hàng
    """
    return render(request, 'store/order_tracking.html')


def wishlist(request):
    """
    Danh sách sản phẩm yêu thích
    """
    return render(request, 'store/wishlist.html')


def login_view(request):
    """
    Đăng nhập người dùng
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Đăng nhập thành công!')
            return redirect('store:home')
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng!')
    return render(request, 'store/login.html')


def profile(request):
    """
    Trang thông tin tài khoản người dùng
    """
    return render(request, 'store/profile.html')
