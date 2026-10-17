from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission

from .models import CalificacionTributaria
from .validators import normalizar_rut


class PuedeVerCalificaciones(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm("calificaciones.view_calificaciontributaria")
        )


class CalificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalificacionTributaria
        fields = [
            "id_calificacion",
            "periodo_anual",
            "rut_emisor",
            "monto_tributario",
            "estado",
            "fecha_creacion",
        ]


class Paginacion(PageNumberPagination):
    page_size = 25


class CalificacionListaAPI(generics.ListAPIView):
    serializer_class = CalificacionSerializer
    permission_classes = [PuedeVerCalificaciones]
    pagination_class = Paginacion

    def get_queryset(self):
        consulta = CalificacionTributaria.objects.all()
        periodo = self.request.query_params.get("periodo")
        rut = self.request.query_params.get("rut")
        if periodo:
            try:
                consulta = consulta.filter(periodo_anual=int(periodo))
            except ValueError:
                raise serializers.ValidationError({"periodo": "Debe ser un año numérico."})
        if rut:
            try:
                consulta = consulta.filter(rut_emisor=normalizar_rut(rut))
            except DjangoValidationError as error:
                raise serializers.ValidationError({"rut": error.messages})
        return consulta
