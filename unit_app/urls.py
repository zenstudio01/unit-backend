from django.urls import path
from . import views
from .api_views.auth import *

urlpatterns = [
    path('', views.index, name='index'),

    # auth
    path('send_test_email/', send_test_email, name='send_test_email'),
    path('refresh_token/', refresh_token, name='refresh_token'),
    path('signin/', signin, name='signin'),
    path('signup/', signup, name='signup'),
    path('delete_account/', delete_account, name='delete_account'),
    path('verify_email/', verify_email, name='verify_email'),
    path('request_reset/', request_reset, name='request_reset'),
    path('reset_password/', reset_password, name='reset_password'),
    path('auth_check/', auth_check, name='auth_check'),
]