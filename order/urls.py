
from django.conf.urls import url
from order.views import OrderPlaceView, OrderCommitView, OrderPayView, CheckPayView, CommentView
urlpatterns = [
    url(r'^place$', OrderPlaceView.as_view(), name='place'),
    url(r'^commit$', OrderCommitView.as_view(), name='commit'),#订单创建
    url(r'^pay$', OrderPayView.as_view(), name='pay'),
    url(r'^check$', CheckPayView.as_view(), name='check'),
    url(r'^comment/(?P<order_id>\d+)$', CommentView.as_view(), name='comment')
]
