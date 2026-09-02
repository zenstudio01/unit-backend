from django.contrib.auth.models import AbstractUser,  BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
import uuid

from decimal import Decimal

from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)


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
    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("pending", "Pending"),
        ("suspended", "Suspended"),
        ("deactivated", "Deactivated"),
    )
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=150, unique=True, default="johndoe@example.com")
    phone_number = models.CharField(max_length=20, unique=True)
    username = models.CharField(max_length=150, unique=True)
    profile_image = models.URLField(default="https://res.cloudinary.com/dc68huvjj/image/upload/v1748102584/kwwwa0avlfoeybpi3key.png")
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=100, default="user")
    requested_role = models.CharField(max_length=100, default="")
    email_verification_token = models.CharField(max_length=255, null=True, blank=True)
    reset_token = models.CharField(max_length=255, null=True, blank=True)
    expo_token = models.CharField(max_length=100, default="")
    is_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    national_id_number = models.CharField(max_length=50, blank=True, null=True)
    kra_pin = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    county = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    refresh_token_id = models.CharField(max_length=255, unique=True)
    device_name = models.CharField(max_length=255, blank=True, null=True)
    device_type = models.CharField(max_length=255, blank=True, null=True)
    operating_system = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    last_used_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.user.username} - {self.refresh_token_id}"


class OTPVerification(models.Model):
    PURPOSE_CHOICES = (
        ("registration", "Registration"),
        ("password_reset", "Password Reset"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="otp_verifications",
    )

    code = models.CharField(
        max_length=6,
    )

    purpose = models.CharField(
        max_length=30,
        choices=PURPOSE_CHOICES,
    )

    expires_at = models.DateTimeField()

    is_used = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )


class Organization(models.Model):
    ORGANIZATION_TYPES = [
        ('property_manager', 'Property Manager'),
        ('landlord', 'Landlord'),
        ('developer', 'Developer'),
        ('contractor', 'Contractor'),
        ('consultancy', 'Consultancy'),
        ('investor', 'Investor'),
        ('corporate_client', 'Corporate Client'),
        ('other', 'Other'),
    ]
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organizations')
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    organization_type = models.CharField(max_length=100, blank=True, null=True)
    kra_pin = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    logo = models.URLField(default="https://res.cloudinary.com/dc68huvjj/image/upload/v1748102584/kwwwa0avlfoeybpi3key.png")
    country = models.CharField(max_length=100, blank=True, null=True)
    county = models.CharField(max_length=100, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    website = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class OrganizationBranch(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    branch_code = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    county = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.organization.name}"


class Role(models.Model):
    ROLES_NAMES = [
        ("organization_owner", "Organization Owner"),
        ("organization_admin", "Organization Admin"),
        ("property_manager", "Property Manager"),

        # PROJECT MANAGEMENT
        ("project_manager", "Project Manager"),
        ("site_manager", "Site Manager"),
        ("site_engineer", "Site Engineer"),
        ("quantity_surveyor", "Quantity Surveyor"),
        ("project_accountant", "Project Accountant"),

        ("accountant", "Accountant"),
        ("landlord", "Landlord"),
        ("tenant", "Tenant"),
        ("investor", "Investor"),
        ("caretaker", "Caretaker"),
        ("leasing_agent", "Leasing Agent"),
        ("support_agent", "Support Agent"),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='roles')
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100, choices=ROLES_NAMES)
    description = models.TextField(blank=True, null=True)
    scope = models.CharField(max_length=100, blank=True, null=True)
    is_system_role = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Permission(models.Model):
    MODULES = [
        # 
        ("property", "Property"),
        ("lease", "Lease"),
        ("rent", "Rent"),
        ("maintenance", "Maintenance"),

        # PROJECT MANAGEMENT
        ("project", "Project"),
        ("project_phase", "Project Phase"),
        ("project_task", "Project Task"),
        ("project_milestone", "Project Milestone"),
        ("site_diary", "Site Diary"),
        ("boq", "Bill of Quantities"),
        ("contractor", "Contractor"),
        ("project_risk", "Project Risk"),
        ("project_report", "Project Report"),
    ]
    ACTIONS = [
        ('create', 'Create'),
        ('read', 'Read'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('approve', 'Approve'),
        ('assign', 'Assign'),
        ('record_payment', 'Record Payment'),
    ]
    module = models.CharField(max_length=100, choices=MODULES)
    action = models.CharField(max_length=100, choices=ACTIONS)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='permission_roles')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.role.name} - {self.permission.name}"



class OrganizationMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organization_memberships')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    roles = models.ManyToManyField(Role, related_name='memberships')
    primary_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name="primary_memberships")
    employee_number = models.CharField(max_length=50, unique=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    is_primary_contact = models.BooleanField(default=False)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_memberships')
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.organization.name} - {self.role.name}"



class OrganizationInvitation(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
    )

    first_name = models.CharField(
        max_length=100
    )

    middle_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    last_name = models.CharField(
        max_length=100
    )

    email = models.EmailField()

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    roles = models.ManyToManyField(
        Role,
        related_name="invitations",
    )

    primary_role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_invitations",
    )

    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invitations",
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    expires_at = models.DateTimeField()

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"{self.email} - "
            f"{self.organization.name}"
        )

class Portifolio(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='portifolios')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_portifolios')
    status = models.CharField(max_length=20, choices=(("active", "Active"), ("inactive", "Inactive")), default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.organization.name}"


