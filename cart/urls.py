
from django.conf.urls import url
from cart.views import CartAdd, CartInfoView, CartUpdateView, CartDeleteView
urlpatterns = [
    url(r'^add$', CartAdd.as_view(), name='add'),
    url(r'^$', CartInfoView.as_view(), name='show'),
    url(r'^update$', CartUpdateView.as_view(), name='update'),
    url(r'^delete$', CartDeleteView.as_view(), name='delete'),
]
