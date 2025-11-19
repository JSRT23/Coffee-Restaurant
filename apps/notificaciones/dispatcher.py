from django.contrib.auth import get_user_model
from django.conf import settings
from .models import Plantilla, PreferenciaCanal, Notificacion, Canal

User = get_user_model()


def dispatch(evento: str, usuario_id: int, **contexto) -> Notificacion:
    """
    Crea la fila Notificación (pendiente) según preferencias del usuario.
    Si no hay preferencia, usa canal por defecto (email).
    """
    user = User.objects.get(id=usuario_id)

    # 1. Preferencia del usuario
    pref = PreferenciaCanal.objects.filter(
        usuario=user, evento=evento, activa=True).first()
    if not pref:
        # Default: email
        canal = Canal.objects.filter(nombre='email', activo=True).first()
        if not canal:
            raise ValueError("No hay canal email activo")
    else:
        canal = pref.canal

    # 2. Plantilla
    plantilla = Plantilla.objects.filter(
        evento=evento, canal=canal, activa=True
    ).first()
    if not plantilla:
        raise ValueError(f"No hay plantilla activa para {evento} → {canal}")

    # 3. Destinatario
    if canal.nombre == 'email':
        destinatario = user.email
    elif canal.nombre == 'sms':
        # necesitarás agregarlo al modelo
        destinatario = getattr(user, 'telefono', '')
        if not destinatario:
            raise ValueError("Usuario sin teléfono")
    else:
        destinatario = ''  # WhatsApp, push, etc.

    # 4. Crear Notificación
    noti = Notificacion.objects.create(
        usuario=user,
        evento=evento,
        plantilla=plantilla,
        destinatario=destinatario,
        contexto_json=contexto,
        estado='pendiente',
        max_intentos=3,
    )
    # 5. Encolar tarea asíncrona
    from .tasks import enviar_notificacion
    if getattr(settings, 'NOTIFICACIONES_ASYNC', True):
        enviar_notificacion.delay(noti.id)
    else:
        enviar_notificacion(noti.id)  # útil en tests

    return noti
