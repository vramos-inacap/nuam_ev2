# Despliegue en EC2 (sin verificar: ajusta según tu AMI)

1. Lanza una EC2 Linux (RHEL 9 o Amazon Linux 2023), asocia una **IP elástica** y abre en el grupo de seguridad solo 80 y 443 (público) y 22 (tu IP).
2. Instala: `sudo dnf install -y python3.11 python3.11-pip git nginx postgresql-server` y MongoDB desde su repositorio oficial (no viene en los repos por defecto; sigue la guía de mongodb.com para tu SO).
3. Inicializa PostgreSQL (`sudo postgresql-setup --initdb`), arráncalo y crea base y usuario `nuam`. Deja ambas bases escuchando solo en localhost.
4. Clona el repositorio en `/opt/nuam`, crea el venv, `pip install -r requirements.txt` y crea `.env` con `DJANGO_DEBUG=False`, tu `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=<IP elástica>`, `CSRF_TRUSTED_ORIGINS=https://<IP elástica>` y `USE_HTTPS=True`.
5. `python manage.py migrate && python manage.py crear_grupos && python manage.py collectstatic --noinput`.
6. Certificado autofirmado:
   `sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/ssl/private/nuam.key -out /etc/ssl/certs/nuam.crt -subj "/CN=<IP elástica>"`
7. Copia `deploy/nginx.conf` a `/etc/nginx/conf.d/nuam.conf` (cambia TU_IP_ELASTICA) y `deploy/nuam.service` a `/etc/systemd/system/`. Luego: `sudo systemctl enable --now nuam nginx postgresql mongod`.
8. En RHEL con SELinux: `sudo setsebool -P httpd_can_network_connect 1`.
9. Los laboratorios de AWS Academy se apagan: deja los servicios habilitados para que inicien solos y prueba todo antes de grabar.
