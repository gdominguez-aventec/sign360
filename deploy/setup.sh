#!/bin/bash
#
# Primera instal·lació de Sign360 al servidor. S'executa una sola vegada, com a
# root. A partir d'aquí, les actualitzacions van amb `deploy.sh`.
#
# El que NO fa aquest script, a propòsit, perquè són decisions que ha de prendre
# una persona: crear el registre DNS, omplir les credencials del `.env` i
# habilitar els vhosts d'nginx.
set -euo pipefail

ROOT=/var/www/sign360
USER_APP=sign360
REPO="${REPO:-git@github.com:gdominguez-aventec/sign360.git}"
DB_NAME="${DB_NAME:-sign360}"
DB_USER="${DB_USER:-sign360}"

echo "==> Usuari de sistema"
id -u "$USER_APP" >/dev/null 2>&1 || adduser --system --group --shell /bin/bash --home "/home/$USER_APP" "$USER_APP"
usermod -aG www-data "$USER_APP"

echo "==> Directoris"
mkdir -p "$ROOT" /var/log/sign360
chown -R "$USER_APP:www-data" "$ROOT" /var/log/sign360

echo "==> Codi"
if [ ! -d "$ROOT/.git" ]; then
    sudo -u "$USER_APP" git clone "$REPO" "$ROOT"
fi

echo "==> Base de dades"
# La contrasenya no es genera aquí: es posa a mà al .env i al rol de postgres,
# per no deixar-la mai en un log de desplegament.
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 \
    || echo "AVÍS: cal crear el rol '$DB_USER' a postgres amb la seva contrasenya."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 \
    || sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"

echo "==> Entorn virtual"
sudo -u "$USER_APP" python3 -m venv "$ROOT/backend/env"
sudo -u "$USER_APP" "$ROOT/backend/env/bin/pip" install -q --upgrade pip

echo "==> Serveis"
cp "$ROOT/deploy/systemd/sign360-backend.socket" /etc/systemd/system/
cp "$ROOT/deploy/systemd/sign360-backend.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now sign360-backend.socket

cp "$ROOT/deploy/nginx/sign360-backend.conf"  /etc/nginx/sites-available/sign360-backend
cp "$ROOT/deploy/nginx/sign360-frontend.conf" /etc/nginx/sites-available/sign360-frontend

cat <<'MSG'

Instal·lació base feta. Ara, a mà:

  1. Crear el rol de postgres amb contrasenya, si l'avís de dalt ho demanava:
       sudo -u postgres psql -c "CREATE ROLE sign360 LOGIN PASSWORD '...'"
  2. Copiar backend/.env.example a backend/.env i omplir-lo (SECRET_KEY,
     DATABASE_*, ALLOWED_HOSTS, SIGNING_*).
  3. Crear frontend/.env amb NUXT_PUBLIC_API_HOST=https://api-sign360.aqua360.cloud
  4. Donar d'alta els registres DNS a Cloudflare (proxied):
       sign360.aqua360.cloud  i  api-sign360.aqua360.cloud
  5. Activar els vhosts i recarregar nginx:
       ln -s /etc/nginx/sites-available/sign360-backend  /etc/nginx/sites-enabled/
       ln -s /etc/nginx/sites-available/sign360-frontend /etc/nginx/sites-enabled/
       nginx -t && systemctl reload nginx
  6. Executar el desplegament:
       /var/www/sign360/deploy/deploy.sh

MSG
