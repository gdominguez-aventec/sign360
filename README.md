# Sign360

**Sign360 is a standalone web application for reviewing, uploading and
electronically signing documents.** Users upload one or more PDFs, list the
people who must sign them, and the documents are sent out for signature through
an external signing provider, which delivers a one-time password to each signer
by email or SMS. Signing is sequential: every signer receives the PDF as the
previous one left it, so a single file ends up carrying the whole chain of
signatures.

Nothing is ever overwritten. The file we received is stored untouched, and each
signature is saved as a new version linked to the one before it, so the original,
every intermediate step and the fully signed result all remain available for
download. Sign360 tracks each request and each signer through its lifecycle —
pending, sent, signed, expired or failed — and logs every exchange with the
provider, giving a full audit trail of who was asked to sign what, and when.

The application is built with Django and Django REST Framework on the back end
and Nuxt 3 (Vue 3) on the front end, following the same conventions as the
Aqua360 Customers platform. It runs on its own database with its own users and
has no runtime dependency on any other Aventec system.

---

Segueix les mateixes convencions que `avsis-customers-backend` /
`avsis-customers-frontend`: Django + DRF al backend i Nuxt 3 (Vue 3) al frontal.

És un projecte **autònom**: té la seva base de dades i els seus usuaris, i no
depèn de la instal·lació d'avsis. L'única dependència externa és l'API de
signatura (Aqua360 Sign), la mateixa que fa servir avsis.

```
sign360/
├── backend/     Django 5 + DRF + PostgreSQL + Celery
└── frontend/    Nuxt 3 + Tailwind + Pinia + i18n
```

## Com funciona la signatura

Una **sol·licitud** (`DocumentSign`) agrupa N documents i M signants. El
proveïdor (sign.aqua360) només accepta **un destinatari per sessió**, així que
cada signant té la seva pròpia sessió i la signatura és **encadenada**:

1. **Càrrega** — es pugen un o més PDF. Cada fitxer es desa tal com ens arriba i
   es crea un `DocumentSignDocument` amb `original_document` = `current_document`.
2. **Enviament** — `POST /documentmanager/document-sign/<id>/send-to-sign/` obre
   la sessió del **primer signant** amb tots els documents. El proveïdor li envia
   l'OTP per correu/SMS.
3. **Callback** — quan firma, el webhook `session.signed` només notifica: el PDF
   firmat es descarrega a part i es desa com una **versió nova** (`version + 1`,
   `parent_document` = versió anterior). `current_document` passa a apuntar-hi.
4. **Torn següent** — tot seguit s'obre automàticament la sessió del signant
   següent, amb els documents en la seva versió actual, de manera que firma sobre
   el que ha firmat l'anterior.
5. **Tancament** — quan han firmat tots, la sol·licitud passa a `SIGNED`.

L'original no es modifica ni es reemplaça mai: es pot recuperar byte a byte, i
també qualsevol pas intermedi de la cadena.

### Models

| Model | Paper |
|---|---|
| `DocumentSign` | La sol·licitud: títol, estat global, qui l'ha creada |
| `DocumentSignDocument` | Un document dins la sol·licitud: `original_document` (intocable) i `current_document` (última versió) |
| `DocumentSignSigner` | Un signant, amb el seu `order` a la cadena, estat propi i token |
| `DocumentSignSignature` | Quin signant ha produït quina versió de quin document |
| `Document` | El fitxer físic. `version` + `parent_document` formen la cadena de versions |
| `SigningSession` | La sessió oberta al proveïdor per a un signant, amb `document_map` |

`SigningSession.document_map` relaciona els ids que el proveïdor assigna als
documents amb els nostres. És necessari perquè, amb més d'un document per sessió,
el webhook ha de saber a quin correspon cada PDF firmat. Es construeix per nom de
fitxer i, si el proveïdor no el retorna, per l'ordre en què els hem enviat.

### Signatura per part de més d'una persona (desactivada)

El model i el flux encadenat estan implementats i provats, però **de moment estan
desactivats**: `MULTI_SIGNER_ENABLED=False` limita cada sol·licitud a un signant.

L'interruptor viu al backend, que és qui el valida, i el frontal el llegeix de
`GET /documentmanager/config/` en lloc de tenir la seva pròpia variable, perquè
no hi hagi dues fonts de veritat que puguin divergir. Amb l'interruptor apagat
s'amaguen el botó d'afegir signants, la seqüència de torns i les columnes de
progrés; el backend rebutja qualsevol alta amb més d'un signant encara que se li
enviï directament per l'API.

