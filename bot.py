import asyncio
import aiohttp
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8183712369:AAHR882gyTlvHTc08eAu8zVdgOsdvN0Z_P0"
CRYPTO_TOKEN = "646898:AA0C8kTljg9S5hkc71S2Ez2W1KyF6afOSll"
CHANNEL_ID = -1004336910104
PRICE = 2

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

db = sqlite3.connect("users.db")
db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, invoice_id TEXT)")
db.commit()

def save_invoice(user_id, invoice_id):
    db.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (user_id, invoice_id))
    db.commit()

def get_invoice(user_id):
    cur = db.execute("SELECT invoice_id FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None

async def create_invoice(user_id):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    data = {"asset": "USDT", "amount": PRICE, "description": f"Доступ для {user_id}"}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, headers=headers, json=data) as r:
            res = await r.json()
            inv = res["result"]
            save_invoice(user_id, str(inv["invoice_id"]))
            return inv["pay_url"]

async def check_invoice(invoice_id):
    url = f"https://pay.crypt.bot/api/getInvoices?invoice_ids={invoice_id}"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers) as r:
            data = await r.json()
            return data["result"]["items"][0]["status"] == "paid"

async def create_invite():
    link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
    return link.invite_link

@dp.message(Command("start"))
async def start(message: types.Message):
    pay_url = await create_invoice(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Оплатить {PRICE} USDT", url=pay_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data="check")]
    ])
    await message.answer(
        f"👋 Привет!\n\n"
        f"Чтобы получить доступ в приватный канал, оплати {PRICE} USDT.\n\n"
        f"После оплаты нажми «Проверить оплату».",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data == "check")
async def check(call: types.CallbackQuery):
    await call.answer()
    inv_id = get_invoice(call.from_user.id)
    if not inv_id:
        await call.message.answer("Счёт не найден. Напиши /start заново.")
        return
    paid = await check_invoice(inv_id)
    if paid:
        link = await create_invite()
        await call.message.answer(
            f"✅ Оплата получена!\n\n"
            f"🔗 Твоя одноразовая ссылка:\n{link}\n\n"
            f"⚠️ Она действует только для 1 человека. Никому не передавай."
        )
    else:
        await call.message.answer("❌ Оплата ещё не поступила. Попробуй через минуту.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
