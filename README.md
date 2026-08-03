# I_SK_MessSender - Setup and Autostart Guide

## Overview
Internal SmartKasa notification service. Accepts localhost HTTP requests to send one-shot phone messages via MyChatbot webhook. Uses PostgreSQL for idempotency (one send per phone + message_type). API binds to `127.0.0.1` only.

## Files
- Entry point: `run.py`
- HTTP API: `app/main.py`
- Config (env): `app/config.py`, `.env`
- DB helpers: `app/db.py`
- Phone normalize: `app/phone.py`
- Auth (`X-Api-Key`): `app/auth.py`
- Message templates: `app/templates.py`
- Webhook send: `app/sender.py`
- Background worker: `app/worker.py`
- Schema: `sql/schema.sql`
- systemd unit example: `deploy/notification-service.service`

---

## Prerequisites
- Python 3.11+
- PostgreSQL (DB + user created)
- `.env` filled from `.env.example`

---

## Linux/Unix Autostart Setup

### 1. Create systemd service file

```bash
sudo nano /etc/systemd/system/I_SK_MessSender.service
```

### 2. Service file content

**Note**: Update paths with your actual project directory.

```ini
[Unit]
Description=SmartKasa Notification Service (I_SK_MessSender)
After=network.target postgresql.service
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/path/to/I_SK_MessSender
EnvironmentFile=/path/to/I_SK_MessSender/.env
Environment=PATH=/path/to/I_SK_MessSender/venv/bin
Environment=PYTHONPATH=/path/to/I_SK_MessSender
ExecStart=/path/to/I_SK_MessSender/venv/bin/python /path/to/I_SK_MessSender/run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=I_SK_MessSender

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/path/to/I_SK_MessSender

[Install]
WantedBy=multi-user.target
```

Do not open the service port in firewall. Keep `HOST=127.0.0.1` in `.env`.

### 3. Initialize and enable service

```bash
sudo systemctl daemon-reload
sudo systemctl enable I_SK_MessSender
sudo systemctl start I_SK_MessSender
sudo systemctl status I_SK_MessSender
```

---

## Service Management Commands

```bash
sudo systemctl start I_SK_MessSender
sudo systemctl stop I_SK_MessSender
sudo systemctl restart I_SK_MessSender
sudo systemctl status I_SK_MessSender
```

### View logs

```bash
sudo journalctl -u I_SK_MessSender -f
sudo journalctl -u I_SK_MessSender -n 50
sudo journalctl -u I_SK_MessSender
```

---

## Verification

```bash
curl http://127.0.0.1:8080/health
# {"status":"ok"}

systemctl is-active I_SK_MessSender
ps aux | grep "run.py"
```

---

## Manual Start (Development)

```bash
cd /path/to/I_SK_MessSender
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # edit values
python run.py
```

Schema (`sql/schema.sql`) is applied automatically on startup.

---

## Dependencies

```bash
pip install -r requirements.txt
```

Main packages:
- `fastapi` / `uvicorn` — HTTP API
- `asyncpg` — PostgreSQL
- `httpx` — webhook HTTP client
- `python-dotenv` — `.env` loading
- `pydantic` — request validation

---

## Configuration

Copy `.env.example` → `.env`:

```env
HOST=127.0.0.1
PORT=8080
API_KEY=your_secret_api_key
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/notifications
LOG_LEVEL=INFO
WORKER_POLL_SECONDS=2
WORKER_MAX_RETRIES=3
PROVIDER_WEBHOOK_URL=https://api.mychatbot.app/webhook/triggers/<token>/<id>
```

Message texts live in `app/templates.py` (not env). No template for `message_type` → message is not sent.

---

## API (for callers on the same host)

Base: `http://127.0.0.1:8080`  
Auth: header `X-Api-Key: <API_KEY>` (except `/health`)

### Send notification

`POST /v1/notifications`

```json
{
  "phone": "+380501234567",
  "message_type": "welcome_new_contractor",
  "payload": {},
  "idempotency_key": "optional-id"
}
```

| Code | Meaning |
|------|---------|
| `202` | accepted (`pending`) |
| `200` | duplicate — already exists, not resent |
| `400` | invalid phone / message_type |
| `401` | bad/missing API key |

Idempotency: unique `(phone, message_type)`; if `idempotency_key` set — unique by that key too.

### Status

`GET /v1/notifications/{id}` → `pending` | `sent` | `failed` | `skipped`

### Health

`GET /health` → `{"status":"ok"}` (no auth)

### Example

```bash
curl -s -X POST http://127.0.0.1:8080/v1/notifications \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: your_secret_api_key" \
  -d '{"phone":"0501234567","message_type":"welcome_new_contractor"}'
```

Service is **not** reachable via public server IP (`HOST=127.0.0.1`). Call only from the same machine: `127.0.0.1`.

---

## How It Works

1. Caller POSTs notification with `X-Api-Key`
2. Service normalizes phone, inserts `pending` row (or returns duplicate)
3. Responds `202` / `200` without waiting for provider
4. In-process worker takes `pending`, resolves text from `app/templates.py`
5. POSTs `{ "context": "<template>", "phone": "+380..." }` to `PROVIDER_WEBHOOK_URL`
6. Marks row `sent` or `failed` (retries with backoff)
