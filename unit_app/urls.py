from django.urls import path
from . import views
from .api_views.auth import *
from .api_views.profile import *
from .api_views.organization import *
from .api_views.dashboard import *
from .api_views.properties import *
from .api_views.finance import *
from .api_views.prop_maintenance import *
from .api_views.owner_dashboard import *
from .api_views.portfolios import *
from .api_views.reports import *
from .api_views.statements import *
from .api_views.owner_profile import *
from .api_views.owner_notifications import *
from .api_views.team import *
from .api_views.invitations import *
from .api_views.prop_units import *
from .api_views.property_structure import *
from .api_views.tenant_payment import *
from .api_views.tenant_profile import *
from .api_views.tenant_notifications import *
from .api_views.tenant_receipts import *
from .api_views.tenant_maintenance import *
from .api_views.kaskazi_integration import *
from .api_views.owner_subscriptions import *
from .api_views.owner_subscription_payments import *
from .api_views.prop_messages import *
from .api_views.prop_worker_verification import *
from .api_views.select_worker import *
from .api_views.record_manual_payment import *
from .api_views.lease import *
from .api_views.invoice import *
from .api_views.prop_profile import *








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
from .api_views.announcements import *
from .api_views.services import *
from .api_views.roles import *
from .api_views.tenant_lease import *

