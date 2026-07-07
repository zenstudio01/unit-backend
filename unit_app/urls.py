from django.urls import path
from . import views
from .api_views.auth import *
from .api_views.dashboard import *
from .api_views.property import *
from .api_views.tenants import *
from .api_views.admin import *
from .api_views.landlord import *
from .api_views.subscription import *
from .api_views.store import *

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

    # admin - users
    path('admin/users/', admin_users_list, name='admin_users_list'),
    path('admin/users/<int:pk>/toggle-active/', admin_toggle_active, name='admin_toggle_active'),
    path('admin/users/<int:pk>/verify/', admin_verify_user, name='admin_verify_user'),
    path('admin/users/<int:pk>/reset-password/', admin_reset_password, name='admin_reset_password'),
    path('admin/users/<int:pk>/update-profile/', admin_update_profile, name='admin_update_profile'),
    path('admin/users/<int:pk>/', admin_delete_user, name='admin_delete_user'),

    # admin - dashboard
    path('admin/dashboard/metrics/', admin_dashboard_metrics, name='admin_dashboard_metrics'),

    # landlord
    path('landlords/', landlord_list, name='landlord_list'),
    path('landlords/create/', landlord_create, name='landlord_create'),
    path('landlords/<int:pk>/payout/', landlord_process_payout, name='landlord_payout'),

    # subscription
    path('packages/', get_packages, name='get_packages'),

    # store
    path('get_stores/', get_stores, name='get_stores'),

]