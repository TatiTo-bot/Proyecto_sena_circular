# circular120/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Configurar el módulo de configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'circular120.settings')

app = Celery('circular120')

# Cargar configuración desde Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodescubrir tareas en todas las apps instaladas
app.autodiscover_tasks()

# Configurar tareas periódicas
app.conf.beat_schedule = {
    # Alerta de fichas próximas a vencer (cada lunes a las 8am)
    'alerta-fichas-proximas-vencer': {
        'task': 'apps.alertas.tasks.enviar_alerta_fichas_proximas_vencer',
        'schedule': crontab(hour=8, minute=0, day_of_week='monday'),
    },
    # Solicitud de inasistencias (día 25 de cada mes)
    'solicitud-inasistencias-mensual': {
        'task': 'apps.alertas.tasks.enviar_solicitud_subida_inasistencias',
        'schedule': crontab(hour=9, minute=0, day_of_month='25'),
    },
    # Solicitud de evaluaciones (cada viernes)
    'solicitud-evaluaciones': {
        'task': 'apps.alertas.tasks.enviar_solicitud_resultados_evaluativos',
        'schedule': crontab(hour=9, minute=0, day_of_week='friday'),
    },
    # Informe bimensual (primer día de cada mes)
    'informe-depuracion-bimensual': {
        'task': 'apps.alertas.tasks.generar_informe_depuracion_bimensual',
        'schedule': crontab(hour=7, minute=0, day_of_month='1'),
    },
    # Actualización automática de estados (diario a las 2am)
    'actualizar-estados-circular120': {
        'task': 'apps.alertas.tasks.actualizar_estados_aprendices_circular120',
        'schedule': crontab(hour=2, minute=0),
    },
}

app.conf.timezone = 'America/Bogota'


# circular120/__init__.py
# Esto asegura que Celery se cargue cuando Django inicia
from .celery import app as celery_app

__all__ = ('celery_app',)