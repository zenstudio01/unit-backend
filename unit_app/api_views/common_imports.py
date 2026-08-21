# =========================
# Django Imports
# =========================
import json
import logging
import os
import secrets
import traceback
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q, Sum, Avg
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt

# =========================
# Django REST Framework
# =========================
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from rest_framework.decorators import api_view, parser_classes, permission_classes

# models
from unit_app.models import User, UserProfile, UserSession, OTPVerification, Organization, TenantUnitAssignment, OrganizationBranch, Role, Permission, RolePermission, OrganizationMembership, OrganizationInvitation, Portifolio, Property, PropertyImage, Building, Floor, Unit, Amenity, PropertyAmenity, UnitAmenity, Asset, AssetDepreciationEntries, Inspection, InspectionItem, InspectionMedia, Owner, PropertyOwnership, OwnerBankAccount, Tenant, TenantEmergencyContact, TenantScreening, Lease, LeaseTenant, LeaseCharge, LeaseDeposit, LeaseRenewal, LeaseTermination, MoveRecord, Invoice, InvoiceItem, Payment, PaymentAllocation, Receipt,Penalty, PaymentReconciliation, MaintenanceTicket, MaintenanceMedia, MaintenanceComment, MaintenanceStatusHistory, MaintenanceApproval, MaintenanceWarranty, Notification,KaskaziMaintenanceBooking, SubscriptionPackage, OrganizationSubscription, SubscriptionPayment


# =========================
# Third-Party Packages
# =========================
import requests
import resend

from .helper import send_push_notification, send_email

# cloudinary
import cloudinary.uploader


from math import radians, sin, cos, sqrt, atan2
from django.db.models import Avg


import requests
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


from django.db.models import Q, Count, Sum
from django.utils.timezone import now
from django.utils.timesince import timesince

import uuid
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Q
from django.contrib.auth import get_user_model

import random
import re


from django.db.models.functions import TruncMonth


import random

from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from rest_framework.decorators import api_view

from django.utils.dateparse import parse_date




import uuid

from django.db import transaction
from django.http import JsonResponse
from django.utils.text import slugify

from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated

from unit_app.models import (
    Organization,
    OrganizationMembership,
    Role,
)


from decimal import Decimal, InvalidOperation

from datetime import date

from calendar import month_name
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone

from decimal import Decimal

from django.db.models import (
    Avg,
    Count,
)

from django.utils import timezone


from datetime import timedelta

from django.db import transaction
from django.utils import timezone


from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone


from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render
from django.utils import timezone

from decimal import Decimal, InvalidOperation



from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date


from dateutil.relativedelta import (relativedelta)

from django.utils.dateparse import (
    parse_date,
    parse_time,
)

from datetime import datetime
from decimal import Decimal