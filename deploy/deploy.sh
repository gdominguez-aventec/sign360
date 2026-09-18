#!/bin/bash
#
# Desplegament d'app.aqua360-sign. S'executa al servidor, com a root:
#
#     /var/www/app-aqua360-sign/deploy/deploy.sh
#
# És idempotent: es pot tornar a executar tantes vegades com calgui. Actualitza
# el codi, refà dependències, migra i reinicia. La primera instal·lació la fa
# `deploy/setup.sh`, no aquest script.
set -euo pipefail

ROOT=/var/www/app-aqua360-sign
USER_APP=app-aqua360-sign
BRANCH="${1:-main}"

echo "==> Codi (branca $BRANCH)"
sudo -u "$USER_APP" git -C "$ROOT" fetch --prune origin
sudo -u "$USER_APP" git -C "$ROOT" reset --hard "origin/$BRANCH"

echo "==> Backend: dependències"
sudo -u "$USER_APP" "$ROOT/backend/env/bin/pip" install -q -r "$ROOT/backend/requirements.txt"

echo "==> Backend: migracions i estàtics"
sudo -u "$USER_APP" "$ROOT/backend/env/bin/python" "$ROOT/backend/manage.py" migrate --noinput
sudo -u "$USER_APP" "$ROOT/backend/env/bin/python" "$ROOT/backend/manage.py" collectstatic --noinput

echo "==> Frontend: dependències i build"
# `npm ci` esborra node_modules i el refà: en un servidor amb poc disc, val més
# assegurar-se que hi ha prou espai abans de començar.
AVAILABLE_MB=$(df -Pm / | awk 'NR==2 {print $4}')
if [ "$AVAILABLE_MB" -lt 2000 ]; then
    echo "ERROR: només queden ${AVAILABLE_MB} MB lliures; calen 2000 MB per refer el frontal." >&2
    exit 1
fi
# El Node del sistema és el 20 (el que fa servir avsis) i el frontal en demana
# 22, així que es fa servir el de l'usuari, instal·lat amb nvm.
sudo -u "$USER_APP" -H bash -lc '
    set -e
    . "$HOME/.nvm/nvm.sh"
    cd /var/www/app-aqua360-sign/frontend
    npm ci --no-audit --no-fund
    npm run build
'

echo "==> Reinici de serveis"
systemctl restart app-aqua360-sign-backend.service
systemctl restart app-aqua360-sign-frontend.service

echo "==> Comprovació"
sleep 4
curl -sf --unix-socket /run/app_aqua360_sign_backend.sock http://localhost/ >/dev/null \
    && echo "backend OK" || { echo "backend NO respon" >&2; exit 1; }
curl -sf -o /dev/null http://127.0.0.1:3006/ \
    && echo "frontend OK" || { echo "frontend NO respon" >&2; exit 1; }

echo "Desplegament acabat."
