# SecureCode AI

> **Plataforma Inteligente para Auditoría Automatizada de Seguridad y Cumplimiento Normativo.**
> Sube código fuente (ZIP o repositorio Git), ejecútalo por 6 motores de análisis + IA (OpenAI),
> obtén vulnerabilidades con CVSS, mapeo a estándares (OWASP, NIST, ISO 27001, CIS, MITRE ATT&CK)
> e informes en PDF / Excel / JSON.

Este README es la **guía completa de despliegue en un servidor Ubuntu con Docker**.
Está escrito para que un agente (OpenCode) o una persona pueda levantar el sistema
de principio a fin sin consultar nada más. **La API queda expuesta en el puerto 1200.**

---

## 1. Arquitectura de despliegue

```
                    ┌──────────────────────────────────────────────┐
  Internet ──1200──▶│  sc-api (FastAPI + frontend SPA)             │
                    │  http://SERVIDOR:1200/  (app)                │
                    │  http://SERVIDOR:1200/docs (Swagger)         │
                    └──────┬───────────────┬───────────────┬───────┘
                           │               │               │
              ┌────────────▼──────┐ ┌──────▼────────┐ ┌───▼───────────┐
              │ sc-mysql (MySQL   │ │ sc-rabbitmq   │ │ sc-redis      │
              │ 8.0, interno)     │ │ (colas, mgmt  │ │ (caché,       │
              │                   │ │ :15672)       │ │  interno)     │
              └───────────────────┘ └───────────────┘ └───────────────┘
              ┌───────────────────┐ ┌───────────────┐
              │ sc-worker         │ │ sc-minio      │
              │ (auditorías en    │ │ (objetos,     │
              │  background)      │ │  consola      │
              │                   │ │  :9001)       │
              └───────────────────┘ └───────────────┘
```

### 1.1 Tabla de servicios y puertos (host)

| Contenedor    | Imagen (o build)              | Puerto host | Uso                          | Expuesto |
|---------------|-------------------------------|-------------|------------------------------|----------|
| `sc-api`      | build `Dockerfile`            | **1200** → 8000 | API + frontend + Swagger | ✅ SÍ |
| `sc-worker`   | build `Dockerfile.worker`     | —           | Ejecuta auditorías en fondo  | No (interno) |
| `sc-mysql`    | `mysql:8.0`                   | —           | Base de datos (interno)      | No (interno) |
| `sc-rabbitmq` | `rabbitmq:3-management`       | 15672       | Consola de gestión RabbitMQ  | Opcional |
| `sc-redis`    | `redis:7-alpine`              | —           | Caché (interno)              | No (interno) |
| `sc-minio`    | `minio/minio`                 | 9001        | Consola web MinIO            | Opcional |

> Solo el puerto **1200** es obligatorio. Los puertos 15672/9001 son consolas
> opcionales: si no se usan, ciérralos en el firewall. MySQL/Redis/AMQP/MinIO-S3
> **no** se publican al host por seguridad (los contenedores se comunican por la red interna).
> SonarQube **no** se incluye en el compose de producción (v10+ no soporta MySQL).

### 1.2 Requisitos del servidor

- Ubuntu 22.04+ (x86_64 — verificar con `uname -m`, debe decir `x86_64`).
- Mínimo **4 GB RAM**.
- Puertos libres: **1200** (obligatorio), 15672/9001 (opcionales).
- Acceso a internet (para descargar imágenes base y paquetes Python).
- Una **API key de OpenAI** (sin ella la app arranca, pero el análisis IA, el chat
  y los reportes por framework fallarán).

---

## 2. Despliegue paso a paso (ejecutar en el servidor)

> Para agentes: ejecutar los bloques en orden. Cada bloque indica el resultado esperado.
> Si un paso falla, ir a la sección 6 (Troubleshooting) antes de continuar.

### Paso 0 — Instalar Docker, Compose y git

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

**Resultado esperado:** `docker --version` y `docker compose version` responden sin error.
(Cierra y reabre la sesión SSH para que el grupo `docker` aplique; o usa `sudo` delante de cada `docker`.)

### Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/doumy007/securecode.git
cd securecode
git log --oneline -3   # debe mostrar commits, p. ej. "deploy: produccion docker puerto 1200"
```

### Paso 2 — Crear el archivo `.env`

El `.env` **no viene con git** (contiene secretos). Créalo copiando la plantilla y editando valores:

```bash
cp .env.example .env
nano .env
```

Contenido mínimo funcional (ajusta lo marcado con ⬅️):

```ini
# --- Base de datos (deben coincidir con docker-compose.prod.yml) ---
DB_HOST=mysql
DB_PORT=3306
DB_USER=securecode
DB_PASSWORD=securecode_pass        # ⬅️ cámbiala en producción
DB_NAME=securecode_db
DB_ROOT_PASSWORD=rootpassword      # ⬅️ cámbiala en producción

