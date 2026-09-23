# -*- coding: utf-8 -*-
import asyncio, logging, os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    Message, CallbackQuery
)
from dotenv import load_dotenv
from sqlalchemy import select, String, Integer, BigInteger, Text, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
logging.basicConfig(level=logging.INFO)

# ==================== DATABASE ====================
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=True)

class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    price: Mapped[int] = mapped_column(Integer)
    duration: Mapped[int] = mapped_column(Integer)
    emoji: Mapped[str] = mapped_column(String(10), default="W")

class Moto(Base):
    __tablename__ = "motos"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(50))
    brand: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    year: Mapped[int] = mapped_column(Integer)
    engine_cc: Mapped[int] = mapped_column(Integer)
    power_hp: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    photo: Mapped[str] = mapped_column(String(500))

class ATV(Base):
    __tablename__ = "atvs"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(50))
    brand: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    year: Mapped[int] = mapped_column(Integer)
    engine_cc: Mapped[int] = mapped_column(Integer)
    power_hp: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    photo: Mapped[str] = mapped_column(String(500))

class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    user_name: Mapped[str] = mapped_column(String(200))
    service_name: Mapped[str] = mapped_column(String(200))
    date: Mapped[str] = mapped_column(String(50))
    time: Mapped[str] = mapped_column(String(10))
    moto_brand: Mapped[str] = mapped_column(String(50))
    moto_model: Mapped[str] = mapped_column(String(100))
    moto_year: Mapped[int] = mapped_column(Integer)
    phone: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="active")

class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    user_name: Mapped[str] = mapped_column(String(200))
    product_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="new")

engine = create_async_engine("sqlite+aiosqlite:///moto.db")
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

SERVICES_DATA = [
    ("Замена масла + фильтр", 3000, 60, "🛢️"),
    ("Замена воздушного фильтра", 500, 30, "💨"),
    ("Замена свечей зажигания", 800, 40, "⚡"),
    ("Замена тормозной жидкости", 1200, 50, "🛑"),
    ("Замена колодок", 2000, 60, "🔴"),
    ("Чистка и смазка цепи", 800, 30, "⛓️"),
    ("Замена цепи + звёзд", 5500, 120, "🔗"),
    ("Диагностика двигателя", 1500, 60, "🔍"),
    ("Регулировка клапанов", 3500, 120, "⚙️"),
    ("Предсезонная подготовка", 6000, 180, "🏁"),
    ("Шиномонтаж", 1500, 60, "🛞"),
    ("Покраска деталей", 8000, 240, "🎨"),
]

MOTOS_DATA = [
    ("sport", "Yamaha", "YZF-R1", 2025, 998, 200, 1850000, "Флагманский спортбайк с крестовым валом и технологиями MotoGP.", "https://picsum.photos/seed/moto1/900/600"),
    ("sport", "Honda", "CBR1000RR-R", 2024, 1000, 214, 2100000, "Топовый спортбайк с аэродинамикой из MotoGP.", "https://picsum.photos/seed/moto2/900/600"),
    ("sport", "Kawasaki", "Ninja ZX-10R", 2025, 998, 203, 1750000, "Легендарный Ninja в новом поколении.", "https://picsum.photos/seed/moto3/900/600"),
    ("cruiser", "Harley-Davidson", "Fat Boy 114", 2025, 1868, 94, 2500000, "Легендарный круизер с Milwaukee-Eight 114.", "https://picsum.photos/seed/moto4/900/600"),
    ("cruiser", "Indian", "Chief Dark Horse", 2024, 1890, 92, 2300000, "Классика американского мотоциклостроения.", "https://picsum.photos/seed/moto5/900/600"),
    ("cruiser", "BMW", "R 18", 2025, 1802, 91, 2200000, "Большой боксер от BMW с неповторимым характером.", "https://picsum.photos/seed/moto6/900/600"),
    ("enduro", "KTM", "450 EXC-F", 2025, 449, 63, 1200000, "Готов к бездорожью и соревнованиям.", "https://picsum.photos/seed/moto7/900/600"),
    ("enduro", "Husqvarna", "FE 501", 2024, 510, 65, 1250000, "Шведский характер и немецкое качество.", "https://picsum.photos/seed/moto8/900/600"),
]

