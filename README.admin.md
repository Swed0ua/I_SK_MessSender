# Admin API

Окремий Django-сервіс (порт `8081`) для історії розсилок і ручної відправки. Ділить Postgres з MessSender.

## Запуск

```bash
pip install -r requirements-admin.txt
py run_admin.py
```

Створити клієнта:

```bash
py manage_admin.py create_admin_client --name web-admin --token <secret>
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

## Auth

`POST /api/v1/auth/token`

```json
{ "name": "web-admin", "token": "<secret>" }
```

Відповідь: `{ "access_token": "...", "token_type": "Bearer" }`

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

### Ручна відправка

`POST /api/v1/notifications/send`

```json
{ "phone": "+380XXXXXXXXX", "text": "текст повідомлення" }
```

Статуси запису: `pending` | `sent` | `failed` | `skipped`.
