# Desplegament

app.aqua360-sign es desplega **de forma nativa**, com `avsis-customers` al mateix
servidor: gunicorn sobre un socket Unix per al backend i el servidor de Nuxt per
al frontal, tots dos amb systemd, i nginx al davant. No es fa servir Docker (els
`Dockerfile` i el `docker-compose.yml` del repositori són per a desenvolupament
local).

A diferència d'avsis, el frontal **no** va amb PM2 sinó amb systemd: necessita un
Node propi (vegeu més avall) i PM2 no se'n surt, amb l'entorn de nvm, quan
s'arrenca fora d'una sessió de login.

## Estructura al servidor

El repositori es clona sencer a `/var/www/app-aqua360-sign`, de manera que la carpeta del
servidor té la mateixa forma que el repositori:

```
/var/www/app-aqua360-sign/
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
| Backend | `app-aqua360-sign-backend.service` → `unix:/run/app_aqua360_sign_backend.sock` |
| Frontal | `app-aqua360-sign-frontend.service` → `127.0.0.1:3006` |
| Base de dades | PostgreSQL de la màquina, base `app_aqua360_sign` |
| Logs | `/var/log/app-aqua360-sign/`, `/var/log/nginx/app-aqua360-sign-*` |

## Dominis

| Servei | Domini |
|---|---|
| Frontal | `app-aqua360-sign.aqua360.cloud` |
| API | `api-app-aqua360-sign.aqua360.cloud` |

Són d'un sol nivell a propòsit: el certificat d'origen de Cloudflare de la
màquina cobreix `*.aqua360.cloud`, i un comodí TLS només val per a una etiqueta,
de manera que `x.y.aqua360.cloud` no hi quedaria cobert.

**`sign.aqua360.cloud` no es pot fer servir**: és el proveïdor de signatura amb
qui parla aquesta aplicació.

Els dominis antics eren `sign360.aqua360.cloud` i `api-sign360.aqua360.cloud`:
cal donar d'alta els nous a Cloudflare (proxied) i retirar-los quan el canvi
estigui fet. El certificat no s'ha de tocar, és el comodí de la màquina.

## Primera instal·lació

```bash
/var/www/app-aqua360-sign/deploy/setup.sh
```

Deixa el sistema a punt però **no** crea el DNS, ni omple les credencials, ni
activa els vhosts: són passos que ha de fer una persona, i l'script els recorda
en acabar.

## Actualitzacions

```bash
/var/www/app-aqua360-sign/deploy/deploy.sh          # branca main
/var/www/app-aqua360-sign/deploy/deploy.sh una-branca
```

Actualitza el codi, refà dependències, migra, reconstrueix el frontal i reinicia.
Abans de refer el frontal comprova que hi hagi **2 GB lliures**: `npm ci` esborra
`node_modules` abans de reinstal·lar-lo, i quedar-se sense disc a mitja
reinstal·lació deixa el frontal trencat.

## Accés temporal per IP (mentre no hi ha DNS)

`nginx/app-aqua360-sign-ip.conf` publica l'aplicació a **http://37.27.209.18** sense
domini ni HTTPS. Tot penja d'un sol origen: el frontal a l'arrel i l'API sota
`/api/`, de manera que el navegador no fa cap petició entre orígens i la
configuració de CORS no s'ha de tocar.

Perquè funcioni calen dues coses més:

- La IP afegida a `ALLOWED_HOSTS` i `CSRF_TRUSTED_ORIGINS` del `backend/.env`.
- Un override de systemd a
  `/etc/systemd/system/app-aqua360-sign-frontend.service.d/override.conf` amb
  `NUXT_PUBLIC_API_HOST=http://37.27.209.18/api`. L'URL de l'API es llegeix en
  temps d'execució, així que **no cal refer el build** per canviar-la.

**Això és HTTP pla: les contrasenyes i els tokens viatgen sense xifrar.** És un
arranjament provisional per poder ensenyar l'aplicació abans de tenir DNS, i
s'ha de retirar quan entrin els vhosts amb domini:

```bash
rm /etc/nginx/sites-enabled/app-aqua360-sign-ip
rm -r /etc/systemd/system/app-aqua360-sign-frontend.service.d
systemctl daemon-reload && systemctl restart app-aqua360-sign-frontend.service
systemctl reload nginx
```

I treure la IP de les dues variables del `backend/.env`.