class Property(models.Model):
    PROPERTY_TYPES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('office', 'Office'),
        ('mall', 'Mall'),
        ('warehouse', 'Warehouse'),
        ('hostel', 'Hostel'),
        ('residential', 'Residential'),
        ('retail', 'Retail'),
        ('warehouse', 'Warehouse'),
        ('industrial', 'Industrial'),
        ('land', 'Land'),
        ('mixed_use', 'Mixed Use'),
        ('student_housing', 'Student Housing'),
        ('other', 'Other'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='properties')
    portifolio = models.ForeignKey(Portifolio, on_delete=models.CASCADE, related_name='properties')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_properties')
    property_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    property_type = models.CharField(max_length=100, choices=PROPERTY_TYPES)
    ownership_type = models.CharField(max_length=100)
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    county = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    year_built = models.PositiveIntegerField(blank=True, null=True)
    total_land_area = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=(("active", "Active"), ("inactive", "Inactive")), default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.portifolio.name}"


class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image_url = models.URLField()

    public_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    is_cover = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.property.name} - Image"


class Building(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='buildings')
    name = models.CharField(max_length=255)
    building_code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    year_built = models.PositiveIntegerField(blank=True, null=True)
    number_of_floors = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=(("active", "Active"), ("inactive", "Inactive")), default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.property.name}"


class Floor(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='floors')
    name = models.CharField(max_length=255)
    floor_code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    floor_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=(("active", "Active"), ("inactive", "Inactive")), default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.building.name}"


class Unit(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('under_maintenance', 'Under Maintenance'),
    ]
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='units')
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='units')
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='units')
    name = models.CharField(max_length=255)
    unit_code = models.CharField(max_length=100, unique=True)
    unit_type = models.CharField(max_length=100)
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    square_footage = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.floor.name}"



class Amenity(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="amenities",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    amenity_type = models.CharField(
        max_length=100
    )

    is_system = models.BooleanField(
        default=False
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "name",
                ],
                name=
                    "unique_organization_amenity",
            )
        ]

    def __str__(self):
        return self.name


class PropertyAmenity(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_amenity')
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE, related_name='prop_amenity')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.amenity.name



class UnitAmenity(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='unit_amenity')
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE, related_name='uni_amenity')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.amenity.name


class Asset(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='organization_asset')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_asset')
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='building_asset')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='unit_asset')
    asset_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    purchase_date = models.DateTimeField(auto_now_add=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_value = models.DecimalField(max_digits=10, decimal_places=2)
    depreciation_method = models.CharField(max_length=100)
    useful_life_years = models.PositiveIntegerField()
    warranty_expiry = models.DateTimeField()
    condition = models.CharField(max_length=200)
    status = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class AssetDepreciationEntries(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='asset_depreciation')
    period_start = models.DateTimeField(auto_now_add=True)
    period_end = models.DateTimeField()
    opening_value = models.DecimalField(max_digits=10, decimal_places=2)
    depreciation_amount = models.DecimalField(max_digits=10, decimal_places=2)
    closing_value = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.asset.name


class Inspection(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='organization_inspections')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_inspections')
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='building_inspections')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='unit_inspections')
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unit_inspector')
    inspection_type = models.CharField(max_length=100)
    scheduled_date = models.DateTimeField()
    completed_at = models.DateTimeField()
    status = models.CharField(max_length=100)
    summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.inspection_type

class InspectionItem(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name='inspection')
    area = models.CharField(max_length=100)
    item = models.CharField(max_length=100)
    condition = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)
    requires_action = models.BooleanField(default=False)

    def __str__(self):
        return self.item


class InspectionMedia(models.Model):
    inspection_item = models.ForeignKey(InspectionItem, on_delete=models.CASCADE, related_name='inspection_item')
    file_url = models.URLField()
    file_type = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Item: {self.inspection_item.item}"


# owners and property ownership
class Owner(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='organization')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user')
    owner_type = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    national_id_number = models.CharField(max_length=8)
    registration_number = models.CharField(max_length=200)
    kra_pin = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Owner: {self.user.first_name}, Email: {self.email}"


class PropertyOwnership(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='owner_property')
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='owner_ownership')
    ownership_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateTimeField(auto_now_add=True)
    effective_to = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Property: {property.name}, Owned by: {owner.user.first_name}"

class OwnerBankAccount(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='owner_bank_account')
    bank_name = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=100) #should be encrypted
    branch_name = models.CharField(max_length=100)
    currency = models.CharField(max_length=10, default="KES")
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Owner: {owner.user.full_name} Bank name: {bank_name}"



# tenants management
class Tenant(models.Model):
    TENANT_TYPES = [
        ("individual", "Individual"),
        ("company", "Company"),
        ("group", "Group"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("blocked", "Blocked"),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,related_name="tenants")
    user = models.ForeignKey(User, on_delete=models.SET_NULL,null=True,blank=True,related_name="tenant_profile")
    tenant_type = models.CharField(max_length=20,choices=TENANT_TYPES,default="individual")
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    national_id_number = models.CharField(max_length=50,null=True,blank=True)
    kra_pin = models.CharField(max_length=50,null=True,blank=True,)
    occupation = models.CharField(max_length=255, null=True, blank=True)
    employer = models.CharField(max_length=255, null=True,blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    def __str__(self):
        return f"{self.full_name} ({self.tenant_type})"


class TenantUnitAssignment(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="tenant_unit_assignments",
    )

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="unit_assignments",
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="tenant_assignments",
    )

    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="tenant_assignments",
    )

    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tenant_assignments",
    )

    move_in_date = models.DateField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    is_active = models.BooleanField(
        default=True,
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unit"],
                condition=models.Q(
                    is_active=True
                ),
                name=
                    "unique_active_tenant_unit",
            ),
        ]

    def __str__(self):
        return (
            f"{self.tenant.full_name} - "
            f"{self.unit.unit_code}"
        )




