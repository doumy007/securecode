# SecureCode AI — Documentación del proyecto

> **Plataforma Inteligente para Auditoría Automatizada de Seguridad y Cumplimiento Normativo**

Documento técnico integral generado a partir del análisis del código fuente. Describe la arquitectura, el stack tecnológico, los módulos, el modelo de datos, los flujos principales y cómo ejecutar el proyecto.

---

## 1. ¿Qué es SecureCode AI?

SecureCode AI es una **plataforma web (API + frontend SPA)** que automatiza la **auditoría de seguridad de código fuente y de infraestructura como código (IaC)**, y genera **informes de cumplimiento normativo** (reportes de cumplimiento) según estándares internacionales.

El flujo conceptual:

1. Un usuario **sube el código fuente** de su aplicación (vía archivo ZIP o clonando un repositorio Git: GitHub, GitLab, Bitbucket, Azure DevOps).
2. El sistema detecta el **lenguaje y framework** del proyecto y ejecuta una serie de **motores de análisis (workers)** que buscan vulnerabilidades (SAST de código, análisis de dependencias/CVEs, escaneo de contenedores y manifiestos K8s, etc.).
3. Los hallazgos se enriquecen con un **análisis basado en IA (OpenAI)** que genera descripción de riesgos, código corregido y recomendaciones.
4. Un **motor de cumplimiento** mapea cada vulnerabilidad a varios estándares: **OWASP Top 10, OWASP ASVS, NIST CSF 2.0, NIST SP 800-82 (ICS), ISO/IEC 27001:2022, CIS Controls v8 y MITRE ATT&CK**.
5. Se calculan **puntajes de riesgo (CVSS v3)** y puntajes de cumplimiento, y se persisten las vulnerabilidades, sus mapeos y planes de remediación.
6. El sistema genera **informes** en PDF, Excel y JSON, y ofrece un **dashboard** con KPIs y un **chat** para consultar los resultados con IA.

---

## 2. Stack tecnológico

### Backend
| Componente | Tecnología | Notas |
|---|---|---|
| Framework API | **FastAPI** (Python 3.11+) | Framework asíncrono, auto-documentación en `/docs` |
| Servidor ASGI | **Uvicorn** | Punto de entrada: `uvicorn app.main:app` |
| ORM | **SQLAlchemy 2.0 (async)** | `DeclarativeBase`, sesión async, `selectinload` |
| Dependencia inyectada | **pydantic-settings** | Configuración vía `.env` (clase `Settings`) |
| Validación | **Pydantic v2** | Schemas de entrada/salida (`BaseModel`) |
| Base de datos | **MySQL** | Driver async `aiomysql` (`DATABASE_URL`) y sync `pymysql` (para Alembic) |
| Migraciones | **Alembic** | `migrations/` con `env.py` y versión `001_initial` |
| Autenticación | **JWT (python-jose)** | HS256, access + refresh tokens |
| Contraseñas | **passlib + bcrypt** | `CryptContext(schemes=["bcrypt"])` |
| MFA | **pyotp + qrcode** | Autenticación de dos factores TOTP (voluntaria) |

### Motor de colas / brokers (parcial)
| Componente | Estado |
|---|---|
| RabbitMQ / aio-pika | Usado como broker de tareas; **con fallback a "modo directo"** si no está disponible o falla la conexión |
| Redis | Configurado en `config.py` (`REDIS_URL`) y en infraestructura |
| MinIO | Almacenamiento de objetos (S3-compatible) para reportes (`storage/minio_client.py`) |

### Análisis (workers)
Los "workers" son **módulos Python que aplican reglas de análisis sobre el contenido** de los archivos subidos. No dependen de herramientas externas en tiempo de ejecución (tienen sus propias reglas internas):

