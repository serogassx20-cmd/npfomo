import asyncio
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp

BOT_TOKEN = "8814461831:AAGfAd7439s8ProjIEh2PfzyYrNQlmYO2s0"
NP_API_KEY = "e3014080a3ef7710fe8f52665c262ad4"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_tracking(ttn: str) -> dict | None:
    url = "https://api.novaposhta.ua/v2.0/json/"
    payload = {
        "apiKey": NP_API_KEY,
        "modelName": "TrackingDocument",
        "calledMethod": "getStatusDocuments",
        "methodProperties": {
            "Documents": [
                {
                    "DocumentNumber": ttn,
                    "Phone": ""
                }
            ]
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                res = await resp.json()
                if res.get("success") and res.get("data"):
                    return res["data"][0]
    return None

def build_response(ttn: str, data: dict):
    status = data.get("Status", "-")
    sender_city = data.get("CitySender", "-")
    recipient_city = data.get("CityRecipient", "-")
    warehouse = data.get("WarehouseRecipient", "-")
    delivery_date = data.get("ScheduledDeliveryDate", "-")
    cost = data.get("DocumentCost", "-")
    recipient_name = data.get("RecipientFullName", "-")
    
    redelivery = data.get("RedeliverySum", "0")
    redelivery_text = "нет" if not redelivery or redelivery == "0" else f"{redelivery} грн"

    weight = data.get("DocumentWeight", "-")
    volume_weight = data.get("VolumeWeight", "-")

    status_icon = "📦"
    if "отправлен" in status.lower() or "еміт" in status.lower():
        status_icon = "🛫"
    elif "отделении" in status.lower() or "прибув" in status.lower():
        status_icon = "🔥"
    elif "получен" in status.lower() or "одержано" in status.lower():
        status_icon = "✅"

    text = (
        f"⚡ **ТРЕК-КАРТОЧКА ПОСЫЛКИ**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **ТТН:** `{ttn}`\n"
        f"👤 **Получатель:** {recipient_name}\n"
        f"{status_icon} **Статус:** {status}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🗺 **Маршрут:** {sender_city} ➔ {recipient_city}\n"
        f"🏠 **Отделение:** {warehouse}\n"
        f"📅 **Прибытие:** {delivery_date}\n"
        f"⚖️ **Вес:** {weight} кг *(объем: {volume_weight} кг)*\n"
        f"💰 **Доставка:** {cost} грн\n"
        f"📦 **Наложка:** {redelivery_text}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_{ttn}"),
            InlineKeyboardButton(text="🌐 Трек на сайте НП", url=f"https://novaposhta.ua/tracking/?cargo_number={ttn}")
        ]
    ])
    return text, kb

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("кидай ттнху текстом или перешли сообщение с ней, расковыряем")

@dp.message(F.text)
async def ttn_handler(message: types.Message):
    text = message.text.strip()
    match = re.search(r'(?:ттн|нп|номер)[\s\:\№]*([\d\s]{14,20})', text, re.IGNORECASE)
    
    if match:
        raw_digits = re.sub(r'\D', '', match.group(1))
        ttn_match = re.search(r'\d{14}', raw_digits)
        ttn = ttn_match.group(0) if ttn_match else None
    else:
        raw_digits = re.sub(r'\D', '', text)
        ttn_match = re.search(r'\d{14}', raw_digits)
        ttn = ttn_match.group(0) if ttn_match else None

    if not ttn:
        await message.answer("неверный формат, нужно 14 цифр, бляха")
        return

    data = await get_tracking(ttn)

    if not data:
        await message.answer(f"ттн `{ttn}` не найдена в базе новой почты")
        return

    resp_text, kb = build_response(ttn, data)
    await message.answer(resp_text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data.startswith("refresh_"))
async def refresh_callback(callback: types.CallbackQuery):
    ttn = callback.data.split("_")[1]
    data = await get_tracking(ttn)
    if not data:
        await callback.answer("не вышло обновить", show_alert=True)
        return
    
    resp_text, kb = build_response(ttn, data)
    try:
        await callback.message.edit_text(resp_text, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        pass
    await callback.answer("статус подтянут")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())