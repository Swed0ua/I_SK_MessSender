CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS notifications (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone             VARCHAR(32)  NOT NULL,
    message_type      VARCHAR(128) NOT NULL,
    idempotency_key   VARCHAR(255) NULL,
    payload           JSONB        NOT NULL DEFAULT '{}'::jsonb,
    status            VARCHAR(16)  NOT NULL DEFAULT 'pending',
    provider_response JSONB        NULL,
    error             TEXT         NULL,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    sent_at           TIMESTAMPTZ  NULL,
    CONSTRAINT notifications_status_chk
        CHECK (status IN ('pending', 'sent', 'failed', 'skipped'))
);

-- Welcome only: one send per phone. Admin/Bitrix may send many times to same phone.
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_phone_type_uq;
DROP INDEX IF EXISTS notifications_phone_type_uq;

CREATE UNIQUE INDEX IF NOT EXISTS notifications_phone_type_welcome_uq
    ON notifications (phone, message_type)
    WHERE message_type = 'welcome_new_contractor';

CREATE UNIQUE INDEX IF NOT EXISTS notifications_idempotency_key_uq
    ON notifications (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS notifications_status_idx
    ON notifications (status)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS notifications_phone_idx
    ON notifications (phone);
