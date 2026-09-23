#!/usr/bin/env bash
# ============================================================
# SecureCode AI - despliegue en este servidor (producción)
# ============================================================
# IMPORTANTE: tu ~/.bash_profile exporta DB_URL / DB_USERNAME / DB_PASSWORD
# de OTRO proyecto (gestion_contractual, PostgreSQL). Docker Compose da
# prioridad a las variables del shell sobre el fichero .env al interpolar
# ${DB_PASSWORD}, lo que inicializaba MySQL con la contraseña equivocada.
# Este script limpia esas variables del entorno para que compose use SIEMPRE
# los valores reales de .env. No modifica tu perfil.
set -euo pipefail
cd "$(dirname "$0")"

env -u DB_PASSWORD -u DB_URL -u DB_USERNAME \
  docker compose -f docker-compose.prod.yml up -d --build "$@"