## Versió de Node

El servidor té **Node 20** al sistema, que és el que fa servir avsis, i no s'hi
toca. El frontal d'app.aqua360-sign necessita **Node 22**: Nuxt 4 declara
`engines.node: ^22.19.0 || ^24.11.0 || >=26`, de manera que amb Node 20 ni
s'instal·la.

La solució és un Node propi de l'usuari `app-aqua360-sign`, instal·lat amb nvm a
`/home/app-aqua360-sign/.nvm`. `setup.sh` l'instal·la i `deploy.sh` el carrega abans de
construir. La ruta al binari surt literalment a
`app-aqua360-sign-frontend.service`: **si es canvia de versió de Node, cal actualitzar-la
allà**.

L'`.nvmrc` del frontal fixa la major (`22`), per si es vol fer `nvm use` a mà.

També cal **npm 11**: el `package-lock.json` està generat amb npm 11, i npm 10
el considera desincronitzat (`npm ci` falla amb «Missing: unplugin@... from lock
file»).

## Canvi de nom: de sign360 a app.aqua360-sign

La instal·lació d'staging es va fer amb el nom antic. Per posar-la al dia, un cop
desplegada aquesta branca, cal fer-ho **a mà** una sola vegada, com a root:

```bash
systemctl stop sign360-frontend.service sign360-backend.service sign360-backend.socket
systemctl disable sign360-frontend.service sign360-backend.service sign360-backend.socket
rm /etc/systemd/system/sign360-*.service /etc/systemd/system/sign360-backend.socket
rm -f /etc/nginx/sites-enabled/sign360-* /etc/nginx/sites-available/sign360-*

# Usuari, directoris i base de dades
usermod  -l app-aqua360-sign -d /home/app-aqua360-sign -m sign360
groupmod -n app-aqua360-sign sign360
mv /var/www/sign360 /var/www/app-aqua360-sign
mv /var/log/sign360 /var/log/app-aqua360-sign
sudo -u postgres psql -c 'ALTER DATABASE sign360 RENAME TO app_aqua360_sign'
sudo -u postgres psql -c 'ALTER ROLE sign360 RENAME TO app_aqua360_sign'
```

El `ALTER ROLE` buida la contrasenya si estava xifrada amb `scram` sobre el nom
antic: cal tornar-la a posar (`ALTER ROLE app_aqua360_sign PASSWORD '...'`) i
deixar `DATABASE_NAME` / `DATABASE_USER` del `backend/.env` amb els noms nous.
La ruta del Node a `app-aqua360-sign-frontend.service` també canvia de `/home`,
i el `.nvm` viatja amb l'usuari gràcies al `-m` de `usermod`.

A més, fora del servidor:

- Reanomenar el repositori a GitHub (`AQUA360/sign360` → `AQUA360/app-aqua360-sign`).
  GitHub redirigeix l'URL antiga, però convé actualitzar el `remote` del clon del
  servidor: `sudo -u app-aqua360-sign git -C /var/www/app-aqua360-sign remote set-url origin git@github.com:AQUA360/app-aqua360-sign.git`
- Donar d'alta els DNS nous i actualitzar `NUXT_PUBLIC_API_HOST` del
  `frontend/.env` amb `https://api-app-aqua360-sign.aqua360.cloud`, i
  `SIGNING_CALLBACK_URL` del `backend/.env` amb el mateix domini.
- Demanar a l'equip de Sign que doni d'alta la nova URL de callback.

Després, `setup.sh` torna a instal·lar les unitats i els vhosts amb els noms nous
i `deploy.sh` desplega com sempre. Les sessions de signatura obertes abans del
canvi segueixen funcionant: el webhook encara accepta el prefix
`sign360-` de l'`external_reference` (vegeu `LEGACY_REFERENCE_PREFIXES`).

## Espai en disc

És la limitació real d'aquesta màquina. Un desplegament d'app.aqua360-sign ocupa uns
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
- `SIGNING_CALLBACK_URL=https://api-app-aqua360-sign.aqua360.cloud/signing/callback/`
- `SIGN_CALLBACK_API_KEY` — clau que el proveïdor ha d'enviar al webhook.

A més, l'equip de Sign ha de donar d'alta la nostra URL de callback. Sense això
l'aplicació es desplega i funciona per pujar i consultar documents, però enviar a
firmar retorna un error explícit.
