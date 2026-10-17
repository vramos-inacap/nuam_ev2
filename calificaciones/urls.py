from django.urls import path

from . import api, views

urlpatterns = [
    path("", views.panel, name="panel"),
    path("calificaciones/nueva/", views.crear, name="crear"),
    path("calificaciones/<int:pk>/", views.detalle, name="detalle"),
    path("calificaciones/<int:pk>/editar/", views.editar, name="editar"),
    path("calificaciones/<int:pk>/eliminar/", views.eliminar, name="eliminar"),
    path("carga-masiva/", views.carga_masiva, name="carga_masiva"),
    path("auditoria/", views.auditoria, name="auditoria"),
    path("api/calificaciones/", api.CalificacionListaAPI.as_view(), name="api_calificaciones"),
]
