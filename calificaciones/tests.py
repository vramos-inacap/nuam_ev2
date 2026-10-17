"""Pruebas automatizadas. Ejecutar con:
    set DJANGO_DEBUG=True
    set DB_ENGINE=sqlite
    python manage.py test -v 2
Las llamadas a MongoDB se simulan (mock) para poder correr sin el servicio.
"""
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .forms import CalificacionForm
from .models import CalificacionTributaria, HistorialAuditoria
from .validators import calcular_dv, normalizar_rut

CLAVE = "ClaveDePrueba-2026"
RUT_OK = "12345678-5"
RUT_2 = "76123456-" + calcular_dv("76123456")


def usuario_en_grupo(nombre_usuario, grupo):
    usuario = User.objects.create_user(nombre_usuario, password=CLAVE)
    usuario.groups.add(Group.objects.get(name=grupo))
    return usuario


class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("crear_grupos", verbosity=0)
        cls.admin = usuario_en_grupo("admin_t", "Administrador NUAM")
        cls.gestor = usuario_en_grupo("gestor_t", "Gestor de Calificaciones")
        cls.auditor = usuario_en_grupo("auditor_t", "Auditor")
        cls.consulta = usuario_en_grupo("consulta_t", "Consulta")
        cls.cal = CalificacionTributaria.objects.create(
            periodo_anual=2024, rut_emisor=RUT_OK, monto_tributario=Decimal("1000"),
            estado="Pendiente", usuario=cls.gestor,
        )

    def entrar(self, usuario):
        self.client.force_login(usuario)


class RutTests(TestCase):
    def test_digito_verificador(self):
        self.assertEqual(calcular_dv("12345678"), "5")

    def test_normaliza_formatos(self):
        self.assertEqual(normalizar_rut("12.345.678-5"), RUT_OK)
        self.assertEqual(normalizar_rut("123456785"), RUT_OK)

    def test_rechaza_dv_incorrecto_y_formato(self):
        with self.assertRaises(ValidationError):
            normalizar_rut("12345678-9")
        with self.assertRaises(ValidationError):
            normalizar_rut("abc")


class FormularioTests(TestCase):
    def datos(self, **cambios):
        base = {"periodo_anual": 2024, "rut_emisor": RUT_OK, "monto_tributario": "500", "estado": "Aprobado"}
        base.update(cambios)
        return base

    def test_valido(self):
        self.assertTrue(CalificacionForm(self.datos()).is_valid())

    def test_rut_vacio(self):
        self.assertFalse(CalificacionForm(self.datos(rut_emisor="")).is_valid())

    def test_monto_negativo(self):
        self.assertFalse(CalificacionForm(self.datos(monto_tributario="-1")).is_valid())

    def test_estado_fuera_de_catalogo(self):
        self.assertFalse(CalificacionForm(self.datos(estado="Otro")).is_valid())


