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
from .api_views.property_manager import *
from .api_views.units import *
from .api_views.push_notifications import *
from .api_views.company import *
from .api_views.notifications import *
from .api_views.payments import *
from .api_views.client import *
from .api_views.health import *
from .api_views.chat import *
from .api_views.maintenance import *
from .api_views.announcements import *
from .api_views.services import *

urlpatterns = [
    path('', views.index, name='index'),
    path('health/', health, name='health'),

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
    path("get_properties_with_units/", get_properties_with_units, name="get_properties_with_units"),
    path('tenant_dashboard/', tenant_dashboard, name='tenant_dashboard'),
    path('tenant_announcements/', tenant_announcements, name='tenant_announcements'),
    path('create_maintenance_request/', create_maintenance_request, name='create_maintenance_request'),
    path('get_my_maintenance_requests/', get_my_maintenance_requests, name='get_my_maintenance_requests'),
    path("tenant_rent_payments/", tenant_rent_payments, name='tenant_rent_payments'),
    path("tenant_profile/", tenant_profile, name="tenant_profile"),

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
    path('landlords/add_landlord/', add_landlord, name='add_landlord'),
    path('landlords/<int:pk>/payout/', landlord_process_payout, name='landlord_payout'),
    path("landlords/landlord_dashboard/", landlord_dashboard, name="landlord_dashboard"),
    path("landlords/landlord_analytics/", landlord_analytics, name="landlord_analytics"),

    # subscription
    path('packages/', get_packages, name='get_packages'),
    path("property_manager_subscribe_plan/", property_manager_subscribe_plan, name='subscribe_plan'),
    path("property_manager_verify_subscription/<str:reference>/", property_manager_verify_subscription, name='verify_subscription'),
    path("property_manager_subscription_callback/", property_manager_subscription_callback, name='subscription_callback'),

    # store
    path('get_stores/', get_stores, name='get_stores'),
    path('store/dashboard_metrics/', store_dashboard_metrics, name='store_dashboard_metrics'),
    path('store/sales_record/', record_sale, name='store_sales_record'),
    path('store/add_product/', add_product, name='store_add_product'),
    path('store/get_products/', get_products, name='store_get_products'),
    path('store/add_stock/', add_stock, name='store_add_stock'),
    path("store/get_orders/", get_orders, name="get_orders"),
    path("store/get_payments/", get_payments, name="get_payments"),
    path("store/profile/", get_store_profile, name="get_store_profile"),
    path("store/profile_update/", update_store_profile, name="update_store_profile"),

    # property manager
    path("prop/dashboard_statistics/", dashboard_statistics, name='dashboard_statistics'),
    path("prop/payment_summary/", payment_summary, name='payment_summary'),
    path("prop/get_payments/", get_payments, name='get_payments'),
    path("property_manager_profile/", property_manager_profile, name="property_manager_profile"),
    path("property_manager_maintenance_requests/", property_manager_maintenance_requests, name='property_manager_maintenance_requests'),
    path("update_maintenance_status/<int:request_id>/", update_maintenance_status, name='update_maintenance_status'),
    path("property_manager_maintenance_requests/", property_manager_maintenance_requests, name='property_manager_maintenance_requests'),
    path("update_maintenance_status/<int:request_id>/", update_maintenance_status, name='update_maintenance_status'),
    path("get_maintenance_requests/", get_maintenance_requests, name="get_maintenance_requests"),

    # property manager announcements
    path("create_announcement/", create_announcement, name='create_announcement'),
    path("get_announcements/", get_announcements, name='get_announcements'),
    path("update_announcement/<int:announcement_id>/", update_announcement, name='update_announcement'),
    path("delete_announcement/<int:announcement_id>/", delete_announcement, name='delete_announcement'),

    # units
    path("units/get_my_units/", get_my_units, name="get_my_units"),
    path("units/update_unit/<int:unit_id>/", update_unit, name='update_unit'),
    path("get_available_units/", get_available_units, name="get_available_units"),
    path("get_unit/<int:unit_id>/", get_unit, name="get_unit"),

    # push notifications
    path("send_expo_token/<int:user_id>/<str:expo_token>/", send_expo_token, name='send_expo_token'),

    # company
    path("get_all_companies/", get_all_companies, name='get_all_compamies'),
    path("get_company_profile/", get_company_profile, name="get_company_profile"),
    path("update_company_profile/", update_company_profile, name="update_company_profile"),
    path("get_company/<int:company_id>/", get_company, name='get_company'),
    path("book_company/", book_company, name='book_company'),
    path("get_company_bookings/", get_company_bookings, name='get_company_bookings'),
    path("old_company_dashboard/", old_company_dashboard, name='old_company_dashboard'),
    path("accept_booking/<int:booking_id>/", accept_booking, name='accept_booking'),
    path("reject_booking/<int:booking_id>/", reject_booking, name='reject_booking'),
    path("company/company_dashboard/", company_dashboard, name="company_dashboard"),
    path("company/company_profile/", company_profile, name="company_profile"),
    path("company/update_company_profile/", update_company_profile, name="update_company_profile"),
    path("company/company_professionals/", company_professionals, name='company_professionals'),
    path("company/add_professional/", add_professional, name='add_professional'),
    path("company/update_professional/<int:id>/", update_professional, name='update_professional'),
    path("company/delete_professional/<int:id>/", delete_professional, name='delete_professional'),

    # notifications
    path("get_notifications/", get_notifications, name='get_notifications'),

    # payments
    path("subscribe_plan/", subscribe_plan, name='subscribe_plan'),
    path("verify_payment/", verify_payment, name='verify_payment'),
    path("payment_callback/", payment_callback, name='payment_callback'),
    path("book_property/", book_property, name='book_property'),
    path("verify_property_booking_payment/", verify_property_booking_payment, name='verify_property_booking_payment'),
    path("property_booking_payment_callback/", property_booking_payment_callback, name='property_booking_payment_callback'),

    # client
    path("get_user_bookings/", get_user_bookings, name='get_user_bookings'),

    # chat
    path("send_company_message/", send_company_message, name='send_company_message'),
    path("company_reply/", company_reply, name='company_reply'),
    path("company_chat/<int:company_id>/", company_chat, name='company_chat'),
    path("company_conversations/", company_conversations, name='company_conversations'),
    path("customer_conversations/", customer_conversations, name='customer_conversations'),
    path("mark_company_messages_read/", mark_company_messages_read, name='mark_company_messages_read'),
    path("company_conversation_messages/<int:conversation_id>/", company_conversation_messages, name='company_conversation_messages'),

    # services
    path("create_company_service/", create_company_service, name='create_company_service'),
    path("get_company_services/", get_company_services, name='get_company_services'),
    path("get_company_service/<int:service_id>/", get_company_service, name='get_company_service'),
    path("update_company_service/<int:service_id>/", update_company_service, name='update_company_service'),
    path("delete_company_service/<int:service_id>/", delete_company_service, name='delete_company_service'),


]