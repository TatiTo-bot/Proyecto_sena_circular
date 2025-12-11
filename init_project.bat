@echo off
chcp 65001 >nul
echo ========================================== ==
echo 🎓 Sistema Circular 120 SENA - Inicialización
echo ==============================================
echo.

echo [1/10] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no está instalado
    pause
    exit /b 1
)
echo ✅ Python instalado
echo.

echo [2/10] Creando entorno virtual...
python -m venv venv
if %errorlevel% neq 0 (
    echo ❌ Error creando entorno virtual
    pause
    exit /b 1
)
echo ✅ Entorno virtual creado
echo.

echo [3/10] Activando entorno virtual...
call venv\Scripts\activate.bat
echo ✅ Entorno activado
echo.

echo [4/10] Instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Error instalando dependencias
    pause
    exit /b 1
)
echo ✅ Dependencias instaladas
echo.

echo [5/10] Creando directorios...
if not exist logs mkdir logs
if not exist media mkdir media
if not exist private_uploads\excel mkdir private_uploads\excel
if not exist staticfiles mkdir staticfiles
echo ✅ Directorios creados
echo.

echo [6/10] Verificando archivo .env...
if not exist .env (
    echo Creando archivo .env...
    (
        echo # Django
        echo SECRET_KEY=django-insecure-change-this-in-production
        echo DEBUG=True
        echo ALLOWED_HOSTS=localhost,127.0.0.1
        echo.
        echo # Base de Datos
        echo DB_NAME=circular120
        echo DB_USER=root
        echo DB_PASSWORD=1234
        echo DB_HOST=localhost
        echo DB_PORT=3306
        echo.
        echo # Email
        echo EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
        echo EMAIL_HOST=smtp.gmail.com
        echo EMAIL_PORT=587
        echo EMAIL_USE_TLS=True
        echo EMAIL_HOST_USER=sistemaaccesosambientessena@gmail.com
        echo EMAIL_HOST_PASSWORD=bjhosgoogzutxnnc
        echo DEFAULT_FROM_EMAIL=sistemaaccesosambientessena@gmail.com
        echo.
        echo # Celery
        echo CELERY_BROKER_URL=redis://localhost:6379/0
        echo.
        echo # Sistema
        echo SITE_URL=http://localhost:8000
    ) > .env
    echo ✅ Archivo .env creado
) else (
    echo ℹ️ Archivo .env ya existe
)
echo.

echo [7/10] Aplicando migraciones...
python manage.py makemigrations
python manage.py migrate
if %errorlevel% neq 0 (
    echo ❌ Error aplicando migraciones
    pause
    exit /b 1
)
echo ✅ Migraciones aplicadas
echo.

echo [8/10] Configurando grupos y permisos...
python manage.py setup_inicial
echo ✅ Grupos configurados
echo.

echo [9/10] Recolectando archivos estáticos...
python manage.py collectstatic --noinput
echo ✅ Archivos estáticos recolectados
echo.

echo [10/10] Creando usuario administrador...
echo.
echo Ingresa los datos del usuario administrador:
python manage.py crear_admin
echo ✅ Usuario administrador creado
echo.

echo ==============================================
echo ✅ Inicialización completada exitosamente
echo ==============================================
echo.
echo 📝 Próximos pasos:
echo.
echo 1. Iniciar el servidor de desarrollo:
echo    python manage.py runserver
echo.
echo 2. En otra terminal, iniciar Celery worker:
echo    celery -A circular120 worker -l info -P gevent
echo.
echo 3. En otra terminal, iniciar Celery beat:
echo    celery -A circular120 beat -l info
echo.
echo 4. Acceder al sistema en:
echo    http://localhost:8000
echo.
echo 5. (Opcional) Cargar datos de prueba:
echo    python manage.py cargar_datos_demo
echo.
echo ==============================================
echo.
pause