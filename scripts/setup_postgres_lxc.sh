#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-isminerals}"
DB_USER="${DB_USER:-isminerals_app}"
: "${DB_PASSWORD:?Set DB_PASSWORD to a long random password.}"
: "${APP_CIDR:?Set APP_CIDR to the app LXC IP/CIDR, preferably x.x.x.x/32.}"
DB_LISTEN_ADDRESSES="${DB_LISTEN_ADDRESSES:-*}"
ALLOW_BROAD_CIDR="${ALLOW_BROAD_CIDR:-false}"

if [[ ! "$DB_NAME" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || [[ ! "$DB_USER" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
  echo "DB_NAME and DB_USER must be simple PostgreSQL identifiers." >&2
  exit 1
fi

if [[ "$APP_CIDR" != */32 && "$ALLOW_BROAD_CIDR" != "true" ]]; then
  echo "APP_CIDR should be a single app host (/32). Set ALLOW_BROAD_CIDR=true to override." >&2
  exit 1
fi

DB_PASSWORD_SQL="${DB_PASSWORD//\'/\'\'}"

echo "[1/6] Instalando PostgreSQL..."
apt update
apt install -y postgresql postgresql-contrib

echo "[2/6] Activando servicio..."
systemctl enable --now postgresql

echo "[3/6] Creando usuario y base de datos..."
sudo -u postgres psql <<SQL
DO
\$do\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}'
   ) THEN
      CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD_SQL}';
   ELSE
      ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD_SQL}';
   END IF;
END
\$do\$;

SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec

GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

PG_VERSION="$(ls /etc/postgresql | sort -V | tail -n 1)"
PG_CONF="/etc/postgresql/${PG_VERSION}/main/postgresql.conf"
PG_HBA="/etc/postgresql/${PG_VERSION}/main/pg_hba.conf"

echo "[4/6] Configurando listen_addresses..."
if grep -q "^#listen_addresses" "$PG_CONF"; then
  sed -i "s/^#listen_addresses.*/listen_addresses = '${DB_LISTEN_ADDRESSES}'/" "$PG_CONF"
elif grep -q "^listen_addresses" "$PG_CONF"; then
  sed -i "s/^listen_addresses.*/listen_addresses = '${DB_LISTEN_ADDRESSES}'/" "$PG_CONF"
else
  echo "listen_addresses = '${DB_LISTEN_ADDRESSES}'" >> "$PG_CONF"
fi

echo "[5/6] Configurando pg_hba.conf para ${APP_CIDR}..."
if ! grep -q "minerales_app_access" "$PG_HBA"; then
  cat >> "$PG_HBA" <<HBA

# minerales_app_access
host    ${DB_NAME}    ${DB_USER}    ${APP_CIDR}    scram-sha-256
HBA
fi

echo "[6/6] Reiniciando PostgreSQL..."
systemctl restart postgresql

echo
echo "PostgreSQL listo."
echo "DB_NAME=${DB_NAME}"
echo "DB_USER=${DB_USER}"
echo "APP_CIDR=${APP_CIDR}"
echo "DB_LISTEN_ADDRESSES=${DB_LISTEN_ADDRESSES}"
echo
echo "DATABASE_URL=postgresql+psycopg://${DB_USER}:<password>@IP_DEL_LXC_DB:5432/${DB_NAME}"
echo
echo "Recuerda sustituir IP_DEL_LXC_DB y guardar la password solo en el entorno de la app."
