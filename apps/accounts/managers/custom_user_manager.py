# apps/accounts/custom_user_managers.py

from django.contrib.auth.models import BaseUserManager
from django.db import models
from apps.accounts.models.constants import AccountType

class CustomUserManager(BaseUserManager):
    """
    Custom user manager for CustomUser model.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        """
        if not email:
            raise ValueError("The Email field must be set")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", AccountType.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)
    
    def create_client(self, email, password=None, **extra_fields):
        """
        Create and save a client user.
        """
        extra_fields.setdefault("role", AccountType.CLIENT)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        
        return self.create_user(email, password, **extra_fields)
    
    def create_driver(self, email, password=None, **extra_fields):
        """
        Create and save a driver user.
        """
        extra_fields.setdefault("role", AccountType.DRIVER)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        
        return self.create_user(email, password, **extra_fields)
    
    def create_staff(self, email, password=None, **extra_fields):
        """
        Create and save a staff user.
        """
        extra_fields.setdefault("role", AccountType.STAFF)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        
        return self.create_user(email, password, **extra_fields)
    
    def create_admin(self, email, password=None, **extra_fields):
        """
        Create and save an admin user (not superuser).
        """
        extra_fields.setdefault("role", AccountType.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", False)
        
        return self.create_user(email, password, **extra_fields)

