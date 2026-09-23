#!/bin/sh
# Entrypoint para SecureCode AI: prepara los directorios de datos y
# ejecuta la app como usuario no-root (appuser) por seguridad.
set -e

mkdir -p /app/storage/uploads/temp /app/uploads /app/reports

if [ "$(id -u)" = "0" ]; then
  chown -R appuser:appuser /app/storage /app/uploads /app/reports 2>/dev/null || true
  if command -v setpriv >/dev/null 2>&1; then
    # exec directo: el proceso real es PID 1 (señales y limpieza correctas)
    exec setpriv --reuid=appuser --regid=appuser --init-groups "$@"
  else
    exec su appuser -s /bin/sh -c "exec \"$@\""
  fi
else
  exec "$@"
fi