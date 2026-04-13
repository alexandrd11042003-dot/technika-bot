import logging
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = "8692133423:AAFT75V7re4VB2Or_-Z2HSgOP8vFLUG9pHU"
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1OhZlZlGj9A-o8CxwqvpUVRFqvFM6mfNtpZf0C75f4rY/edit"
CREDS_FILE = "creds.json"

# ========== ТЕХНИКА ==========
EQUIPMENT = [
    "Экскаватор №1", "Экскаватор №2", "Экскаватор №3", "Экскаватор №4", "Экскаватор №5",
    "Кран №1", "Кран №2",
    "Фронт. погрузчик №1", "Фронт. погрузчик №2",
    "Телеск. погрузчик №1", "Телеск. погрузчик №2", "Телеск. погрузчик №3",
    "Минипогрузчик №1", "Минипогрузчик №2", "Минипогрузчик №3", "Минипогрузчик №4",
    "Каток", "МТЗ", "Газель", "Ситроен"
]

# ========== СОСТОЯНИЯ ==========
CHOOSE_ACTION, CHOOSE_EQUIPMENT, ENTER_LOCATION, ENTER_PROBLEM, ENTER_WORK, ENTER_PARTS, ENTER_COST, ENTER_HOURS, ENTER_NOTE = range(9)
FUEL_EQUIPMENT, FUEL_LOCATION, FUEL_TYPE, FUEL_LITERS, FUEL_PRICE, FUEL_HOURS = range(10, 16)

logging.basicConfig(level=logging.INFO)

# ========== GOOGLE SHEETS ==========
def get_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(SPREADSHEET_URL)
    return spreadsheet.worksheet(sheet_name)

def add_repair(data):
    sheet = get_sheet("Журнал работ")
    row = [
        data["date"], data["equipment"], data["location"],
        data["problem"], data["work"], data["parts"],
        data["cost"], data["hours"], "Александр", data["note"]
    ]
    sheet.append_row(row)

def add_fuel(data):
    sheet = get_sheet("Учёт топлива")
    row = [
        data["date"], data["equipment"], data["location"],
        data["fuel_type"], data["liters"], data["price"],
        "", data["hours"], ""
    ]
    sheet.append_row(row)

# ========== КЛАВИАТУРЫ ==========
def equipment_keyboard():
    rows = []
    for i in range(0, len(EQUIPMENT), 2):
        row = EQUIPMENT[i:i+2]
        rows.append(row)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def main_keyboard():
    return ReplyKeyboardMarkup([
        ["🔧 Ремонт / ТО", "⛽ Топливо"],
        ["📊 Отчёт за сегодня"]
    ], resize_keyboard=True)

def location_keyboard():
    return ReplyKeyboardMarkup([["База", "Объект №1", "Объект №2", "Объект №3"]], resize_keyboard=True)

def skip_keyboard():
    return ReplyKeyboardMarkup([["Пропустить"]], resize_keyboard=True)

# ========== СТАРТ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет, Александр!\n\nЯ помогу вести учёт техники на базе.\nВыбери что хочешь записать:",
        reply_markup=main_keyboard()
    )
    return CHOOSE_ACTION

# ========== РЕМОНТ ==========
async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🔧 Ремонт / ТО":
        await update.message.reply_text("Выбери технику:", reply_markup=equipment_keyboard())
        context.user_data["type"] = "repair"
        return CHOOSE_EQUIPMENT
    elif text == "⛽ Топливо":
        await update.message.reply_text("Выбери технику:", reply_markup=equipment_keyboard())
        context.user_data["type"] = "fuel"
        return FUEL_EQUIPMENT
    elif text == "📊 Отчёт за сегодня":
        await show_today(update, context)
        return CHOOSE_ACTION

async def choose_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["equipment"] = update.message.text
    await update.message.reply_text("Где находится техника?", reply_markup=location_keyboard())
    return ENTER_LOCATION

async def enter_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["location"] = update.message.text
    await update.message.reply_text("Что сломалось? Опиши неисправность:", reply_markup=ReplyKeyboardRemove())
    return ENTER_PROBLEM

async def enter_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["problem"] = update.message.text
    await update.message.reply_text("Что сделали? Опиши выполненные работы:")
    return ENTER_WORK

async def enter_work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["work"] = update.message.text
    await update.message.reply_text("Какие запчасти использовали?", reply_markup=skip_keyboard())
    return ENTER_PARTS

async def enter_parts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["parts"] = "" if update.message.text == "Пропустить" else update.message.text
    await update.message.reply_text("Сколько потратили на запчасти? (руб, только цифры)", reply_markup=skip_keyboard())
    return ENTER_COST

