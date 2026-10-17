from django.contrib import admin

from .models import CalificacionTributaria, HistorialAuditoria


@admin.register(CalificacionTributaria)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ("id_calificacion", "rut_emisor", "periodo_anual", "estado", "usuario")
    list_filter = ("estado", "periodo_anual")
    search_fields = ("rut_emisor",)


@admin.register(HistorialAuditoria)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ("fecha_hora", "usuario", "accion_realizada", "ip_origen")
    readonly_fields = [f.name for f in HistorialAuditoria._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
