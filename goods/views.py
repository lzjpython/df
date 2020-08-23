from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django_redis import get_redis_connection
from django.core.cache import cache
from django.core.paginator import Paginator

from goods.models import GoodsType, IndexTypeGoodsBanner, IndexGoodsBanner, IndexPromotionBanner, \
                         GoodsSKU
from order.models import OrderGoods
# Create your views here.
# def index(request):
#     return render(request, 'index.html')

class IndexView(View):
    def get(self, request):
        # from celery_tasks.tasks import generate_static_index_html
        # generate_static_index_html.delay()
        # 尝试获取缓存
        context = cache.get('index_page_data')
        if context is None:
            '''没有缓存'''
            # print('111111111111111')
            types = GoodsType.objects.all()

            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # type_goods_banners = IndexTypeGoodsBanner.objects.all()
            for type1 in types:
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type1, display_type=1)
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type1, display_type=0)
                type1.image_banners = image_banners
                type1.title_banners = title_banners

            # 设置缓存
            context = {
                'types': types,
                'goods_banners': goods_banners,
                'promotion_banners': promotion_banners,
            }
            # key value timeout
            cache.set('index_page_data', context, 3600)


        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)

        context.update(cart_count=cart_count)
        return render(request, 'index.html', context)

class DetailView(View):
    '''详情页面'''
    def get(self, request, goods_id):
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 商品分类
        types = GoodsType.objects.all()
        # 商品评论
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')
        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]
        # 获取同一spu的其他商品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)
        # 获取购物车
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

            # 添加用户浏览记录
            conn = get_redis_connection('default')
            history_key = 'history_%d'%user.id
            conn.lrem(history_key, 0, goods_id)
            conn.lpush(history_key, goods_id)
            conn.ltrim(history_key, 0, 4)

        context = {'sku': sku,
                   'types': types,
                   'sku_orders': sku_orders,
                   'new_skus': new_skus,
                   'cart_count': cart_count}
        return render(request, 'detail.html', context)

class ListView(View):
    '''列表页'''
    def get(self, request, type_id, page):
        try:
            type1 = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 获取分类
        types = GoodsType.objects.all()

        sort = request.GET.get('sort')

        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type1).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type1).order_by('-sales')
        else:
            sort = 'dafault'
            skus = GoodsSKU.objects.filter(type=type1).order_by('-id')

        # 对数据进行分页
        paginator = Paginator(skus, 1)
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > paginator.num_pages:
            page = 1
        # 获取第page页的实例对象
        skus_page = paginator.page(page)
        #控制页码
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)
        elif page <= 3 :
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages-4, num_pages+1)
        else:
            pages = range(num_pages-2, num_pages+3)
        # 获取购物车
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type1).order_by('-create_time')[:2]

        context = {'type1': type1,
                   'types': types,
                   'skus_page': skus_page,
                   'new_skus': new_skus,
                   'cart_count': cart_count,
                   'pages': pages,
                   'sort': sort}
        return render(request, 'list.html', context)