| Worker | Función |
|---|---|
| **SonarQubeWorker** | SAST: SQLi, secrets hardcodeados, XSS, command injection, path traversal |
| **SemgrepWorker** | Reglas (crypto insegura, log forging, hash débil, XXE, deserialización, null pointer, open redirect) |
| **DependencyCheckWorker** | Busca CVEs en dependencias (pom.xml, package.json, requirements.txt, build.gradle, go.mod) |
| **TrivyWorker** | Escaneo de Dockerfile / docker-compose / manifiestos K8s |
| **StaticAnalysisWorker** | Análisis por lenguaje (Java, Python, JS/TS, Go) |
| **InfraScannerWorker** | Escaneo de IaC (Terraform, Helm, `.env`, claves privadas) |

### Inteligencia Artificial
| Componente | Tecnología |
|---|---|
| Cliente OpenAI | **AsyncOpenAI** (modelo `gpt-4o-mini` por defecto) |
| Análisis combinado | `COMBINED_ANALYSIS_PROMPT` → descripción + riesgo + estándares + remediación + código corregido |
| Reportes por framework | Prompts específicos por estándar (JSON estructurado) |
| Chat | `AuditChat` con contexto de la auditoría y memoria por sesión |
| Embeddings | `EmbeddingService` con `text-embedding-3-small`; búsqueda de vulnerabilidades similares por similitud coseno |

### Reportes
| Tipo | Generador |
|---|---|
| PDF | `PDFReportGenerator` (WeasyPrint opcional; si no está, genera HTML) |
| Excel | `ExcelReportGenerator` (openpyxl) |
| JSON | `JSONReportGenerator` (estructura JSON nativa) |

### Frontend
- **SPA estática**: `app/static/index.html` + `js/app.js` + `css/style.css`
- **Bootstrap 5.3** + **Bootstrap Icons** + **Chart.js** (vía CDN)
- JavaScript vanilla; enrutado por hash (`#/`, `#/audits`, etc.); **JWT almacenado en `localStorage`**
- Se sirve desde FastAPI en `/` (redirecciona a `/static/index.html`)