ATVS_DATA = [
    ("utility", "Can-Am", "Outlander 1000R", 2025, 976, 91, 1500000, "Мощный утилитарный квадроцикл для работы и охоты.", "https://picsum.photos/seed/atv1/900/600"),
    ("utility", "Polaris", "Sportsman 850", 2024, 850, 78, 1300000, "Надёжный помощник для любых задач.", "https://picsum.photos/seed/atv2/900/600"),
    ("sport", "Yamaha", "Raptor 700R", 2025, 686, 45, 1100000, "Спортивный квадроцикл для экстрима.", "https://picsum.photos/seed/atv3/900/600"),
    ("sport", "Can-Am", "Renegade 1000R", 2024, 976, 91, 1600000, "Для экстремальной езды по бездорожью.", "https://picsum.photos/seed/atv4/900/600"),
]

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        cnt = (await s.execute(select(func.count()).select_from(Service))).scalar()
        if cnt == 0:
            for n, p, d, e in SERVICES_DATA:
                s.add(Service(name=n, price=p, duration=d, emoji=e))
        cnt = (await s.execute(select(func.count()).select_from(Moto))).scalar()
        if cnt == 0:
            for c, b, m, y, cc, hp, pr, desc, ph in MOTOS_DATA:
                s.add(Moto(category=c, brand=b, model=m, year=y, engine_cc=cc, power_hp=hp, price=pr, description=desc, photo=ph))
        cnt = (await s.execute(select(func.count()).select_from(ATV))).scalar()
        if cnt == 0:
            for c, b, m, y, cc, hp, pr, desc, ph in ATVS_DATA:
                s.add(ATV(category=c, brand=b, model=m, year=y, engine_cc=cc, power_hp=hp, price=pr, description=desc, photo=ph))
        await s.commit()

# ==================== KEYBOARDS ====================
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Записаться на сервис", callback_data="svc_list")],
        [InlineKeyboardButton(text="🏍️ Мотоциклы", callback_data="moto_cats"),
         InlineKeyboardButton(text="🚙 Квадроциклы", callback_data="atv_cats")],
        [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_bookings"),
         InlineKeyboardButton(text="📞 Контакты", callback_data="contacts")],
        [InlineKeyboardButton(text="ℹ️ О нас", callback_data="about")],
    ])

def back_to_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])

def services_kb(services):
    rows = []
    for s in services:
        rows.append([InlineKeyboardButton(text=f"{s.emoji} {s.name} — {s.price}₽", callback_data=f"svc_{s.id}")])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def dates_kb():
    rows, row = [], []
    today = datetime.now()
    for i in range(1, 15):
        d = today + timedelta(days=i)
        if d.weekday() == 6:
            continue
        row.append(InlineKeyboardButton(text=d.strftime("%d.%m"), callback_data=f"dt_{d.strftime('%Y-%m-%d')}"))
        if len(row) == 4:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="svc_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def times_kb():
    rows, row = [], []
    for h in range(9, 19):
        t = f"{h:02d}:00"
        row.append(InlineKeyboardButton(text=t, callback_data=f"tm_{t}"))
        if len(row) == 4:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="svc_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def confirm_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_all")],
    ])

def phone_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)

def moto_cats_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏁 Спортбайки", callback_data="moto_cat_sport")],
        [InlineKeyboardButton(text="🛣️ Круизеры", callback_data="moto_cat_cruiser")],
        [InlineKeyboardButton(text="🌲 Эндуро", callback_data="moto_cat_enduro")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])

def atv_cats_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠️ Утилитарные", callback_data="atv_cat_utility")],
        [InlineKeyboardButton(text="🏁 Спортивные", callback_data="atv_cat_sport")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])

def product_list_kb(items, back_cb, prefix):
    rows = []
    for it in items:
        rows.append([InlineKeyboardButton(text=f"➡️ {it.brand} {it.model}", callback_data=f"{prefix}_{it.id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def product_card_kb(pid, prefix, back_cb):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Заказать звонок", callback_data=f"lead_{prefix}_{pid}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)],
    ])

def admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Записи на сервис", callback_data="adm_bookings"),
         InlineKeyboardButton(text="📨 Заявки на звонок", callback_data="adm_leads")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])

