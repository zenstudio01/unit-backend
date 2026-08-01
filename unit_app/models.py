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
    PLATFORM_ROLES = (
        ("platform_admin", "Platform Admin"),
        ("user", "User"),
    )

    full_name = models.CharField(max_length=100)
    role = models.CharField( max_length=20,choices=PLATFORM_ROLES,default="user")
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    profile_image = models.URLField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9,decimal_places=6,null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=255, null=True, blank=True)
    reset_token = models.CharField(max_length=255, null=True, blank=True)
    expo_token = models.CharField(max_length=100, default="", null=True, blank=True)
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
    BILLING_CYCLES = (
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    )

    company = models.ForeignKey("Company",on_delete=models.CASCADE,related_name="subscriptions")
    package = models.ForeignKey(Package,on_delete=models.PROTECT,related_name="subscriptions",)
    billing_cycle = models.CharField(max_length=20,choices=BILLING_CYCLES)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="pending",)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.name} - {self.package.name}"


class SubscriptionPayment(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    subscription = models.ForeignKey(Subscription,on_delete=models.CASCADE,related_name="payments",)
    company = models.ForeignKey( "Company", on_delete=models.CASCADE,related_name="subscription_payments",)
    initiated_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="initiated_subscription_payments",)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    reference = models.CharField(max_length=150, unique=True)
    transaction_id = models.CharField(max_length=150,blank=True,null=True,)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="pending",)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company.name} - {self.reference}"



class Company(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_companies")
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    logo = models.URLField(default="https://res.cloudinary.com/dc68huvjj/image/upload/v1748102584/kwwwa0avlfoeybpi3key.png", blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class CompanyStaff(models.Model):
    ROLES = (
        ("admin", "Admin"),
        ("property_manager", "Property Manager"),
        ("accountant", "Accountant"),
        ("leasing_officer", "Leasing Officer"),
        ("maintenance_officer", "Maintenance Officer"),
    )
    company = models.ForeignKey(Company,on_delete=models.CASCADE,related_name="staff")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=30,choices=ROLES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.role}"


class Landlord(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="landlords")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    national_id = models.CharField(max_length=50)
    tax_number = models.CharField(max_length=50,blank=True,null=True,)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name} - Landlord"



class Property(models.Model):

    PROPERTY_TYPES = (
        ("apartment","Apartment"),
        ("house","House"),
        ("hostel","Hostel"),
        ("office","Office"),
        ("mall","Mall"),
        ("warehouse","Warehouse"),
    )

    STATUS = (
        ("active","Active"),
        ("inactive","Inactive"),
        ("maintenance","Maintenance"),
    )

    company = models.ForeignKey(Company,on_delete=models.CASCADE,related_name="properties")
    landlord = models.ForeignKey(Landlord,on_delete=models.CASCADE,related_name="properties")
    manager = models.ForeignKey(CompanyStaff,on_delete=models.SET_NULL,null=True,blank=True,related_name="managed_properties")
    name = models.CharField(max_length=255)
    property_type = models.CharField(max_length=30,choices=PROPERTY_TYPES)
    description = models.TextField()
    amenities = models.JSONField(default=list)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9,decimal_places=6,null=True,blank=True)
    longitude = models.DecimalField(max_digits=9,decimal_places=6,null=True,blank=True)
    images = models.JSONField(default=list)
    status = models.CharField(max_length=20,choices=STATUS,default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.name



class Unit(models.Model):
    STATUS_CHOICES = (
        ("available", "Available"),
        ("occupied", "Occupied"),
        ("maintenance", "Maintenance"),
        ("reserved", "Reserved"),
        ("inactive", "Inactive"),
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="units",
    )
    unit_number = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    rent = models.DecimalField(max_digits=12, decimal_places=2)
    deposit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    bedrooms = models.PositiveIntegerField(default=0)
    bathrooms = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["property", "unit_number"],
                name="unique_unit_number_per_property",
            ),
        ]

    def __str__(self):
        return f"{self.property.name} - {self.unit_number}"



class Tenant(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="tenants",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tenant_profiles",
    )
    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True,
    )
    emergency_contact_phone = models.CharField(
        max_length=30,
        blank=True,
    )
    national_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "user"],
                name="unique_tenant_per_company",
            ),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.company.name}"


class Lease(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("active", "Active"),
        ("expired", "Expired"),
        ("terminated", "Terminated"),
        ("cancelled", "Cancelled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="leases",
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="leases",
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="leases",
    )
    lease_start = models.DateField()
    lease_end = models.DateField()
    monthly_rent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    security_deposit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    payment_due_day = models.PositiveSmallIntegerField(default=5)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )
    signed_at = models.DateTimeField(null=True, blank=True)
    terminated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        errors = {}

        if self.lease_end <= self.lease_start:
            errors["lease_end"] = "Lease end must be after lease start."

        if self.tenant_id and self.unit_id:
            if self.tenant.company_id != self.unit.property.company_id:
                errors["tenant"] = (
                    "Tenant and unit must belong to the same company."
                )

        if self.company_id and self.unit_id:
            if self.unit.property.company_id != self.company_id:
                errors["unit"] = (
                    "Unit must belong to the lease company."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.tenant.user.full_name} - {self.unit.unit_number}"



