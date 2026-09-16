# Desplegament

Sign360 es desplega **de forma nativa**, com `avsis-customers` al mateix
servidor: gunicorn sobre un socket Unix per al backend i el servidor de Nuxt per
al frontal, tots dos amb systemd, i nginx al davant. No es fa servir Docker (els
`Dockerfile` i el `docker-compose.yml` del repositori són per a desenvolupament
local).

A diferència d'avsis, el frontal **no** va amb PM2 sinó amb systemd: necessita un
Node propi (vegeu més avall) i PM2 no se'n surt, amb l'entorn de nvm, quan
s'arrenca fora d'una sessió de login.

## Estructura al servidor

El repositori es clona sencer a `/var/www/sign360`, de manera que la carpeta del
servidor té la mateixa forma que el repositori:

```
/var/www/sign360/
├── backend/          Django + gunicorn (entorn virtual a backend/env/)
│   └── .env          configuració real (no versionada)
├── frontend/         Nuxt (build a frontend/.output/)
│   └── .env
└── deploy/           aquests fitxers
```

Perquè actualitzar sigui un `git pull`, i no calgui mantenir dues còpies
sincronitzades.

| Peça | On |
|---|---|
| Backend | `sign360-backend.service` → `unix:/run/sign360_backend.sock` |
| Frontal | `sign360-frontend.service` → `127.0.0.1:3006` |
| Base de dades | PostgreSQL de la màquina, base `sign360` |
| Logs | `/var/log/sign360/`, `/var/log/nginx/sign360-*` |

## Dominis

| Servei | Domini |
|---|---|
| Frontal | `sign360.aqua360.cloud` |
| API | `api-sign360.aqua360.cloud` |

Són d'un sol nivell a propòsit: el certificat d'origen de Cloudflare de la
màquina cobreix `*.aqua360.cloud`, i un comodí TLS només val per a una etiqueta,
de manera que `x.y.aqua360.cloud` no hi quedaria cobert.

**`sign.aqua360.cloud` no es pot fer servir**: és el proveïdor de signatura amb
qui parla aquesta aplicació.

## Primera instal·lació

```bash
/var/www/sign360/deploy/setup.sh
```

Deixa el sistema a punt però **no** crea el DNS, ni omple les credencials, ni
activa els vhosts: són passos que ha de fer una persona, i l'script els recorda
en acabar.

## Actualitzacions

```bash
/var/www/sign360/deploy/deploy.sh          # branca main
/var/www/sign360/deploy/deploy.sh una-branca
```

Actualitza el codi, refà dependències, migra, reconstrueix el frontal i reinicia.
Abans de refer el frontal comprova que hi hagi **2 GB lliures**: `npm ci` esborra
`node_modules` abans de reinstal·lar-lo, i quedar-se sense disc a mitja
reinstal·lació deixa el frontal trencat.

## Accés temporal per IP (mentre no hi ha DNS)

`nginx/sign360-ip.conf` publica l'aplicació a **http://37.27.209.18** sense
domini ni HTTPS. Tot penja d'un sol origen: el frontal a l'arrel i l'API sota
`/api/`, de manera que el navegador no fa cap petició entre orígens i la
configuració de CORS no s'ha de tocar.

Perquè funcioni calen dues coses més:

- La IP afegida a `ALLOWED_HOSTS` i `CSRF_TRUSTED_ORIGINS` del `backend/.env`.
- Un override de systemd a
  `/etc/systemd/system/sign360-frontend.service.d/override.conf` amb
  `NUXT_PUBLIC_API_HOST=http://37.27.209.18/api`. L'URL de l'API es llegeix en
  temps d'execució, així que **no cal refer el build** per canviar-la.

**Això és HTTP pla: les contrasenyes i els tokens viatgen sense xifrar.** És un
arranjament provisional per poder ensenyar l'aplicació abans de tenir DNS, i
s'ha de retirar quan entrin els vhosts amb domini:

```bash
rm /etc/nginx/sites-enabled/sign360-ip
rm -r /etc/systemd/system/sign360-frontend.service.d
systemctl daemon-reload && systemctl restart sign360-frontend.service
systemctl reload nginx
```

I treure la IP de les dues variables del `backend/.env`.

## Versió de Node

El servidor té **Node 20** al sistema, que és el que fa servir avsis, i no s'hi
toca. El frontal de Sign360 necessita **Node 22**: `@nuxtjs/i18n` v9 (obligatori
amb Nuxt 3.21, perquè la v8 no és compatible amb unhead v2) arrossega paquets que
demanen `node >= 22`.

La solució és un Node propi de l'usuari `sign360`, instal·lat amb nvm a
`/home/sign360/.nvm`. `setup.sh` l'instal·la i `deploy.sh` el carrega abans de
construir. La ruta al binari surt literalment a
`sign360-frontend.service`: **si es canvia de versió de Node, cal actualitzar-la
allà**.

També cal **npm 11**: el `package-lock.json` està generat amb npm 11, i npm 10
el considera desincronitzat (`npm ci` falla amb «Missing: unplugin@... from lock
file»).

## Espai en disc

És la limitació real d'aquesta màquina. Un desplegament de Sign360 ocupa uns
**800 MB – 1 GB** (entorn virtual de Python més `node_modules` i el build).

Convé comprovar-ho abans de cada desplegament:

```bash
df -h /
```

`deploy.sh` s'atura sol si queden menys de 2 GB lliures.

El que més ocupa en aquesta màquina són les releases antigues d'avsis (el seu
desplegament en guarda 6 i només n'usa una) i el cache de build de Docker.

## Celery

L'aplicació té Celery configurat però **no defineix cap tasca**, així que al
servidor no cal ni worker ni beat. Si algun dia se n'hi afegeix (recordatoris de
signatures pendents, per exemple), caldrà una unitat de systemd com les de
`customers`, apuntant al Redis que ja corre a la màquina.

## Signatura

Perquè el circuit funcioni de punta a punta calen, al `backend/.env`:

- `SIGNING_BASE_URL` i `SIGNING_API_KEY` — credencials de sign.aqua360.
- `SIGNING_CALLBACK_URL=https://api-sign360.aqua360.cloud/signing/callback/`
- `SIGN_CALLBACK_API_KEY` — clau que el proveïdor ha d'enviar al webhook.

A més, l'equip de Sign ha de donar d'alta la nostra URL de callback. Sense això
l'aplicació es desplega i funciona per pujar i consultar documents, però enviar a
firmar retorna un error explícit.
