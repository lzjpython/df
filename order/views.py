from datetime import datetime
import os

from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django.http import JsonResponse
from django.db import transaction
from django_redis import get_redis_connection
from django.conf import settings

from alipay import AliPay
# Create your views here.

from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods
from user.models import Address
from utils.mixin import LoginRequiredMinin

class OrderPlaceView(LoginRequiredMinin, View):
    '''订单提交'''
    def post(self, request):
        sku_ids = request.POST.getlist('sku_ids')

        if not sku_ids:
            return redirect(reverse('cart:show'))

        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%request.user.id

        skus = []
        total_count = 0
        total_price = 0
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            count = conn.hget(cart_key, sku_id)
            amount = sku.price*int(count)
            sku.count = count
            sku.amount = amount
            skus.append(sku)
            total_count += int(count)
            total_price += amount

        # 运费，有自己的子系统，这里写死
        transit_price = 10
        total_pay = total_price + transit_price

        # 获取用户收件地址
        addrs = Address.objects.filter(user=request.user)

        sku_ids = ','.join(sku_ids)

        context = {
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'sku_ids': sku_ids,
            'addrs': addrs,
        }

        return render(request, 'place_order.html', context)

#加悲观锁视图类
class OrderCommitView(View):
    # 事物装饰器
    @transaction.atomic()
    def post(self, request):
        if not request.user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法的支付方式'})

        try:
            addr = Address.objects.get(id=int(addr_id))
        except Address.Does.NotExist:
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})

        # 组织参数
        #订单id:时间+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(request.user.id)
        # 运费：写死
        transit_price = 10
        #总数目与总金额
        total_count = 0
        total_price = 0
        #设置保存点
        save_id = transaction.savepoint()
        try:
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=request.user,
                                             addr=addr,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)
            sku_ids = sku_ids.split(',')
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%request.user.id

            for sku_id in sku_ids:
                try:
                    # 加悲观锁
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                count = conn.hget(cart_key, sku_id)

                # 判断商品库存
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price)

                # 更新库存与销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()

                amount = sku.price*int(count)
                total_count += int(count)
                total_price += amount

            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)

        # 删除购物车记录
        conn.hdel(cart_key, *sku_ids)

        return JsonResponse({'res': 5, 'message': '创建成功'})

# 加乐观锁
class OrderCommitView(View):
    # 事物装饰器
    @transaction.atomic()
    def post(self, request):
        if not request.user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法的支付方式'})

        try:
            addr = Address.objects.get(id=int(addr_id))
        except Address.Does.NotExist:
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})

        # 组织参数
        #订单id:时间+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(request.user.id)
        # 运费：写死
        transit_price = 10
        #总数目与总金额
        total_count = 0
        total_price = 0
        #设置保存点
        save_id = transaction.savepoint()
        try:
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=request.user,
                                             addr=addr,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)
            sku_ids = sku_ids.split(',')
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%request.user.id

            for sku_id in sku_ids:
                for i in range(3):
                    try:
                        # 加悲观锁
                        sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                    count = conn.hget(cart_key, sku_id)

                    # 判断商品库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                    # 更新库存与销量
                    # 加乐观锁，更新时检查
                    orgin_stock = sku.stock
                    new_stock = orgin_stock - int(count)
                    new_sales = orgin_stock + int(count)

                    res = GoodsSKU.objects.filter(id=sku_id, stock=orgin_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        if i == 2:
                            # 尝试三次不成功，则下单失败
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res':7 ,'errmsg': '下单失败'})
                        else:
                            continue
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)



                    amount = sku.price*int(count)
                    total_count += int(count)
                    total_price += amount

                    break

            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)

        # 删除购物车记录
        conn.hdel(cart_key, *sku_ids)

        return JsonResponse({'res': 5, 'message': '创建成功'})

class OrderPayView(View):
    ''''''
    def post(self, request):
        if not request.user.is_authenticated():
            return JsonResponse({'res': 0, 'errmssg': '请先登录'})

        order_id = request.POST.get('order_id')
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单id'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                  user=request.user,
                                  pay_method=3,
                                  order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})
        # 初始化
        # 配置地址
        private_path = os.path.join(settings.BASE_DIR, 'order/app_private_key.pem')
        public_path = os.path.join(settings.BASE_DIR, 'order/alipay_public_key.pem')
        # 获取公私钥字符串
        app_private_key_string = open(private_path).read()
        alipay_public_key_string = open(public_path).read()

        alipay = AliPay(
            appid='2016101900720150',
            app_notify_url=None,
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,
            sign_type='RSA2',
            debug=True
        )
        # 调用支付接口
        total_pay = order.total_price+order.transit_price
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay), #支付总金额
            subject='天天生鲜%s'%order_id,
            return_url=None,
            notify_url=None
        )
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})

class CheckPayView(View):
    ''''''
    def post(self, request):
        if not request.user.is_authenticated():
            return JsonResponse({'res': 0, 'errmssg': '请先登录'})

        order_id = request.POST.get('order_id')
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单id'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                  user=request.user,
                                  pay_method=3,
                                  order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})
        # 初始化
        # 配置地址
        private_path = os.path.join(settings.BASE_DIR, 'order/app_private_key.pem')
        public_path = os.path.join(settings.BASE_DIR, 'order/alipay_public_key.pem')
        # 获取公私钥字符串
        app_private_key_string = open(private_path).read()
        alipay_public_key_string = open(public_path).read()
        alipay = AliPay(
            appid='2016101900720150',
            app_notify_url=None,
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,
            sign_type='RSA2',
            debug=True
        )
        # 调用支付宝的交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            # response = {
            #     "trade_no": "2017032121001004070200176844",  #支付宝交易号
            #     "code": "10000", #接口调用是否成功
            #     "invoice_amount": "20.00",
            #     "open_id": "20880072506750308812798160715407",
            #     "fund_bill_list": [
            #       {
            #         "amount": "20.00",
            #         "fund_channel": "ALIPAYACCOUNT"
            #       }
            #     ],
            #     "buyer_logon_id": "csq***@sandbox.com",
            #     "send_pay_date": "2017-03-21 13:29:17",
            #     "receipt_amount": "20.00",
            #     "out_trade_no": "out_trade_no15",
            #     "buyer_pay_amount": "20.00",
            #     "buyer_user_id": "2088102169481075",
            #     "msg": "Success",
            #     "point_amount": "0.00",
            #     "trade_status": "TRADE_SUCCESS", #支付结果
            #     "total_amount": "20.00"
            # }
            code = response.get('code')
            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                #支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                order.trade_no = trade_no
                order.order_status = 4# 代评价
                order.save()

                return JsonResponse({'res':3 ,'message': '支付成功'})
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                import time
                time.sleep(5)
                continue
            else:
                print(code)
                return JsonResponse({'res': 4, 'message': '支付失败'})

class CommentView(LoginRequiredMinin, View):
    def get(self, request, order_id):
        '''评论页面'''
        if not order_id:
            return redirect(reverse('user:order'))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=request.user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        order_skus = OrderGoods.objects.filter(order_id=order_id)

        for order_sku in order_skus:
            amount = order_sku.count*order_sku.price
            order.amount = amount
        order.order_skus = order_skus

        return render(request, 'order_comment.html', {'order': order})

    def post(self, request, order_id):

        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=request.user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        #获取评论条数
        total_count = request.POST.get('total_count')
        total_count = int(total_count)

        for i in range(1, total_count+1):
            sku_id = request.POST.get('sku_%d'%i)
            content = request.POST.get('content_%d'%i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()
        order.order_status = 5
        order.save()

        return redirect(reverse('user:order', kwargs={'page': 1}))
