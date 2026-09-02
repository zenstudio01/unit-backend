from django.contrib import admin

from .models import (
    # =====================================================
    # AUTHENTICATION
    # =====================================================
    User,
    UserProfile,
    UserSession,
    OTPVerification,

    # =====================================================
    # ORGANIZATION
    # =====================================================
    Organization,
    OrganizationBranch,
    Role,
    Permission,
    RolePermission,
    OrganizationMembership,
    OrganizationInvitation,

    # =====================================================
    # PROPERTY MANAGEMENT
    # =====================================================
    Portifolio,
    Property,
    PropertyImage,
    Building,
    Floor,
    Unit,
    Amenity,
    PropertyAmenity,
    UnitAmenity,
    TenantUnitAssignment,

    # =====================================================
    # ASSETS
    # =====================================================
    Asset,
    AssetDepreciationEntries,

    # =====================================================
    # INSPECTIONS
    # =====================================================
    Inspection,
    InspectionItem,
    InspectionMedia,

    # =====================================================
    # OWNERS
    # =====================================================
    Owner,
    PropertyOwnership,
    OwnerBankAccount,

    # =====================================================
    # TENANTS
    # =====================================================
    Tenant,
    TenantEmergencyContact,
    TenantScreening,

    # =====================================================
    # LEASES
    # =====================================================
    Lease,
    LeaseTenant,
    LeaseCharge,
    LeaseDeposit,
    LeaseRenewal,
    LeaseTermination,
    MoveRecord,

    # =====================================================
    # INVOICES & PAYMENTS
    # =====================================================
    Invoice,
    InvoiceItem,
    Payment,
    PaymentAllocation,
    Receipt,
    Penalty,
    PaymentReconciliation,

    # =====================================================
    # MAINTENANCE
    # =====================================================
    MaintenanceTicket,
    MaintenanceMedia,
    MaintenanceComment,
    MaintenanceStatusHistory,
    MaintenanceApproval,
    MaintenanceWarranty,
    KaskaziMaintenanceBooking,

    # =====================================================
    # NOTIFICATIONS
    # =====================================================
    Notification,

    # =====================================================
    # SUBSCRIPTIONS
    # =====================================================
    SubscriptionPackage,
    OrganizationSubscription,
    SubscriptionPayment,

    # =====================================================
    # CONSTRUCTION PROJECT MANAGEMENT
    # =====================================================
    ConstructionProject,
    ProjectPhase,
    ProjectMilestone,
    ProjectTask,
    ProjectTaskDependency,
    BOQItem,
    Contractor,
    ProjectContractor,
    SiteDiary,
    SiteDiaryMedia,
    ProjectRisk,
    ProjectProgressUpdate,
)


# ============================================================
# AUTHENTICATION
# ============================================================

admin.site.register(User)
admin.site.register(UserProfile)
admin.site.register(UserSession)
admin.site.register(OTPVerification)


# ============================================================
# ORGANIZATION
# ============================================================

admin.site.register(Organization)
admin.site.register(OrganizationBranch)
admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(RolePermission)
admin.site.register(OrganizationMembership)
admin.site.register(OrganizationInvitation)


# ============================================================
# PROPERTY MANAGEMENT
# ============================================================

admin.site.register(Portifolio)
admin.site.register(Property)
admin.site.register(PropertyImage)
admin.site.register(Building)
admin.site.register(Floor)
admin.site.register(Unit)
admin.site.register(Amenity)
admin.site.register(PropertyAmenity)
admin.site.register(UnitAmenity)
admin.site.register(TenantUnitAssignment)


# ============================================================
# ASSETS
# ============================================================

admin.site.register(Asset)
admin.site.register(AssetDepreciationEntries)


# ============================================================
# INSPECTIONS
# ============================================================

admin.site.register(Inspection)
admin.site.register(InspectionItem)
admin.site.register(InspectionMedia)


# ============================================================
# OWNERS
# ============================================================

admin.site.register(Owner)
admin.site.register(PropertyOwnership)
admin.site.register(OwnerBankAccount)


# ============================================================
# TENANTS
# ============================================================

admin.site.register(Tenant)
admin.site.register(TenantEmergencyContact)
admin.site.register(TenantScreening)


# ============================================================
# LEASE MANAGEMENT
# ============================================================

admin.site.register(Lease)
admin.site.register(LeaseTenant)
admin.site.register(LeaseCharge)
admin.site.register(LeaseDeposit)
admin.site.register(LeaseRenewal)
admin.site.register(LeaseTermination)
admin.site.register(MoveRecord)


# ============================================================
# INVOICES & PAYMENTS
# ============================================================

admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(Payment)
admin.site.register(PaymentAllocation)
admin.site.register(Receipt)
admin.site.register(Penalty)
admin.site.register(PaymentReconciliation)


# ============================================================
# MAINTENANCE
# ============================================================

admin.site.register(MaintenanceTicket)
admin.site.register(MaintenanceMedia)
admin.site.register(MaintenanceComment)
admin.site.register(MaintenanceStatusHistory)
admin.site.register(MaintenanceApproval)
admin.site.register(MaintenanceWarranty)
admin.site.register(KaskaziMaintenanceBooking)


# ============================================================
# NOTIFICATIONS
# ============================================================

admin.site.register(Notification)


# ============================================================
# SUBSCRIPTIONS
# ============================================================

admin.site.register(SubscriptionPackage)
admin.site.register(OrganizationSubscription)
admin.site.register(SubscriptionPayment)


# ============================================================
# CONSTRUCTION PROJECT MANAGEMENT
# ============================================================

admin.site.register(ConstructionProject)
admin.site.register(ProjectPhase)
admin.site.register(ProjectMilestone)
admin.site.register(ProjectTask)
admin.site.register(ProjectTaskDependency)
admin.site.register(BOQItem)
admin.site.register(Contractor)
admin.site.register(ProjectContractor)
admin.site.register(SiteDiary)
admin.site.register(SiteDiaryMedia)
admin.site.register(ProjectRisk)
admin.site.register(ProjectProgressUpdate)