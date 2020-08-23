from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from django_redis import get_redis_connection

from utils.mixin import LoginRequiredMinin
from goods.models import GoodsSKU
# Create your views here.

class CartAdd(View):
    '''购物车添加商品'''
    def post(self, request):

        if not request.user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg': '请先登录'})

        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        if not all([sku_id, count]):
            return JsonResponse({'res':1, 'errmsg': '数据不完整'})

        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res':2, 'errmsg': '商品数目出错'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res':3, 'errmsg': '商品不存在'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%request.user.id
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            count += int(cart_count)
        if count > sku.stock:
            return JsonResponse({'res':4, 'errmsg': '商品库存不足'})

        conn.hset(cart_key, sku_id, count)

        total_count = conn.hlen(cart_key)

        return JsonResponse({'res':5, 'total_count':total_count, 'message': '添加成功'})

class CartInfoView(LoginRequiredMinin, View):
    def get(self, request):

        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%request.user.id
        cart_dict = conn.hgetall(cart_key)

        skus = []
        total_count = 0
        total_price = 0

        for sku_id, count in cart_dict.items():
            count = int(count)
            sku = GoodsSKU.objects.get(id=sku_id)

            amount = sku.price*count

            sku.amount = amount
            sku.count = count
            skus.append(sku)

            total_count += count
            total_price +=amount

        context = {'total_count': total_count,
                   'total_price': total_price,
                   'skus': skus}
        return render(request, 'cart.html', context)

class CartUpdateView(View):
    '''购物车添加商品'''
    def post(self, request):

        if not request.user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%request.user.id

        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})
        conn.hset(cart_key, sku_id, count)
        #计算购物车总数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'res': 5, 'total_count': total_count, 'message': '更新成功'})

class CartDeleteView(View):
    def post(self, request):
        if not request.user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        sku_id = request.POST.get('sku_id')
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的商品id'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%request.user.id

        conn.hdel(cart_key, sku_id)
        # 计算购物车总数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'res': 3, 'total_count': total_count, 'message': '删除成功'})