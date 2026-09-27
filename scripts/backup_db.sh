#!/usr/bin/env bash
# ============================================================
# SecureCode AI - Backup de la base de datos externa.
#
# Uso:      ./scripts/backup_db.sh
# Programar (crontab del host, p. ej. cada día a las 03:00):
#   0 3 * * * cd /ruta/a/securecode && ./scripts/backup_db.sh >> storage/backups/backup.log 2>&1
#
# Guarda hasta $BACKUPS_KEEP copias comprimidas (gzip) en
# ./backups (junto al repo, añadido a .gitignore) con el nombre
# securecode_<fecha>.sql.gz y falla con código 1 si el dump sale vacío
# (p. ej. red del hosting caída).
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

BACKUP_DIR="${BACKUP_DIR:-$DIR/backups}"
BACKUPS_KEEP="${BACKUPS_KEEP:-14}"
mkdir -p "$BACKUP_DIR"

# Cargar SOLO las variables de BD desde .env sin evaluar todo el archivo
# ('source .env' es frágil: cualquier valor con espacios/# rompe el parseo).
# Además la contraseña no se imprime en logs ni en ps (se pasa por MYSQL_PWD).
envfile="$DIR/.env"
for key in DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME; do
  val=$(grep -E "^${key}=" "$envfile" | head -1 | cut -d= -f2-)
  val="${val%\"}"; val="${val#\"}"   # quitar comillas envolventes si las hay
  export "$key=$val"
done
: "${DB_HOST:?DB_HOST no definido en .env}"
: "${DB_USER:?DB_USER no definido en .env}"
: "${DB_PASSWORD:?DB_PASSWORD no definido en .env}"
: "${DB_NAME:?DB_NAME no definido en .env}"
DB_PORT="${DB_PORT:-3306}"

run_mysqldump() {
  if command -v mysqldump >/dev/null 2>&1; then
    mysqldump "$@"
    return
  fi

  # Fallback con docker. La contraseña se pasa por --env-file (NO por -e en
  # línea de comandos): evita exponerla en ps/logs y problemas de expansión
  # del shell interno de sg.
  local envfile
  envfile=$(mktemp "${TMPDIR:-/tmp}/sc_backup_env.XXXXXX") || return 1
  trap 'rm -f "$envfile"' RETURN
  chmod 600 "$envfile"
  printf 'MYSQL_PWD=%s\n' "$MYSQL_PWD" > "$envfile"

  local base=(docker run --rm -i --env-file "$envfile" mysql:8.0 mysqldump)

  if docker version >/dev/null 2>&1; then
    "${base[@]}" "$@"
  elif command -v sg >/dev/null 2>&1 && sg docker -c "docker version" >/dev/null 2>&1; then
    # Construir el comando para el shell interno de sg con escape %q seguro.
    local cmd=""
    local arg
    for arg in "${base[@]}"; do
      cmd+="$(printf '%q ' "$arg")"
    done
    for arg in "$@"; do
      cmd+="$(printf '%q ' "$arg")"
    done
    sg docker -c "$cmd"
  else
    echo "[$(date -Is)] ERROR: mysqldump no encontrado (ni cliente MySQL ni acceso a docker)." >&2
    rm -f "$envfile"
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