class RentInvoice(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("partially_paid", "Partially Paid"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="rent_invoices",
    )
    lease = models.ForeignKey(
        Lease,
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    billing_month = models.DateField()
    rent_amount = models.DecimalField(max_digits=12, decimal_places=2)
    service_charge = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    penalties = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lease", "billing_month"],
                name="unique_monthly_invoice_per_lease",
            ),
        ]

    @property
    def total_due(self):
        return self.rent_amount + self.service_charge + self.penalties

    @property
    def balance(self):
        return self.total_due - self.amount_paid




class RentPayment(models.Model):
    PAYMENT_METHODS = (
        ("mpesa", "M-Pesa"),
        ("bank", "Bank"),
        ("card", "Card"),
        ("cash", "Cash"),
        ("other", "Other"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("reversed", "Reversed"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="rent_payments",
    )
    invoice = models.ForeignKey(
        RentInvoice,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="rent_payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHODS,
    )
    transaction_id = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )
    receipt_number = models.CharField(
        max_length=100,
        unique=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    recorded_by = models.ForeignKey(
        CompanyStaff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_rent_payments",
    )
    paid_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.receipt_number} - {self.amount}"




class MaintenanceRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("emergency", "Emergency"),
    )

    CATEGORY_CHOICES = (
        ("plumbing", "Plumbing"),
        ("electrical", "Electrical"),
        ("cleaning", "Cleaning"),
        ("painting", "Painting"),
        ("security", "Security"),
        ("other", "Other"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="maintenance_requests",
    )
    lease = models.ForeignKey(
        Lease,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_requests",
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name="maintenance_requests",
    )
    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reported_maintenance_requests",
    )
    assigned_staff = models.ForeignKey(
        CompanyStaff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_maintenance_requests",
    )
    assigned_provider = models.ForeignKey(
        "ServiceProvider",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_jobs",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="other",
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    images = models.JSONField(default=list, blank=True)
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.unit.unit_number} - {self.title}"





class Announcement(models.Model):
    TARGET_CHOICES = (
        ("all", "All Company Tenants"),
        ("property", "Specific Property"),
        ("unit", "Specific Unit"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    created_by = models.ForeignKey(
        CompanyStaff,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_announcements",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="announcements",
        null=True,
        blank=True,
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name="announcements",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    target = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES,
        default="property",
    )
    is_active = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)




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
    msg_type = models.CharField(max_length=50, default="general")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.title}"




class CompanyService(models.Model):
    SERVICE_CATEGORY = [
    ("plumbing", "Plumbing"),
    ("electrical", "Electrical"),
    ("cleaning", "Cleaning"),
    ("painting", "Painting"),
    ("roofing", "Roofing"),
    ("carpentry", "Carpentry"),
    ("moving", "Moving"),
    ("security", "Security"),
    ("internet", "Internet"),
    ("other", "Other"),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="services")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=30, choices=SERVICE_CATEGORY, default="other")
    minimum_price = models.DecimalField(max_digits=10, decimal_places=2)
    maximum_price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=100, blank=True, null=True, help_text="Example: 1 Hour, 2 Days")
    image = models.URLField(blank=True, null=True,help_text="Cloudinary image URL")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.name} - {self.title}"

# professional model
class Professional(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='professional_profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='professional_company')
    professional_title = models.CharField(max_length=255)
    years_of_experience = models.PositiveIntegerField()
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.full_name} - {self.company.name}"



class CompanyBooking(models.Model):
    STATUS = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
    ]

    customer = models.ForeignKey(User,on_delete=models.CASCADE,related_name="company_bookings")
    company = models.ForeignKey(Company, on_delete=models.CASCADE,related_name="bookings")
    assigned_worker = models.ForeignKey(Professional, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_jobs")
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    budget = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    status = models.CharField( max_length=20, choices=STATUS,default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.username} -> {self.company.name}"


# payments
class CompanyBookingPayment(models.Model):
    STATUS = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    )
    company_booking = models.OneToOneField(CompanyBooking,on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=50, blank=True, null=True) 
    amount = models.DecimalField( max_digits=10,decimal_places=2)
    revenue = models.DecimalField( max_digits=10,decimal_places=2)
    transaction_id = models.CharField(max_length=100, blank=True,null=True)
    payment_status = models.CharField( max_length=20, choices=STATUS, default="pending")
    receipt_number = models.CharField(max_length=100,blank=True,null=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.id} {self.payment_method} {self.amount} {self.payment_status}"


class CompanyWallet(models.Model):
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    available_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    pending_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    reserved_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.name} - {self.available_balance}"



class CompanyWalletTransaction(models.Model):
    TRANSACTION_TYPES = (
        ("credit", "Credit"),
        ("debit", "Debit"),
    )

    wallet = models.ForeignKey(
        CompanyWallet,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=150, unique=True)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


# conversation models
class CompanyConversation(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="company_conversations")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.full_name} - {self.company.name}"


class CompanyMessage(models.Model):
    conversation = models.ForeignKey(CompanyConversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="company_messages")
    message = models.TextField()
    image = models.URLField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.message[:40]




