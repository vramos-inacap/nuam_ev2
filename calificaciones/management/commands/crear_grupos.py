from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

GRUPOS = {
    "Administrador NUAM": [
        "view_calificaciontributaria",
        "add_calificaciontributaria",
        "change_calificaciontributaria",
        "delete_calificaciontributaria",
        "ver_auditoria",
    ],
    "Gestor de Calificaciones": [
        "view_calificaciontributaria",
        "add_calificaciontributaria",
        "change_calificaciontributaria",
    ],
    "Auditor": ["view_calificaciontributaria", "ver_auditoria"],
    "Consulta": ["view_calificaciontributaria"],
}


class Command(BaseCommand):
    help = "Crea los perfiles (grupos) y sus permisos. Ejecutar despues de migrate."

    def handle(self, *args, **options):
        for nombre, codigos in GRUPOS.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            permisos = Permission.objects.filter(
                content_type__app_label="calificaciones", codename__in=codigos
            )
            if permisos.count() != len(codigos):
                self.stderr.write(f"Faltan permisos para {nombre}: ¿ejecutaste migrate?")
            grupo.permissions.set(permisos)
            self.stdout.write(self.style.SUCCESS(f"Grupo listo: {nombre}"))
