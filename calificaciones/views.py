import csv
import io

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import mongo_service
from .forms import (
    CalificacionCrearForm,
    CalificacionForm,
    CargaMasivaForm,
    FiltroForm,
)
from .models import CalificacionTributaria, HistorialAuditoria
from .services import registrar_auditoria

COLUMNAS_CSV = ["periodo_anual", "rut_emisor", "monto_tributario", "estado"]


def requiere(permiso):
    """Exige sesion iniciada y el permiso indicado (403 si no lo tiene)."""

    def decorador(vista):
        return login_required(permission_required(permiso, raise_exception=True)(vista))

    return decorador


@requiere("calificaciones.view_calificaciontributaria")
def panel(request):
    filtro = FiltroForm(request.GET or None)
    consulta = CalificacionTributaria.objects.select_related("usuario")
    if filtro.is_valid():
        if filtro.cleaned_data.get("periodo"):
            consulta = consulta.filter(periodo_anual=filtro.cleaned_data["periodo"])
        if filtro.cleaned_data.get("rut"):
            consulta = consulta.filter(rut_emisor=filtro.cleaned_data["rut"])
    pagina = Paginator(consulta, 20).get_page(request.GET.get("page"))
    parametros = request.GET.copy()
    parametros.pop("page", None)
    return render(
        request,
        "panel.html",
        {"filtro": filtro, "pagina": pagina, "querystring": parametros.urlencode()},
    )


@requiere("calificaciones.view_calificaciontributaria")
def detalle(request, pk):
    calificacion = get_object_or_404(CalificacionTributaria, pk=pk)
    certificado, error_mongo = mongo_service.obtener_certificado(calificacion.pk)
    eventos = []
    if request.user.has_perm("calificaciones.ver_auditoria"):
        eventos = calificacion.eventos.select_related("usuario")[:10]
    return render(
        request,
        "detalle.html",
        {
            "cal": calificacion,
            "certificado": certificado,
            "error_mongo": error_mongo,
            "eventos": eventos,
        },
    )


@requiere("calificaciones.add_calificaciontributaria")
def crear(request):
    form = CalificacionCrearForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            calificacion = form.save(commit=False)
            calificacion.usuario = request.user
            calificacion.save()
            registrar_auditoria(
                request,
                f"CREAR calificación #{calificacion.pk} RUT {calificacion.rut_emisor} "
                f"período {calificacion.periodo_anual}",
                calificacion,
            )
        guardado = mongo_service.guardar_certificado(
            calificacion,
            empresa=form.cleaned_data.get("empresa", ""),
            tipo_certificado=form.cleaned_data.get("tipo_certificado") or "Calificación",
            observaciones=form.cleaned_data.get("observaciones", ""),
            evaluador=request.user.get_username(),
        )
        if guardado:
            messages.success(request, "Calificación creada correctamente.")
        else:
            registrar_auditoria(
                request,
                f"CERTIFICADO_PENDIENTE calificación #{calificacion.pk}: MongoDB no disponible",
                calificacion,
            )
            messages.warning(
                request,
                "La calificación se creó, pero el certificado quedó pendiente "
                "porque MongoDB no está disponible.",
            )
        return redirect("detalle", pk=calificacion.pk)
    return render(request, "form.html", {"form": form, "titulo": "Nueva calificación"})


@requiere("calificaciones.change_calificaciontributaria")
def editar(request, pk):
    calificacion = get_object_or_404(CalificacionTributaria, pk=pk)
    original = CalificacionTributaria.objects.get(pk=pk)  # copia previa a la edicion
    form = CalificacionForm(request.POST or None, instance=calificacion)
    if request.method == "POST" and form.is_valid():
        if not form.has_changed():
            messages.info(request, "No se realizaron cambios.")
            return redirect("detalle", pk=pk)
        cambios = "; ".join(
            f"{campo} {getattr(original, campo)} → {form.cleaned_data[campo]}"
            for campo in form.changed_data
        )
        with transaction.atomic():
            form.save()
            registrar_auditoria(request, f"EDITAR calificación #{pk}: {cambios}", calificacion)
        if "rut_emisor" in form.changed_data:
            mongo_service.actualizar_rut(pk, calificacion.rut_emisor)
        messages.success(request, "Calificación actualizada.")
        return redirect("detalle", pk=pk)
    return render(
        request, "form.html", {"form": form, "titulo": f"Editar calificación #{pk}"}
    )