# ==================== FSM ====================
class Book(StatesGroup):
    svc = State(); dt = State(); tm = State()
    mb = State(); mm = State(); my = State(); ph = State(); confirm = State()

class LeadFSM(StatesGroup):
    waiting_phone = State()

class AdminFSM(StatesGroup):
    broadcast = State()

# ==================== ROUTER ====================
dp = Dispatcher()

async def safe_edit(msg, text=None, **kwargs):
    """Безопасно редактирует сообщение или отправляет новое."""
    try:
        if text is not None:
            await msg.edit_text(text, **kwargs)
        else:
            await msg.edit_reply_markup(reply_markup=kwargs.get("reply_markup"))
    except Exception:
        try:
            await msg.delete()
        except Exception:
            pass
        if text is not None:
            await msg.answer(text, **kwargs)


@dp.message(CommandStart())
async def cmd_start(m: Message):
    async with SessionLocal() as s:
        u = await s.get(User, m.from_user.id)
        if not u:
            s.add(User(id=m.from_user.id, username=m.from_user.username, full_name=m.from_user.full_name))
            await s.commit()
    await m.answer(
        f"🏍️ <b>Добро пожаловать в MotoService!</b>\n\n"
        f"Мы — сервис по ремонту мотоциклов и квадроциклов, а также официальный дилер новой техники.\n\n"
        f"🔧 Ремонт и ТО\n🏍️ Продажа мотоциклов\n🚙 Продажа квадроциклов\n\n"
        f"Выберите раздел 👇",
        reply_markup=main_menu_kb()
    )

