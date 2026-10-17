# NUAM · Gestión de Calificaciones Tributarias

Django + PostgreSQL + MongoDB. Perfiles: Administrador NUAM, Gestor de Calificaciones, Auditor y Consulta.

## Puesta en marcha en VS Code (Windows)

1. Instala Python 3.11+, PostgreSQL y MongoDB Community. Abre esta carpeta en VS Code.
2. Terminal de VS Code:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```
   Edita `.env` (clave y contraseña de PostgreSQL).
3. En PostgreSQL crea la base `nuam` y un usuario `nuam` con la contraseña de tu `.env`.
4. Migraciones y datos:
   ```
   python manage.py makemigrations calificaciones
   python manage.py migrate
   python manage.py crear_grupos
   python manage.py crear_datos_demo --password "UnaClaveLarga-2026"
   python manage.py runserver
   ```
5. Abre http://127.0.0.1:8000 e ingresa con `admin_nuam`, `gestor`, `auditor` o `consulta`.

Para probar rápido sin PostgreSQL: `DB_ENGINE=sqlite` en `.env`. Sin MongoDB el sistema funciona, pero el certificado queda «pendiente» y se audita.

## Pruebas
```
set DJANGO_DEBUG=True
set DB_ENGINE=sqlite
python manage.py test -v 2
```
Rendimiento: `pruebas_carga/k6_busqueda.js` (instrucciones en la cabecera).

## API
`POST /api/token/` con usuario y contraseña; luego `GET /api/calificaciones/?periodo=2024&rut=12345678-5` con `Authorization: Bearer <token>`.

## Despliegue en AWS
Ver `DESPLIEGUE_AWS.md` y la carpeta `deploy/`.

## Estado
Este código se escribió sin poder ejecutarlo. Lo primero es correr las pruebas y corregir lo que falle.
