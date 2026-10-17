from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtener"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refrescar"),
    path("", include("calificaciones.urls")),
]