@requiere("calificaciones.delete_calificaciontributaria")
@require_POST
def eliminar(request, pk):
    calificacion = get_object_or_404(CalificacionTributaria, pk=pk)
    descripcion = (
        f"ELIMINAR calificación #{pk} RUT {calificacion.rut_emisor} "
        f"período {calificacion.periodo_anual}"
    )
    with transaction.atomic():
        registrar_auditoria(request, descripcion, calificacion)
        calificacion.delete()
    if not mongo_service.eliminar_certificado(pk):
        registrar_auditoria(
            request, f"DOCUMENTO_HUERFANO calificación #{pk}: no se pudo borrar en MongoDB"
        )
        messages.warning(
            request, "Se eliminó la calificación, pero no se pudo borrar su certificado en MongoDB."
        )
    else:
        messages.success(request, "Calificación eliminada.")
    return redirect("panel")


@requiere("calificaciones.ver_auditoria")
def auditoria(request):
    eventos = HistorialAuditoria.objects.select_related("usuario")
    pagina = Paginator(eventos, 50).get_page(request.GET.get("page"))
    return render(request, "auditoria.html", {"pagina": pagina})


def _detectar_delimitador(texto):
    lineas = texto.splitlines()
    primera = lineas[0] if lineas else ""
    return ";" if primera.count(";") > primera.count(",") else ","


@requiere("calificaciones.add_calificaciontributaria")
def carga_masiva(request):
    errores = []
    form = CargaMasivaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            texto = form.cleaned_data["archivo"].read().decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = None
            form.add_error("archivo", "El archivo debe estar codificado en UTF-8.")
        if texto is not None:
            lector = csv.DictReader(io.StringIO(texto), delimiter=_detectar_delimitador(texto))
            if set(lector.fieldnames or []) != set(COLUMNAS_CSV):
                form.add_error(
                    "archivo", "Las columnas deben ser exactamente: " + ", ".join(COLUMNAS_CSV)
                )
            else:
                formularios = []
                for numero, fila in enumerate(lector, start=2):
                    if numero - 1 > settings.CARGA_MASIVA_MAX_FILAS:
                        errores.append(
                            f"El archivo supera el máximo de {settings.CARGA_MASIVA_MAX_FILAS} filas."
                        )
                        break
                    datos = {c: (fila.get(c) or "").strip() for c in COLUMNAS_CSV}
                    fila_form = CalificacionForm(datos)
                    if fila_form.is_valid():
                        formularios.append(fila_form)
                    else:
                        for campo, lista in fila_form.errors.items():
                            for mensaje in lista:
                                errores.append(f"Fila {numero}, {campo}: {mensaje}")
                if not formularios and not errores:
                    errores.append("El archivo no contiene filas de datos.")
                if not errores:
                    nuevas = []
                    with transaction.atomic():
                        for fila_form in formularios:
                            cal = fila_form.save(commit=False)
                            cal.usuario = request.user
                            cal.save()
                            registrar_auditoria(
                                request,
                                f"CARGA_MASIVA crear calificación #{cal.pk} RUT {cal.rut_emisor} "
                                f"período {cal.periodo_anual}",
                                cal,
                            )
                            nuevas.append(cal)
                    fallidos = sum(
                        0
                        if mongo_service.guardar_certificado(
                            cal, evaluador=request.user.get_username()
                        )
                        else 1
                        for cal in nuevas
                    )
                    if fallidos:
                        registrar_auditoria(
                            request,
                            f"CERTIFICADO_PENDIENTE carga masiva: {fallidos} registros sin documento en MongoDB",
                        )
                        messages.warning(
                            request,
                            f"{fallidos} certificados quedaron pendientes (MongoDB no disponible).",
                        )
                    messages.success(request, f"Se crearon {len(nuevas)} calificaciones.")
                    return redirect("panel")
    return render(
        request,
        "carga_masiva.html",
        {"form": form, "errores": errores, "columnas": ", ".join(COLUMNAS_CSV)},
    )
