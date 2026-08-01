from django.contrib import admin
from .models import User, Package, Subscription, Property, Unit, Tenant, RentPayment, Notification, MaintenanceRequest, Company, CompanyService, Professional, CompanyBooking, CompanyBookingPayment, CompanyWallet, CompanyConversation, CompanyMessage, Announcement, CompanyStaff, Lease, RentInvoice, CompanyWalletTransaction, ServiceProvider


admin.site.register(User)
admin.site.register(Package)
admin.site.register(Subscription)
admin.site.register(Property)
admin.site.register(Unit)
admin.site.register(Tenant)
admin.site.register(RentPayment)
admin.site.register(Notification)
admin.site.register(MaintenanceRequest)
admin.site.register(Company)
admin.site.register(CompanyService)
admin.site.register(Professional)
admin.site.register(CompanyBooking)
admin.site.register(CompanyBookingPayment)
admin.site.register(CompanyWallet)
admin.site.register(CompanyConversation)
admin.site.register(CompanyMessage)
admin.site.register(Announcement)
admin.site.register(CompanyStaff)
admin.site.register(Lease)
admin.site.register(RentInvoice)
admin.site.register(CompanyWalletTransaction)
admin.site.register(ServiceProvider)



