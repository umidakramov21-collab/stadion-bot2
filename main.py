import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ===================== SOZLAMALAR =====================
TOKEN = "8750959132:AAEIUcjT76TCiLsCXTa9Yf_ub1A_fjQwMgg"
ADMIN_ID = 1216412017

KARTA_RAQAM = "5614 6819 0849 5173"
STADION_NOMI = "21 Arena"
TELEFON = "+998 90 000 04 21"

# Narxlar
NARXLAR = {
    "kunduz": 100_000,   # 09:00 - 17:00
    "kechqurun": 150_000  # 17:00 - 23:00
}

# Ish vaqti
BOSHLANISH = 9
TUGASH = 26  # 02:00 kecha (24+2)

# ===================== HOLATLAR =====================
SANA, VAQT, DAVOMIYLIK, TOLLOV, CHEK = range(5)

# Bronlar xotirasi (bot ishlaganda saqlanadi)
bronlar = {}  # {sana: [(soat, davomiylik, user_id, ism, telefon, tollov_turi)]}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===================== YORDAMCHI FUNKSIYALAR =====================

def vaqt_bosh_mi(sana, soat, davomiylik):
    """Berilgan vaqt band emasligini tekshiradi"""
    if sana not in bronlar:
        return True
    for bron in bronlar[sana]:
        b_soat, b_davom, *_ = bron
        if not (soat + davomiylik <= b_soat or soat >= b_soat + b_davom):
            return False
    return True

def narx_hisob(soat, davomiylik):
    """Soat va davomiylikka qarab narx hisoblaydi"""
    jami = 0
    for i in range(davomiylik):
        h = (soat + i) % 24
        if 9 <= h < 17:
            jami += NARXLAR["kunduz"]
        else:
            jami += NARXLAR["kechqurun"]
    return jami

