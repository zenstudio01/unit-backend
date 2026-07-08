from django.contrib.auth.models import AbstractUser,  BaseUserManager
from django.db import models
from django.utils import timezone


# user model
class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        user = self.model(
            username=username,
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    ROLES = (
        ("admin", "Admin"),
        ("property manager", "Property Manager"),
        ("landlord", "Landlord"),
        ("caretaker", "Caretaker"),
        ("tenant", "Tenant"),
        ("service provider", "Service Provider"),
        ("store owner", "Store Owner"),
        ("equipment supplier", "Equipment Supplier"),
        ("client", "Client"),
    )
    full_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLES)
    email = models.CharField(max_length=100, default="johndoe@example.com")
    phone_number = models.CharField(max_length=20, unique=True)
    username = models.CharField(max_length=150, unique=True)
    profile_image = models.URLField(default="https://res.cloudinary.com/dc68huvjj/image/upload/v1748102584/kwwwa0avlfoeybpi3key.png")
    id_front_image = models.URLField(blank=True,null=True, default="https://res.cloudinary.com/dc68huvjj/image/upload/v1748102584/kwwwa0avlfoeybpi3key.png")
    id_back_image = models.URLField(blank=True,null=True, default="https://res.cloudinary.com/dc68huvjj/image/upload/v1748102584/kwwwa0avlfoeybpi3key.png")
    location = models.CharField(max_length=255,blank=True,null=True)
    latitude = models.DecimalField( max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField( max_digits=9, decimal_places=6, blank=True, null=True)
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=255, null=True, blank=True)
    reset_token = models.CharField(max_length=255, null=True, blank=True)
    expo_token = models.CharField(max_length=100, default="")
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    def __str__(self):
        return self.username


class Package(models.Model):
    CHOICES = (
        ('starter bundle', 'Starter Bundle'),
        ('growth engine', 'Growth Engine'),
        ('enterprise core', 'Enterprise Core'),
    )
    name = models.CharField(max_length=100, choices=CHOICES)
    description = models.TextField()
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2)
    yearly_price = models.DecimalField(max_digits=10, decimal_places=2)
    month_days = models.PositiveIntegerField(default=30)
    year_days = models.PositiveIntegerField(default=365)
    number_of_units = models.PositiveIntegerField(default=0)
    mpesa_daraja = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=False)
    logs_duration = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='subscriptions')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.package.name}"

class Property(models.Model):
    PROPERTY_TYPES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('condo', 'Condo'),
        ('townhouse', 'Townhouse'),
    ]

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('under_maintenance', 'Under Maintenance'),
    ]
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    landlord = models.ForeignKey(User, on_delete=models.CASCADE, related_name='landlord_properties', null=True, blank=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='properties')
    name = models.CharField(max_length=255)
    description = models.TextField()
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    address = models.CharField(max_length=255)
    legal_plot_number = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    images = models.JSONField(default=list)  # Store image URLs as JSON array
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Unit(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('under_maintenance', 'Under Maintenance'),
    ]
    name = models.CharField(max_length=255)
    description = models.TextField()
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='units')
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    max_guests = models.PositiveIntegerField()
    amenities = models.JSONField(default=list)  # Store as JSON array
    status = models.CharField(max_length=20, choices=Property.STATUS_CHOICES, default='available')
    images = models.JSONField(default=list)  # Store image URLs as JSON array
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.property.name}"

class Tenant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='tenant_profile')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='tenants')
    lease_start_date = models.DateField()
    lease_end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.unit.name}"

class RentPayment(models.Model):
    CHOICES = [
        ('mpesa', 'Mpesa'),
        ('paystack', 'Paystack'),
        ('bank', 'Bank'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='rent_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(default=timezone.now)
    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, choices=CHOICES, default="Mpesa")  # Assuming M-Pesa as default
    transaction_id = models.CharField(max_length=255, blank=True, null=True, default="M299920sjsjsk")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tenant.user.full_name} - {self.amount} - {'Paid' if self.is_paid else 'Unpaid'}"


class ServiceProvider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='service_provider_profile')
    services_offered = models.JSONField(default=list)  # Store as JSON array
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.services_offered}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.title}"

class MaintenanceRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='maintenance_requests')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='maintenance_requests')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tenant.user.full_name} - {self.unit.name} - {self.status}"

class Store(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stores')
    store_name = models.CharField(max_length=255, default="Default Store")
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.store_name

class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    product_name = models.CharField(max_length=255)
    description = models.TextField()
    stock_quantity = models.PositiveIntegerField()
    barcode_number = models.CharField(max_length=100, blank=True, null=True)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product_name} - {self.store.store_name}"


# product sales model
class ProductSale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='products')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='store_sales', default=1)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sold_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale # {self.id} for {self.store.store_name} Product {self.product.product_name}"

# payment model
class ProductPayment(models.Model):
    PAYMENT_METHODS = [
        ("mpesa", "Mpesa"),
        ("card", "Card"),
        ("paystack", "Paystack"),
    ]
    STATUS = [
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("pending", "Pending"),
    ]
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=10, choices=STATUS)
    checkout_request_id = models.CharField(max_length=100, default="N/A")
    receipt_number = models.CharField(max_length=100, default="N/A")
    paid_at = models.DateTimeField(default=timezone.now)