# avsis-docsign

Aplicació per **consultar, carregar i firmar documents**. Segueix les mateixes
convencions que `avsis-customers-backend` / `avsis-customers-frontend`: Django +
DRF al backend i Nuxt 3 (Vue 3) al frontal.

És un projecte **autònom**: té la seva base de dades i els seus usuaris, i no
depèn de la instal·lació d'avsis. L'única dependència externa és l'API de
signatura (Aqua360 Sign), la mateixa que fa servir avsis.

```
avsis-docsign/
├── backend/     Django 5 + DRF + PostgreSQL + Celery
└── frontend/    Nuxt 3 + Tailwind + Pinia + i18n
```

## Com funciona la signatura

El flux replica el d'avsis (`integrations/outbound/signing`):

1. **Càrrega** — es puja un PDF i es crea un `DocumentSign` en estat `PENDING`.
2. **Enviament** — `POST /documentmanager/document-sign/<id>/send-to-sign/` obre
   una sessió al proveïdor, que envia un OTP al signant per correu/SMS. L'estat
   passa a `SENDED`.
3. **Callback** — quan el signant firma, el proveïdor crida
   `POST /signing/callback/` amb l'esdeveniment `session.signed`. El webhook
   només notifica: el PDF firmat es descarrega a part del proveïdor i es desa com
   un `Document` nou (`document_file_signed`). L'estat passa a `SIGNED`.
4. **Caducitat** — l'esdeveniment `session.expired` deixa la sol·licitud a
   `EXPIRED` i es pot tornar a enviar.

L'original mai es sobreescriu: el PDF firmat és un document a part, de manera que
sempre es poden descarregar tots dos.

El callback s'autentica amb la capçalera `X-API-Key` contra `SIGN_CALLBACK_API_KEY`.
Si aquesta variable es deixa buida, el callback **no es valida** — només per a
desenvolupament local.

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
| `GET` | `/documentmanager/document-sign/` | Llista (filtres: `search`, `status`, `otp_email`) |
| `POST` | `/documentmanager/document-sign/` | Alta amb PDF (multipart) i `send_now` opcional |
| `POST` | `/documentmanager/document-sign/<id>/send-to-sign/` | Obre la sessió de signatura |
| `GET` | `/documentmanager/document-sign/<id>/view/` | PDF per visualitzar (firmat si n'hi ha) |
| `GET` | `/documentmanager/document-sign/<id>/download/` | Descàrrega |
| `GET` | `/documentmanager/document-sign/<id>/download-original/` | Descàrrega de l'original |
| `POST` | `/signing/callback/` | Webhook del proveïdor |

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
- `/signs` — llista de documents, filtres per estat i cerca, càrrega de PDF i
  enviament a firmar.
- `/signs/<id>` — visor del PDF, fitxa del signant i accions.

El visor mostra el PDF dins d'un `<iframe>` sobre un *blob*: l'endpoint demana el
token a la capçalera i un `<iframe src>` no en pot enviar cap.

## Docker

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Backend a `http://localhost:8000`, frontal a `http://localhost:3000`.
