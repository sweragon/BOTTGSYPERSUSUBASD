from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import requests

TOKEN = '7594465048:AAEqLZ5AUcT0UszShIE1W3PxdpSjZzQnqgY'
ADMIN_ID = 7595576719  # Замените на ваш Telegram ID
YOOMONEY_WALLET = '4100118963292219'
YOOMONEY_TOKEN = '1A5DD0EBF5CA1773F43BE694D31FB4670EACA80B06EB40CD4562D849A1A9DCCD4E3DC6282922E61826B71ED3219C904554467C0F91222760AB939AAD75F11F79'

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class OrderStars(StatesGroup):
    waiting_for_name = State()
    waiting_for_quantity = State()
    waiting_for_payment = State()

# Клавиатура
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton("💳 Купить звёзды"), KeyboardButton("🎁 Купить подарок"))
main_menu.add(KeyboardButton("💬 Отзывы"), KeyboardButton("🧑‍💻 Написать в поддержку"))
main_menu.add(KeyboardButton("💵 Прайс звёзды"), KeyboardButton("💵 Прайс подарки"))
main_menu.add(KeyboardButton("📄 Документы"))

admin_menu = ReplyKeyboardMarkup(resize_keyboard=True)
admin_menu.add(KeyboardButton("📋 Все заявки"), KeyboardButton("✅ Подтвердить заявку"))
admin_menu.add(KeyboardButton("❌ Отклонить заявку"))

orders = {}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Привет, Админ!", reply_markup=admin_menu)
    else:
        await message.answer("Привет! Добро пожаловать в магазин звёзд. Выберите действие ниже:", reply_markup=main_menu)

@dp.message_handler(lambda message: message.text == "💳 Купить звёзды")
async def buy_stars(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Оформить заявку", callback_data="order_stars"))
    await message.answer("Чтобы купить звёзды, нажмите кнопку ниже:", reply_markup=keyboard)

@dp.callback_query_handler(lambda call: call.data == "order_stars")
async def order_stars(call: types.CallbackQuery):
    await call.message.answer("Введите ваше имя для оформления заявки:")
    await OrderStars.waiting_for_name.set()
    await call.answer()

@dp.message_handler(state=OrderStars.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько звёзд вы хотите купить?")
    await OrderStars.waiting_for_quantity.set()

@dp.message_handler(state=OrderStars.waiting_for_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число!")
        return
    if int(message.text) < 50:
        await message.answer("Минимальное количество звёзд для покупки — 50!")
        return
    await state.update_data(quantity=message.text)
    user_data = await state.get_data()
    payment_link = f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YOOMONEY_WALLET}&sum={int(message.text)}&paymentType=AC&label={message.chat.id}"
    await message.answer(f"Оплатите по ссылке: {payment_link}\nПосле оплаты отправьте скриншот.")
    await OrderStars.waiting_for_payment.set()

async def check_payment(label):
    headers = {"Authorization": f"Bearer {YOOMONEY_TOKEN}"}
    response = requests.get("https://yoomoney.ru/api/operation-history", headers=headers, params={"label": label, "records": 1})
    if response.status_code == 200:
        operations = response.json().get("operations", [])
        if operations:
            return True
    return False

@dp.message_handler(state=OrderStars.waiting_for_payment, content_types=types.ContentType.PHOTO)
async def process_payment(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    name = user_data['name']
    quantity = user_data['quantity']
    username = message.from_user.username if message.from_user.username else 'Не указан'
    label = str(message.chat.id)
    if await check_payment(label):
        orders[message.chat.id] = {'name': name, 'quantity': quantity}
        await bot.send_message(ADMIN_ID, f"🚨 Новая заявка!\nИмя: {name}\nКоличество звёзд: {quantity}\nОт пользователя: @{username}")
        await message.answer("✅ Заявка оформлена! Мы свяжемся с вами в ближайшее время.")
        await state.finish()
    else:
        await message.answer("❌ Оплата не найдена. Проверьте правильность оплаты или подождите пару минут.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
