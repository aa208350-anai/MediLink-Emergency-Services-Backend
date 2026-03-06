#!/usr/bin/env bash
# start_server.sh — Startup Script for Development & Production
# Automatically adapts based on DEBUG environment variable

set -euo pipefail

# ===============================================================================
# ENVIRONMENT CONFIGURATION
# ===============================================================================

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
ASGI_MODULE="config.asgi:application"
DJANGO_SETTINGS_MODULE="config.settings"

DEBUG="${DEBUG:-True}"
if [ "$DEBUG" = "False" ] || [ "$DEBUG" = "false" ] || [ "$DEBUG" = "0" ]; then
    ENV_NAME="PRODUCTION"
    IS_DEV=false
    WORKERS="${WEB_CONCURRENCY:-4}"
else
    ENV_NAME="DEVELOPMENT"
    IS_DEV=true
    WORKERS=1
fi

export DJANGO_SETTINGS_MODULE

# ===============================================================================
# LOGGING
# ===============================================================================

log() {
    echo "► $1"
}

print_banner() {
    echo ""
    echo "════════════════════════════════════════"
    echo "  Medilink Emergency Services — $ENV_NAME"
    echo "════════════════════════════════════════"
    echo "  Port: $PORT | Workers: $WORKERS"
    echo "════════════════════════════════════════"
    echo ""
}

# ===============================================================================
# DATABASE
# ===============================================================================

setup_database() {
    local db_url="${DATABASE_URL:-}"

    log "Setting up database..."

    # ── PostgreSQL extensions ──────────────────────────────────────────────────
    if [ -n "$db_url" ]; then
        log "Enabling PostgreSQL extensions..."

        local EXT_RC=0
        python manage.py dbshell -- --variable=ON_ERROR_STOP=1 << 'EOF' || EXT_RC=$?
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
EOF

        if [ "$EXT_RC" -eq 0 ]; then
            log "✅ PostgreSQL extensions enabled (pg_trgm, unaccent)"
        else
            log "⚠️  Could not enable extensions — db user may lack superuser privileges. Continuing..."
        fi
    else
        log "⚠️  No DATABASE_URL set — skipping extensions (SQLite fallback)"
    fi

    # ── Migrations ─────────────────────────────────────────────────────────────
    log "Running migrations..."

    if python manage.py migrate --run-syncdb; then
        log "✅ Migrations complete"
    else
        log "❌ Migrations failed"
        exit 1
    fi
}

# ===============================================================================
# ADMIN USER
# ===============================================================================

create_admin_user() {
    log "Creating admin user if needed..."
    python manage.py createadmin || true
    # python manage.py createadmin --replace 
}

# ===============================================================================
# STATIC FILES
# ===============================================================================

collect_static_files() {
    log "Collecting static files..."

    if python manage.py collectstatic --noinput --clear -v 0; then
        log "✅ Static files collected"
    else
        log "⚠️  collectstatic failed — check storage backend config"
    fi
}

# ===============================================================================
# SERVER STARTUP
# ===============================================================================

start_server() {
    log "Starting $ENV_NAME server on $HOST:$PORT..."
    echo ""

    # ── Daphne (preferred — best WebSocket support) ────────────────────────────
    if command -v daphne &> /dev/null; then
        log "Using Daphne (ASGI)"
        exec daphne -b "$HOST" -p "$PORT" "$ASGI_MODULE"

    # ── Uvicorn ────────────────────────────────────────────────────────────────
    elif command -v uvicorn &> /dev/null; then
        log "Using Uvicorn (ASGI)"
        if [ "$IS_DEV" = true ]; then
            exec uvicorn "$ASGI_MODULE" \
                --host "$HOST" \
                --port "$PORT" \
                --reload
        else
            exec uvicorn "$ASGI_MODULE" \
                --host "$HOST" \
                --port "$PORT" \
                --workers "$WORKERS"
        fi

    # ── Django dev server (last resort, development only) ─────────────────────
    elif [ "$IS_DEV" = true ]; then
        log "⚠️  No ASGI server found — falling back to Django dev server"
        exec python manage.py runserver "$HOST:$PORT"

    # ── No server available in production → hard fail ─────────────────────────
    else
        log "❌ No ASGI server found. Install one before deploying:"
        log "   pip install daphne    # recommended (WebSocket support)"
        log "   pip install uvicorn   # alternative"
        exit 1
    fi
}

# ===============================================================================
# MAIN  — order matters:
#   1. migrations first   (tables must exist before admin creation)
#   2. admin user second  (needs auth tables from migrations)
#   3. static files third (independent, but do before serving)
#   4. server last
# ===============================================================================

main() {
    print_banner
    setup_database
    create_admin_user
    collect_static_files
    start_server
}

main