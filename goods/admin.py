from django.contrib import admin
from django.core.cache import cache

from goods.models import Goods,GoodsSKU,GoodsType, IndexTypeGoodsBanner, IndexGoodsBanner, IndexPromotionBanner
# Register your models here.

class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from celery_tasks.tasks import generate_static_index_html
        # 生成首页静态页面
        generate_static_index_html.delay()
        # 清除首页缓存
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()
        # 清除首页缓存
        cache.delete('index_page_data')

class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass

class GoodsTypeAdmin(BaseModelAdmin):
    pass

class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass

class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass

admin.site.register(Goods)
admin.site.register(GoodsSKU)
admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)