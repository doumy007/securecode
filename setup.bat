@echo off
title SecureCode AI - Setup
chcp 65001 >nul

echo ============================================
echo  SecureCode AI - Instalacion automatica
echo ============================================
echo.

:: ---------- 1. Verificar Python ----------
echo [1/5] Verificando Python...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python no encontrado. Instala Python 3.11+ y vuelve a ejecutar.
    pause
    exit /b 1
)
python --version

:: ---------- 2. Crear entorno virtual ----------
echo.
echo [2/5] Creando entorno virtual...
if not exist ".venv\" (
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo ERROR: No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo Entorno virtual creado en .venv\
) else (
    echo Entorno virtual ya existe, continuando...
)

:: ---------- 3. Instalar dependencias ----------
echo.
echo [3/5] Instalando dependencias...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -e . -q
if %ERRORLEVEL% neq 0 (
    echo ERROR: Fallo la instalacion de dependencias.
    pause
    exit /b 1
)
echo Dependencias instaladas correctamente.

:: ---------- 4. Configurar .env ----------
echo.
echo [4/5] Configurando variables de entorno...
if not exist ".env" (
    copy .env.example .env >nul
    echo Se creo .env a partir de .env.example.
    echo.
    echo  IMPORTANTE: Edita .env con tus valores:
    echo    - DB_HOST, DB_USER, DB_PASSWORD, DB_NAME (MySQL)
    echo    - OPENAI_API_KEY (tu API key de OpenAI)
    echo    - JWT_SECRET_KEY (cambiala por una segura)
    echo.
    echo  Luego vuelve a ejecutar este script.
    pause
    exit /b 0
) else (
    echo .env ya existe.
)

:: ---------- 5. Inicializar BD y seed ----------
echo.
echo [5/5] Inicializando base de datos y datos iniciales...
echo.
echo  NOTA: Asegurate de tener MySQL corriendo en localhost:3306
echo  con las credenciales configuradas en .env
echo.
echo  Si no tienes MySQL local, puedes usar Docker:
echo    docker run -d --name securecode-mysql ^
echo      -e MYSQL_ROOT_PASSWORD=root ^
echo      -e MYSQL_DATABASE=securecode_db ^
echo      -p 3306:3306 mysql:8.0
echo.
choice /M "Intentar iniciar la aplicacion ahora?"
if %ERRORLEVEL% equ 1 (
    echo.
    python -c "import asyncio; from app.database import engine, Base; asyncio.run(Base.metadata.create_all(bind=engine))" 2>nul
    echo Intentando seed de admin...
    python -c "import asyncio, httpx; asyncio.run(httpx.AsyncClient().post('http://localhost:8000/auth/seed'))" 2>nul
    echo.
    echo Iniciando servidor en http://localhost:8000 ...
    echo.
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    echo.
    echo Para iniciar manualmente despues:
    echo   call .venv\Scripts\activate.bat
    echo   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    echo.
    pause
)
