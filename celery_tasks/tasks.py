from celery import Celery

from django.core.mail import send_mail
from django.conf import settings
from django.template import loader, RequestContext

from goods.models import GoodsType, IndexTypeGoodsBanner, IndexGoodsBanner, IndexPromotionBanner
import os
#import django
#os.environ.setdefault("DJANGO_SETTINGS_MODULE", "df.settings")
#django.setup()



app = Celery('celery_tasks.tasks', broker='redis://192.168.153.128:6379/8')

@app.task
def send_register_active_email(to_email, username, token):
    # 发邮件
    subject = 'qing'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = '''<h1>%s,欢迎你成为天天生鲜注册会员,点击下面链接完成激活</h1></br>\
                    <a href="http://127.0.0.1:8000/user/active/%s">\
                    http://127.0.0.1/user/active/%s</a>\
                   ''' % (username, token, token)
    send_mail(subject, message, sender, receiver, html_message=html_message)

@app.task
def generate_static_index_html():
    types = GoodsType.objects.all()

    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    type_goods_banners = IndexTypeGoodsBanner.objects.all()
    for type1 in types:
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type1, display_type=1)
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type1, display_type=0)
        type1.image_banners = image_banners
        type1.title_banners = title_banners


    context = {
        'types': types,
        'goods_banners': goods_banners,
        'promotion_banners': promotion_banners,
    }
    #1.使用模板
    temp = loader.get_template('static_index.html')
    #2.定义模板上下文
    # context = RequestContext(request, context)
    #3.渲染
    static_index_html = temp.render(context)

    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_index_html)

