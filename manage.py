#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def print_startup_info():
    """Print minimal startup information."""
    from decouple import config
    
    DEBUG = config("DEBUG", default=True, cast=bool)
    command = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Only show info for server commands
    if command in ("runserver", "daphne", "uvicorn"):
        env = "DEV" if DEBUG else "PROD"
        print(f"\n► MediLink Emergency Services [{env}]")
        
        if command == "runserver":
            print("  ⚠️  WebSockets NOT supported with runserver")
            print("  💡 Use: daphne config.asgi:application -b 0.0.0.0 -p 8000")
        else:
            print("  ✓ WebSockets supported")
        
        print()


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Show minimal startup info
    try:
        print_startup_info()
    except:
        pass  # Don't break if config fails
    
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()