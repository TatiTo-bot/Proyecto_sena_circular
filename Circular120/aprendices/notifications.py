# aprendices/notifications.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

def enviar_aviso_instructor(instructor_email, ficha_num, fecha_limite, instructor_name=None):
    subject = f"[Acción requerida] Subir inasistencias - Ficha {ficha_num}"
    context = {
        'instructor_name': instructor_name or 'Instructor',
        'ficha_num': ficha_num,
        'fecha_limite': fecha_limite,
        'portal_link': getattr(settings, 'SITE_URL', '') + '/aprendices/upload/' if getattr(settings, 'SITE_URL', '') else '/aprendices/upload/'
    }
    body = render_to_string('aprendices/email_aviso_instructor.txt', context)
    html = render_to_string('aprendices/email_aviso_instructor.html', context)
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [instructor_email], html_message=html, fail_silently=False)