class TenantEmergencyContact(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE,related_name="emergency_contacts",)
    name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.name} - {self.relationship} ({self.tenant.full_name})"




class TenantScreening(models.Model):
    SCREENING_TYPES = [
        ("identity", "Identity Verification"),
        ("credit", "Credit Check"),
        ("criminal", "Criminal Background Check"),
        ("employment", "Employment Verification"),
        ("income", "Income Verification"),
        ("reference", "Reference Check"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    RESULT_CHOICES = [
        ("pending", "Pending"),
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("review_required", "Review Required"),
    ]

    tenant = models.ForeignKey(Tenant,on_delete=models.CASCADE, related_name="screenings")
    screening_type = models.CharField(max_length=30, choices=SCREENING_TYPES)
    provider = models.CharField(max_length=255,null=True,blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,default="pending",)
    result = models.CharField(max_length=20,choices=RESULT_CHOICES,default="pending")
    notes = models.TextField(blank=True,default="")
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL,null=True,blank=True,related_name="reviewed_tenant_screenings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.tenant.full_name} - {self.get_screening_type_display()}"



# lease management - models
class Lease(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending_approval", "Pending Approval"),
        ("pending_signature", "Pending Signature"),
        ("active", "Active"),
        ("expired", "Expired"),
        ("terminated", "Terminated"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("semi_annually", "Semi Annually"),
        ("annually", "Annually"),
    ]

    organization = models.ForeignKey(Organization,on_delete=models.CASCADE,related_name="leases")
    unit = models.ForeignKey("Unit",on_delete=models.PROTECT,related_name="leases")
    lease_number = models.CharField(max_length=100,unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = models.DecimalField(max_digits=12,decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    billing_day = models.PositiveSmallIntegerField(help_text="Day of the month rent is billed (1-31).",)
    payment_frequency = models.CharField(max_length=20,choices=PAYMENT_FREQUENCY_CHOICES,default="monthly")
    grace_period_days = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_leases")
    approved_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="approved_leases")
    signed_at = models.DateTimeField(null=True,blank=True,)
    terminated_at = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.lease_number} - {self.unit}"





class LeaseTenant(models.Model):
    TENANT_ROLE_CHOICES = [
        ("primary", "Primary Tenant"),
        ("co_tenant", "Co-Tenant"),
        ("occupant", "Occupant"),
        ("guarantor", "Guarantor"),
    ]

    lease = models.ForeignKey(Lease,on_delete=models.CASCADE, related_name="lease_tenants")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tenant_leases")
    tenant_role = models.CharField(max_length=20, choices=TENANT_ROLE_CHOICES,default="co_tenant")
    is_primary = models.BooleanField(default=False)
    joined_at = models.DateField()
    left_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    def __str__(self):
        return f"{self.tenant.full_name} - {self.lease.lease_number}"





class LeaseCharge(models.Model):
    CHARGE_TYPES = [
        ("rent", "Rent"),
        ("service_charge", "Service Charge"),
        ("parking", "Parking"),
        ("water", "Water"),
        ("electricity", "Electricity"),
        ("gas", "Gas"),
        ("security", "Security"),
        ("waste_collection", "Waste Collection"),
        ("internet", "Internet"),
        ("cleaning", "Cleaning"),
        ("other", "Other"),
    ]

    FREQUENCY_CHOICES = [
        ("one_time", "One Time"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("semi_annually", "Semi Annually"),
        ("annually", "Annually"),
    ]

    lease = models.ForeignKey("Lease", on_delete=models.CASCADE, related_name="charges")
    charge_type = models.CharField(max_length=30,choices=CHARGE_TYPES)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12,decimal_places=2)
    frequency = models.CharField(max_length=20,choices=FREQUENCY_CHOICES,default="monthly")
    is_taxable = models.BooleanField(default=False,)
    start_date = models.DateField()
    end_date = models.DateField(null=True,blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.lease.lease_number}"





class LeaseDeposit(models.Model):
    DEPOSIT_TYPES = [
        ("security", "Security Deposit"),
        ("utility", "Utility Deposit"),
        ("key", "Key Deposit"),
        ("cleaning", "Cleaning Deposit"),
        ("damage", "Damage Deposit"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("partially_paid", "Partially Paid"),
        ("paid", "Paid"),
        ("partially_refunded", "Partially Refunded"),
        ("refunded", "Refunded"),
        ("forfeited", "Forfeited"),
    ]

    lease = models.ForeignKey(Lease,on_delete=models.CASCADE,related_name="deposits")
    deposit_type = models.CharField(max_length=30,choices=DEPOSIT_TYPES,default="security")
    required_amount = models.DecimalField(max_digits=12,decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2,default=0)
    status = models.CharField(max_length=25,choices=STATUS_CHOICES,default="pending")
    received_at = models.DateTimeField(null=True,blank=True)
    refunded_at = models.DateTimeField(null=True,blank=True)
    deducted_amount = models.DecimalField(max_digits=12, decimal_places=2,default=0)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.lease.lease_number}"





class LeaseRenewal(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    lease = models.ForeignKey(Lease,on_delete=models.CASCADE,related_name="renewals")
    proposed_start_date = models.DateField()
    proposed_end_date = models.DateField()
    proposed_rent = models.DecimalField(max_digits=12,decimal_places=2)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="pending")
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT,related_name="requested_lease_renewals")
    approved_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="approved_lease_renewals")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return (f"{self.lease.lease_number} "f"({self.proposed_start_date} - {self.proposed_end_date})")





class LeaseTermination(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    lease = models.ForeignKey(Lease,on_delete=models.CASCADE,related_name="terminations")
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT,related_name="requested_lease_terminations")
    reason = models.TextField()
    notice_date = models.DateField()
    termination_date = models.DateField()
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="pending")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,related_name="approved_lease_terminations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return (
            f"{self.lease.lease_number} - "
            f"{self.termination_date} ({self.status})"
        )






