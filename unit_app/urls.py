from django.urls import path
from . import views
from .api_views.auth import *
from .api_views.dashboard import *
from .api_views.property import *
from .api_views.tenants import *

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

    # dashboard
    path('dashboard_metrics/', dashboard_metrics, name='dashboard_metrics'),

    # property
    path('property_list/', property_list, name='property_list'),
    path('property_create/', property_create, name='property_create'),

    # tenants
    path('get_tenants/', get_tenants, name='get_tenants'),
    path('add_tenant/', add_tenant, name='add_tenant'),
    path('request_rent/', request_rent, name='request_rent'),

]