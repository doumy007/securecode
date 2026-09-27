#!/usr/bin/env bash
# ============================================================
# SecureCode AI - Backup de la base de datos externa.
#
# Uso:      ./scripts/backup_db.sh
# Programar (crontab del host, p. ej. cada día a las 03:00):
#   0 3 * * * cd /ruta/a/securecode && ./scripts/backup_db.sh >> storage/backups/backup.log 2>&1
#
# Guarda hasta $BACKUPS_KEEP copias comprimidas (gzip) en
# ./storage/backups con el nombre securecode_<fecha>.sql.gz y
# falla con código 1 si el dump sale vacío (p. ej. red del hosting caída).
# NOTA: mantén una copia fuera de este servidor (off-site) para
# recuperación ante desastre del hosting.
#
# Requisitos: mysqldump (cliente MySQL) instalado en el host. Si no está,
# el script usa 'docker run --rm mysql:8.0 mysqldump' como alternativa
# (requiere acceso a docker, p. ej. 'sg docker -c ...' o grupo docker).
# ============================================================
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

BACKUP_DIR="${BACKUP_DIR:-$DIR/storage/backups}"
BACKUPS_KEEP="${BACKUPS_KEEP:-14}"
mkdir -p "$BACKUP_DIR"

# Cargar credenciales desde .env (no se imprimen en logs/cliente).
set -a
# shellcheck disable=SC1091
source .env
set +a
: "${DB_HOST:?DB_HOST no definido en .env}"
: "${DB_USER:?DB_USER no definido en .env}"
: "${DB_PASSWORD:?DB_PASSWORD no definido en .env}"
: "${DB_NAME:?DB_NAME no definido en .env}"
DB_PORT="${DB_PORT:-3306}"

run_mysqldump() {
  if command -v mysqldump >/dev/null 2>&1; then
    mysqldump "$@"
  elif command -v docker >/dev/null 2>&1 && docker version >/dev/null 2>&1; then
    docker run --rm mysql:8.0 mysqldump "$@"
  else
    echo "[$(date -Is)] ERROR: mysqldump no encontrado (ni cliente MySQL ni docker)." >&2
    exit 1
  fi
}

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/securecode_${STAMP}.sql.gz"

# MYSQL_PWD evita exponer la contraseña en ps/logs. mysqldump no la incluye
# en el SQL: se usa al conectar.
export MYSQL_PWD="$DB_PASSWORD"
if ! run_mysqldump \
  -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" \
  --single-transaction --quick --routines --triggers \
  "$DB_NAME" 2>/dev/null | gzip > "$OUT"; then
  echo "[$(date -Is)] ERROR: mysqldump falló ($DB_HOST/$DB_NAME). ¿Red o credenciales?" >&2
  rm -f "$OUT"
  exit 1
fi

if [ ! -s "$OUT" ]; then
  echo "[$(date -Is)] ERROR: backup vacío ($DB_HOST/$DB_NAME). ¿Red o credenciales?" >&2
  rm -f "$OUT"
  exit 1
fi

# Retención: eliminar copias más antiguas que BACKUPS_KEEP
ls -1t "$BACKUP_DIR"/securecode_*.sql.gz 2>/dev/null | tail -n +$((BACKUPS_KEEP + 1)) | xargs -r rm -f

echo "[$(date -Is)] OK: $(du -h "$OUT" | cut -f1) -> $OUT"