@dp.callback_query(F.data == "main_menu")
async def cb_main(c: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await safe_edit(c.message, 
            "🏠 <b>Главное меню</b>\n\nВыберите раздел 👇",
            reply_markup=main_menu_kb()
        )
    except Exception:
        await c.message.answer("🏠 <b>Главное меню</b>", reply_markup=main_menu_kb())
    await c.answer()

@dp.callback_query(F.data == "contacts")
async def cb_contacts(c: CallbackQuery):
    await safe_edit(c.message, 
        "📞 <b>Наши контакты</b>\n\n"
        "🏢 <b>Адрес:</b> г. Москва, ул. Мотостроителей, 15\n"
        "🕘 <b>Часы работы:</b> Пн–Сб 09:00–19:00\n"
        "☎️ <b>Телефон:</b> +7 (999) 123-45-67\n"
        "📧 <b>Email:</b> info@motoservice.ru\n\n"
        "🗺 <a href='https://yandex.ru/maps'>Мы на карте</a>",
        reply_markup=back_to_main_kb(), disable_web_page_preview=True
    )
    await c.answer()

@dp.callback_query(F.data == "about")
async def cb_about(c: CallbackQuery):
    await safe_edit(c.message, 
        "ℹ️ <b>О нас</b>\n\n"
        "MotoService — это команда профессионалов с 12-летним опытом.\n\n"
        "🏆 <b>Наши преимущества:</b>\n"
        "• Оригинальные запчасти\n"
        "• Гарантия на работы 6 месяцев\n"
        "• Собственный склад\n"
        "• Онлайн-запись 24/7\n"
        "• Работаем с 2014 года\n\n"
        "🏍️ Более 5000 довольных клиентов!",
        reply_markup=back_to_main_kb()
    )
    await c.answer()

# ---------- BOOKING ----------
@dp.callback_query(F.data == "svc_list")
async def cb_svc_list(c: CallbackQuery, state: FSMContext):
    await state.clear()
    async with SessionLocal() as s:
        r = await s.execute(select(Service).order_by(Service.id))
        services = r.scalars().all()
    await safe_edit(c.message, 
        "🔧 <b>Выберите услугу:</b>\n\n<i>Все цены указаны за работу, без стоимости запчастей.</i>",
        reply_markup=services_kb(services)
    )
    await c.answer()

@dp.callback_query(F.data.startswith("svc_"))
async def cb_svc_pick(c: CallbackQuery, state: FSMContext):
    sid = int(c.data.split("_")[1])
    async with SessionLocal() as s:
        svc = await s.get(Service, sid)
    await state.update_data(svc_name=f"{svc.emoji} {svc.name}", svc_price=svc.price)
    await state.set_state(Book.dt)
    await safe_edit(c.message, 
        f"🔧 <b>{svc.emoji} {svc.name}</b>\n"
        f"💰 Стоимость: <b>{svc.price}₽</b>\n"
        f"⏱ Время: ~{svc.duration} мин\n\n"
        f"📅 <b>Выберите дату визита:</b>",
        reply_markup=dates_kb()
    )
    await c.answer()

@dp.callback_query(F.data.startswith("dt_"))
async def cb_date(c: CallbackQuery, state: FSMContext):
    d = c.data.split("_", 1)[1]
    await state.update_data(date=d)
    await state.set_state(Book.tm)
    await safe_edit(c.message, 
        f"📅 <b>Дата:</b> {d}\n\n⏰ <b>Выберите время:</b>",
        reply_markup=times_kb()
    )
    await c.answer()

@dp.callback_query(F.data.startswith("tm_"))
async def cb_time(c: CallbackQuery, state: FSMContext):
    t = c.data.split("_", 1)[1]
    await state.update_data(time=t)
    await state.set_state(Book.mb)
    await safe_edit(c.message, 
        f"⏰ <b>Время:</b> {t}\n\n"
        f"🏍️ <b>Марка мотоцикла?</b>\n"
        f"<i>Например: Yamaha, Honda, BMW, KTM</i>"
    )
    await c.answer()

@dp.message(Book.mb)
async def st_brand(m: Message, state: FSMContext):
    await state.update_data(moto_brand=m.text.strip())
    await state.set_state(Book.mm)
    await m.answer("📝 <b>Модель?</b>\n<i>Например: YZF-R1, CBR600RR, S1000RR</i>")

@dp.message(Book.mm)
async def st_model(m: Message, state: FSMContext):
    await state.update_data(moto_model=m.text.strip())
    await state.set_state(Book.my)
    await m.answer("📅 <b>Год выпуска?</b>\n<i>Только цифры, например 2020</i>")

@dp.message(Book.my)
async def st_year(m: Message, state: FSMContext):
    try:
        y = int(m.text.strip())
        assert 1950 <= y <= 2026
    except Exception:
        await m.answer("⚠️ Введите корректный год (1950–2026)")
        return
    await state.update_data(moto_year=y)
    await state.set_state(Book.ph)
    await m.answer(
        "📞 <b>Ваш номер телефона?</b>\n"
        "Нажмите кнопку ниже или введите вручную:",
        reply_markup=phone_kb()
    )

@dp.message(Book.ph, F.contact)
async def st_phone_contact(m: Message, state: FSMContext):
    await _finalize_phone(m, state, m.contact.phone_number)

@dp.message(Book.ph)
async def st_phone_text(m: Message, state: FSMContext):
    await _finalize_phone(m, state, m.text.strip())

async def _finalize_phone(m: Message, state: FSMContext, phone: str):
    await state.update_data(phone=phone)
    data = await state.get_data()
    await state.set_state(Book.confirm)
    text = (
        f"📋 <b>Проверьте запись:</b>\n\n"
        f"🔧 Услуга: <b>{data['svc_name']}</b>\n"
        f"💰 Стоимость: <b>{data['svc_price']}₽</b>\n"
        f"📅 Дата: <b>{data['date']}</b>\n"
        f"⏰ Время: <b>{data['time']}</b>\n"
        f"🏍️ Мотоцикл: <b>{data['moto_brand']} {data['moto_model']}, {data['moto_year']}</b>\n"
        f"📞 Телефон: <b>{phone}</b>\n\n"
        f"Всё верно?"
    )
    await m.answer("✅ Данные приняты!", reply_markup=ReplyKeyboardRemove())
    await m.answer(text, reply_markup=confirm_kb())

@dp.callback_query(F.data == "confirm_yes")
async def cb_confirm(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    async with SessionLocal() as s:
        b = Booking(
            user_id=c.from_user.id,
            user_name=c.from_user.full_name,
            service_name=data["svc_name"],
            date=data["date"], time=data["time"],
            moto_brand=data["moto_brand"], moto_model=data["moto_model"],
            moto_year=data["moto_year"], phone=data["phone"]
        )
        s.add(b); await s.commit()
    for aid in ADMIN_IDS:
        try:
            await c.bot.send_message(aid,
                f"🔔 <b>НОВАЯ ЗАПИСЬ!</b>\n\n"
                f"👤 {c.from_user.full_name}\n"
                f"🔧 {data['svc_name']} — {data['svc_price']}₽\n"
                f"📅 {data['date']} в {data['time']}\n"
                f"🏍️ {data['moto_brand']} {data['moto_model']}, {data['moto_year']}\n"
                f"📞 {data['phone']}"
            )
        except Exception:
            pass
    await safe_edit(c.message, 
        f"🎉 <b>Запись оформлена!</b>\n\n"
        f"📍 г. Москва, ул. Мотостроителей, 15\n"
        f"📞 +7 (999) 123-45-67\n\n"
        f"🗓 {data['date']} в {data['time']}\n"
        f"🔧 {data['svc_name']}\n\n"
        f"<i>За 24 часа до визита мы напомним.</i>",
        reply_markup=back_to_main_kb()
    )
    await c.answer("Запись создана!", show_alert=False)

@dp.callback_query(F.data == "cancel_all")
async def cb_cancel(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(c.message, "❌ Отменено.\n\nВозвращаемся в меню 👇", reply_markup=main_menu_kb())
    await c.answer()

@dp.callback_query(F.data == "my_bookings")
async def cb_my(c: CallbackQuery):
    async with SessionLocal() as s:
        r = await s.execute(select(Booking).where(Booking.user_id == c.from_user.id, Booking.status == "active").order_by(Booking.id.desc()))
        items = r.scalars().all()
    if not items:
        await safe_edit(c.message, "📋 У вас пока нет активных записей.", reply_markup=back_to_main_kb())
        await c.answer(); return
    text = "📋 <b>Ваши записи:</b>\n\n"
    for b in items:
        text += (
            f"🔧 {b.service_name}\n"
            f"📅 {b.date} в {b.time}\n"
            f"🏍️ {b.moto_brand} {b.moto_model}, {b.moto_year}\n"
            f"📞 {b.phone}\n\n"
        )
    await safe_edit(c.message, text, reply_markup=back_to_main_kb())
    await c.answer()

# ---------- CATALOG MOTO ----------
@dp.callback_query(F.data == "moto_cats")
async def cb_moto_cats(c: CallbackQuery):
    await safe_edit(c.message, 
        "🏍️ <b>Каталог мотоциклов</b>\n\nВыберите категорию 👇",
        reply_markup=moto_cats_kb()
    )
    await c.answer()

@dp.callback_query(F.data.startswith("moto_cat_"))
async def cb_moto_list(c: CallbackQuery):
    cat = c.data.replace("moto_cat_", "")
    async with SessionLocal() as s:
        r = await s.execute(select(Moto).where(Moto.category == cat))
        items = r.scalars().all()
    names = {"sport": "🏁 Спортбайки", "cruiser": "🛣️ Круизеры", "enduro": "🌲 Эндуро"}
    await safe_edit(c.message, 
        f"{names.get(cat, cat)}\n\nНайдено: <b>{len(items)}</b>\nВыберите модель 👇",
        reply_markup=product_list_kb(items, "moto_cats", "moto_item")
    )
    await c.answer()

@dp.callback_query(F.data.startswith("moto_item_"))
async def cb_moto_card(c: CallbackQuery):
    pid = int(c.data.split("_")[2])
    async with SessionLocal() as s:
        it = await s.get(Moto, pid)
    text = (
        f"🏍️ <b>{it.brand} {it.model}</b> ({it.year})\n\n"
        f"📊 <b>Характеристики:</b>\n"
        f"• Объём: {it.engine_cc} см³\n"
        f"• Мощность: {it.power_hp} л.с.\n"
        f"• Год: {it.year}\n\n"
        f"💰 <b>Цена: {it.price:,} ₽</b>\n\n"
        f"{it.description}"
    ).replace(",", " ")
    try:
        await c.message.delete()
    except Exception:
        pass
    try:
        await c.message.answer_photo(
            photo=it.photo, caption=text,
            reply_markup=product_card_kb(pid, "moto", "moto_cats")
        )
    except Exception:
        await c.message.answer(text, reply_markup=product_card_kb(pid, "moto", "moto_cats"))
    await c.answer()

# ---------- CATALOG ATV ----------
@dp.callback_query(F.data == "atv_cats")
async def cb_atv_cats(c: CallbackQuery):
    await safe_edit(c.message, 
        "🚙 <b>Каталог квадроциклов</b>\n\nВыберите категорию 👇",
        reply_markup=atv_cats_kb()
    )
    await c.answer()

@dp.callback_query(F.data.startswith("atv_cat_"))
async def cb_atv_list(c: CallbackQuery):
    cat = c.data.replace("atv_cat_", "")
    async with SessionLocal() as s:
        r = await s.execute(select(ATV).where(ATV.category == cat))
        items = r.scalars().all()
    names = {"utility": "🛠️ Утилитарные", "sport": "🏁 Спортивные"}
    await safe_edit(c.message, 
        f"{names.get(cat, cat)}\n\nНайдено: <b>{len(items)}</b>\nВыберите модель 👇",
        reply_markup=product_list_kb(items, "atv_cats", "atv_item")
    )
    await c.answer()

@dp.callback_query(F.data.startswith("atv_item_"))
async def cb_atv_card(c: CallbackQuery):
    pid = int(c.data.split("_")[2])
    async with SessionLocal() as s:
        it = await s.get(ATV, pid)
    text = (
        f"🚙 <b>{it.brand} {it.model}</b> ({it.year})\n\n"
        f"📊 <b>Характеристики:</b>\n"
        f"• Объём: {it.engine_cc} см³\n"
        f"• Мощность: {it.power_hp} л.с.\n"
        f"• Год: {it.year}\n\n"
        f"💰 <b>Цена: {it.price:,} ₽</b>\n\n"
        f"{it.description}"
    ).replace(",", " ")
    try:
        await c.message.delete()
    except Exception:
        pass
    try:
        await c.message.answer_photo(
            photo=it.photo, caption=text,
            reply_markup=product_card_kb(pid, "atv", "atv_cats")
        )
    except Exception:
        await c.message.answer(text, reply_markup=product_card_kb(pid, "atv", "atv_cats"))
    await c.answer()

# ---------- LEAD ----------
@dp.callback_query(F.data.startswith("lead_"))
async def cb_lead(c: CallbackQuery, state: FSMContext):
    _, ptype, pid = c.data.split("_")
    async with SessionLocal() as s:
        obj = await s.get(Moto, int(pid)) if ptype == "moto" else await s.get(ATV, int(pid))
    name = f"{obj.brand} {obj.model}"
    await state.update_data(lead_product=name)
    await state.set_state(LeadFSM.waiting_phone)
    await c.message.answer(
        f"📞 <b>Заявка на звонок</b>\n\n"
        f"Товар: <b>{name}</b>\n\n"
        f"Отправьте ваш номер телефона кнопкой ниже 👇",
        reply_markup=phone_kb()
    )
    await c.answer()

@dp.message(LeadFSM.waiting_phone, F.contact)
async def lead_contact(m: Message, state: FSMContext):
    await _save_lead(m, state, m.contact.phone_number)

@dp.message(LeadFSM.waiting_phone)
async def lead_text(m: Message, state: FSMContext):
    await _save_lead(m, state, m.text.strip())

async def _save_lead(m: Message, state: FSMContext, phone: str):
    data = await state.get_data()
    await state.clear()
    async with SessionLocal() as s:
        s.add(Lead(
            user_id=m.from_user.id, user_name=m.from_user.full_name,
            product_name=data.get("lead_product", "—"), phone=phone
        ))
        await s.commit()
    for aid in ADMIN_IDS:
        try:
            await m.bot.send_message(aid,
                f"🔔 <b>НОВАЯ ЗАЯВКА!</b>\n\n"
                f"👤 {m.from_user.full_name}\n"
                f"🏍️ {data.get('lead_product', '—')}\n"
                f"📞 {phone}"
            )
        except Exception:
            pass
    await m.answer(
        f"✅ <b>Заявка принята!</b>\n\n"
        f"Мы свяжемся с вами в течение 15 минут.\n\n"
        f"Товар: <b>{data.get('lead_product', '—')}</b>\n"
        f"Телефон: <b>{phone}</b>",
        reply_markup=ReplyKeyboardRemove()
    )
    await m.answer("Возвращаемся в меню 👇", reply_markup=main_menu_kb())

# ---------- ADMIN ----------
@dp.message(Command("admin"))
async def cmd_admin(m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.answer("⛔ Нет доступа.")
        return
    await m.answer("🛡️ <b>Админ-панель</b>", reply_markup=admin_menu_kb())

@dp.callback_query(F.data == "adm_bookings")
async def adm_bookings(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS:
        await c.answer("⛔ Нет доступа", show_alert=True); return
    async with SessionLocal() as s:
        r = await s.execute(select(Booking).where(Booking.status == "active").order_by(Booking.id.desc()).limit(20))
        items = r.scalars().all()
    if not items:
        await safe_edit(c.message, "📋 Нет активных записей.", reply_markup=admin_menu_kb())
        await c.answer(); return
    text = f"📋 <b>Активные записи ({len(items)}):</b>\n\n"
    for b in items:
        text += (
            f"👤 {b.user_name}\n"
            f"🔧 {b.service_name}\n"
            f"📅 {b.date} в {b.time}\n"
            f"🏍️ {b.moto_brand} {b.moto_model}\n"
            f"📞 {b.phone}\n\n"
        )
    await safe_edit(c.message, text, reply_markup=admin_menu_kb())
    await c.answer()

@dp.callback_query(F.data == "adm_leads")
async def adm_leads(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS:
        await c.answer("⛔ Нет доступа", show_alert=True); return
    async with SessionLocal() as s:
        r = await s.execute(select(Lead).order_by(Lead.id.desc()).limit(20))
        items = r.scalars().all()
    if not items:
        await safe_edit(c.message, "📨 Заявок нет.", reply_markup=admin_menu_kb())
        await c.answer(); return
    text = f"📨 <b>Заявки ({len(items)}):</b>\n\n"
    for l in items:
        text += f"👤 {l.user_name}\n🏍️ {l.product_name}\n📞 {l.phone}\n\n"
    await safe_edit(c.message, text, reply_markup=admin_menu_kb())
    await c.answer()

@dp.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(c: CallbackQuery, state: FSMContext):
    if c.from_user.id not in ADMIN_IDS:
        await c.answer("⛔ Нет доступа", show_alert=True); return
    await state.set_state(AdminFSM.broadcast)
    await safe_edit(c.message, 
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте текст сообщения. Он уйдёт всем пользователям бота.\n\n"
        "Для отмены напишите <code>/cancel</code>"
    )
    await c.answer()

@dp.message(AdminFSM.broadcast)
async def do_broadcast(m: Message, state: FSMContext):
    if m.text == "/cancel":
        await state.clear()
        await m.answer("❌ Отменено.", reply_markup=admin_menu_kb())
        return
    await state.clear()
    async with SessionLocal() as s:
        r = await s.execute(select(User.id))
        ids = [row[0] for row in r.all()]
    ok, fail = 0, 0
    for uid in ids:
        try:
            await m.bot.send_message(uid, m.text)
            ok += 1
        except Exception:
            fail += 1
    await m.answer(f"✅ Отправлено: {ok}\n❌ Ошибок: {fail}", reply_markup=admin_menu_kb())

# ==================== MAIN ====================
from aiohttp import web

async def health(request):
    return web.Response(text="OK")

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health server started on port {port}")

async def main():
    await init_db()
    await start_health_server()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
