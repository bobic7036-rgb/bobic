"""Кнопки та обробники підписок / оплат."""
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from bot import db
from bot.config import ADMIN_ID

router = Router()

# pending invoice: invoice_id -> {user_id, plan}
_invoices = {}
_invoice_seq = 0


def make_invoice_id():
    global _invoice_seq
    _invoice_seq += 1
    return f"INV-{int(asyncio.get_event_loop().time())}-{_invoice_seq}"


async def subscription_kb(user_id: int):
    u = await db.get_user(user_id)
    base_price = await db.get_int("base_price")
    pro_price = await db.get_int("pro_price")
    base_days = await db.get_int("base_days")
    pro_days = await db.get_int("pro_days")
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(
        f"📦 БАЗОВА — {base_price}$ / {base_days} дн.",
        callback_data=f"buy:base"))
    kb.add(InlineKeyboardButton(
        f"💎 ПРОФЕСІЙНА — {pro_price}$ / {pro_days} дн.",
        callback_data=f"buy:pro"))
    return kb


@router.message(Command("subscribe"))
@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.ensure_user(message.from_user.id, message.from_user.username or "")
    u = await db.get_user(message.from_user.id)
    now = int(asyncio.get_event_loop().time())

    def until(ts):
        d = (ts - now) // 86400
        return f"ще {d} дн." if d > 0 else "❌ немає"

    text = (
        "🤖 <b>Crypto Signals Bot</b>\n"
        "Готові зделки з Binance Futures: вхід, стоп, 2 тейки, шанс і пояснення.\n\n"
        f"📦 Базова підписка: {until(u['base_until'])}\n"
        f"💎 Професійна підписка: {until(u['pro_until'])}\n\n"
        "Обери підписку 👇 або напиши /help"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=await subscription_kb(message.from_user.id))


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(cb: CallbackQuery):
    plan = cb.data.split(":")[1]
    price = await db.get_int(f"{plan}_price")
    days = await db.get_int(f"{plan}_days")
    inv_id = make_invoice_id()
    _invoices[inv_id] = {"user_id": cb.from_user.id, "plan": plan}

    name = "БАЗОВА" if plan == "base" else "ПРОФЕСІЙНА"
    pay_text = (
        f"🧾 <b>Рахунок на оплату</b>\n\n"
        f"Підписка: <b>{name}</b> на {days} днів\n"
        f"Сума до оплати: <b>{price} USDT (TRC20)</b>\n"
        f"Номер рахунку: <code>{inv_id}</code>\n\n"
        f"⚠️ Оплати за реквізитами, які надішле адміністратор у особистих повідомленнях, "
        f"та натисни кнопку нижче. Адмін підтвердить оплату і відкриє доступ."
    )
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("✅ Я оплатив — підтвердити", callback_data=f"paid:{inv_id}"))
    await cb.message.answer(pay_text, parse_mode="HTML", reply_markup=kb)

    # сповіщення адміну
    admin_kb = InlineKeyboardMarkup(row_width=2)
    admin_kb.insert(InlineKeyboardButton("✔️ Підтвердити", callback_data=f"acc_yes:{inv_id}"))
    admin_kb.insert(InlineKeyboardButton("✖️ Відхилити", callback_data=f"acc_no:{inv_id}"))
    try:
        await cb.bot.send_message(
            ADMIN_ID,
            f"💰 Нова оплата!\nUser: @{cb.from_user.username or ''} (id {cb.from_user.id})\n"
            f"План: {name}, {price} USDT, рахунок {inv_id}",
            reply_markup=admin_kb,
        )
    except Exception:
        pass
    await cb.answer()


@router.callback_query(F.data.startswith("paid:"))
async def cb_paid(cb: CallbackQuery):
    await cb.answer("⏳ Очікуй підтвердження від адміністратора...", show_alert=True)


@router.callback_query(F.data.startswith("acc_yes:"))
async def cb_accept(cb: CallbackQuery):
    inv_id = cb.data.split(":")[1]
    info = _invoices.pop(inv_id, None)
    if not info:
        await cb.answer("Рахунок не знайдено (можливо вже оброблено)", show_alert=True)
        return
    plan = info["plan"]
    days = await db.get_int(f"{plan}_days")
    await db.set_subscription(info["user_id"], plan, days)
    name = "БАЗОВУ" if plan == "base" else "ПРОФЕСІЙНУ"
    await cb.bot.send_message(
        info["user_id"],
        f"🎉 Оплата підтверджена! Активовано <b>{name}</b> підписку на {days} днів.\n"
        f"Команда /signals — отримати актуальні зделки.",
        parse_mode="HTML",
    )
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.bot.send_message(cb.from_user.id, f"✅ Підписку активовано (рахунок {inv_id}).")
    await cb.answer()


@router.callback_query(F.data.startswith("acc_no:"))
async def cb_reject(cb: CallbackQuery):
    inv_id = cb.data.split(":")[1]
    info = _invoices.pop(inv_id, None)
    if info:
        await cb.bot.send_message(
            info["user_id"],
            f"❌ Оплату по рахунку {inv_id} не підтверджено. "
            f"Якщо ти все ж оплатив — напиши адміну.",
        )
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer("Відхилено")