async def enter_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["cost"] = "" if text == "Пропустить" else text.replace(" ", "").replace("р", "").replace("₽", "")
    await update.message.reply_text("Сколько часов отработала техника?", reply_markup=skip_keyboard())
    return ENTER_HOURS

async def enter_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["hours"] = "" if text == "Пропустить" else text
    await update.message.reply_text("Примечание (или нажми Пропустить):", reply_markup=skip_keyboard())
    return ENTER_NOTE

async def enter_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["note"] = "" if text == "Пропустить" else text
    context.user_data["date"] = datetime.now().strftime("%d.%m.%Y")

    try:
        add_repair(context.user_data)
        d = context.user_data
        await update.message.reply_text(
            f"✅ Записано в таблицу!\n\n"
            f"📅 {d['date']}\n"
            f"🚜 {d['equipment']} — {d['location']}\n"
            f"❌ Проблема: {d['problem']}\n"
            f"✅ Что сделали: {d['work']}\n"
            f"🔩 Запчасти: {d['parts'] or '—'}\n"
            f"💰 Стоимость: {d['cost'] or '—'} руб\n"
            f"⏱ Часы: {d['hours'] or '—'}",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка записи: {e}", reply_markup=main_keyboard())

    context.user_data.clear()
    return CHOOSE_ACTION

# ========== ТОПЛИВО ==========
async def fuel_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["equipment"] = update.message.text
    await update.message.reply_text("Где заправляли?", reply_markup=location_keyboard())
    return FUEL_LOCATION

async def fuel_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["location"] = update.message.text
    await update.message.reply_text("Вид топлива:", reply_markup=ReplyKeyboardMarkup([["Дизель", "Бензин", "Газ"]], resize_keyboard=True))
    return FUEL_TYPE

async def fuel_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["fuel_type"] = update.message.text
    await update.message.reply_text("Сколько литров заправили?", reply_markup=ReplyKeyboardRemove())
    return FUEL_LITERS

async def fuel_liters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["liters"] = update.message.text
    await update.message.reply_text("Цена за литр (руб):", reply_markup=skip_keyboard())
    return FUEL_PRICE

async def fuel_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["price"] = "" if text == "Пропустить" else text
    await update.message.reply_text("Показания счётчика / часов:", reply_markup=skip_keyboard())
    return FUEL_HOURS

async def fuel_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["hours"] = "" if text == "Пропустить" else text
    context.user_data["date"] = datetime.now().strftime("%d.%m.%Y")

    try:
        add_fuel(context.user_data)
        d = context.user_data
        liters = float(d["liters"]) if d["liters"] else 0
        price = float(d["price"]) if d["price"] else 0
        total = liters * price
        await update.message.reply_text(
            f"✅ Топливо записано!\n\n"
            f"📅 {d['date']}\n"
            f"🚜 {d['equipment']}\n"
            f"⛽ {d['fuel_type']}: {d['liters']} л\n"
            f"💰 {d['price'] or '—'} руб/л = {total:.0f} руб",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка записи: {e}", reply_markup=main_keyboard())

    context.user_data.clear()
    return CHOOSE_ACTION

# ========== ОТЧЁТ ==========
async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%d.%m.%Y")
    try:
        sheet = get_sheet("Журнал работ")
        records = sheet.get_all_values()
        today_records = [r for r in records[2:] if r and r[0] == today]

        if not today_records:
            await update.message.reply_text(f"📋 За сегодня ({today}) записей нет.", reply_markup=main_keyboard())
        else:
            text = f"📋 Записи за {today}:\n\n"
            total_cost = 0
            for r in today_records:
                text += f"🚜 {r[1]}\n❌ {r[3]}\n✅ {r[4]}\n💰 {r[6] or '—'} руб\n\n"
                try:
                    total_cost += float(r[6]) if r[6] else 0
                except:
                    pass
            text += f"💰 Итого затрат: {total_cost:.0f} руб"
            await update.message.reply_text(text, reply_markup=main_keyboard())
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}", reply_markup=main_keyboard())

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=main_keyboard())
    return CHOOSE_ACTION

# ========== ЗАПУСК ==========
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.TEXT & ~filters.COMMAND, choose_action)],
        states={
            CHOOSE_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_action)],
            CHOOSE_EQUIPMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_equipment)],
            ENTER_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_location)],
            ENTER_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_problem)],
            ENTER_WORK: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_work)],
            ENTER_PARTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_parts)],
            ENTER_COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_cost)],
            ENTER_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_hours)],
            ENTER_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_note)],
            FUEL_EQUIPMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, fuel_equipment)],
            FUEL_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, fuel_location)],
            FUEL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, fuel_type)],
            FUEL_LITERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, fuel_liters)],
            FUEL_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, fuel_price)],
            FUEL_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, fuel_hours)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
