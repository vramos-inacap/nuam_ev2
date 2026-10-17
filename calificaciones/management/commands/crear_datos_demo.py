from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError

from calificaciones import mongo_service
from calificaciones.models import CalificacionTributaria
from calificaciones.validators import calcular_dv

USUARIOS = {
    "admin_nuam": "Administrador NUAM",
    "gestor": "Gestor de Calificaciones",
    "auditor": "Auditor",
    "consulta": "Consulta",
}

DATOS = [
    ("76123456", 2024, "2400000", "Aprobado", "Contribuyente Uno SpA"),
    ("96543210", 2023, "1850000", "Pendiente", "Contribuyente Dos S.A."),
    ("77888999", 2022, "4200000", "Rechazado", "Contribuyente Tres Ltda."),
    ("76000111", 2024, "950000", "Aprobado", "Contribuyente Cuatro SpA"),
]


class Command(BaseCommand):
    help = "Crea usuarios de ejemplo (uno por perfil) y calificaciones de prueba."

    def add_arguments(self, parser):
        parser.add_argument("--password", required=True, help="Contraseña (mínimo 10 caracteres)")

    def handle(self, *args, **options):
        clave = options["password"]
        if len(clave) < 10:
            raise CommandError("La contraseña debe tener al menos 10 caracteres.")
        for nombre, grupo in USUARIOS.items():
            usuario, _ = User.objects.get_or_create(username=nombre)
            usuario.set_password(clave)
            usuario.save()
            usuario.groups.set([Group.objects.get(name=grupo)])
            self.stdout.write(f"Usuario {nombre} -> {grupo}")
        autor = User.objects.get(username="gestor")
        for cuerpo, periodo, monto, estado, empresa in DATOS:
            rut = f"{cuerpo}-{calcular_dv(cuerpo)}"
            cal, _ = CalificacionTributaria.objects.get_or_create(
                rut_emisor=rut,
                periodo_anual=periodo,
                defaults={"monto_tributario": monto, "estado": estado, "usuario": autor},
            )
            ok = mongo_service.guardar_certificado(
                cal,
                empresa=empresa,
                tipo_certificado="Calificación",
                observaciones=f"Período anual {periodo}",
                evaluador="Sistema NUAM",
            )
            if not ok:
                self.stderr.write(f"MongoDB no disponible: sin certificado para {rut}")
        self.stdout.write(self.style.SUCCESS("Datos de demostración listos."))
