# Desplegament

Sign360 es desplega **de forma nativa**, com `avsis-customers` al mateix
servidor: gunicorn sobre un socket Unix amb systemd per al backend, PM2 per al
frontal Nuxt i nginx al davant. No es fa servir Docker (els `Dockerfile` i el
`docker-compose.yml` del repositori són per a desenvolupament local).

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
| Frontal | PM2 `Sign360 Frontend` → `127.0.0.1:3006` |
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

## Espai en disc

És la limitació real d'aquesta màquina. Un desplegament de Sign360 ocupa uns
**800 MB – 1 GB** (entorn virtual de Python més `node_modules` i el build).

Convé comprovar-ho abans de cada desplegament:

```bash
df -h /
```

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
