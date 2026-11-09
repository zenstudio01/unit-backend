from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView


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

# project manager
from .api_views.project_manager.project_manager_dashboard import *
from .api_views.project_manager.project_manager_projects import *
from .api_views.project_manager.project_manager_tasks import *
from .api_views.project_manager.project_manager_site_diary import *
from .api_views.project_manager.project_manager_profile import *
from .api_views.project_manager.project_phases_milestones import *
from .api_views.project_manager.project_boq import *
from .api_views.project_manager.project_budget import *
from .api_views.project_manager.project_documents import *
from .api_views.project_manager.project_schedule import *
from .api_views.project_manager.project_procurement import *
from .api_views.project_manager.project_workforce import *
from .api_views.project_manager.project_quality import *
from .api_views.project_manager.project_stakeholders import *
from .api_views.project_manager.project_risk_issues import *
from .api_views.project_manager.project_handover import *
from .api_views.project_manager.off_plan_portal import *
from .api_views.project_manager.off_plan_sales import *



# unit app admin
from .api_views.platform_admin.admin_dashboard import *
from .api_views.platform_admin.admin_auth import *
from .api_views.platform_admin.admin_organizations import *
from .api_views.platform_admin.admin_users import *
from .api_views.platform_admin.admin_properties import *
from .api_views.platform_admin.admin_construction_projects import *
from .api_views.platform_admin.admin_subscriptions import *
from .api_views.platform_admin.admin_payments import *
from .api_views.platform_admin.admin_maintenance import *
from .api_views.platform_admin.admin_tenants import *
from .api_views.platform_admin.admin_reports import *
from .api_views.platform_admin.admin_settings import *









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
    path("leases/", property_manager_leases, name="property-manager-leases"),

    # invoice
    path("invoices/create-options/", invoice_create_options, name="invoice_create_options"),
    path("invoices/create/", create_invoice, name="create_invoice"),
    path("invoices/", get_invoices, name="get_invoices"),
    path("invoices/<int:invoice_id>/", invoice_details, name="invoice_details"),


    # ==========================================
    # project manager module
    # ==========================================
    # dashboard
    path("project-manager/dashboard/", project_manager_dashboard, name="project-manager-dashboard"),
    # projects
    path("project-manager/projects/", project_manager_projects, name="project-manager-projects"),
    path("project-manager/projects/<int:project_id>/", project_manager_project_detail, name="project-manager-project-detail"),

    # tasks
    path("project-manager/tasks/", project_manager_tasks, name="project-manager-tasks"),
    path("project-manager/tasks/<int:task_id>/", project_manager_task_detail, name="project-manager-task-detail"),

    # site diary
    path("project-manager/site-diary/", project_manager_site_diary, name="project-manager-site-diary"),
    path("project-manager/site-diary/<int:entry_id>/", project_manager_site_diary_detail, name="project-manager-site-diary-detail"),

    # profile
    path("project-manager/profile/", project_manager_profile, name="project-manager-profile"),
    path("project-manager/profile/change-password/", project_manager_change_password, name="project-manager-change-password"),

    # project phases and milestones
    path("project-manager/planning/projects/", project_planning_projects, name="project-planning-projects"),
    path("project-manager/phases/", project_phases, name="project-manager-phases"),
    path("project-manager/phases/<int:phase_id>/", project_phase_detail, name="project-manager-phase-detail"),
    path("project-manager/milestones/", project_milestones, name="project-manager-milestones"),
    path("project-manager/milestones/<int:milestone_id>/", project_milestone_detail, name="project-manager-milestone-detail"),
    path("project-manager/planning/summary/",project_planning_summary, name="project-planning-summary"),

    # project BOQ
    path("project-manager/boq/sections/", boq_sections, name="project-manager-boq-sections"),
    path("project-manager/boq/sections/<int:section_id>/", boq_section_detail, name="project-manager-boq-section-detail"),
    path("project-manager/boq/items/", boq_items, name="project-manager-boq-items"),
    path("project-manager/boq/items/<int:item_id>/", boq_item_detail, name="project-manager-boq-item-detail"),
    path("project-manager/boq/summary/", boq_summary, name="project-manager-boq-summary"),

    # project budget and expenses
    path("project-manager/budgets/", project_budgets, name="project-manager-budgets"),
    path("project-manager/budgets/<int:budget_id>/", project_budget_detail, name="project-manager-budget-detail"),
    path("project-manager/expenses/", project_expenses, name="project-manager-expenses"),
    path("project-manager/expenses/<int:expense_id>/", project_expense_detail, name="project-manager-expense-detail"),
    path("project-manager/expenses/<int:expense_id>/status/", project_expense_status, name="project-manager-expense-status"),
    path("project-manager/financial-summary/", project_financial_summary, name="project-manager-financial-summary"),



    # project documents
    path("project-manager/documents/", project_documents, name="project-manager-documents"),
    path("project-manager/documents/summary/", project_document_summary, name="project-manager-document-summary"),
    path("project-manager/documents/<int:document_id>/", project_document_detail, name="project-manager-document-detail"),
    path("project-manager/documents/<int:document_id>/versions/", project_document_versions, name="project-manager-document-versions"),
    path("project-manager/documents/<int:document_id>/review/", project_document_review, name="project-manager-document-review"),
    path("project-manager/documents/<int:document_id>/versions/<int:version_id>/download/", project_document_download, name="project-manager-document-download"),


    # project schedule activities
    path("project-manager/schedules/activities/", schedule_activities, name="project-manager-schedule-activities"),
    path("project-manager/schedules/activities/<int:activity_id>/", schedule_activity_detail, name="project-manager-schedule-activity-detail"),
    path("project-manager/schedules/gantt/", schedule_gantt, name="project-manager-schedule-gantt"),
    path("project-manager/schedules/summary/", schedule_summary, name="project-manager-schedule-summary"),


    # project procurement
    path("project-manager/procurement/suppliers/", procurement_suppliers),
    path("project-manager/procurement/materials/", procurement_materials),
    path("project-manager/procurement/orders/", procurement_orders),
    path("project-manager/procurement/orders/<int:order_id>/", procurement_order_detail),
    path("project-manager/procurement/orders/<int:order_id>/status/", procurement_order_status),
    path("project-manager/procurement/deliveries/", procurement_deliveries),
    path("project-manager/procurement/issues/", procurement_issues),
    path("project-manager/procurement/inventory/", procurement_inventory),
    path("project-manager/procurement/summary/", procurement_summary),


    # project workforce
    path("project-manager/workforce/subcontractors/", workforce_subcontractors),
    path("project-manager/workforce/workers/", workforce_workers),
    path("project-manager/workforce/assignments/", workforce_assignments),
    path("project-manager/workforce/assignments/<int:assignment_id>/", workforce_assignment_detail),
    path("project-manager/workforce/attendance/", workforce_attendance),
    path("project-manager/workforce/tasks/", workforce_tasks),
    path("project-manager/workforce/tasks/<int:task_id>/", workforce_task_detail),
    path("project-manager/workforce/payments/", workforce_payments),
    path("project-manager/workforce/payroll/", workforce_payroll),
    path("project-manager/workforce/summary/", workforce_summary),


    # project quality inspection
    path("project-manager/quality/inspections/", quality_inspections),
    path("project-manager/quality/summary/", quality_summary),
    path("project-manager/quality/inspections/<int:inspection_id>/", quality_inspection_detail),
    path("project-manager/quality/inspections/<int:inspection_id>/status/", quality_inspection_status),
    path("project-manager/quality/inspections/<int:inspection_id>/checklists/", quality_checklists),
    path("project-manager/quality/checklists/<int:checklist_id>/", quality_checklist_detail),
    path("project-manager/quality/inspections/<int:inspection_id>/defects/", quality_defects),
    path("project-manager/quality/defects/<int:defect_id>/status/", quality_defect_status),
    path("project-manager/quality/inspections/<int:inspection_id>/evidence/", quality_upload_evidence),

    # project stakeholders
    path("projects/<int:project_id>/stakeholders/", project_stakeholders),
    path("projects/<int:project_id>/stakeholders/stats/", project_stakeholder_stats),
    path("projects/<int:project_id>/stakeholders/<int:stakeholder_id>/", project_stakeholder_detail),

    # project risks and issues
    path("projects/<int:project_id>/risk-issues/", project_risk_issues),
    path("projects/<int:project_id>/risk-issues/stats/", project_risk_issue_stats),
    path("projects/<int:project_id>/risk-issues/options/", project_risk_issue_options),
    path("projects/<int:project_id>/risk-issues/<int:item_id>/", project_risk_issue_detail),

    # project handover
    path("projects/<int:project_id>/handover/", handover_overview),
    path("projects/<int:project_id>/handover/options/", handover_options),
    path("projects/<int:project_id>/handover/readiness/", handover_readiness),
    path("projects/<int:project_id>/handover/checklist/", checklist_collection),
    path("projects/<int:project_id>/handover/checklist/<int:item_id>/", checklist_detail),
    path("projects/<int:project_id>/handover/documents/", document_collection),
    path("projects/<int:project_id>/handover/documents/<int:link_id>/", document_detail),
    path("projects/<int:project_id>/handover/inspections/", inspection_collection),
    path("projects/<int:project_id>/handover/inspections/<int:link_id>/", inspection_detail),
    path("projects/<int:project_id>/handover/submit/", submit_for_review),
    path("projects/<int:project_id>/handover/acceptances/", acceptance_collection),
    path("projects/<int:project_id>/handover/reopen/", reopen_handover),
    path("projects/<int:project_id>/handover/finalize/", finalize_handover),

    # project off sale plans
    path('projects/<int:project_id>/off-plan/dashboard/', dashboard),
    path('projects/<int:project_id>/off-plan/reservations/', reservations),
    path('projects/<int:project_id>/off-plan/reservations/<int:pk>/', reservation_detail),
    path('projects/<int:project_id>/off-plan/sales/', sales),
    path('projects/<int:project_id>/off-plan/sales/<int:pk>/', sale_detail),
    path('projects/<int:project_id>/off-plan/installments/', installments),
    path('projects/<int:project_id>/off-plan/installments/<int:pk>/', installment_detail),
    path('projects/<int:project_id>/off-plan/payments/', payments),
    path('projects/<int:project_id>/off-plan/payments/<int:pk>/confirm/', confirm_payment),
    path('projects/<int:project_id>/off-plan/payments/<int:pk>/allocate/', allocate_payment),
    path('projects/<int:project_id>/off-plan/handovers/', handovers),
    path('projects/<int:project_id>/off-plan/handovers/<int:pk>/', handover_detail),
    path('projects/<int:project_id>/off-plan/<str:resource>/', collection),
    path('projects/<int:project_id>/off-plan/<str:resource>/<int:pk>/', detail),
    path('buyer/off-plan/dashboard/', dashboard),
    path('buyer/off-plan/reservations/', reservations),
    path('buyer/off-plan/purchases/', purchases),
    path('buyer/off-plan/purchases/<int:sale_id>/', purchase_detail),
    path('buyer/off-plan/installments/', installments),
    path('buyer/off-plan/payments/', payments),
    path('buyer/off-plan/handovers/', handovers),
    path('buyer/off-plan/handovers/<int:handover_id>/accept/', accept_handover),




    # admin
    path("admin/dashboard/", admin_dashboard, name='admin_dashboard'),

    # admin auth
    path("admin/signin/", admin_signin, name="admin-signin"),
    path("admin/me/", admin_me, name="admin-me"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # organizations
    path("admin/organizations/", admin_organizations),
    path("admin/organizations/stats/", admin_organization_stats),
    path("admin/organizations/<int:organization_id>/", admin_organization_detail),
    path("admin/organizations/<int:organization_id>/verification/", admin_organization_verification),


    # users
    path("admin/users/", admin_users, name="admin-users"),
    path("admin/users/stats/", admin_user_stats, name="admin-user-stats"),
    path("admin/users/<int:user_id>/", admin_user_detail, name="admin-user-detail"),
    
    # properties
    path("admin/properties/", admin_properties, name="admin-properties"),
    path("admin/properties/stats/", admin_property_stats, name="admin-property-stats"),
    path("admin/properties/<int:property_id>/", admin_property_detail, name="admin-property-detail"),


    # construction projects
    path("admin/construction-projects/", admin_construction_projects),
    path("admin/construction-projects/stats/", admin_construction_project_stats),
    path("admin/construction-projects/<int:project_id>/", admin_construction_project_detail),


    # subscriptions
    path("admin/subscriptions/", admin_subscriptions),
    path("admin/subscriptions/stats/", admin_subscription_stats),
    path("admin/subscriptions/packages/", admin_subscription_packages),
    path("admin/subscriptions/packages/<int:package_id>/", admin_subscription_package_detail),
    path("admin/subscriptions/payments/", admin_subscription_payments),
    path("admin/subscriptions/<int:subscription_id>/", admin_subscription_detail),


    # payments
    path("admin/payments/", admin_payments),
    path("admin/payments/stats/", admin_payment_stats),
    path("admin/payments/subscriptions/", admin_subscription_transactions),
    path("admin/payments/reconciliations/", admin_payment_reconciliations),
    path("admin/payments/<int:payment_id>/", admin_payment_detail),

    # maintenance
    path("admin/maintenance/", admin_maintenance_tickets),
    path("admin/maintenance/stats/", admin_maintenance_stats),
    path("admin/maintenance/<int:ticket_id>/", admin_maintenance_detail),


    # tenants
    path("admin/tenants/", admin_tenants),
    path("admin/tenants/stats/", admin_tenant_stats),
    path("admin/tenants/leases/", admin_tenant_leases),
    path("admin/tenants/<int:tenant_id>/", admin_tenant_detail),

    # reports
    path("admin/reports/overview/", admin_reports_overview),
    path("admin/reports/revenue/", admin_reports_revenue),
    path("admin/reports/occupancy/", admin_reports_occupancy),
    path("admin/reports/maintenance/", admin_reports_maintenance),
    path("admin/reports/construction/", admin_reports_construction),
    path("admin/reports/subscriptions/", admin_reports_subscriptions),


    # settings
    path("admin/settings/", admin_platform_settings),
    path("admin/settings/profile/", admin_settings_profile),
    path("admin/settings/change-password/", admin_settings_change_password),















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