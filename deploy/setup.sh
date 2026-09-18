#!/bin/bash
#
# Primera instal·lació d'app.aqua360-sign al servidor. S'executa un sol cop, com a
# root. A partir d'aquí, les actualitzacions van amb `deploy.sh`.
#
# El que NO fa aquest script, a propòsit, perquè són decisions que ha de prendre
# una persona: crear el registre DNS, omplir les credencials del `.env` i
# habilitar els vhosts d'nginx.
set -euo pipefail

ROOT=/var/www/app-aqua360-sign
USER_APP=app-aqua360-sign
REPO="${REPO:-git@github.com:AQUA360/app-aqua360-sign.git}"
DB_NAME="${DB_NAME:-app_aqua360_sign}"
DB_USER="${DB_USER:-app_aqua360_sign}"
NODE_VERSION="${NODE_VERSION:-22}"

echo "==> Usuari de sistema"
id -u "$USER_APP" >/dev/null 2>&1 || adduser --system --group --shell /bin/bash --home "/home/$USER_APP" "$USER_APP"
usermod -aG www-data "$USER_APP"

echo "==> Directoris"
mkdir -p "$ROOT" /var/log/app-aqua360-sign "/home/$USER_APP"
chown -R "$USER_APP:www-data" "$ROOT" /var/log/app-aqua360-sign "/home/$USER_APP"

echo "==> Clau de desplegament"
# Clau pròpia de l'usuari, per poder fer `git pull` sense la clau de root.
sudo -u "$USER_APP" mkdir -p "/home/$USER_APP/.ssh"
if [ ! -f "/home/$USER_APP/.ssh/id_ed25519" ]; then
    sudo -u "$USER_APP" ssh-keygen -q -t ed25519 -N "" -C "$USER_APP@$(hostname)" -f "/home/$USER_APP/.ssh/id_ed25519"
    echo "    Cal donar d'alta aquesta clau com a deploy key (lectura) al repositori:"
    cat "/home/$USER_APP/.ssh/id_ed25519.pub"
fi
sudo -u "$USER_APP" ssh-keyscan -H github.com >> "/home/$USER_APP/.ssh/known_hosts" 2>/dev/null
chmod 700 "/home/$USER_APP/.ssh"

echo "==> Codi"
[ -d "$ROOT/.git" ] || sudo -u "$USER_APP" git clone "$REPO" "$ROOT"

echo "==> Base de dades"
# La contrasenya no es genera aquí: es posa a mà al .env i al rol de postgres,
# per no deixar-la mai en un log de desplegament.
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 \
    || echo "    AVÍS: cal crear el rol '$DB_USER' a postgres amb la seva contrasenya."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 \
    || sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"

echo "==> Entorn virtual de Python"
sudo -u "$USER_APP" python3 -m venv "$ROOT/backend/env"
sudo -u "$USER_APP" "$ROOT/backend/env/bin/pip" install -q --upgrade pip

echo "==> Node $NODE_VERSION per a l'usuari (nvm)"
# El Node del sistema és el 20, que fa servir avsis; no s'hi toca. El frontal
# demana Node >= 22 (dependències de @nuxtjs/i18n v9) i npm 11, que és amb el
# que s'ha generat el package-lock.json.
sudo -u "$USER_APP" -H bash -lc "
    set -e
    export NVM_DIR=\$HOME/.nvm
    [ -d \$NVM_DIR ] || curl -sfLo- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    . \$NVM_DIR/nvm.sh
    nvm install $NODE_VERSION
    nvm alias default $NODE_VERSION
    npm install -g npm@11
"

echo "==> Serveis"
cp "$ROOT/deploy/systemd/app-aqua360-sign-backend.socket"   /etc/systemd/system/
cp "$ROOT/deploy/systemd/app-aqua360-sign-backend.service"  /etc/systemd/system/
cp "$ROOT/deploy/systemd/app-aqua360-sign-frontend.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable app-aqua360-sign-backend.socket app-aqua360-sign-backend.service app-aqua360-sign-frontend.service

cp "$ROOT/deploy/nginx/app-aqua360-sign-backend.conf"  /etc/nginx/sites-available/app-aqua360-sign-backend
cp "$ROOT/deploy/nginx/app-aqua360-sign-frontend.conf" /etc/nginx/sites-available/app-aqua360-sign-frontend

cat <<'MSG'

Instal·lació base feta. Ara, a mà:

  1. Donar d'alta la deploy key de dalt al repositori de GitHub.
  2. Crear el rol de postgres amb contrasenya, si l'avís ho demanava:
       sudo -u postgres psql -c "CREATE ROLE app_aqua360_sign LOGIN PASSWORD '...'"
  3. Copiar backend/.env.example a backend/.env i omplir-lo (SECRET_KEY,
     DATABASE_*, ALLOWED_HOSTS, SIGNING_*).
  4. Crear frontend/.env amb NUXT_PUBLIC_API_HOST=https://api-app-aqua360-sign.aqua360.cloud
  5. Donar d'alta els registres DNS a Cloudflare (proxied):
       app-aqua360-sign.aqua360.cloud  i  api-app-aqua360-sign.aqua360.cloud
  6. Activar els vhosts i recarregar nginx:
       ln -s /etc/nginx/sites-available/app-aqua360-sign-backend  /etc/nginx/sites-enabled/
       ln -s /etc/nginx/sites-available/app-aqua360-sign-frontend /etc/nginx/sites-enabled/
       nginx -t && systemctl reload nginx
  7. Executar el desplegament:
       /var/www/app-aqua360-sign/deploy/deploy.sh

MSG
