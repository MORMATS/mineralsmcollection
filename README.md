# Minerales Streamlit App — PostgreSQL en LXC Proxmox + Mindat API

App base para una colección/catálogo virtual de minerales con:

- Streamlit multipágina.
- PostgreSQL alojado en un LXC de Proxmox.
- SQLAlchemy 2.
- Driver moderno `psycopg`.
- Subida de fotos por pieza.
- Tabla índice de colección con ID, vendido/no vendido, características especiales, minerales secundarios y link de compra.
- Filtros por vendido, ubicación, mineral y chakra.
- Importación/enriquecimiento desde Mindat API.

## 1. Preparar PostgreSQL en el LXC

Crea un LXC Debian 12 o Ubuntu Server en Proxmox, asígnale una IP fija o reserva DHCP, y entra por consola/SSH.

Dentro del LXC puedes ejecutar:

```bash
sudo bash scripts/setup_postgres_lxc.sh
```

O seguir la guía manual:

```text
docs/proxmox_lxc_postgresql.md
```

## 2. Configurar la app Streamlit

En la máquina donde correrá Streamlit:

```bash
cp .env.example .env
```

Edita `.env` y cambia la IP y password:

```env
DATABASE_URL=postgresql+psycopg://minerales_user:TU_PASSWORD@IP_DEL_LXC:5432/minerales
MINDAT_API_KEY=
```

## 3. Arrancar la app

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/test_db.py
python scripts/init_db.py
streamlit run app.py
```

## 4. Usar Mindat API

Pon tu token en `.env`:

```env
MINDAT_API_KEY=tu_token
```

Importar desde terminal:

```bash
python scripts/import_mindat.py --names "Quartz,Amethyst,Fluorite"
```

O desde la web app: abre la página **Importar API**.

## 5. Estructura principal

```text
app.py
pages/
  1_Coleccion.py
  2_Ficha.py
  3_Alta_edicion.py
  4_Admin_datos.py
  5_Importar_API.py
scripts/
  setup_postgres_lxc.sh
  init_db.py
  import_mindat.py
  test_db.py
docs/
  proxmox_lxc_postgresql.md
src/
  db.py
  models.py
  crud.py
  mindat_api.py
  seeds.py
  image_utils.py
```

## 6. Seguridad mínima recomendada

- Usa IP fija/reserva DHCP para el LXC.
- No abras PostgreSQL a Internet; limítalo a tu LAN o VPN.
- En `pg_hba.conf`, permite solo la IP de la máquina donde corre Streamlit.
- Usa una contraseña larga.
- Haz backups del LXC o dumps con `pg_dump`.