# --- JWT ---
JWT_SECRET_KEY=GENERA-UNA-CLAVE-LARGA-ALEATORIA   # ⬅️ ver comando abajo
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# --- OpenAI (OBLIGATORIA para IA) ---
OPENAI_API_KEY=sk-proj-TU-CLAVE-REAL-AQUI         # ⬅️ tu clave real
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4096
OPENAI_TEMPERATURE=0.1

# --- RabbitMQ / Redis / MinIO (valores internos del compose) ---
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=securecode
RABBITMQ_PASSWORD=securecode_pass
RABBITMQ_QUEUE=audit_tasks
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin         # ⬅️ cámbialas en producción
MINIO_SECRET_KEY=minioadmin         # ⬅️ cámbialas en producción
MINIO_BUCKET=securecode-reports
MINIO_SECURE=false

# --- App ---
APP_NAME=SecureCode AI
APP_VERSION=1.0.0
APP_ENV=production
APP_DEBUG=false
APP_PORT=8000                       # puerto INTERNO del contenedor (no tocar)
APP_HOST=0.0.0.0
APP_LOG_LEVEL=INFO
APP_CORS_ORIGINS=http://localhost:4200,http://localhost:3000
APP_UPLOAD_DIR=./uploads
APP_MAX_UPLOAD_SIZE_MB=500
MFA_ISSUER_NAME=SecureCode AI
SONARQUBE_URL=http://localhost:9000  # no desplegado por defecto (excluido del compose prod)
SONARQUBE_TOKEN=
```

Generar un secreto JWT seguro:

```bash
openssl rand -hex 32
```

**Resultado esperado:** existe `.env` con `OPENAI_API_KEY` real y `JWT_SECRET_KEY` de 64 caracteres hex.
⚠️ **Nunca** subas el `.env` a git (ya está en `.gitignore`).

### Paso 3 — Construir y levantar todo

```bash
mkdir -p uploads reports
docker compose -f docker-compose.prod.yml up -d --build
```

El primer build tarda varios minutos (instala dependencias Python 3.11).
**Resultado esperado:** `docker compose -f docker-compose.prod.yml ps` muestra
`sc-api`, `sc-worker`, `sc-mysql` (healthy), `sc-rabbitmq` (healthy), `sc-redis`, `sc-minio` en `Up`.

> SonarQube **no se incluye** en el compose de producción: v10+ ya no soporta
> MySQL (exige su propia BD y `vm.max_map_count`). La app funciona sin él;
> sus workers de análisis son autocontenidos.

### Paso 4 — Verificar salud y crear el admin

```bash
curl -s http://localhost:1200/health
# Esperado: {"status":"ok","app":"SecureCode AI","version":"1.0.0","environment":"production"}

docker compose -f docker-compose.prod.yml logs --tail=30 api
# Esperado: "Base de datos inicializada" (las tablas se crean solas al arrancar)

curl -s -X POST http://localhost:1200/auth/seed
# Esperado: {"message":"Admin user created",...} o {"message":"Admin user already exists"}
```

### Paso 5 — Entrar a la aplicación

| URL | Uso |
|---|-----|
| `http://SERVIDOR:1200/` | Frontend (SPA) — entrar con `admin` / `Admin123!` |
| `http://SERVIDOR:1200/docs` | Swagger interactivo de la API |
| `http://SERVIDOR:1200/health` | Salud del servicio |
| `http://SERVIDOR:15672` | RabbitMQ (según `.env`) — opcional |
| `http://SERVIDOR:9001` | MinIO (según `.env`) — opcional |

**Resultado esperado:** login OK en el frontend y `GET /docs` responde 200.

### Paso 6 — Endurecimiento inmediato (obligatorio)

1. Entra como `admin` y **cambia la contraseña** (`Perfil` → cambiar contraseña).
2. Cierra puertos innecesarios con UFW (solo 22 SSH + 1200 app):
   ```bash
   sudo ufw allow 22/tcp && sudo ufw allow 1200/tcp && sudo ufw --force enable
   sudo ufw status
   ```
3. Valora desactivar `POST /auth/seed` tras crear el admin (endpoint público con
   credenciales por defecto — ver `docs/PROYECTO.md` §10 y `reports/`).

