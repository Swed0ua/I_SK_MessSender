from __future__ import annotations

from typing import Any

from app.bitrix_config import MESSAGE_TYPE_KASA_VIBER

# message_type -> text. Placeholders: {pdf_url}. No template = do not send.
MESSAGE_TEMPLATES: dict[str, str] = {
    "welcome_new_contractor": (
        "📢 Відкриваєте бізнес або плануєте оновити касове обладнання?\n"
        "\n"
        "Не знаєте, яке рішення обрати саме для вашого бізнесу? Ми допоможемо.\n"
        "\n"
        "💡 Безкоштовно підберемо касове рішення, яке відповідатиме вашим потребам та бюджету.\n"
        "\n"
        "Допоможемо обрати:\n"
        "✅ касове обладнання\n"
        "✅ POS-термінал\n"
        "✅ ПРРО\n"
        "✅ програмне забезпечення для обліку та продажів\n"
        "✅ оптимальний варіант без переплати за зайві функції\n"
        "\n"
        "Ми врахуємо специфіку саме вашого бізнесу та запропонуємо рішення, "
        "яке буде зручним у роботі й відповідатиме вимогам законодавства.\n"
        "\n"
        "💬 Напишіть нам у відповідь на це повідомлення та коротко розкажіть "
        "про свій бізнес. Ми підготуємо персональну пропозицію саме для вас."
    ),
    MESSAGE_TYPE_KASA_VIBER: (
        "Добрий день!\n"
        "\n"
        "Дякуємо, що обрали SmartKasa 💙\n"
        "Ваше замовлення майже готове — лишилось лише підтвердити оплату.\n"
        "\n"
        "📄 Рахунок для оплати:\n"
        "{pdf_url}\n"
        "\n"
        "Будь ласка, після оплати надішліть:\n"
        "• назву ФОП / ТОВ\n"
        "• ІПН / ЄДРПОУ\n"
        "• суму оплати\n"
        "\n"
        "Це допоможе нам швидше активувати ваше замовлення ✅\n"
        "\n"
        "Якщо виникнуть питання — пишіть у наші боти підтримки:\n"
        "Telegram: @Smartkasahelp_bot\n"
        "Viber: smartkasabot\n"
        "\n"
        "Дякуємо, що ви з нами! 💙\n"
        "Команда SmartKasa"
    ),
}

# Types sent via mailing API (not the legacy trigger webhook).
MAILING_MESSAGE_TYPES = frozenset({MESSAGE_TYPE_KASA_VIBER})


def render_template(message_type: str, payload: dict[str, Any] | None = None) -> str | None:
    template = MESSAGE_TEMPLATES.get(message_type)
    if template is None:
        return None
    data = payload or {}
    return template.format(
        pdf_url=str(data.get("pdf_url") or "").strip(),
    )