class MoveRecord(models.Model):
    MOVE_TYPE_CHOICES = [
        ("move_in", "Move In"),
        ("move_out", "Move Out"),
        ("transfer_in", "Transfer In"),
        ("transfer_out", "Transfer Out"),
    ]

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE,related_name="move_records")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT,related_name="move_records")
    move_type = models.CharField(max_length=20, choices=MOVE_TYPE_CHOICES)
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True,blank=True)
    inspection = models.ForeignKey(Inspection, on_delete=models.SET_NULL,null=True,blank=True,related_name="move_records")
    meter_readings = models.JSONField(default=dict, blank=True,help_text="Stores electricity, water, gas, and other meter readings.")
    keys_issued_or_returned = models.JSONField(default=dict,blank=True,help_text="Stores issued or returned keys, access cards, and remotes.")
    notes = models.TextField(blank=True,default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    def __str__(self):
        return (f"{self.lease.lease_number} - {self.unit}")


# rent invoice and payment
class Invoice(models.Model):
    INVOICE_TYPES = [
        ("rent", "Rent"),
        ("deposit", "Deposit"),
        ("utility", "Utility"),
        ("service_charge", "Service Charge"),
        ("parking", "Parking"),
        ("maintenance", "Maintenance"),
        ("penalty", "Penalty"),
        ("refund", "Refund"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("issued", "Issued"),
        ("partially_paid", "Partially Paid"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
        ("void", "Void"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,related_name="invoices")
    lease = models.ForeignKey(Lease, on_delete=models.SET_NULL, null=True,blank=True,related_name="invoices")
    tenant = models.ForeignKey(Tenant,on_delete=models.SET_NULL, null=True,blank=True,related_name="invoices")
    property = models.ForeignKey(Property,on_delete=models.SET_NULL,null=True,blank=True,related_name="invoices")
    invoice_number = models.CharField(max_length=100,unique=True)
    invoice_type = models.CharField(max_length=30,choices=INVOICE_TYPES,default="rent")
    issue_date = models.DateField()
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=12,decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    discount_amount = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    total_amount = models.DecimalField(max_digits=12,decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    balance = models.DecimalField(max_digits=12,decimal_places=2)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="draft")
    created_at = models.DateTimeField(auto_now_add=True,)
    updated_at = models.DateTimeField(auto_now=True)

    

    def __str__(self):
        return f"{self.invoice_number} - {self.total_amount}"




class InvoiceItem(models.Model):
    CHARGE_TYPES = [
        ("rent", "Rent"),
        ("service_charge", "Service Charge"),
        ("parking", "Parking"),
        ("water", "Water"),
        ("electricity", "Electricity"),
        ("gas", "Gas"),
        ("security", "Security"),
        ("waste_collection", "Waste Collection"),
        ("maintenance", "Maintenance"),
        ("deposit", "Deposit"),
        ("penalty", "Penalty"),
        ("discount", "Discount"),
        ("other", "Other"),
    ]
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE,related_name="items")
    charge_type = models.CharField(max_length=30,choices=CHARGE_TYPES, default="other")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10,decimal_places=2,default=1,)
    unit_price = models.DecimalField(max_digits=12,decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2,default=0,help_text="Tax percentage (e.g. 16.00 for 16% VAT).")
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.description}"







class Payment(models.Model):
    PROVIDER_CHOICES = [
        ("mpesa", "M-Pesa"),
        ("paystack", "Paystack"),
        ("stripe", "Stripe"),
        ("bank", "Bank"),
        ("cash", "Cash"),
        ("other", "Other"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("mobile_money", "Mobile Money"),
        ("card", "Card"),
        ("bank_transfer", "Bank Transfer"),
        ("cash", "Cash"),
        ("cheque", "Cheque"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
        ("partially_refunded", "Partially Refunded"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="payments")
    tenant = models.ForeignKey(Tenant,on_delete=models.SET_NULL,null=True,blank=True,related_name="payments")
    payment_reference = models.CharField(max_length=100,unique=True,db_index=True)
    external_reference = models.CharField(max_length=255,null=True,blank=True,db_index=True,help_text="Reference returned by the external payment provider.",)
    provider = models.CharField(max_length=30,choices=PROVIDER_CHOICES)
    payment_method = models.CharField(max_length=30,choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=3,default="KES",help_text="ISO 4217 currency code, such as KES, USD, or EUR.")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending",db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,related_name="received_payments")
    metadata = models.JSONField(default=dict,blank=True,help_text="Additional payment provider data.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    def __str__(self):
        return (
            f"{self.payment_reference} - "
            f"{self.currency} {self.amount} ({self.status})"
        )





class PaymentAllocation(models.Model):
    payment = models.ForeignKey("Payment",on_delete=models.CASCADE,related_name="allocations")
    invoice = models.ForeignKey("Invoice", on_delete=models.CASCADE,related_name="payment_allocations")
    allocated_amount = models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0.01)])
    allocated_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return (
            f"{self.payment.payment_reference} → "
            f"{self.invoice.invoice_number}: "
            f"{self.allocated_amount}"
        )



class Receipt(models.Model):
    organization = models.ForeignKey(Organization,on_delete=models.CASCADE,related_name="receipts")
    payment = models.ForeignKey(Payment,on_delete=models.CASCADE,related_name="receipts")
    receipt_number = models.CharField(max_length=100, unique=True,db_index=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="issued_receipts")
    file_url = models.URLField(max_length=500,null=True,blank=True,help_text="URL to the generated receipt PDF or file.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.receipt_number} - {self.payment.payment_reference}"





class Penalty(models.Model):
    PENALTY_TYPE_CHOICES = [
        ("late_payment", "Late Payment"),
        ("lease_violation", "Lease Violation"),
        ("returned_cheque", "Returned Cheque"),
        ("property_damage", "Property Damage"),
        ("utility", "Utility Penalty"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("applied", "Applied"),
        ("waived", "Waived"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
    ]

    invoice = models.ForeignKey("Invoice",on_delete=models.CASCADE,related_name="penalties")
    penalty_type = models.CharField(max_length=30,choices=PENALTY_TYPE_CHOICES,)
    rate = models.DecimalField(max_digits=5,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0)],help_text="Percentage rate used to calculate the penalty, e.g. 5.00 for 5%.")
    amount = models.DecimalField(max_digits=12,decimal_places=2,validators=[MinValueValidator(0)])
    applied_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    def __str__(self):
        return (
            f"{self.invoice.invoice_number} - "
            f"{self.get_penalty_type_display()} "
            f"({self.amount})"
        )





class PaymentReconciliation(models.Model):
    PROVIDER_CHOICES = [
        ("mpesa", "M-Pesa"),
        ("paystack", "Paystack"),
        ("stripe", "Stripe"),
        ("bank", "Bank"),
        ("cash", "Cash"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("matched", "Matched"),
        ("partially_matched", "Partially Matched"),
        ("mismatch", "Mismatch"),
        ("reviewed", "Reviewed"),
        ("closed", "Closed"),
    ]

    organization = models.ForeignKey("Organization",on_delete=models.CASCADE, related_name="payment_reconciliations")
    provider = models.CharField(max_length=30,choices=PROVIDER_CHOICES)
    statement_reference = models.CharField(max_length=100,unique=True,db_index=True)
    period_start = models.DateField()
    period_end = models.DateField()
    expected_amount = models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    received_amount = models.DecimalField(max_digits=14,decimal_places=2,validators=[MinValueValidator(0)])
    difference = models.DecimalField(max_digits=14,decimal_places=2,default=0,help_text="received_amount - expected_amount")
    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default="pending")
    reviewed_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="reviewed_payment_reconciliations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    def __str__(self):
        return (
            f"{self.statement_reference} - "
            f"{self.provider} ({self.status})"
        )


# maintenance management
class MaintenanceTicket(models.Model):
    CATEGORY_CHOICES = [
        ("plumbing", "Plumbing"),
        ("electrical", "Electrical"),
        ("carpentry", "Carpentry"),
        ("painting", "Painting"),
        ("cleaning", "Cleaning"),
        ("hvac", "HVAC"),
        ("security", "Security"),
        ("appliance", "Appliance"),
        ("roofing", "Roofing"),
        ("landscaping", "Landscaping"),
        ("general", "General"),
        ("other", "Other"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
        ("emergency", "Emergency"),
    ]

    SOURCE_CHOICES = [
        ("tenant", "Tenant"),
        ("landlord", "Landlord"),
        ("manager", "Property Manager"),
        ("inspection", "Inspection"),
        ("system", "System"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("published_to_kaskazi", "Published to Kaskazi"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("awaiting_approval", "Awaiting Approval"),
        ("completed", "Completed"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    ]

    organization = models.ForeignKey("Organization",on_delete=models.CASCADE, related_name="maintenance_tickets")
    property = models.ForeignKey(Property,on_delete=models.CASCADE,related_name="maintenance_tickets")
    building = models.ForeignKey(Building, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_tickets")
    unit = models.ForeignKey(Unit,on_delete=models.SET_NULL,null=True,blank=True,related_name="maintenance_tickets")
    lease = models.ForeignKey(Lease,on_delete=models.SET_NULL,null=True,blank=True,related_name="maintenance_tickets")
    reported_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reported_maintenance_tickets")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_maintenance_tickets")
    ticket_number = models.CharField(max_length=100,unique=True,db_index=True)
    category = models.CharField(max_length=30,choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=20,choices=PRIORITY_CHOICES,default="medium")
    source = models.CharField(max_length=30,choices=SOURCE_CHOICES)
    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default="open")
    preferred_date = models.DateField(null=True,blank=True)
    scheduled_at = models.DateTimeField(null=True,blank=True)
    completed_at = models.DateTimeField(null=True,blank=True)
    closed_at = models.DateTimeField(null=True,blank=True)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0)])
    actual_cost = models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    def __str__(self):
        return f"{self.ticket_number} - {self.title}"





class MaintenanceMedia(models.Model):
    FILE_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("document", "Document"),
        ("audio", "Audio"),
        ("other", "Other"),
    ]

    MEDIA_STAGE_CHOICES = [
        ("reported", "Reported"),
        ("before_work", "Before Work"),
        ("during_work", "During Work"),
        ("after_work", "After Work"),
    ]

    maintenance_ticket = models.ForeignKey(MaintenanceTicket, on_delete=models.CASCADE, related_name="media")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_maintenance_media")
    file_url = models.URLField(max_length=500,help_text="Cloudinary, S3, Azure Blob, or other file URL.")
    file_type = models.CharField(max_length=20,choices=FILE_TYPE_CHOICES,default="image",)
    media_stage = models.CharField(max_length=20,choices=MEDIA_STAGE_CHOICES,default="reported")
    caption = models.CharField(max_length=255,blank=True,default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    def __str__(self):
        return (f"{self.maintenance_ticket.ticket_number}")





class MaintenanceComment(models.Model):
    maintenance_ticket = models.ForeignKey(MaintenanceTicket,on_delete=models.CASCADE,related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name="maintenance_comments")
    comment = models.TextField()
    is_internal = models.BooleanField(default=False,help_text="If True, only staff and property managers can view this comment.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    def __str__(self):
        return (
            f"{self.user} - "
            f"{self.maintenance_ticket.ticket_number}"
        )





class MaintenanceStatusHistory(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("published_to_kaskazi", "Published to Kaskazi"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("awaiting_approval", "Awaiting Approval"),
        ("completed", "Completed"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    ]

    maintenance_ticket = models.ForeignKey(MaintenanceTicket,on_delete=models.CASCADE,related_name="status_history")
    previous_status = models.CharField(max_length=30,choices=STATUS_CHOICES,null=True,blank=True,help_text="Previous ticket status. Null for the initial status.")
    new_status = models.CharField(max_length=30,choices=STATUS_CHOICES)
    changed_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="maintenance_status_changes")
    notes = models.TextField(blank=True,default="")
    created_at = models.DateTimeField(auto_now_add=True)

    

    def __str__(self):
        return (
            f"{self.maintenance_ticket.ticket_number}: "
            f"{self.previous_status or 'None'} → {self.new_status}"
        )




class MaintenanceApproval(models.Model):
    APPROVAL_TYPE_CHOICES = [
        ("manager", "Property Manager Approval"),
        ("landlord", "Landlord Approval"),
        ("finance", "Finance Approval"),
        ("tenant", "Tenant Approval"),
        ("vendor", "Vendor Approval"),
        ("completion", "Completion Approval"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    maintenance_ticket = models.ForeignKey(MaintenanceTicket,on_delete=models.CASCADE,related_name="approvals")
    approval_type = models.CharField(max_length=30,choices=APPROVAL_TYPE_CHOICES)
    requested_from = models.ForeignKey(User,on_delete=models.PROTECT,related_name="maintenance_approval_requests")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,default="pending")
    comments = models.TextField(blank=True,default="")
    approved_at = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    def __str__(self):
        return (
            f"{self.maintenance_ticket.ticket_number} - "
            f"({self.status})"
        )






class MaintenanceWarranty(models.Model):
    PROVIDER_TYPE_CHOICES = [
        ("internal", "Internal Team"),
        ("contractor", "Contractor"),
        ("vendor", "Vendor"),
        ("manufacturer", "Manufacturer"),
        ("kaskazi", "Kaskazi Service Provider"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("void", "Void"),
        ("claimed", "Claimed"),
    ]

    maintenance_ticket = models.ForeignKey(MaintenanceTicket,on_delete=models.CASCADE,related_name="warranties")
    provider_type = models.CharField(max_length=30,choices=PROVIDER_TYPE_CHOICES)
    external_provider_id = models.CharField(max_length=100,null=True,blank=True,help_text="Reference ID from an external contractor, vendor, manufacturer, or Kaskazi provider.")
    start_date = models.DateField()
    end_date = models.DateField()
    terms = models.TextField(blank=True,default="",help_text="Warranty terms, exclusions, and coverage details.")
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return (
            f"{self.maintenance_ticket.ticket_number} - "
            f"({self.status})"
        )





class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("maintenance", "Maintenance"),
        ("payment", "Payment"),
        ("lease", "Lease"),
        ("tenant", "Tenant"),
        ("property", "Property"),
        ("invoice", "Invoice"),
        ("organization", "Organization"),
        ("system", "System"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default="system",
    )

    title = models.CharField(
        max_length=255,
    )

    message = models.TextField()

    reference_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    property = models.ForeignKey(
        "Property",
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )

    is_read = models.BooleanField(
        default=False,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return f"{self.title} - {self.user}"



class KaskaziMaintenanceBooking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("requested", "Requested"),
        ("accepted", "Accepted"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
    ]

    maintenance_ticket = models.OneToOneField(
        MaintenanceTicket,
        on_delete=models.CASCADE,
        related_name="kaskazi_booking",
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="kaskazi_maintenance_bookings",
    )

    external_booking_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )

    external_worker_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    worker_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    worker_phone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    service_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    service_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="requested",
    )

    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    quoted_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    final_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    external_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

# subscriptions and packages
class SubscriptionPackage(models.Model):
    BILLING_CYCLE_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    monthly_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    yearly_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    max_properties = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Null means unlimited.",
    )

    max_units = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Null means unlimited.",
    )

    max_users = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum organization members. Null means unlimited.",
    )

    max_portfolios = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Null means unlimited.",
    )

    has_maintenance = models.BooleanField(
        default=True,
    )

    has_kaskazi_integration = models.BooleanField(
        default=False,
    )

    has_financial_reports = models.BooleanField(
        default=False,
    )

    has_advanced_reports = models.BooleanField(
        default=False,
    )

    has_owner_portal = models.BooleanField(
        default=False,
    )

    has_tenant_portal = models.BooleanField(
        default=True,
    )

    has_api_access = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    sort_order = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name



class OrganizationSubscription(models.Model):
    STATUS_CHOICES = [
        ("trial", "Trial"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
        ("suspended", "Suspended"),
    ]

    BILLING_CYCLE_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription",
    )

    package = models.ForeignKey(
        SubscriptionPackage,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="trial",
    )

    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CYCLE_CHOICES,
        default="monthly",
    )

    trial_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    trial_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    current_period_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    current_period_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    auto_renew = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"{self.organization.name} - "
            f"{self.package.name}"
        )

    @property
    def is_trial_active(self):
        if (
            self.status != "trial"
            or not self.trial_end
        ):
            return False

        return timezone.now() < self.trial_end

    @property
    def is_active_subscription(self):
        if self.status == "trial":
            return self.is_trial_active

        if self.status != "active":
            return False

        if not self.current_period_end:
            return False

        return (
            timezone.now()
            < self.current_period_end
        )

    @property
    def days_remaining(self):
        end_date = None

        if self.status == "trial":
            end_date = self.trial_end

        elif self.status == "active":
            end_date = self.current_period_end

        if not end_date:
            return 0

        remaining = (
            end_date -
            timezone.now()
        )

        return max(
            remaining.days,
            0,
        )


