from celery import shared_task
from django.core.management import call_command

@shared_task
def importar_excel_task(path):
    try:
        call_command('import_consolidado', path)
        return "OK"
    except Exception as e:
        return str(e)