urlpatterns = [
    path('', views.index, name='index'),
    path('health/', health, name='health'),

    # auth
    path('auth/send_test_email/', send_test_email, name='send_test_email'),
    path('auth/refresh_token/', refresh_token, name='refresh_token'),
    path('auth/signin/', signin, name='signin'),
    path('auth/signup/', signup, name='signup'),
    path('auth/delete_account/', delete_account, name='delete_account'),
    path('auth/verify_email/', verify_email, name='verify_email'),
    path('auth/request_reset/', request_reset, name='request_reset'),
    path('auth/reset_password/', reset_password, name='reset_password'),
    path('auth/auth_check/', auth_check, name='auth_check'),
    path('auth/verify_otp/', verify_otp, name='verify_otp'),

    # profile
    path('profile/complete_profile/', complete_profile, name='complete_profile'),


    # organization
    path('organization/create_organization/', create_organization, name='create_organization'),
    path('organization/my_organizations/', my_organizations, name='my_organizations'),
    path('organization/<int:organization_id>/my_organization_roles/', my_organization_roles, name='my_organization_roles'),

    # notifications
    path("notifications/", get_notifications, name="get_notifications"),
    path("notifications/<int:notification_id>/read/", mark_notification_read, name="mark_notification_read"),
    path("notifications/mark_all_read/", mark_all_notifications_read, name="mark_all_notifications_read"),
    path("notifications/unread_count/", notification_unread_count, name="notification_unread_count"),

    # propert manager dashboard
    path("dashboard/manager/", manager_dashboard, name="manager_dashboard"),

    # properties
    path("properties/", get_properties, name="get_properties"),
    path("properties/form_options/", property_form_options, name="property_form_options"),
    path("properties/create/", create_property, name="create_property"),
    path("properties/<int:property_id>/", get_property_details, name="get_property_details"),
    path("properties/owner/", get_owner_properties, name="get_owner_properties"),

    # maintenance
    path("prop/maintenance/", get_manager_maintenance_tickets, name="get_manager_maintenance_tickets"),
    path("prop/maintenance/<int:ticket_id>/", manager_maintenance_detail, name="manager_maintenance_detail"),
    path("prop/maintenance/<int:ticket_id>/status/", manager_update_maintenance_status, name="manager_update_maintenance_status"),
    path("prop/maintenance/<int:ticket_id>/assign/", manager_assign_maintenance, name="manager_assign_maintenance"),
    path("prop/maintenance/<int:ticket_id>/comments/", manager_add_maintenance_comment, name="manager_add_maintenance_comment"),

    # finance
    path("finance/manager/", manager_finance_dashboard, name="manager_finance_dashboard"),

    # owner dashboard
    path("dashboard/owner/", owner_dashboard, name="owner_dashboard"),

    # owner portifolios
    path("portfolios/", get_owner_portfolios, name="get_owner_portfolios"),
    path("portfolios/create/", create_portfolio, name="create_portfolio"),
    path("portfolios/<int:portfolio_id>/", get_portfolio_details, name="get_portfolio_details"),

    # reports
    path("reports/owner/", owner_reports, name="owner_reports"),

    # owner statements
    path("statements/owner/", owner_statements, name="owner_statements"),
    path("statements/owner/details/", owner_statement_details, name="owner_statement_details"),

    # owner profile
    path("profile/owner/", get_owner_profile, name="get_owner_profile"),
    path("profile/owner/update/", update_owner_profile, name="update_owner_profile"),

    # owner notifications
    path("notifications/", get_notifications, name="get_notifications"),
    path("notifications/<int:notification_id>/read/", mark_notification_read, name="mark_notification_read"),
    path("notifications/read-all/", mark_all_notifications_read, name="mark_all_notifications_read"),

    # team
    path("team/", get_team_members, name="get_team_members"),
    path("team/roles/", get_team_roles, name="get_team_roles"),
    path("team/add/", add_team_member, name="add_team_member"),


    # roles
    path("roles/options/", get_role_options, name="get_role_options"),
    path("roles/create/", create_role, name="create_role"),
    path("roles/", get_organization_roles, name="get_organization_roles"),
    path("roles/<int:role_id>/", get_role_details, name="get_role_details"),
    path("roles/<int:role_id>/update/", update_role, name="update_role"),
    path("roles/<int:role_id>/status/", update_role_status, name="update_role_status"),
    path("roles/<int:role_id>/delete/", delete_role, name="delete_role"),


    # invitations
    path("invitations/details/", get_invitation_details, name="get_invitation_details"),
    path("invitations/accept/", accept_invitation, name="accept_invitation"),
    path("invitations/accept_invitation/", accept_invitation_web, name="accept_invitation_web"),

    # prop units
    path("units/form_options/",unit_form_options, name="unit_form_options"),
    path("units/create/", create_unit, name="create_unit"),
    path("units/bulk_create/", bulk_create_units, name="bulk_create_units"),


    # property structure
    path("properties/<int:property_id>/structure/", property_structure, name="property_structure"),
    path("buildings/create/", create_building, name="create_building"),
    path("floors/create/", create_floor, name="create_floor"),
    path("amenities/", get_amenities, name="get_amenities"),
    path("amenities/create/", create_amenity, name="create_amenity"),


    # tenants
    path("tenants/properties/", tenant_properties, name="tenant_properties"),
    path("tenants/available-units/", available_property_units, name="available_property_units"),
    path("tenants/create-and-assign/", create_and_assign_tenant, name="create_and_assign_tenant"),
    path("tenant/activate/", activate_tenant_web, name="activate_tenant_web"),

    path("dashboard/tenant/", tenant_dashboard, name="tenant_dashboard"),
    path("tenant/maintenance/", tenant_maintenance_list, name="tenant_maintenance_list"),
    path("tenant/maintenance/<int:ticket_id>/", tenant_maintenance_detail, name="tenant_maintenance_detail"),
    

    # tenant payments
    path("tenant/payments/", tenant_payments, name="tenant_payments"),
    path("tenant/payments/initiate/", initiate_tenant_payment, name="initiate_tenant_payment"),
    path("payments/mpesa/callback/", mpesa_payment_callback, name="mpesa_payment_callback"),



    # tenant profile
    path("tenant/profile/",tenant_profile, name="tenant_profile"),
    path("tenant/profile/update/", update_tenant_profile, name="update_tenant_profile"),
    path("tenant/change-password/", tenant_change_password, name="tenant_change_password"),

    # tenant notifications
    path("tenant/notifications/", tenant_notifications, name="tenant_notifications"),
    path("tenant/notifications/<int:notification_id>/read/", tenant_notification_mark_read, name="tenant_notification_mark_read"),
    path("tenant/notifications/read-all/", tenant_notifications_mark_all_read, name="tenant_notifications_mark_all_read"),


    # tenant lease
    path("tenant/lease/", tenant_lease, name="tenant_lease"),

    # tenant receipts
    path("tenant/receipts/", tenant_receipts, name="tenant_receipts"),
    path("tenant/receipts/<int:payment_id>/", tenant_receipt_detail, name="tenant_receipt_detail"),

    # tenant maintenance
    path("tenant/maintenance/create-options/", tenant_maintenance_create_options, name="tenant_maintenance_create_options"),
    path("tenant/maintenance/create/", tenant_create_maintenance, name="tenant_create_maintenance"),


    # owner_subscriptions
    path("subscription/packages/", subscription_packages, name="subscription_packages"),
    path("subscription/current/", current_subscription, name="current_subscription"),

    # owner_subscriptions payment
    path("subscription/paystack/initialize/", initialize_subscription_payment, name="initialize_subscription_payment"),
    path("subscription/paystack/verify/<str:reference>/", verify_subscription_payment, name="verify_subscription_payment"),
    path("subscription/paystack/callback/", subscription_paystack_callback, name="subscription_paystack_callback"),
    path("subscription/payments/", subscription_payment_history, name="subscription_payment_history"),


    # prop profile
    path("property_manager/profile/", new_property_manager_profile, name="property_manager_profile"),
    path("property_manager/profile/update/", update_property_manager_profile, name="update_property_manager_profile"),


    # kaskazi integration -- keep this at the end
    path("integrations/kaskazi/services/", kaskazi_services, name="kaskazi_services"),
    path("prop/maintenance/<int:ticket_id>/kaskazi/", maintenance_kaskazi_booking, name="maintenance_kaskazi_booking"),
    path("prop/maintenance/<int:ticket_id>/kaskazi/book/", book_kaskazi_worker, name="book_kaskazi_worker"),
    path("prop/maintenance/<int:ticket_id>/kaskazi/applications/", maintenance_kaskazi_applications, name="maintenance_kaskazi_applications"),

    # prop messages
    path("prop/maintenance/<int:ticket_id>/kaskazi/messages/", maintenance_kaskazi_messages, name="maintenance_kaskazi_messages"),
    path("prop/maintenance/<int:ticket_id>/kaskazi/messages/send/", maintenance_kaskazi_send_message, name="maintenance_kaskazi_send_message"),

    # prop worker verification
    path("prop/maintenance/<int:ticket_id>/kaskazi/verify_worker/", maintenance_kaskazi_verify_worker, name="maintenance_kaskazi_verify_worker"),

    # prop select worker
    path("prop/maintenance/<int:ticket_id>/kaskazi/select_worker/", maintenance_kaskazi_select_worker, name="maintenance_kaskazi_select_worker"),


    # record manual payment
    path("payments/manual/", record_manual_payment, name="record_manual_payment"),


    # lease
    path("leases/create/", create_lease, name="create_lease"),
    path("tenants/", get_organization_tenants, name="get_organization_tenants"),
    path("properties/<int:property_id>/lease-units/", get_property_units_for_lease, name="get_property_units_for_lease"),
    path("leases/<int:lease_id>/", lease_details, name="lease_details"),
    path("tenants/<int:tenant_id>/payment-leases/", tenant_payment_leases, name="tenant_payment_leases"),
    path("leases/<int:lease_id>/payment-invoices/", lease_payment_invoices, name="lease_payment_invoices"),
    path("payments/<int:payment_id>/", payment_details, name="payment_details"),

    # invoice
    path("invoices/create-options/", invoice_create_options, name="invoice_create_options"),
    path("invoices/create/", create_invoice, name="create_invoice"),
    path("invoices/", get_invoices, name="get_invoices"),
    path("invoices/<int:invoice_id>/", invoice_details, name="invoice_details"),















    # property
    path('property_list/', property_list, name='property_list'),
    path('property_create/', property_create, name='property_create'),


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
    path("company/get_company_professionals/", get_company_professionals, name='get_company_professionals'),
    path("company/assign_worker/<int:booking_id>/", assign_worker, name='assign_worker'),
    path("company/booking_details/<int:booking_id>/", booking_details, name="booking_details"),

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
    path("admin_get_company_services/", admin_get_company_services, name='admin_get_company_services'),
    path("get_company_service/<int:service_id>/", get_company_service, name='get_company_service'),
    path("update_company_service/<int:service_id>/", update_company_service, name='update_company_service'),
    path("delete_company_service/<int:service_id>/", delete_company_service, name='delete_company_service'),
    path("get_company_services/<int:company_id>/", get_company_services, name="get_company_services"),


]