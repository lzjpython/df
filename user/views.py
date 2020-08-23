import re

from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django_redis import get_redis_connection
from django.core.paginator import Paginator


from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired

from user.models import User, Address
from goods.models import GoodsSKU
from order.models import OrderGoods, OrderInfo

from celery_tasks.tasks import send_register_active_email
from utils.mixin import LoginRequiredMinin
# Create your views here.

#注册类
class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        password1 = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        user1 = True
        if not all([username, password, password1, email, allow]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            user1 = False

        if user1:
            return render(request, 'register.html', {'errmsg': '用户已存在'})

        #创建用户
        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_active = 0
        user.save()

        #加密用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)
        token = token.decode()

        # 发邮件
        send_register_active_email.delay(email, username, token)
        return redirect(reverse('goods:index'))


class ActiveView(View):
    def get(self, request, token):
        serializer = Serializer(settings.SECRET_KEY, '3600')
        try:
            info = serializer.loads(token)
            user_id = info['confirm']

            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            return HttpResponse('激活链接已过期')


class LoginView(View):
    ''''''
    def get(self, request):
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remeber = request.POST.get('remeber')

        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})

        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:

                login(request, user)

                next_url = request.GET.get('next', reverse('goods:index'))

                response = redirect(next_url)

                if remeber == 'on':
                    response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    response.delete_cookie('username')
                return response
            else:
                return render(request, 'login.html', {'errmsg': '请激活你的账户'})
        else:
            return render(request, 'login.html', {'errmsg': '用户名或密码不对'})

class LogoutView(View):
    def get(self, request):
        logout(request)

        return redirect(reverse('goods:index'))

class UserInfoView(LoginRequiredMinin, View):
    def get(self, request):

        user = request.user
        address = Address.objects.get_default_address(user=user)

        #获取用户浏览记录
        con = get_redis_connection('default')
        history_key = 'history_%d'%user.id
        sku_ids = con.lrange(history_key, 0, 4)
        goods_li = []
        try:
            for id1 in sku_ids:
                goods = GoodsSKU.objects.get(id=id1)
                goods_li.append(goods)
        except:
            context = {'page': 'user',
                       'address': address,
                       'user': user}
        context = {'page': 'user',
                   'address': address,
                   'user': user,
                   'goods_li': goods_li}
        return render(request, 'user_center_info.html', context)

class UserOrderView(LoginRequiredMinin, View):
    def get(self, request, page):
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        for order in orders:
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)
            for order_sku in order_skus:
                amount = order_sku.count*order_sku.price
                order_sku.amount = amount
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            order.order_skus = order_skus

        # 对数据进行分页
        paginator = Paginator(orders, 1)
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > paginator.num_pages:
            page = 1
        # 获取第page页的实例对象
        order_page = paginator.page(page)
        # 控制页码
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(num_pages - 2, num_pages + 3)

        context = {
                   'order_page': order_page,
                   'pages': pages,
                   'page': 'order'
        }

        return render(request, 'user_center_order.html', context)

class AddressView(LoginRequiredMinin, View):
    def get(self, request):

        user = request.user

        try:
            address = Address.objects.get(user=user, is_default=True)
        except Address.DoesNotExist:
            address = None

        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整'})

        if not re.match(r'^1[3|4|5|7|8][0-9]{9}', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机格式不合法'})

        user = request.user
        try:
            address = Address.objects.get(user=user, is_default=True)
        except Address.DoesNotExist:
            address = None

        if address:
            is_default = False
        else:
            is_default = True

        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)

        return redirect(reverse('user:address'))