class SubscriptionPayment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("paystack", "Paystack"),
        ("mpesa", "M-Pesa"),
        ("card", "Card"),
        ("bank", "Bank Transfer"),
        ("manual", "Manual"),
        ("other", "Other"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="subscription_payments",
    )

    subscription = models.ForeignKey(
        OrganizationSubscription,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    package = models.ForeignKey(
        SubscriptionPackage,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    currency = models.CharField(
        max_length=10,
        default="KES",
    )

    billing_cycle = models.CharField(
        max_length=20,
        choices=OrganizationSubscription.BILLING_CYCLE_CHOICES,
        default="monthly",
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
    )

    payment_reference = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
    )

    external_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    period_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    period_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.payment_reference


# project management

# ============================================================
# CONSTRUCTION PROJECT
# ============================================================

class ConstructionProject(models.Model):

    PROJECT_TYPE_CHOICES = [
        ("new_construction", "New Construction"),
        ("renovation", "Renovation"),
        ("extension", "Extension"),
        ("fit_out", "Fit Out"),
        ("infrastructure", "Infrastructure"),
        ("residential", "Residential"),
        ("commercial", "Commercial"),
        ("industrial", "Industrial"),
        ("mixed_use", "Mixed Use"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("planning", "Planning"),
        ("pending_approval", "Pending Approval"),
        ("approved", "Approved"),
        ("in_progress", "In Progress"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="construction_projects",
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="construction_projects",
        help_text="Optional property linked to this construction project.",
    )

    project_code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    name = models.CharField(
        max_length=255,
    )

    project_type = models.CharField(
        max_length=50,
        choices=PROJECT_TYPE_CHOICES,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    expected_end_date = models.DateField(
        null=True,
        blank=True,
    )

    actual_end_date = models.DateField(
        null=True,
        blank=True,
    )

    approved_budget = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(Decimal("0.00"))
        ],
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="planning",
        db_index=True,
    )

    project_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_construction_projects",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_construction_projects",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "organization",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "project_manager",
                    "status",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.project_code} - "
            f"{self.name}"
        )


