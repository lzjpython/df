from django.contrib.auth.decorators import login_required

class LoginRequiredMinin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiredMinin, cls).as_view(**initkwargs)
        return login_required(view)