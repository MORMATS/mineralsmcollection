# PostgreSQL en un LXC de Proxmox para la app de Minerales

Esta guía sustituye el `docker-compose.yml`. PostgreSQL vivirá en un contenedor LXC de Proxmox y la app Streamlit se conectará por IP.

## Arquitectura recomendada

```text
[Streamlit app] ---> TCP 5432 ---> [LXC Proxmox: PostgreSQL]
```

Puede ser:

1. Streamlit en tu PC/servidor y PostgreSQL en LXC.
2. Streamlit y PostgreSQL en el mismo LXC.
3. Streamlit en otro LXC y PostgreSQL en un LXC separado.

Para separar responsabilidades, recomiendo la opción 1 o 3.

## 1. Crear LXC en Proxmox

Desde la interfaz web de Proxmox:

- Template: Debian 12 o Ubuntu Server LTS.
- CPU: 1-2 cores.
- RAM: 1-2 GB para empezar.
- Disco: 8-16 GB mínimo; más si guardarás muchas copias/backups.
- Red: bridge `vmbr0`.
- IP: fija o reserva DHCP, por ejemplo `192.168.1.50`.
- Unprivileged container: recomendado.

Después entra por consola o SSH.

## 2. Instalar PostgreSQL dentro del LXC

Copia el proyecto al LXC o solo el script `scripts/setup_postgres_lxc.sh`.

Ejemplo con variables:

```bash
export DB_NAME="minerales"
export DB_USER="minerales_user"
export DB_PASSWORD="pon_una_password_larga"
export APP_CIDR="192.168.1.25/32"  # IP de la maquina donde corre Streamlit
sudo bash scripts/setup_postgres_lxc.sh
```

Si Streamlit puede correr desde cualquier equipo de tu LAN, puedes usar temporalmente:

```bash
export APP_CIDR="192.168.1.0/24"
```

Mejor usar `/32` para permitir solo una IP.

## 3. Configuración que aplica el script

Instala:

```bash
apt update
apt install -y postgresql postgresql-contrib
```

Crea:

```sql
CREATE ROLE minerales_user LOGIN PASSWORD '...';
CREATE DATABASE minerales OWNER minerales_user;
GRANT ALL PRIVILEGES ON DATABASE minerales TO minerales_user;
```

Modifica `postgresql.conf`:

```conf
listen_addresses = '*'
```

Y añade en `pg_hba.conf`:

```conf
host    minerales    minerales_user    192.168.1.25/32    scram-sha-256
```

Luego reinicia:

```bash
systemctl restart postgresql
```

## 4. Configurar Streamlit

En la máquina donde corre Streamlit:

```env
DATABASE_URL=postgresql+psycopg://minerales_user:pon_una_password_larga@192.168.1.50:5432/minerales
MINDAT_API_KEY=
```

Después:

```bash
python scripts/test_db.py
python scripts/init_db.py
streamlit run app.py
```

## 5. Comprobar conexión manual

Desde la máquina de Streamlit:

```bash
psql "postgresql://minerales_user:pon_una_password_larga@192.168.1.50:5432/minerales"
```

Dentro de `psql`:

```sql
select current_database(), current_user;
```

## 6. Firewall

Si usas firewall en Proxmox o dentro del LXC, permite solo la IP de Streamlit hacia el puerto `5432`.

Ejemplo con UFW dentro del LXC:

```bash
ufw allow from 192.168.1.25 to any port 5432 proto tcp
ufw enable
```

## 7. Backups

Dump lógico:

```bash
pg_dump -U minerales_user -h localhost minerales > minerales_backup.sql
```

Restaurar:

```bash
psql -U minerales_user -h localhost minerales < minerales_backup.sql
```

También puedes usar backups de Proxmox a nivel de LXC.
