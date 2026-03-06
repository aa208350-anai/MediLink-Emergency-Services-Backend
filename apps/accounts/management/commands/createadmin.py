# accounts/management/commands/createadmin.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from decouple import config


class Command(BaseCommand):
    help = "Create a superuser from environment variables (safe for production)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete all existing superusers before creating the new one.",
        )

    def handle(self, *args, **kwargs):
        User = get_user_model()
        username_field = User.USERNAME_FIELD   # "email"
        replace = kwargs["replace"]

        # 1️⃣  Read credentials from environment
        email    = config(f"ADMIN_{username_field.upper()}", default=None)  # ADMIN_EMAIL
        password = config("ADMIN_PASSWORD", default=None)

        if not email or not password:
            self.stderr.write(
                self.style.ERROR(
                    f"❌ Missing env vars: ADMIN_{username_field.upper()} "
                    f"and ADMIN_PASSWORD must both be set."
                )
            )
            return

        # 2️⃣  Handle existing superusers
        existing = User.objects.filter(is_superuser=True)
        if existing.exists():
            if not replace:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠️  A superuser already exists. "
                        "Run with --replace to delete it and create a new one."
                    )
                )
                return

            count = existing.count()
            existing.delete()
            self.stdout.write(self.style.WARNING(f"🗑️  Deleted {count} existing superuser(s)."))

        # 3️⃣  Create superuser
        #
        #  IMPORTANT — CustomUser has is_active=False by default, which blocks
        #  Django admin login entirely. We must explicitly activate the account
        #  and set the role to "admin" so all permission helpers work correctly.
        try:
            with transaction.atomic():
                user = User.objects.create_superuser(
                    **{username_field: email},
                    password=password,
                )

                # Force-activate regardless of what create_superuser does internally
                needs_save = False

                if not user.is_active:
                    user.is_active = True
                    needs_save = True

                if user.role != "admin":
                    user.role = "admin"
                    needs_save = True

                if needs_save:
                    user.save(update_fields=["is_active", "role"])

            self.stdout.write(
                self.style.SUCCESS(f"✅ Superuser '{email}' created successfully!")
            )

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"❌ Failed to create superuser: {str(e)}")
            )