# ============================================================
# PROJECT PHASE
# ============================================================

class ProjectPhase(models.Model):

    STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="phases",
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    sequence = models.PositiveIntegerField(
        default=1,
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="not_started",
        db_index=True,
    )

    completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "sequence"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "project",
                    "sequence",
                ],
                name=
                    "unique_project_phase_sequence",
            ),
        ]

    def __str__(self):
        return (
            f"{self.project.project_code} - "
            f"{self.name}"
        )


# ============================================================
# PROJECT MILESTONE
# ============================================================

class ProjectMilestone(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("overdue", "Overdue"),
        ("cancelled", "Cancelled"),
    ]

    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="milestones",
    )

    phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="milestones",
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "due_date",
            "id",
        ]

    def __str__(self):
        return (
            f"{self.project.project_code} - "
            f"{self.name}"
        )


# ============================================================
# PROJECT TASK
# ============================================================

class ProjectTask(models.Model):

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
        ("critical", "Critical"),
    ]

    STATUS_CHOICES = [
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("blocked", "Blocked"),
        ("under_review", "Under Review"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="tasks",
    )

    phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )

    parent_task = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subtasks",
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_project_tasks",
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
        db_index=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="todo",
        db_index=True,
    )

    completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )

    estimated_cost = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(
                Decimal("0.00")
            )
        ],
    )

    actual_cost = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(
                Decimal("0.00")
            )
        ],
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_project_tasks",
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "project",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "assigned_to",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "due_date",
                    "status",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.project.project_code} - "
            f"{self.title}"
        )


