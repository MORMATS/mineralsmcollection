# Despliegue production ready

Objetivo: publicar `isminerals.neodataglobal.com` con dos LXC Proxmox:

- `isminerals-db`: PostgreSQL.
- `isminerals-app`: Streamlit, backups y Cloudflare Tunnel.

## 1. Rotar secretos antes de publicar

Si alguna credencial estuvo en archivos versionados, rota:

- Password de PostgreSQL.
- `MINDAT_API_KEY`.
- `ADMIN_PASSWORD_HASH`.

Los ejemplos del repo deben contener solo placeholders.

## 2. LXC de PostgreSQL

En `isminerals-db`:

```bash
export DB_NAME="isminerals"
export DB_USER="isminerals_app"
export DB_PASSWORD="CAMBIA_ESTA_PASSWORD_LARGA"
export APP_CIDR="IP_DEL_LXC_APP/32"
export DB_LISTEN_ADDRESSES="*"
sudo bash scripts/setup_postgres_lxc.sh
```

Usa firewall de Proxmox o del LXC para permitir TCP 5432 solo desde `IP_DEL_LXC_APP`.

## 3. LXC de app

Crear usuario y directorios:

```bash
sudo useradd --system --home /opt/isminerals --shell /bin/bash isminerals
sudo mkdir -p /opt/isminerals /etc/isminerals /var/lib/isminerals/uploads /var/backups/isminerals
sudo chown -R isminerals:isminerals /opt/isminerals /var/lib/isminerals /var/backups/isminerals
```

Clonar repo en `/opt/isminerals/app` y crear `/etc/isminerals/isminerals.env` desde `deploy/env/isminerals.env.example`.

Instalar servicios:

```bash
sudo cp deploy/systemd/isminerals.service /etc/systemd/system/
sudo cp deploy/systemd/isminerals-backup.service /etc/systemd/system/
sudo cp deploy/systemd/isminerals-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now isminerals
sudo systemctl enable --now isminerals-backup.timer
```

## 4. Primer deploy

```bash
sudo APP_DIR=/opt/isminerals/app bash /opt/isminerals/app/scripts/deploy_lxc.sh
```

El script hace `git pull`, instala dependencias, ejecuta Alembic y reinicia `isminerals.service`.
Antes de ejecutar Alembic carga `/etc/isminerals/isminerals.env` para usar la misma `DATABASE_URL` que el servicio. Si usas otro archivo, pasalo con `ENV_FILE=/ruta/al/env`.
Si no pasas `APP_DIR`, intenta leer el `WorkingDirectory` real del servicio systemd y lo usa como ruta de la app. Para confirmar que estas actualizando la misma ruta que ejecuta el servicio:

```bash
systemctl show isminerals --property=WorkingDirectory --value
systemctl cat isminerals
```

## 5. Cloudflare Tunnel

Instala `cloudflared`, autentica el túnel y usa como base `deploy/cloudflared/config.yml.example`:

```yaml
ingress:
  - hostname: isminerals.neodataglobal.com
    service: http://127.0.0.1:8501
  - service: http_status:404
```

Después:

```bash
sudo systemctl enable --now cloudflared
```

## 6. Comprobaciones

```bash
systemctl status isminerals cloudflared isminerals-backup.timer
curl --fail http://127.0.0.1:8501
python scripts/test_db.py
```

Revisa que los logs no contengan `DATABASE_URL`, tokens ni contraseña.

Si la web muestra que la base de datos necesita una actualizacion tras subir cambios, ejecuta:

```bash
sudo APP_DIR=/opt/isminerals/app ENV_FILE=/etc/isminerals/isminerals.env bash /opt/isminerals/app/scripts/deploy_lxc.sh
sudo journalctl -u isminerals -n 80 --no-pager
```
