from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .validators import validar_rut


class CalificacionTributaria(models.Model):
    class Estado(models.TextChoices):
        APROBADO = "Aprobado", "Aprobado"
        PENDIENTE = "Pendiente", "Pendiente"
        RECHAZADO = "Rechazado", "Rechazado"

    id_calificacion = models.AutoField(primary_key=True)
    periodo_anual = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)]
    )
    rut_emisor = models.CharField(max_length=12, validators=[validar_rut])
    monto_tributario = models.DecimalField(
        max_digits=16, decimal_places=2, validators=[MinValueValidator(0)]
    )
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="calificaciones",
    )

    class Meta:
        ordering = ["-fecha_creacion", "-id_calificacion"]
        indexes = [models.Index(fields=["rut_emisor", "periodo_anual"])]

    def __str__(self):
        return f"#{self.pk} {self.rut_emisor} ({self.periodo_anual})"


class HistorialAuditoria(models.Model):
    id_auditoria = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="eventos_auditoria",
    )
    calificacion = models.ForeignKey(
        CalificacionTributaria,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="eventos",
    )
    accion_realizada = models.CharField(max_length=500)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_hora", "-id_auditoria"]
        permissions = [("ver_auditoria", "Puede consultar la auditoría")]

    def save(self, *args, **kwargs):
        # Los registros de auditoria son de solo escritura: no se editan.
        if self.pk is not None and not self._state.adding:
            raise PermissionError("Los registros de auditoría no se pueden modificar.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fecha_hora:%Y-%m-%d %H:%M} {self.accion_realizada[:60]}"