# ============================================================
# PROJECT TASK DEPENDENCY
# ============================================================

class ProjectTaskDependency(models.Model):

    DEPENDENCY_TYPE_CHOICES = [
        (
            "finish_to_start",
            "Finish to Start"
        ),
        (
            "start_to_start",
            "Start to Start"
        ),
        (
            "finish_to_finish",
            "Finish to Finish"
        ),
        (
            "start_to_finish",
            "Start to Finish"
        ),
    ]

    task = models.ForeignKey(
        ProjectTask,
        on_delete=models.CASCADE,
        related_name="dependencies",
    )

    depends_on_task = models.ForeignKey(
        ProjectTask,
        on_delete=models.CASCADE,
        related_name="dependent_tasks",
    )

    dependency_type = models.CharField(
        max_length=30,
        choices=DEPENDENCY_TYPE_CHOICES,
        default="finish_to_start",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "task",
                    "depends_on_task",
                ],
                name=
                    "unique_project_task_dependency",
            ),
        ]

    def __str__(self):
        return (
            f"{self.task.title} depends on "
            f"{self.depends_on_task.title}"
        )


# ============================================================
# BILL OF QUANTITIES ITEM
# ============================================================

class BOQItem(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("procured", "Procured"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="boq_items",
    )

    parent_item = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    item_code = models.CharField(
        max_length=100,
    )

    description = models.TextField()

    unit = models.CharField(
        max_length=50,
        help_text=
            "Examples: pcs, m, m2, m3, kg, tonnes, lump_sum",
    )

    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        validators=[
            MinValueValidator(
                Decimal("0.000")
            )
        ],
    )

    unit_rate = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(
                Decimal("0.00")
            )
        ],
    )

    estimated_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(
                Decimal("0.00")
            )
        ],
    )

    actual_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        validators=[
            MinValueValidator(
                Decimal("0.000")
            )
        ],
    )

    actual_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(
                Decimal("0.00")
            )
        ],
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "item_code"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "project",
                    "item_code",
                ],
                name=
                    "unique_project_boq_item_code",
            ),
        ]

    def __str__(self):
        return (
            f"{self.item_code} - "
            f"{self.description[:50]}"
        )