def band_soatlar(sana):
    """Berilgan sanada band soatlar ro'yxati"""
    if sana not in bronlar:
        return []
    band = []
    for bron in bronlar[sana]:
        soat, davom, *_ = bron
        for i in range(davom):
            band.append(soat + i)
    return band

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📅 Bron qilish", callback_data="bron")],
        [InlineKeyboardButton("💰 Narxlar", callback_data="narxlar")],
        [InlineKeyboardButton("📋 Mening bronlarim", callback_data="mening_bronlarim")],
        [InlineKeyboardButton("📞 Aloqa", callback_data="aloqa")],
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_menu():
    keyboard = [
        [InlineKeyboardButton("📋 Barcha bronlar", callback_data="admin_bronlar")],
        [InlineKeyboardButton("📅 Bugungi jadval", callback_data="admin_bugun")],
        [InlineKeyboardButton("❌ Bronni bekor qilish", callback_data="admin_bekor")],
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_stat")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ===================== START =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data.clear()

    if user.id == ADMIN_ID:
        await update.message.reply_text(
            f"👋 Xush kelibsiz, Admin!\n\n🏟 *{STADION_NOMI}* boshqaruv paneli",
            parse_mode="Markdown",
            reply_markup=admin_menu()
        )
    else:
        await update.message.reply_text(
            f"⚽ *{STADION_NOMI}* ga xush kelibsiz!\n\n"
            f"🕐 Ish vaqti: 09:00 – 02:00\n"
            f"📍 Tuman markazi\n\n"
            f"Quyidagilardan birini tanlang:",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )


# ===================== NARXLAR =====================

async def narxlar_korsatish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        f"💰 *{STADION_NOMI} — Narxlar*\n\n"
        f"🌤 Kunduz (09:00–17:00): *{NARXLAR['kunduz']:,} so'm/soat*\n"
        f"🌙 Kechqurun (17:00–02:00): *{NARXLAR['kechqurun']:,} so'm/soat*\n\n"
        f"📌 Minimal bron: 1 soat\n"
        f"💳 Avans: 50% (karta orqali)\n"
        f"📞 Savol: {TELEFON}"
    )
    keyboard = [[InlineKeyboardButton("📅 Bron qilish", callback_data="bron"),
                 InlineKeyboardButton("🏠 Bosh menyu", callback_data="bosh")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ===================== ALOQA =====================

async def aloqa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        f"📞 *Aloqa*\n\n"
        f"📱 Telefon: {TELEFON}\n"
        f"🏟 Stadion: {STADION_NOMI}\n"
        f"📍 Joylashuv: Tuman markazi\n"
        f"🕐 Ish vaqti: 09:00 – 02:00"
    )
    keyboard = [[InlineKeyboardButton("🏠 Bosh menyu", callback_data="bosh")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ===================== BRON JARAYONI =====================

async def bron_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    # Bugun va keyingi 7 kun
    bugun = datetime.now().date()
    keyboard = []
    row = []
    for i in range(7):
        sana = bugun + timedelta(days=i)
        nomi = "Bugun" if i == 0 else ("Ertaga" if i == 1 else sana.strftime("%d-%b"))
        row.append(InlineKeyboardButton(nomi, callback_data=f"sana_{sana.strftime('%Y-%m-%d')}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="bosh")])

    await query.edit_message_text(
        "📅 *Qaysi kunga bron qilmoqchisiz?*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SANA


async def sana_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sana_str = query.data.replace("sana_", "")
    context.user_data["sana"] = sana_str

    # Bo'sh soatlarni ko'rsatish
    band = band_soatlar(sana_str)
    keyboard = []
    row = []
    for soat in range(BOSHLANISH, TUGASH):
        soat_nomi = f"{soat % 24:02d}:00"
        if soat in band:
            btn = InlineKeyboardButton(f"🔴 {soat_nomi}", callback_data="band")
        else:
            btn = InlineKeyboardButton(f"✅ {soat_nomi}", callback_data=f"soat_{soat}")
        row.append(btn)
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="bron"),
                     InlineKeyboardButton("❌ Bekor", callback_data="bosh")])

    await query.edit_message_text(
        f"🕐 *{sana_str} — soat tanlang:*\n\n✅ Bo'sh  |  🔴 Band",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return VAQT


async def vaqt_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "band":
        await query.answer("Bu soat band! Boshqa soat tanlang.", show_alert=True)
        return VAQT

    soat = int(query.data.replace("soat_", ""))
    context.user_data["soat"] = soat
    sana_str = context.user_data["sana"]

    # Davomiylik tanlash
    band = band_soatlar(sana_str)
    keyboard = []
    row = []
    max_davom = 1
    for i in range(1, 5):  # max 4 soat
        if soat + i > TUGASH:
            break
        if any(soat + j in band for j in range(i)):
            break
        max_davom = i
    
    for i in range(1, max_davom + 1):
        narx = narx_hisob(soat, i)
        row.append(InlineKeyboardButton(f"{i} soat — {narx:,}", callback_data=f"davom_{i}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=f"sana_{sana_str}"),
                     InlineKeyboardButton("❌ Bekor", callback_data="bosh")])

    await query.edit_message_text(
        f"⏱ *Necha soat o'ynaysiz?*\n\nBoshlanish: {soat:02d}:00",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return DAVOMIYLIK


async def davomiylik_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    davom = int(query.data.replace("davom_", ""))
    context.user_data["davomiylik"] = davom

    soat = context.user_data["soat"]
    sana = context.user_data["sana"]
    narx = narx_hisob(soat, davom)
    avans = narx // 2
    context.user_data["narx"] = narx
    context.user_data["avans"] = avans

    keyboard = [
        [InlineKeyboardButton("💳 Avans to'lash (50%)", callback_data="tollov_avans")],
        [InlineKeyboardButton("🤝 To'lovsiz bron", callback_data="tollov_yoq")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="bosh")]
    ]

    await query.edit_message_text(
        f"📋 *Bron ma'lumotlari:*\n\n"
        f"📅 Sana: {sana}\n"
        f"🕐 Soat: {soat:02d}:00 – {soat+davom:02d}:00\n"
        f"⏱ Davomiylik: {davom} soat\n"
        f"💰 Jami narx: *{narx:,} so'm*\n"
        f"💳 Avans (50%): *{avans:,} so'm*\n\n"
        f"To'lov turini tanlang:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return TOLLOV


async def tollov_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tollov_turi = query.data

    if tollov_turi == "tollov_avans":
        avans = context.user_data["avans"]
        keyboard = [
            [InlineKeyboardButton("✅ To'lovni amalga oshirdim", callback_data="chek_yuborish")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="bosh")]
        ]
        await query.edit_message_text(
            f"💳 *To'lov ma'lumotlari:*\n\n"
            f"💰 To'lov miqdori: *{avans:,} so'm*\n"
            f"💳 Karta raqami: `{KARTA_RAQAM}`\n\n"
            f"⚠️ To'lovni amalga oshirgach, *chek rasmini* yuboring yoki tugmani bosing.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["tollov"] = "avans"
        return CHEK
    else:
        context.user_data["tollov"] = "yoq"
        return await bron_saqlash(update, context)


async def chek_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rasm yoki tugma orqali chek qabul qilish"""
    if update.message and update.message.photo:
        context.user_data["chek_file_id"] = update.message.photo[-1].file_id
    return await bron_saqlash_message(update, context)


async def chek_tasdiqlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await bron_saqlash(update, context)


async def bron_saqlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    return await _saqlash(query=query, user=user, context=context)


async def bron_saqlash_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    return await _saqlash(message=update.message, user=user, context=context)


async def _saqlash(context, user, query=None, message=None):
    d = context.user_data
    sana = d["sana"]
    soat = d["soat"]
    davom = d["davomiylik"]
    narx = d["narx"]
    avans = d["avans"]
    tollov = d["tollov"]

    # Bronni saqlash
    if sana not in bronlar:
        bronlar[sana] = []
    bron_id = f"{sana}_{soat}_{user.id}"
    bronlar[sana].append((soat, davom, user.id, user.full_name, tollov, bron_id))

    # Foydalanuvchiga xabar
    tollov_text = f"💳 Avans: {avans:,} so'm to'landi" if tollov == "avans" else "🤝 To'lovsiz bron (joyda to'lanadi)"
    text = (
        f"✅ *Bron tasdiqlandi!*\n\n"
        f"📅 Sana: {sana}\n"
        f"🕐 Soat: {soat % 24:02d}:00 – {(soat+davom) % 24:02d}:00\n"
        f"💰 Jami: {narx:,} so'm\n"
        f"{tollov_text}\n\n"
        f"📞 Savol: {TELEFON}\n"
        f"⚽ O'yningiz xayrli bo'lsin!"
    )
    keyboard = [[InlineKeyboardButton("🏠 Bosh menyu", callback_data="bosh")]]

    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    # Adminga xabar yuborish
    admin_text = (
        f"🔔 *Yangi bron!*\n\n"
        f"👤 Mijoz: {user.full_name}\n"
        f"🆔 ID: {user.id}\n"
        f"📅 Sana: {sana}\n"
        f"🕐 Soat: {soat % 24:02d}:00 – {(soat+davom) % 24:02d}:00\n"
        f"💰 Narx: {narx:,} so'm\n"
        f"💳 To'lov: {'Avans '+str(avans)+' so\'m' if tollov == 'avans' else 'To\'lovsiz'}"
    )
    admin_keyboard = [[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_ok_{bron_id}"),
                       InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_rad_{bron_id}")]]

    try:
        if d.get("chek_file_id"):
            await context.bot.send_photo(
                ADMIN_ID, d["chek_file_id"],
                caption=admin_text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(admin_keyboard)
            )
        else:
            await context.bot.send_message(
                ADMIN_ID, admin_text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(admin_keyboard)
            )
    except Exception as e:
        logger.error(f"Admin xabar xatosi: {e}")

    context.user_data.clear()
    return ConversationHandler.END


# ===================== MENING BRONLARIM =====================

async def mening_bronlarim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    topildi = []
    for sana, sana_bronlar in bronlar.items():
        for bron in sana_bronlar:
            soat, davom, uid, ism, tollov, bid = bron
            if uid == user_id:
                topildi.append((sana, soat, davom, tollov))

    if not topildi:
        text = "📋 Sizda hech qanday bron yo'q.\n\n📅 Yangi bron qilish uchun tugmani bosing."
    else:
        text = "📋 *Sizning bronlaringiz:*\n\n"
        for sana, soat, davom, tollov in topildi:
            emoji = "💳" if tollov == "avans" else "🤝"
            text += f"📅 {sana} | 🕐 {soat:02d}:00–{soat+davom:02d}:00 {emoji}\n"

    keyboard = [[InlineKeyboardButton("📅 Yangi bron", callback_data="bron"),
                 InlineKeyboardButton("🏠 Bosh menyu", callback_data="bosh")]]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ===================== ADMIN PANEL =====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    action = query.data

    if action == "admin_bronlar":
        if not bronlar:
            text = "📋 Hozircha hech qanday bron yo'q."
        else:
            text = "📋 *Barcha bronlar:*\n\n"
            for sana, sana_bronlar in sorted(bronlar.items()):
                text += f"📅 *{sana}:*\n"
                for bron in sana_bronlar:
                    soat, davom, uid, ism, tollov, _ = bron
                    t = "💳Avans" if tollov == "avans" else "🤝Joyi"
                    text += f"  🕐 {soat:02d}:00–{soat+davom:02d}:00 | {ism} | {t}\n"
                text += "\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin menyu", callback_data="admin_menu")]]))

    elif action == "admin_bugun":
        bugun = datetime.now().date().strftime("%Y-%m-%d")
        text = f"📅 *Bugungi jadval ({bugun}):*\n\n"
        band = bronlar.get(bugun, [])
        if not band:
            text += "Bugun hech qanday bron yo'q."
        else:
            for bron in sorted(band, key=lambda x: x[0]):
                soat, davom, uid, ism, tollov, _ = bron
                t = "💳" if tollov == "avans" else "🤝"
                text += f"🕐 {soat % 24:02d}:00 – {(soat+davom) % 24:02d}:00 | {ism} {t}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin menyu", callback_data="admin_menu")]]))

    elif action == "admin_stat":
        jami_bron = sum(len(v) for v in bronlar.values())
        jami_daromad = 0
        for sana_bronlar in bronlar.values():
            for bron in sana_bronlar:
                soat, davom, *_ = bron
                jami_daromad += narx_hisob(soat, davom)
        text = (
            f"📊 *Statistika:*\n\n"
            f"📋 Jami bronlar: {jami_bron} ta\n"
            f"💰 Kutilgan daromad: {jami_daromad:,} so'm\n"
            f"📅 Ish kunlari: {len(bronlar)} kun"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Admin menyu", callback_data="admin_menu")]]))

    elif action == "admin_menu":
        await query.edit_message_text(
            f"👋 Admin paneli — *{STADION_NOMI}*",
            parse_mode="Markdown",
            reply_markup=admin_menu()
        )


async def admin_ok_rad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    data = query.data
    if data.startswith("admin_ok_"):
        bron_id = data.replace("admin_ok_", "")
        await query.edit_message_reply_markup(None)
        await query.message.reply_text(f"✅ Bron tasdiqlandi: `{bron_id}`", parse_mode="Markdown")
    elif data.startswith("admin_rad_"):
        bron_id = data.replace("admin_rad_", "")
        # Bronni o'chirish
        parts = bron_id.split("_")
        if len(parts) >= 2:
            sana = parts[0]
            if sana in bronlar:
                bronlar[sana] = [b for b in bronlar[sana] if b[5] != bron_id]
        await query.edit_message_reply_markup(None)
        await query.message.reply_text(f"❌ Bron rad etildi va o'chirildi: `{bron_id}`", parse_mode="Markdown")


async def bosh_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    user = query.from_user

    if user.id == ADMIN_ID:
        await query.edit_message_text(
            f"👋 Admin paneli — *{STADION_NOMI}*",
            parse_mode="Markdown",
            reply_markup=admin_menu()
        )
    else:
        await query.edit_message_text(
            f"⚽ *{STADION_NOMI}*\n\nQuyidagilardan birini tanlang:",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    return ConversationHandler.END


# ===================== ASOSIY =====================

def main():
    app = Application.builder().token(TOKEN).build()

    bron_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(bron_boshlash, pattern="^bron$")],
        states={
            SANA: [CallbackQueryHandler(sana_tanlash, pattern="^sana_")],
            VAQT: [CallbackQueryHandler(vaqt_tanlash, pattern="^(soat_|band)"),
                   CallbackQueryHandler(bron_boshlash, pattern="^bron$")],
            DAVOMIYLIK: [CallbackQueryHandler(davomiylik_tanlash, pattern="^davom_")],
            TOLLOV: [CallbackQueryHandler(tollov_tanlash, pattern="^tollov_")],
            CHEK: [
                CallbackQueryHandler(chek_tasdiqlash, pattern="^chek_yuborish$"),
                MessageHandler(filters.PHOTO, chek_qabul)
            ],
        },
        fallbacks=[CallbackQueryHandler(bosh_menu, pattern="^bosh$")],
        per_user=True,
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(bron_conv)
    app.add_handler(CallbackQueryHandler(narxlar_korsatish, pattern="^narxlar$"))
    app.add_handler(CallbackQueryHandler(aloqa, pattern="^aloqa$"))
    app.add_handler(CallbackQueryHandler(mening_bronlarim, pattern="^mening_bronlarim$"))
    app.add_handler(CallbackQueryHandler(bosh_menu, pattern="^bosh$"))
    app.add_handler(CallbackQueryHandler(admin_ok_rad, pattern="^admin_(ok|rad)_"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_"))

    print("✅ Bot ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()
