from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from .models import Notificacion
import traceback


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enviar_notificacion(self, notificacion_id):
    noti = Notificacion.objects.get(id=notificacion_id)
    if noti.estado == 'enviado':
        return  # ya fue

    try:
        canal = noti.plantilla.canal.nombre
        if canal == 'email':
            _enviar_email(noti)
        elif canal == 'sms':
            _enviar_sms(noti)
        else:
            raise ValueError(f"Canal {canal} no implementado")

        noti.estado = 'enviado'
        noti.enviado_en = timezone.now()
        noti.error = ''
        noti.save(update_fields=['estado', 'enviado_en', 'error'])

    except Exception as exc:
        noti.intento += 1
        noti.error = traceback.format_exc()
        if noti.intento >= noti.max_intentos:
            noti.estado = 'fallido'
        else:
            noti.estado = 'reintentando'
            noti.prox_reintento = timezone.now() + timedelta(minutes=5)
            # Re-encola
            self.retry(exc=exc)
        noti.save(update_fields=['intento', 'estado',
                  'error', 'prox_reintento'])

# ----------- IMPLEMENTACIONES BÁSICAS -----------


def _enviar_email(noti):
    from django.core.mail import send_mail
    from django.template import Template, Context

    plantilla = noti.plantilla
    asunto = plantilla.asunto or ''
    txt = Template(plantilla.cuerpo_txt).render(Context(noti.contexto_json))

    send_mail(
        subject=asunto,
        message=txt,
        from_email=None,  # usa DEFAULT_FROM_EMAIL
        recipient_list=[noti.destinatario],
        fail_silently=False,
    )


def _enviar_sms(noti):
    # placeholder – integras Twilio después
    print(
        f"[SMS] Para: {noti.destinatario} | Texto: {noti.plantilla.cuerpo_txt.format(**noti.contexto_json)}")
