# apps/accounts/services/registration_service.py

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.models.constants import AccountType

User = get_user_model()


class RegistrationService:
    """
    Handles all user creation and role-upgrade flows atomically.
    Email verification is disabled — accounts are active immediately.
    """

    # Public: new account creation (open registration)

    @staticmethod
    @transaction.atomic
    def register_client(*, email, first_name, last_name, password, phone=None, **_ignored):
        """
        Create a CLIENT account (active immediately — email verification disabled).
        """
        from apps.accounts.models.profile import ClientProfile

        user = User.objects.create_client(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            is_active=True,
        )

        profile = ClientProfile.objects.create(user=user)

        if phone:
            profile.phone = phone
            profile.save(update_fields=["phone"])

        return user

    @staticmethod
    @transaction.atomic
    def register_driver(*, email, first_name, last_name, password, phone=None, **profile_fields):
        """
        Create a DRIVER account (active immediately — email verification disabled).
        """
        from apps.accounts.models.profile import DriverProfile

        user = User.objects.create_driver(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            is_active=True,
        )

        profile = DriverProfile.objects.create(user=user)

        if phone:
            profile.phone = phone
            profile.whatsapp_number = phone

        for field, value in profile_fields.items():
            if hasattr(profile, field):
                setattr(profile, field, value)

        profile.save()

        return user

    @staticmethod
    @transaction.atomic
    def register_provider_admin(*, email, first_name, last_name, password, phone=None, **profile_fields):
        """
        Create a PROVIDER ADMIN account (active immediately — email verification disabled).
        """
        from apps.accounts.models.profile import ProviderAdminProfile

        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            role=AccountType.PROVIDER_ADMIN,
            is_active=True,
        )

        profile = ProviderAdminProfile.objects.create(user=user)

        if phone:
            profile.phone = phone
            profile.whatsapp_number = phone

        for field, value in profile_fields.items():
            if hasattr(profile, field):
                setattr(profile, field, value)

        profile.save()

        return user

    
    # Public: role upgrades (authenticated user only)
    
    @staticmethod
    @transaction.atomic
    def upgrade_to_driver(*, user, phone=None, **profile_fields):
        """
        Upgrade an existing CLIENT to DRIVER.
        Migrates to DriverProfile and removes the old ClientProfile.
        """
        from apps.accounts.models.profile import DriverProfile, ClientProfile

        user.role = AccountType.DRIVER
        user.save(update_fields=["role"])

        profile, _ = DriverProfile.objects.get_or_create(user=user)
        if phone:
            profile.phone = phone
            profile.whatsapp_number = phone
        for field, value in profile_fields.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        profile.save()

        ClientProfile.objects.filter(user=user).delete()
        return user

    @staticmethod
    @transaction.atomic
    def upgrade_to_provider_admin(*, user, phone=None, **profile_fields):
        """
        Upgrade an existing CLIENT or STAFF user to PROVIDER ADMIN.
        """
        from apps.accounts.models.profile import ProviderAdminProfile, ClientProfile, StaffProfile

        user.role = AccountType.PROVIDER_ADMIN
        user.save(update_fields=["role"])

        profile, _ = ProviderAdminProfile.objects.get_or_create(user=user)
        if phone:
            profile.phone = phone
            profile.whatsapp_number = phone
        for field, value in profile_fields.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        profile.save()

        ClientProfile.objects.filter(user=user).delete()
        StaffProfile.objects.filter(user=user).delete()
        return user