from django.contrib import admin
from .models import User, Package, Subscription, Property, Unit, Tenant, RentPayment, ServiceProvider, Notification, MaintenanceRequest, Store, Product


admin.site.register(User)
admin.site.register(Package)
admin.site.register(Subscription)
admin.site.register(Property)
admin.site.register(Unit)
admin.site.register(Tenant)
admin.site.register(RentPayment)
admin.site.register(ServiceProvider)
admin.site.register(Notification)
admin.site.register(MaintenanceRequest)
admin.site.register(Store)
admin.site.register(Product)