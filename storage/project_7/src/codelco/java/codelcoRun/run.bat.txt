@echo off
SETLOCAL

SET PORT=9002
SET JAR_PATH=C:\codelco\java\codelcoRun\codelco-csv-0.0.1-SNAPSHOT.jar
SET CONFIG_PATH=file:///C:/codelco/java/codelcoRun/

echo 🔴 Liberando puerto %PORT%...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo Matando proceso PID %%a
    taskkill /PID %%a /F > nul 2>&1
)

echo ✅ Puerto liberado

echo 🚀 Ejecutando aplicación...

java -jar "%JAR_PATH%" ^
--spring.profiles.active=local ^
--spring.config.additional-location=%CONFIG_PATH%

echo ✅ Proceso finalizado
pause