### Infraestructura y DevOps
- **docker-compose.yml**: MySQL, RabbitMQ, Redis, MinIO, API, worker
- **Dockerfile** / **Dockerfile.worker**
- **kubernetes/**: manifiestos (configmap con secretos, deploy, etc.)
- **.github/workflows/ci.yml**: CI con Python 3.11, `ruff`, `mypy`, `pytest`
- **Makefile**: comandos `install`, `dev`, `run`, `migrate`, `test`, `lint`, `docker-up/down`

### Herramientas de desarrollo / calidad
- `ruff` (lint) + `mypy` (tipado) + `pytest` (tests) en CI

---

## 3. Estructura de directorios

```
securecode/
├── app/
│   ├── main.py                 # Punto de entrada FastAPI (monta routers, static, lifespan)
│   ├── config.py               # Settings (entorno, DB, JWT, OpenAI, RabbitMQ, MinIO, Redis)
│   ├── database.py             # Engine async, async_session, Base, init_db(), get_db()
│   ├── dependencies.py         # get_current_user, get_current_active_user, require_role, require_permission
│   ├── middleware.py           # CORS, Logging, Exception middleware
│   ├── exceptions.py           # SecureCodeException y subclases (404/401/403/422/409)
│   ├── auth/                   # Autenticación, autorización, roles, MFA, gestión de usuarios
│   │   ├── router.py, service.py, schemas.py, models.py, utils.py
│   ├── projects/               # Gestión de proyectos, subida de código, detección de lenguaje/framework
│   │   ├── router.py, service.py, schemas.py, models.py, parser.py, detector.py
│   ├── audits/                 # Orquestación de auditorías, workers, IA, compliance, agregación
│   │   ├── router.py, service.py, orchestrator.py, scheduler.py, schemas.py, models.py
│   ├── ai/                     # Integración OpenAI (análisis, chat, fixes, embeddings, prompts)
│   │   ├── analyzer.py, openai_client.py, chat.py, fix_generator.py, embeddings.py, prompts.py, router.py
│   ├── workers/                # Motores de análisis
│   │   ├── base.py, runner.py, sonarqube.py, semgrep.py, dependency_check.py,
│   │   ├── trivy.py, static_analysis.py, infra_scanner.py, result_aggregator.py
│   ├── compliance/             # Motor de cumplimiento y cálculo de riesgo
│   │   ├── engine.py, risk_calculator.py, mapper.py, standards/{owasp,nist_csf,nist_800_82,iso_27001,cis,mitre_attck}.py
│   ├── reports/                # Generación de informes (PDF, Excel, JSON)
│   │   ├── router.py, __init__.py, pdf.py, excel.py, json_export.py
│   ├── dashboard/              # KPIs, tendencias, gráficas
│   │   ├── router.py, __init__.py (service), service.py (vacío)
│   ├── integrations/           # Webhooks (GitHub, GitLab, Azure) y Jira
│   │   ├── router.py, __init__.py
│   ├── storage/                # MinIO / FileManager
│   │   ├── minio_client.py, file_manager.py (vacío)
│   ├── shared/                 # Utilidades transversales
│   │   ├── validators.py, cache.py, constants.py, pagination.py, logging.py
│   └── static/                 # Frontend SPA
│       ├── index.html, js/app.js, css/style.css
├── migrations/                 # Alembic
│   ├── env.py, versions/001_initial.py
├── reports/                    # Informes (incluye auditoría de seguridad)
├── docs/                       # Documentación (este archivo)
├── docker-compose.yml
├── Dockerfile, Dockerfile.worker
├── kubernetes/
├── .github/workflows/ci.yml
├── pyproject.toml, setup.py
├── Makefile
└── .env.example
```

---

## 4. Arquitectura y flujo de una auditoría

### Flujo de autenticación (auth)
1. `POST /auth/seed` crea el usuario `admin` (password `Admin123!`, `rol_id=1`) si no existe. ⚠️ **Público y con credenciales default** (hallazgo crítico).
2. `POST /auth/register` crea un usuario (acepta `rol_id` opcional — ⚠️ riesgo de escalada).
3. `POST /auth/login` valida credenciales (bcrypt) y devuelve `access_token` (30 min) y `refresh_token` (7 días, JWT HS256).
4. `GET /auth/me`, `PUT /auth/me`, `POST /auth/change-password`, `POST /auth/mfa/setup` y `/auth/mfa/verify`.
5. Panel admin (`require_role("admin")`): gestión de usuarios (`/auth/users`, `/auth/roles`).

**Autorización**: `get_current_active_user` decodifica el JWT con `JWT_SECRET_KEY`, y `require_role`/`require_permission` validan contra el rol/permisos. ⚠️ Hay rutas que autorizan con `rol_id == 1` (admin hardcodeado).

### Flujo de subida / creación de proyecto
1. `POST /projects` crea un `Proyecto` asociado al usuario.
2. `POST /projects/{id}/upload` recibe un **ZIP**, lo guarda en `storage/project_{id}/` y lo descomprime con `zipfile.extractall` (⚠️ **zip-slip**, hallazgo crítico).
3. `ProjectService.process_upload` recorre los archivos, calcula hash SHA-256, detecta lenguaje/framework (`LanguageDetector`) y los parsea (`DependencyParser`).

### Flujo de auditoría (núcleo)
1. `POST /audits` crea la `Auditoria` (con `frameworks` seleccionados, opcional `git_url`/token) y lanza la ejecución **en background** (`asyncio.create_task`).
2. `AuditOrchestrator.run_audit`:
   - **Paso 0 — Clonar**: si hay `git_url`, clona con `gitpython` (`Repo.clone_from`) a un directorio temporal y carga los archivos. (⚠️ SSRF potencial — la URL la pone el cliente).
   - **Pasos 1–6 — Workers**: ejecuta los 6 workers en secuencia, registrando `ResultadoWorker` y progreso por cada uno.
   - **Paso AI**: `AIAnalyzer.analyze_vulnerabilities` procesa los hallazgos con OpenAI (semáforo de 4 conexiones).
   - **Paso Compliance**: `ComplianceEngine.evaluate` mapea a estándares y `RiskCalculator.calculate_all` calcula CVSS v3.
   - **Paso Agregación**: `ResultAggregator.save_results` persiste `Vulnerabilidad`, `MapeoEstandar` y `TareaRemediacion`.
3. El progreso se guarda en `audit.resultado_resumen` (JSON con `percentage`, `steps`, `message`, `vulnerabilities_found`).
4. Estados: `pendiente` → `ejecutando` → `completada` | `fallida`. Al arrancar el servidor, las auditorías en `ejecutando` se marcan `fallida`.

### Flujo de reportes / cumplimiento
- `GET /audits` — lista auditorías (admin ve todas, resto las de su `user_id`).
- `GET /audits/{id}/progress` — progreso en tiempo real.
- `GET /audits/{id}/report/{framework}` — genera (con IA) el informe de cumplimiento del framework y lo cachea en `resultado_resumen.reports`.
- `POST /reports/pdf/{id}`, `/excel/{id}`, `/json/{id}` — generan reportes descargables (archivos en `./reports/` o `APP_UPLOAD_DIR`).

### Consumo / programación de tareas
- `AuditScheduler` intenta publicar en RabbitMQ; si no hay broker (o falla), ejecuta en **modo directo**.
- `app/workers/runner.py` es un **worker loop** que cada 10s procesa auditorías `pendiente`.

---

## 5. Modelo de datos (tablas `sc_*`)

### Roles y usuarios
| Tabla | Campos clave |
|---|---|
| `sc_roles` | `id`, `nombre` (único), `descripcion`, `permisos` (JSON) |
| `sc_usuarios` | `id`, `username` (único), `email` (único), `password_hash`, `nombre_completo`, `rol_id`, `activo`, `mfa_secret`, `mfa_enabled`, `ultimo_login` |

Roles predefinidos: `admin` (`*`), `auditor`, `developer`, `jefe_ti`, `cliente`.

### Proyectos
| Tabla | Campos clave |
|---|---|
| `sc_proyectos` | `id`, `nombre`, `descripcion`, `lenguaje`, `framework`, `repo_url`, `repo_tipo` (zip/github/gitlab/bitbucket), `estado`, `version_actual`, `user_id` |
| `sc_archivos_proyecto` | `id`, `proyecto_id`, `ruta`, `hash` (SHA-256), `tamano`, `lenguaje`, `contenido` |

### Auditorías
| Tabla | Campos clave |
|---|---|
| `sc_auditorias` | `id`, `proyecto_id`, `user_id`, `nombre`, `estado`, `tipo`, `version`, `resultado_resumen` (JSON), `frameworks` (JSON), `git_url`, `git_username`, `git_token`, `created_at`, `completed_at` |
| `sc_resultados_worker` | `id`, `auditoria_id`, `worker`, `estado`, `resultado` (JSON) |
| `sc_vulnerabilidades` | `id`, `auditoria_id`, `archivo_id`, `tipo`, `nombre`, `descripcion`, `severidad`, `cvss_score`, `impacto`, `probabilidad`, `prioridad`, `linea_inicio/fin`, `codigo_vulnerable`, `codigo_corregido`, `recomendacion`, `fuente`, `resuelta` |
| `sc_mapeo_estandares` | `id`, `vulnerabilidad_id`, `estandar`, `categoria`, `referencia`, `descripcion` |
| `sc_tareas_remediacion` | `id`, `auditoria_id`, `vulnerabilidad_id`, `paso`, `descripcion`, `archivo`, `metodo`, `prioridad`, `estado`, `user_id` |
| `sc_historial_ejecuciones` | `id`, `auditoria_id`, `evento`, `detalle` (JSON) |

> `app/database.py:init_db()` crea las tablas con `Base.metadata.create_all` y además hace `ALTER TABLE` ad-hoc para asegurar columnas de `sc_auditorias`.

---

## 6. API — Endpoints principales

### Auth (`/auth`)
| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| POST | `/auth/register` | Crea usuario | Público |
| POST | `/auth/seed` | Crea admin default | Público ⚠️ |
| POST | `/auth/login` | Inicia sesión, devuelve tokens | Público |
| POST | `/auth/refresh` | Renueva access token | Público (token) |
| POST | `/auth/mfa/setup`, `/auth/mfa/verify` | Configurar/verificar MFA | Autenticado |
| GET/PUT | `/auth/me` | Perfil | Autenticado |
| POST | `/auth/change-password` | Cambiar contraseña | Autenticado |
| CRUD | `/auth/users`, `/auth/roles` | Gestión admin | admin |

### Projects (`/projects`)
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Listar proyectos |
| POST | `/` | Crear proyecto |
| GET/PUT/DELETE | `/{id}` | Obtener / actualizar / eliminar (delete = admin) |
| POST | `/{id}/upload` | Subir ZIP de código |
| GET | `/{id}/files`, `/{id}/stats` | Archivos / estadísticas |

### Audits (`/audits`)
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/` | Crear y disparar auditoría (background) |
| GET | `/` | Listar (admin: todas; resto: propias) |
| GET | `/{id}` , `/{id}/progress` | Detalle / progreso |
| POST | `/reset-stuck` | Resetear auditorías atascadas (admin) |
| DELETE | `/{id}` | Eliminar (admin) |
| GET | `/{id}/vulnerabilities`(+`/{vuln_id}`) | Vulnerabilidades |
| PUT | `/vulnerabilities/{id}/status` | Actualizar estado de una vulnerabilidad |
| GET | `/frameworks` | Lista de frameworks soportados |
| GET | `/{id}/report/{framework}` | Informe de cumplimiento (IA) |
| GET | `/summary` | Resumen global/propio |

### Reports (`/reports`)
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/pdf/{id}` | Genera PDF |
| GET | `/pdf/{id}/download` | Descarga PDF |
| POST | `/excel/{id}` | Genera Excel |
| POST | `/json/{id}` | Genera JSON |

### Dashboard (`/dashboard`)
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/kpi`, `/vulnerabilities-by-severity`, `/trends`, `/compliance-radar` | Métricas y gráficas |

### AI (`/ai`)
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/chat` | Pregunta a la IA sobre una auditoría |
| POST | `/chat/clear` | Borra historial del chat |

### Integrations (`/integrations`)
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/github/webhook`, `/gitlab/webhook`, `/azure/webhook` | Disparar auditoría por webhook (sin firma verificada ⚠️) |
| POST | `/jira/ticket` | Crear ticket Jira (mocked) |

### Misceláneos
- `GET /` → redirige a `/static/index.html` (frontend)
- `GET /health` → estado de la app
- `GET /docs`, `/redoc` → documentación interactiva de FastAPI

---

## 7. Cumplimiento normativo (ComplianceEngine)

`ComplianceEngine` mantiene una *knowledge base* que mapea cada tipo de vulnerabilidad a múltiples estándares y motores:

- **OWASP Top 10 (2021)** y **OWASP ASVS v4.0** (`owasp.py`)
- **NIST CSF 2.0 / NIST SP 800-53** (`nist_csf.py`)
- **NIST SP 800-82 Rev.3 (sistemas ICS/SCADA)** (`nist_800_82.py`)
- **ISO/IEC 27001:2022** y su Anexo A (`iso_27001.py`)
- **CIS Controls v8** y CIS Benchmarks (`cis.py`)
- **MITRE ATT&CK v14** / D3FEND (`mitre_attck.py`)

`RiskCalculator` calcula **CVSS v3** a partir de métricas por tipo de vulnerabilidad, y deriva `severidad`, `impacto` y `probabilidad`. Los reportes de cada framework se generan con IA usando prompts dedicados (`app/ai/prompts.py`).

---

## 8. Frontend (SPA estática)

- **`app/static/index.html`** — estructura de la SPA con vistas por hash.
- **`app/static/js/app.js`** (1122 líneas) — lógica de cliente: autenticación, proyectos, auditorías, progreso, reportes por framework (HTML para imprimir/PDF), perfil, panel admin, chat IA.
- **`app/static/css/style.css`** — estilos personalizados.

Vistas principales: inicio (`/`), mis proyectos, auditorías (con detalle de progreso por pasos), resultados/vulnerabilidades, reportes por framework, perfil, panel admin (usuarios/roles), chat.

> ⚠️ El token JWT se guarda en `localStorage` (`app/static/js/app.js`), lo que lo expone a XSS.

---

## 9. Ejecutar el proyecto

### Requisitos
- Python **3.11+** (recomendado 3.11/3.12; **no 3.14**, ya que librerías como `numpy`, `pandas`, `matplotlib`, `weasyprint` y `asyncmy` no tienen wheels y fallan al compilar).
- MySQL disponible (o vía docker-compose).
- (Opcional) RabbitMQ, Redis, MinIO, clave OpenAI.

### Instalación
```bash
pip install -e ".[dev]"
```

### Configuración
Copiar `.env.example` a `.env` y completar credenciales (DB, JWT secret, OpenAI, etc.).

### Base de datos
```bash
alembic upgrade head        # o el init_db() automático al arrancar
```

### Arranque (API)
> ⚠️ **Debe ejecutarse desde la RAÍZ del proyecto** (donde está `pyproject.toml`), NO desde `app/`:
```bash
cd C:\Users\56967\Desktop\openClode\securecode
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```
Accede a:
- Frontend: `http://localhost:8001/`
- Docs Swagger: `http://localhost:8001/docs`

### Arranque (worker)
```bash
python -m app.workers.runner
```

### Docker
```bash
make docker-up      # o: docker compose up -d
```

### Tests / lint / typecheck
```bash
pytest -v --cov=app
ruff check .
mypy app
```

---

## 10. Consideraciones de seguridad (resumen)

Se realizó una **auditoría de seguridad** completa del código. El informe detallado está en `reports/auditoria-seguridad-securecode.md`. Los hallazgos más relevantes:

**Críticos**
1. **C1 — Escalada de privilegios**: `POST /auth/register` acepta `rol_id` arbitrario → un usuario puede registrarse como `admin` (`rol_id=1`).
2. **C2/C3/C4 — IDOR**: endpoints de proyectos/auditorías/reportes no verifican propietario; aunque `GET /audits` filtra por `user_id`, otros endpoints (`GET /audits/{id}`, reportes, vulnerabilidades) devuelven datos de cualquier usuario.
3. **C5 — Seed público con credenciales por defecto**: `/auth/seed` crea `admin` / `Admin123!` sin restricción.
4. **C6 — Zip-slip**: `zipfile.extractall` en `ProjectService.process_upload` permite escribir fuera del directorio.

**Altos**
- Webhooks sin verificación de firma (pese a existir `verify_signature`, no se usa).
- JWT en `localStorage` (XSS).
- MFA no obligatorio.
- SSRF potencial en clonado de repositorios (`Repo.clone_from` con URL del cliente).
- XSS en generación de PDF (HTML no sanitizado de hallazgos).
- Autorización por `rol_id == 1` hardcodeado.

---

## 11. Notas de implementación y deuda técnica

- `app/dashboard/service.py`, `app/storage/file_manager.py`, `app/auth/utils.py`, `app/compliance/mapper.py` están **vacíos** (esqueletos).
- `FixGenerator.generate_fix` llama a `client.generate_fix(...)`, pero `OpenAIClient` **no lo implementa** → fallará en runtime (método inexistente).
- El `CacheService` local no aplica TTL (ignora `ttl_seconds`).
- Algunos endpoints tienen **IDOR** (ver sección 10).
- La dependencia `numpy` (usada por `embeddings.py`) y `weasyprint` (usada por `pdf.py`) se importan de forma **lazy** dentro de funciones, por lo que no bloquean el arranque básico de la API.
- `python-3.14` no es compatible con el stack completo (build de `numpy`/`matplotlib`/`asyncmy` falla).

---

*Documento generado por análisis del código fuente del repositorio. Revisar junto con el informe de auditoría de seguridad en `reports/`.*