---

## 3. Operación diaria

```bash
cd securecode
docker compose -f docker-compose.prod.yml ps              # estado
docker compose -f docker-compose.prod.yml logs -f api     # logs API en vivo
docker compose -f docker-compose.prod.yml logs -f worker  # logs worker
docker compose -f docker-compose.prod.yml restart api     # reiniciar API
docker compose -f docker-compose.prod.yml down            # detener todo
docker compose -f docker-compose.prod.yml up -d           # arrancar (sin rebuild)
```

### Actualizar a una versión nueva del código

```bash
git pull origin master
docker compose -f docker-compose.prod.yml up -d --build
```

### Backup de la base de datos

```bash
docker compose -f docker-compose.prod.yml exec mysql \
  mysqldump -u securecode -psecurecode_pass securecode_db > backup_$(date +%F).sql
```

---

## 4. Despliegue alternativo: imágenes preconstruidas

Si prefieres construir en otro equipo y solo subir imágenes (útil con internet lento en el servidor):

```bash
# En el equipo de build (misma arquitectura que el servidor):
docker build -t securecode-api:1.0.0 -f Dockerfile .
docker build -t securecode-worker:1.0.0 -f Dockerfile.worker .
docker save securecode-api:1.0.0 | gzip > api.tar.gz
docker save securecode-worker:1.0.0 | gzip > worker.tar.gz
scp api.tar.gz worker.tar.gz docker-compose.prod.yml .env.example usuario@SERVIDOR:/opt/securecode/
```

```bash
# En el servidor:
cd /opt/securecode
docker load < api.tar.gz && docker load < worker.tar.gz
cp .env.example .env && nano .env   # completar (Paso 2)
docker compose -f docker-compose.prod.yml up -d   # sin --build: usa las imágenes cargadas
```

> El `image: securecode-api:1.0.0` / `securecode-worker:1.0.0` ya está declarado en
> `docker-compose.prod.yml`, así que `up` reutiliza las imágenes cargadas.
> Las imágenes públicas (mysql, rabbitmq, redis, minio) se descargan solas.

---

## 5. Notas técnicas

- **Puerto 1200:** el mapeo es `1200:8000`. Dentro del contenedor la app siempre escucha
  en el 8000 (`CMD` del `Dockerfile`); no cambies `APP_PORT` salvo que cambies el `Dockerfile`.
- **Python 3.11:** las imágenes usan `python:3.11-slim` a propósito. No usar 3.14
  (`numpy`/`matplotlib`/`asyncmy` no tienen wheels y rompen el build).
- **Migraciones:** al arrancar, `init_db()` crea las tablas automáticamente
  (`app/database.py`). Alembic (`migrations/`) queda para evolución futura del esquema.
- **Modo degradado:** si RabbitMQ/MinIO/OpenAI no responden, la app arranca igual;
  las auditorías corren en modo directo y los pasos IA fallan de forma aislada (ver logs).
- **`.dockerignore`:** impide que `.env`, `.venv/`, `storage/`, `.git/` etc. entren en la imagen.
- **Documentación del código:** `docs/PROYECTO.md` (arquitectura, módulos, modelo de datos, endpoints).
- **Auditoría de seguridad del propio proyecto:** `reports/auditoria-seguridad-securecode.md`
  (leer antes de exponer a internet: IDOR, `/auth/seed` público, zip-slip, JWT en localStorage…).

---

## 6. Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `port 1200 is already allocated` | Puerto ocupado | `sudo ss -tlnp \| grep 1200` y libera el proceso, o cambia el mapeo en el compose |
| `sc-mysql` nunca pasa a `healthy` | Falta memoria / disco | `docker compose logs mysql`; libera disco (`docker system prune`) |
| Build muy lento / falla por red | Descarga de wheels | Reintenta `up -d --build`; verifica DNS/internet del servidor |
| `/health` responde pero login falla | `.env` con JWT distinto entre builds o BD vacía | Re-ejecuta `POST /auth/seed`; revisa `logs api` |
| Auditoría se queda en `ejecutando` | Worker caído o reinicio a mitad | `POST /audits/reset-stuck` como admin, o reinicia `worker` |
| Pasos IA fallan (`OpenAI API error`) | `OPENAI_API_KEY` inválida/ausente o sin saldo | Corrige `.env` y `restart api worker` |
| `curl /auth/seed` → 500 | Tablas no creadas aún | Espera a `Base de datos inicializada` en `logs api` y reintenta |

---

*SecureCode AI v1.0.0 — Despliegue Docker en puerto 1200.*
