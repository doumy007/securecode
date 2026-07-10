@ECHO OFF
SET @var=-1
SET "URLNOTIFI=http://localhost:9001/"

:: Iniciar el servidor Java en segundo plano
start javaw -jar C:\codelco\java\codelcoRun\codelco-csv-0.0.1-SNAPSHOT.jar

:: Esperar un tiempo suficiente para que el servidor se inicie
timeout /t 60

:: Realizar una petición HTTP GET al controlador utilizando PowerShell
SET "HTTP="
FOR /F "delims=" %%a IN ('powershell -Command "(Invoke-RestMethod -Uri '%URLNOTIFI%').StatusCode"') DO SET "HTTP=%%a"

:: Comprobación del código de respuesta HTTP
IF "%HTTP%" -eq "200" (
    ECHO El servidor está en funcionamiento. Código HTTP: %HTTP%
) ELSE (
    ECHO El servidor no responde correctamente. Código HTTP: %HTTP%
)

:: Matar el proceso del servidor Java
FOR /F "tokens=5 USEBACKQ" %%F IN (`netstat -ano ^| findstr :9001`) DO (
    taskkill /PID %%F /F
)


