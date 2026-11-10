from __future__ import annotations

from typing import Any

from app.bitrix_config import (
    MESSAGE_TYPE_CABINET_VIBER,
    MESSAGE_TYPE_KASA_PURCHASE_VIBER,
)

# message_type -> text. Placeholders filled via render_template. No template = do not send.
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
    MESSAGE_TYPE_CABINET_VIBER: (
        "Добрий день!\n"
        "\n"
        "Надсилаємо Вам рахунок на оплату тарифного плану Смарт Каса.\n"
        "Рахунок за посиланням {pdf_url}\n"
        "УВАГА!\n"
        "Якщо бажаєте, щоб кошти за кабінет були зараховані одразу. "
        "❗️Відправте це повідомлення в бот з платіжкою\n"
        "Ми одразу поповнимо баланс вашого кабінету. 🧾✅\n"
        "\n"
        "Прошу поповнити баланс кабінету за такими даними:\n"
        "📱 Номер телефону кабінету: {cabinet_phone}\n"
        "📄 Номер рахунку на оплату:- {invoice_number}\n"
        "💰 Сума поповнення: … {amount}\n"
        "🏢 ФОП / назваТОВ: {fop_tov} {last_name} {first_name}\n"
        "\n"
        "Телеграм БОТ - https://t.me/Smartkasahelp_bot\n"
        "Вайбер БОТ- viber://pa?chatURI=smartkasabot\n"
        "Якщо платіжний документ не надіслано, кошти будуть зараховані на ваш баланс "
        "наступного банківського дня, після того як ми побачимо надходження на рахунку."
    ),
    MESSAGE_TYPE_KASA_PURCHASE_VIBER: (
        "Добрий день!\n"
        "\n"
        "Надсилаємо Вам рахунок на придбання Смарт Каса.\n"
        "Рахунок за посиланням {pdf_url}\n"
        "УВАГА!\n"
        "Обов’язково ВКАЖІТЬ, ЗА КОГО ОПЛАТА, та № РАХУНКУ, а також надішліть нам "
        "в чат бот ПЛАТІЖКУ, якщо бажаєте, щоб Смарт каса поїхала відразу❗️\n"
        "Телеграм - https://t.me/Smartkasahelp_bot\n"
        "Вайбер - viber://pa?chatURI=smartkasabot\n"
        "Якщо платіжний документ не надіслано каса поїде , "
        "після того як ми побачимо надходження на рахунку."
    ),
}

def render_template(message_type: str, payload: dict[str, Any] | None = None) -> str | None:
    template = MESSAGE_TEMPLATES.get(message_type)
    if template is None:
        return None
    data = payload or {}
    return template.format(
        pdf_url=_val(data, "pdf_url"),
        cabinet_phone=_val(data, "cabinet_phone"),
        invoice_number=_val(data, "invoice_number"),
        amount=_val(data, "amount"),
        fop_tov=_val(data, "fop_tov"),
        last_name=_val(data, "last_name"),
        first_name=_val(data, "first_name"),
    )


def _val(data: dict[str, Any], key: str) -> str:
    return str(data.get(key) or "").strip()
