# Admin API

Окремий Django-сервіс (порт `8081`) для історії розсилок і ручної відправки. Ділить Postgres з MessSender.

## Запуск

**Прод / разом з MessSender** — один процес:

```bash
pip install -r requirements.txt
py run.py
```

Піднімає MessSender (`HOST`/`PORT`, зазвичай `:8080`) і Admin (`ADMIN_HOST`/`ADMIN_PORT`, зазвичай `:8081`).

**Лише адмінка** (локально):

```bash
pip install -r requirements-admin.txt
py run_admin.py
```

Веб-форма: `http://127.0.0.1:8081/` (`web_admin/index.html`).

Міграції `admin_api` застосовуються при старті admin (з `run.py` або `run_admin.py`).

## Користувачі та токени

Два типи доступу:

| Тип | Для чого | Логін |
|-----|----------|--------|
| **User** (username + password) | люди / веб-адмінка | `username` + `password` |
| **Client** (name + token) | розробка, Postman | `name` + `token` |

Паролі й токени зберігаються лише як хеш. При створенні raw значення друкується **один раз**.

### Користувачі (паролі)

```bash
# створити / оновити пароль (якщо --password без значення — згенерується)
py manage_admin.py create_admin_user --username operator --password "SecretPass1"

# список
py manage_admin.py list_admin_users

# видалити
py manage_admin.py delete_admin_user --username operator
```

### Клієнти (токени, для dev)

```bash
# створити / оновити токен
py manage_admin.py create_admin_client --name postman-dev --token "skadmin_dev_token_001"

# або без --token — згенерує сам
py manage_admin.py create_admin_client --name postman-dev

# список
py manage_admin.py list_admin_clients

# видалити
py manage_admin.py delete_admin_client --name postman-dev
```

## Env

| Змінна | Опис |
|--------|------|
| `DATABASE_URL` | той самий Postgres, що MessSender |
| `MYCHATBOT_MAILING_WEBHOOK_URL` | Trigger Outreach webhook |
| `ADMIN_HOST` / `ADMIN_PORT` | default `127.0.0.1:8081` |
| `ADMIN_SECRET_KEY` | Django secret |
| `ADMIN_JWT_SECRET` | підпис JWT (fallback → `ADMIN_SECRET_KEY`) |
| `ADMIN_JWT_TTL_SECONDS` | default `86400` |
| `GOOGLE_CLIENT_ID` | OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth Client Secret |
| `GOOGLE_REFRESH_TOKEN` | з `scripts/get_google_refresh_token.py` |
| `GOOGLE_DRIVE_FOLDER_ID` | id папки Drive для фото |

### Google Drive (фото)

```bash
pip install -r requirements.txt
# client_secret.json у корені проєкту (gitignore)
py scripts/get_google_refresh_token.py
```

Додай у `.env` надруковані `GOOGLE_*` і `GOOGLE_DRIVE_FOLDER_ID`.

## Auth

`POST /api/v1/auth/token`

Користувач (веб):

```json
{ "username": "operator", "password": "SecretPass1" }
```

Клієнт (dev):

```json
{ "name": "postman-dev", "token": "skadmin_dev_token_001" }
```

Відповідь: `{ "access_token": "...", "token_type": "Bearer", "kind": "user"|"client" }`

Далі: `Authorization: Bearer <access_token>`

## Endpoints

### Список

`GET /api/v1/notifications`

Query (усі опційні):

| Параметр | Приклад | Опис |
|----------|---------|------|
| `status` | `sent`, `failed`, `pending`, `skipped` | також `success` → sent, `unsuccessful` → failed |
| `phone` | `+380XXXXXXXXX` | нормалізація UA |
| `date` | `2026-10-22` | календарний день (`Europe/Kyiv`) |
| `hour` | `15` | година 0–23, тільки разом з `date` |
| `date_from` / `date_to` | `2026-10-01` або ISO datetime | діапазон (не з `date`) |
| `page` | `1` | пагінація, page size 20 |

### За телефоном

`GET /api/v1/notifications/by-phone/{phone}`

Ті самі фільтри (`status`, `date`, `hour`, `date_from`/`date_to`). У path `+` кодувати як `%2B`  
(напр. `/by-phone/%2B380XXXXXXXXX`).

### Завантаження фото (Drive)

`POST /api/v1/media/upload` — `multipart/form-data`, поле `file` (jpeg/png/webp/gif).

Відповідь: `{ file_id, url }` де `url` = `https://lh3.googleusercontent.com/d/<id>`.

### Ручна відправка

`POST /api/v1/notifications/send`

```json
{ "phone": "+380XXXXXXXXX", "text": "текст", "image_url": "https://lh3.googleusercontent.com/d/..." }
```

`image_url` опційний; дописується в кінець `context` для MyChatbot/Viber.

### Групова розсилка (CSV / XLSX)

`POST /api/v1/notifications/parse-phones` — лише `file` → `{ total, invalid_count }` (прев’ю без відправки).

`POST /api/v1/notifications/send-bulk` — `multipart/form-data`:

| Поле | Опис |
|------|------|
| `text` | текст повідомлення |
| `file` | `.csv` / `.xlsx` з телефонами (до 1000) |
| `image_url` | опційно, той самий URL на всі номери |

Відповідь `202`: `{ campaign_id, total, invalid_count, invalid }`.  
Відправка послідовна у фоні. У історії групається по `payload.campaign_id`  
(`GET /notifications?campaign_id=...` — усі номери сесії).

Статуси запису: `pending` | `sent` | `failed` | `skipped`.
