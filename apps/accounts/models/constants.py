from django.db import models


class AccountType(models.TextChoices):
    ADMIN           = "admin",     "Administrator"
    PROVIDER_ADMIN  = "provider_admin", "Provider Admin"
    CLIENT          = "client",    "Client"
    DRIVER          = "driver",    "Driver"
    STAFF           = "staff",     "Staff"
