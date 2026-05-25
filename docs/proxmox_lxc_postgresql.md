# PostgreSQL en LXC Proxmox para IS Minerals

Esta guia cubre solo el LXC de PostgreSQL. Para el despliegue completo con app, backups y Cloudflare Tunnel, usa tambien `docs/production_deploy.md`.

## Arquitectura recomendada

```text
[LXC isminerals-app] ---> TCP 5432 ---> [LXC isminerals-db: PostgreSQL]
```

Usa dos LXC separados para aislar la app de la base de datos.

## 1. Crear LXC de PostgreSQL

Desde Proxmox:

- Template: Debian 12 o Ubuntu Server LTS.
- CPU: 1-2 cores.
- RAM: 1-2 GB para empezar.
- Disco: 8-16 GB minimo, mas si guardas backups locales.
- Red: bridge `vmbr0`.
- IP: fija o reserva DHCP, por ejemplo `192.168.1.50`.
- Unprivileged container: recomendado.

## 2. Instalar PostgreSQL

Copia el proyecto o al menos `scripts/setup_postgres_lxc.sh` al LXC de DB.

```bash
export DB_NAME="isminerals"
export DB_USER="isminerals_app"
export DB_PASSWORD="pon_una_password_larga"
export APP_CIDR="192.168.1.25/32"  # IP del LXC de app
export DB_LISTEN_ADDRESSES="*"     # O la IP privada concreta del LXC DB
sudo bash scripts/setup_postgres_lxc.sh
```

El script no acepta `APP_CIDR` amplio salvo que lo autorices explicitamente:

```bash
export ALLOW_BROAD_CIDR=true
export APP_CIDR="192.168.1.0/24"
```

Para produccion, usa `/32`.

## 3. Configuracion aplicada

El script instala PostgreSQL, crea:

```sql
CREATE ROLE isminerals_app LOGIN PASSWORD '...';
CREATE DATABASE isminerals OWNER isminerals_app;
GRANT ALL PRIVILEGES ON DATABASE isminerals TO isminerals_app;
```

Y anade una regla `pg_hba.conf` restringida al LXC de app:

```conf
host    isminerals    isminerals_app    192.168.1.25/32    scram-sha-256
```

## 4. Configurar la app

En el LXC de app, guarda en `/etc/isminerals/isminerals.env`:

```env
APP_ENV=production
DATABASE_URL=postgresql+psycopg://isminerals_app:pon_una_password_larga@192.168.1.50:5432/isminerals
ADMIN_PASSWORD_HASH=tu_contrasena_o_hash
UPLOAD_DIR=/var/lib/isminerals/uploads
MINDAT_API_KEY=
```

Despues ejecuta:

```bash
python scripts/test_db.py
python scripts/init_db.py
```

## 5. Comprobar conexion manual

Desde el LXC de app:

```bash
psql "postgresql://isminerals_app:pon_una_password_larga@192.168.1.50:5432/isminerals"
```

Dentro de `psql`:

```sql
select current_database(), current_user;
```

## 6. Firewall

Permite solo la IP del LXC de app hacia el puerto `5432`.

Ejemplo con UFW dentro del LXC DB:

```bash
ufw allow from 192.168.1.25 to any port 5432 proto tcp
ufw enable
```

## 7. Backups

En produccion usa `isminerals-backup.timer`, definido en `deploy/systemd/`.

Comprobacion manual:

```bash
systemctl start isminerals-backup.service
ls -lh /var/backups/isminerals
```