Per reactivar-ho només cal posar `MULTI_SIGNER_ENABLED=True` al `.env` i
reiniciar. No cal tocar codi ni migrar res: el model ja guarda l'ordre dels
signants i la cadena de versions.

### Si un torn caduca o falla

L'estat viu a dos nivells: el del signant i el de la sol·licitud. Un torn caducat
o erroni es pot reenviar només a aquell signant
(`{"signer": <id>, "force": true}`) sense refer la cadena ni tornar a pujar res.
Si en rebre una signatura falla l'obertura de la sessió següent, la signatura
rebuda **no es desfà**: queda desada i la sol·licitud en estat d'error, a punt
per reintentar.

## Backend

```bash
cd backend
python -m venv env && source env/bin/activate
pip install -r requirements.txt
cp .env.example .env        # omple credencials i base de dades
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Endpoints principals

| Mètode | Ruta | Descripció |
|---|---|---|
| `POST` | `/auth/login/` | Login; retorna el token DRF |
| `GET` | `/auth/me/` | Usuari actual |
| `GET` | `/documentmanager/config/` | Configuració per al frontal (multisignant, mida màxima, proveïdor configurat) |
| `GET` | `/documentmanager/document-sign/` | Llista (filtres: `search`, `status`, `signer_email`) |
| `POST` | `/documentmanager/document-sign/` | Alta: N fitxers a `files` i els signants com a JSON a `signers` |
| `POST` | `/documentmanager/document-sign/<id>/send-to-sign/` | Envia al signant de torn (o a un de concret amb `signer`) |
| `GET` | `/documentmanager/document-sign/<id>/documents/` | Documents de la sol·licitud |
| `GET` | `/documentmanager/sign-document/<id>/view/` | Versió actual, per visualitzar |
| `GET` | `/documentmanager/sign-document/<id>/download/` | Versió actual |
| `GET` | `/documentmanager/sign-document/<id>/download-original/` | Original tal com el vam rebre |
| `GET` | `/documentmanager/document/<id>/download/` | Qualsevol versió intermèdia de la cadena |
| `POST` | `/signing/callback/` | Webhook del proveïdor |

L'alta va com a multipart. `signers` és una cadena JSON perquè un multipart no
admet estructures niuades:

```
files=@contracte.pdf  files=@annex.pdf
title=Conveni
signers=[{"name":"Anna Garcia","email":"anna@example.com","phone":"+34600000000"},
         {"name":"Bernat Roca","email":"bernat@example.com"}]
send_now=true
```

### Emmagatzematge

Els fitxers es desen al disc (`DOCUMENT_STORAGE_PATH`). El model `Document` manté
el camp `service` d'avsis amb les altres opcions (azure, aws, ftp) reservades,
però només `hdd` està implementat: `main_utils` llança `UnsupportedServiceError`
per a la resta, de manera que afegir-ne un no obliga a migrar el model.

### Segellat amb certificat (opcional)

Si es configura `PFX_PATH` / `PFX_PASS`, `documentmanager/utils/pdf_utils.seal_pdf`
pot segellar un PDF amb pyHanko (PAdES). Si el segellat falla, retorna el PDF
original: és una garantia addicional i no pot fer caure el flux de signatura.

## Frontend

```bash
cd frontend
npm install
cp .env.example .env        # NUXT_PUBLIC_API_HOST cap al backend
npm run dev
```

Pàgines:

- `/auth/login` — login contra `/auth/login/`, el token es desa a `localStorage`.
- `/signs` — llista de sol·licituds amb filtres per estat i cerca, progrés de
  signatures (`2 / 3`) i de qui és el torn. La càrrega admet diversos PDF i
  diversos signants, amb l'ordre de la cadena.
- `/signs/<id>` — visor a amplada completa amb una pestanya per document i un
  selector de versió (original, cada pas de la cadena, versió actual), la
  seqüència de signants amb el seu estat i les descàrregues.

La interfície ocupa el 100% de l'amplada de la pantalla.

El visor mostra el PDF dins d'un `<iframe>` sobre un *blob*: l'endpoint demana el
token a la capçalera i un `<iframe src>` no en pot enviar cap.

## Docker

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Backend a `http://localhost:8000`, frontal a `http://localhost:3000`.
