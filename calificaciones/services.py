import ipaddress

from .models import HistorialAuditoria


def obtener_ip(request):
    """IP de origen. Solo confia en X-Real-IP si la peticion llega desde el proxy local."""
    remota = request.META.get("REMOTE_ADDR")
    if remota in ("127.0.0.1", "::1"):
        real = request.META.get("HTTP_X_REAL_IP", "").strip()
        if real:
            remota = real
    try:
        return str(ipaddress.ip_address(remota))
    except (ValueError, TypeError):
        return None


def registrar_auditoria(request, accion, calificacion=None):
    usuario = request.user if request.user.is_authenticated else None
    return HistorialAuditoria.objects.create(
        usuario=usuario,
        calificacion=calificacion,
        accion_realizada=accion[:500],
        ip_origen=obtener_ip(request),
    )