class PermisosTests(BaseTest):
    def test_anonimo_redirige_a_login(self):
        respuesta = self.client.get(reverse("panel"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/login/", respuesta.url)

    def test_consulta_no_puede_crear_ni_eliminar(self):
        self.entrar(self.consulta)
        self.assertEqual(self.client.get(reverse("crear")).status_code, 403)
        respuesta = self.client.post(reverse("eliminar", args=[self.cal.pk]))
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(CalificacionTributaria.objects.filter(pk=self.cal.pk).exists())

    def test_boton_eliminar_solo_para_administrador(self):
        with mock.patch("calificaciones.mongo_service.obtener_certificado", return_value=(None, False)):
            self.entrar(self.consulta)
            self.assertNotContains(self.client.get(reverse("detalle", args=[self.cal.pk])), "Eliminar registro")
            self.entrar(self.admin)
            self.assertContains(self.client.get(reverse("detalle", args=[self.cal.pk])), "Eliminar registro")

    def test_auditoria_solo_con_permiso(self):
        self.entrar(self.gestor)
        self.assertEqual(self.client.get(reverse("auditoria")).status_code, 403)
        self.entrar(self.auditor)
        self.assertEqual(self.client.get(reverse("auditoria")).status_code, 200)

    def test_eliminar_requiere_post(self):
        self.entrar(self.admin)
        self.assertEqual(self.client.get(reverse("eliminar", args=[self.cal.pk])).status_code, 405)


class FlujoCrudTests(BaseTest):
    def _datos(self):
        return {
            "periodo_anual": 2023, "rut_emisor": RUT_2, "monto_tributario": "750000",
            "estado": "Aprobado", "empresa": "Empresa X",
            "tipo_certificado": "Calificación", "observaciones": "",
        }

    def test_crear_guarda_auditoria_y_certificado(self):
        self.entrar(self.gestor)
        with mock.patch("calificaciones.mongo_service.guardar_certificado", return_value=True) as guardar:
            self.client.post(reverse("crear"), self._datos())
        self.assertEqual(CalificacionTributaria.objects.filter(periodo_anual=2023).count(), 1)
        self.assertTrue(HistorialAuditoria.objects.filter(accion_realizada__startswith="CREAR").exists())
        guardar.assert_called_once()

    def test_crear_con_mongo_caido_registra_pendiente(self):
        self.entrar(self.gestor)
        with mock.patch("calificaciones.mongo_service.guardar_certificado", return_value=False):
            self.client.post(reverse("crear"), self._datos())
        self.assertTrue(
            HistorialAuditoria.objects.filter(accion_realizada__startswith="CERTIFICADO_PENDIENTE").exists()
        )

    def test_crear_incompleto_no_guarda(self):
        self.entrar(self.gestor)
        datos = self._datos()
        datos["rut_emisor"] = ""
        self.client.post(reverse("crear"), datos)
        self.assertEqual(CalificacionTributaria.objects.filter(periodo_anual=2023).count(), 0)

    def test_editar_registra_cambio(self):
        self.entrar(self.gestor)
        self.client.post(reverse("editar", args=[self.cal.pk]), {
            "periodo_anual": 2024, "rut_emisor": RUT_OK, "monto_tributario": "1000", "estado": "Aprobado"})
        self.cal.refresh_from_db()
        self.assertEqual(self.cal.estado, "Aprobado")
        self.assertTrue(HistorialAuditoria.objects.filter(accion_realizada__startswith="EDITAR").exists())

    def test_eliminar_conserva_auditoria(self):
        self.entrar(self.admin)
        with mock.patch("calificaciones.mongo_service.eliminar_certificado", return_value=True):
            self.client.post(reverse("eliminar", args=[self.cal.pk]))
        self.assertFalse(CalificacionTributaria.objects.filter(pk=self.cal.pk).exists())
        evento = HistorialAuditoria.objects.get(accion_realizada__startswith="ELIMINAR")
        self.assertIsNone(evento.calificacion)
        self.assertIn(RUT_OK, evento.accion_realizada)

    def test_auditoria_no_se_modifica(self):
        evento = HistorialAuditoria.objects.create(usuario=self.admin, accion_realizada="X")
        evento.accion_realizada = "Y"
        with self.assertRaises(PermissionError):
            evento.save()


class CargaMasivaTests(BaseTest):
    def subir(self, texto):
        archivo = SimpleUploadedFile("datos.csv", texto.encode("utf-8"), content_type="text/csv")
        return self.client.post(reverse("carga_masiva"), {"archivo": archivo})

    def test_carga_valida(self):
        self.entrar(self.gestor)
        with mock.patch("calificaciones.mongo_service.guardar_certificado", return_value=True):
            self.subir(f"periodo_anual,rut_emisor,monto_tributario,estado\n2022,{RUT_2},1500.50,Aprobado\n")
        self.assertTrue(CalificacionTributaria.objects.filter(periodo_anual=2022).exists())

    def test_una_fila_invalida_no_guarda_nada(self):
        self.entrar(self.gestor)
        antes = CalificacionTributaria.objects.count()
        respuesta = self.subir(
            "periodo_anual,rut_emisor,monto_tributario,estado\n"
            f"2022,{RUT_2},1500,Aprobado\n2022,11111111-2,10,Aprobado\n")
        self.assertEqual(CalificacionTributaria.objects.count(), antes)
        self.assertContains(respuesta, "Fila 3")

    def test_rechaza_extension_incorrecta(self):
        self.entrar(self.gestor)
        archivo = SimpleUploadedFile("datos.txt", b"x")
        respuesta = self.client.post(reverse("carga_masiva"), {"archivo": archivo})
        self.assertContains(respuesta, "Solo se aceptan archivos .csv")


class ApiTests(BaseTest):
    def test_requiere_autenticacion(self):
        self.assertIn(APIClient().get("/api/calificaciones/").status_code, (401, 403))

    def test_filtra_por_periodo_y_rut(self):
        CalificacionTributaria.objects.create(
            periodo_anual=2021, rut_emisor=RUT_2, monto_tributario=Decimal("10"), estado="Aprobado")
        cliente = APIClient()
        cliente.force_authenticate(self.consulta)
        datos = cliente.get("/api/calificaciones/", {"periodo": 2024, "rut": RUT_OK}).json()
        self.assertEqual(datos["count"], 1)

    def test_entrada_maliciosa_devuelve_400(self):
        cliente = APIClient()
        cliente.force_authenticate(self.consulta)
        self.assertEqual(cliente.get("/api/calificaciones/", {"periodo": "1 OR 1=1"}).status_code, 400)
        self.assertEqual(cliente.get("/api/calificaciones/", {"rut": "' OR '1'='1"}).status_code, 400)