# ============================================================
# CONTRACTOR
# ============================================================

class Contractor(models.Model):

    CATEGORY_CHOICES = [
        ("general", "General Contractor"),
        ("electrical", "Electrical Contractor"),
        ("plumbing", "Plumbing Contractor"),
        ("civil", "Civil Works"),
        ("structural", "Structural Works"),
        ("mechanical", "Mechanical"),
        ("painting", "Painting"),
        ("roofing", "Roofing"),
        ("landscaping", "Landscaping"),
        ("supplier", "Supplier"),
        ("consultant", "Consultant"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("suspended", "Suspended"),
        ("blacklisted", "Blacklisted"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="contractors",
    )

    name = models.CharField(
        max_length=255,
    )

    registration_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    kra_pin = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
        default="",
    )

    phone_number = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="general",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="active",
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "name"
        ]

    def __str__(self):
        return self.name


# ============================================================
# PROJECT CONTRACTOR
# ============================================================

class ProjectContractor(models.Model):

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("terminated", "Terminated"),
        ("cancelled", "Cancelled"),
    ]

    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="project_contractors",
    )

    contractor = models.ForeignKey(
        Contractor,
        on_delete=models.PROTECT,
        related_name="project_contracts",
    )

    contract_reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    scope = models.TextField(
        blank=True,
        default="",
    )

    contract_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(
                Decimal("0.00")
            )
        ],
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="draft",
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "project",
                    "contractor",
                    "contract_reference",
                ],
                name=
                    "unique_project_contractor_contract",
            ),
        ]

    def __str__(self):
        return (
            f"{self.project.project_code} - "
            f"{self.contractor.name}"
        )


# ============================================================
# SITE DIARY
# ============================================================

class SiteDiary(models.Model):

    WEATHER_CHOICES = [
        ("sunny", "Sunny"),
        ("cloudy", "Cloudy"),
        ("rainy", "Rainy"),
        ("stormy", "Stormy"),
        ("windy", "Windy"),
        ("mixed", "Mixed"),
        ("other", "Other"),
    ]

    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="site_diaries",
    )

    entry_date = models.DateField(
        db_index=True,
    )

    weather = models.CharField(
        max_length=30,
        choices=WEATHER_CHOICES,
        null=True,
        blank=True,
    )

    workers_present = models.PositiveIntegerField(
        default=0,
    )

    work_completed = models.TextField(
        blank=True,
        default="",
    )

    materials_received = models.TextField(
        blank=True,
        default="",
    )

    equipment_used = models.TextField(
        blank=True,
        default="",
    )

    issues = models.TextField(
        blank=True,
        default="",
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_site_diaries",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-entry_date",
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "project",
                    "entry_date",
                ],
                name=
                    "unique_project_site_diary_date",
            ),
        ]

    def __str__(self):
        return (
            f"{self.project.project_code} - "
            f"{self.entry_date}"
        )


# ============================================================
# SITE DIARY MEDIA
# ============================================================

class SiteDiaryMedia(models.Model):

    FILE_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("document", "Document"),
        ("other", "Other"),
    ]

    site_diary = models.ForeignKey(
        SiteDiary,
        on_delete=models.CASCADE,
        related_name="media",
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_site_diary_media",
    )

    file_url = models.URLField(
        max_length=500,
    )

    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPE_CHOICES,
        default="image",
    )

    caption = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"{self.site_diary.project.project_code} - "
            f"{self.file_type}"
        )


# ============================================================
# PROJECT RISK
# ============================================================

class ProjectRisk(models.Model):

    LIKELIHOOD_CHOICES = [
        ("rare", "Rare"),
        ("unlikely", "Unlikely"),
        ("possible", "Possible"),
        ("likely", "Likely"),
        ("almost_certain", "Almost Certain"),
    ]

    IMPACT_CHOICES = [
        ("insignificant", "Insignificant"),
        ("minor", "Minor"),
        ("moderate", "Moderate"),
        ("major", "Major"),
        ("severe", "Severe"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("monitoring", "Monitoring"),
        ("mitigated", "Mitigated"),
        ("closed", "Closed"),
        ("accepted", "Accepted"),
    ]

    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="risks",
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField()

    likelihood = models.CharField(
        max_length=30,
        choices=LIKELIHOOD_CHOICES,
    )

    impact = models.CharField(
        max_length=30,
        choices=IMPACT_CHOICES,
    )

    risk_score = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(25),
        ],
    )

    mitigation = models.TextField(
        blank=True,
        default="",
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_project_risks",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="open",
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-risk_score",
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.project.project_code} - "
            f"{self.title}"
        )


# ============================================================
# PROJECT PROGRESS UPDATE
# ============================================================

class ProjectProgressUpdate(models.Model):

    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="progress_updates",
    )

    phase = models.ForeignKey(
        ProjectPhase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="progress_updates",
    )

    task = models.ForeignKey(
        ProjectTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="progress_updates",
    )

    completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal("0.00")
            ),
            MaxValueValidator(
                Decimal("100.00")
            ),
        ],
    )

    summary = models.TextField()

    reported_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="project_progress_reports",
    )

    reported_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-reported_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "project",
                    "reported_at",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.project.project_code} - "
            f"{self.completion_percentage}%"
        )




