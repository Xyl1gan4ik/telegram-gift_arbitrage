import nest_asyncio
nest_asyncio.apply()

import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import json
import curl_cffi # Импортируем curl_cffi

# --- Конфигурация Telegram Бота ---
# ЗАМЕНИТЕ ЭТО: Токен вашего Telegram бота, полученный от @BotFather
TELEGRAM_BOT_TOKEN = '7478514610:AAGxgAcectD6dLG0JBluiSAmBYoe99-FqgQ'
# ЗАМЕНИТЕ ЭТО: Ваш ID чата для тестирования.
# Можно получить, отправив сообщение боту @userinfobot и посмотрев 'id'.
TELEGRAM_USER_ID = 1291677325 

DEFAULT_INTERVAL = 30 # Интервал проверки аукционов по умолчанию (в секундах)
DEFAULT_MIN_PROFIT = 5 # Минимальный процент прибыли по умолчанию

# ⚙️ Настройки логирования
# Настраиваем логирование для вывода информации о работе бота в консоль
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 🔧 Настройки пользователя
# Словарь для хранения настроек каждого пользователя бота.
# По умолчанию содержит настройки для одного пользователя (TELEGRAM_USER_ID).
user_settings = {
    TELEGRAM_USER_ID: {
        'min_profit': DEFAULT_MIN_PROFIT,
        'interval': DEFAULT_INTERVAL,
        'price_range': (5, 25), # Диапазон цен для ставок (от, до)
        'active': False, # Флаг активности бота для пользователя
        'notified_ids': set() # Множество ID подарков, о которых уже было уведомлено
    }
}

# Функция escape_markdown_v2 теперь не нужна для форматирования сообщений,
# но оставим её заглушкой, если где-то есть вызовы, которые могли бы сломаться.
# По сути, она теперь просто возвращает текст без изменений.
def escape_markdown_v2(text):
    """
    Возвращает текст без изменений, так как MarkdownV2 форматирование отключено.
    """
    if text is None:
        return 'N/A'
    return str(text)

# 🔑 Авторизационные данные
# ВНИМАНИЕ: Этот токен AUTH_DATA крайне чувствителен и, скорее всего, временный.
# Для стабильной работы бота его нужно регулярно обновлять из сетевых запросов в DevTools браузера.
# Ищите запрос, содержащий "authData" в теле или заголовках.
AUTH_DATA = "user=%7B%22id%22%3A1291677325%2C%22first_name%22%3A%22%D0%94%D0%B8%D0%BC%D0%B0%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22otcseller132%22%2C%22language_code%22%3A%22ru%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2Fi_6TgYWBnuSgDGilK8pmZuIUf-kC7SV2VP9GETs7WwU.svg%22%7D&chat_instance=8370872738174365064&chat_type=sender&auth_date=1751722177&signature=duBioXksZJiZTCpo8piGJBK-EnxXMLqrFen58V3fS7voQWEwiBXM_vq73hLr0NZheuWbjhYi7B4WUR_asIl6BA&hash=5f61305b56acfda600e24c57668110ea80a3ece4a25be79e2189527b3d06f011"

# Инициализируем сессию curl_cffi с имитацией Chrome
# Используем одну сессию для всех запросов к API, чтобы имитировать поведение реального браузера
# и потенциально сохранять куки или другие состояния сессии.
session = curl_cffi.Session(impersonate="chrome131")

def get_floor_price(name, model):
    """
    Получает минимальную (floor) цену для конкретного подарка (по имени и модели)
    с помощью API gifts3.tonnel.network/api/filterStats.
    """
    key = f"{name}_{model}"
    try:
        # Ключ в payload должен быть "authData", как показано на скриншотах
        payload = {
            "authData": AUTH_DATA # Отправляем AUTH_DATA как строку
        }

        # Отправляем POST-запрос с помощью curl_cffi session
        res = session.post(
            "https://gifts3.tonnel.network/api/filterStats",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://market.tonnel.network/",
                "Content-Type": "application/json", # Важно: указываем JSON тип контента
                "Origin": "https://market.tonnel.network",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
                "Sec-GPC": "1",
                "Priority": "u=4",
            },
            json=payload, # Отправляем данные как JSON
            timeout=10, # Таймаут для запроса
            verify=False # ВНИМАНИЕ: Отключение проверки SSL-сертификата не рекомендуется в продакшене!
        )

        # Проверяем статус код HTTP ответа
        if res.status_code != 200:
            logger.error("[ERROR] floorPrice: HTTP %s - %s", res.status_code, res.text)
            return None

        # Пробуем декодировать ответ как JSON
        try:
            data = res.json()
        except json.JSONDecodeError:
            logger.warning("[WARN] floorPrice: Не удалось декодировать JSON из ответа:\n%s", res.text[:500])
            return None

        # Ожидаем, что ответ будет словарем с ключом 'data',
        # и внутри него статистика по ключам вида "ИмяПодарка_МодельПодарка"
        # Пример ожидаемой структуры: {"data": {"GiftName_ModelName": {"floorPrice": 123.45, ...}}}
        floor_data = data.get("data", {})
        return floor_data.get(key, {}).get("floorPrice")

    except Exception as e:
        logger.error("[ERROR] Ошибка при получении floor price для %s_%s: %s", name, model, e)
        return None

async def check_auctions(app):
    """
    Асинхронная функция для периодической проверки активных аукционов.
    Выполняется в фоновом режиме.
    """
    while True:
        # Перебираем настройки каждого пользователя бота
        for user_id, settings in user_settings.items():
            if not settings['active']: # Пропускаем, если бот для пользователя не активен
                continue

            try:
                # Формируем полезную нагрузку для запроса к API pageGifts
                payload = {
                    "page": 1,
                    "limit": 30, # Получаем 30 последних активных аукционов
                    "sort": '{"auctionEndTime":1,"gift_id":-1}', # Сортировка по времени окончания аукциона
                    "filter": '{"auction_id":{"$exists":true},"status":"active","asset":"TON"}', # Фильтр для активных TON-аукционов
                    "price_range": None, # Оставляем None, чтобы получить все активные аукционы, а фильтровать по цене позже
                    "ref": 0,
                    "user_auth": AUTH_DATA # Используем AUTH_DATA как строку
                }

                # Отправляем POST-запрос с помощью curl_cffi session
                res = session.post(
                    "https://gifts3.tonnel.network/api/pageGifts",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0",
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Referer": "https://market.tonnel.network/",
                        "Content-Type": "application/json",
                        "Origin": "https://market.tonnel.network",
                        "Connection": "keep-alive",
                        "Sec-Fetch-Dest": "empty",
                        "Sec-Fetch-Mode": "cors",
                        "Sec-Fetch-Site": "cross-site",
                        "Sec-GPC": "1",
                        "Priority": "u=4",
                    },
                    json=payload,
                    timeout=10,
                    verify=False # ВНИМАНИЕ: Отключение проверки SSL-сертификата не рекомендуется в продакшене!
                )

                # Проверяем статус код HTTP ответа
                if res.status_code != 200:
                    logger.error("[ERROR] check_auctions: HTTP %s - %s", res.status_code, res.text)
                    continue # Переходим к следующему пользователю или итерации, если ошибка

                # Пробуем декодировать ответ как JSON
                try:
                    data = res.json()
                except json.JSONDecodeError:
                    logger.warning("[WARN] check_auctions: Не удалось декодировать JSON из ответа:\n%s", res.text[:500])
                    continue

                # API pageGifts может возвращать список напрямую или словарь с ключом 'auctions'
                auctions = data if isinstance(data, list) else data.get('auctions', [])
                logger.info("\U0001F50D Найдено активных аукционов: %d", len(auctions))

                # Перебираем найденные аукционы
                for gift in auctions:
                    gift_id = gift.get('gift_id')
                    if gift_id is None:
                        logger.warning("Объект подарка без gift_id: %s", gift)
                        continue # Пропускаем, если нет уникального ID подарка

                    # Пропускаем подарки, о которых уже было уведомлено
                    if gift_id in settings['notified_ids']:
                        continue

                    # Извлечение данных о подарке
                    name = gift.get('name', 'N/A')
                    model = gift.get('model', 'N/A')
                    backdrop = gift.get('backdrop', 'N/A') # Фон
                    auction_data = gift.get('auction', {})
                    bid_history = auction_data.get('bidHistory', [])
                    
                    # Получаем текущую ставку (последнюю в истории или стартовую)
                    bid = float(bid_history[-1]['amount']) if bid_history else float(auction_data.get('startingBid', 0))
                    
                    # Форматируем время окончания аукциона
                    end_time_raw = auction_data.get('auctionEndTime', '')
                    end_time = end_time_raw[:19].replace('T',' ') if end_time_raw else 'N/A'
                    
                    # Используем gift_id в качестве gift_num, если gift_num отсутствует
                    gift_num = gift.get('gift_num', gift.get('gift_id', 'N/A')) 

                    # Проверяем, находится ли текущая ставка в заданном диапазоне цен пользователя
                    if not (settings['price_range'][0] <= bid <= settings['price_range'][1]):
                        logger.debug("Аукцион %s (ставка %.2f) вне диапазона цен %s для пользователя %s", 
                                     gift_id, bid, settings['price_range'], user_id)
                        continue

                    # Получаем "floor price" (минимальную цену) для расчета потенциальной прибыли
                    min_price = get_floor_price(name, model)
                    if min_price is None:
                        logger.warning("Не удалось получить floor price для %s_%s. Пропускаем подарок %s.", name, model, gift_id)
                        continue

                    # Расчет потенциальной прибыли
                    total_cost = bid * 1.1 # Предполагается комиссия 10% или дополнительные расходы
                    profit = min_price - total_cost
                    percent = (profit / total_cost) * 100 if total_cost > 0 else -100 # Избегаем деления на ноль

                    # Проверяем, соответствует ли процент прибыли минимальному, установленному пользователем
                    if percent < settings['min_profit']:
                        logger.debug("Аукцион %s (прибыль %.1f%%) ниже минимальной прибыли %d%% для пользователя %s", 
                                     gift_id, percent, settings['min_profit'], user_id)
                        continue

                    # Формирование прямой ссылки на подарок в Telegram (для мини-приложения)
                    # Теперь это будет обычная URL-строка, без Markdown-форматирования
                    gift_link = f"https://t.me/tonnel_network_bot/gift?startapp={gift_num}" if gift_num != 'N/A' else 'Ссылка недоступна'

                    # Формирование сообщения для Telegram в формате обычного текста (без MarkdownV2)
                    message = (
                        f"🎁Название: {name}\n" 
                        f"Модель: {model}\n"
                        f"Фон: {backdrop}\n"
                        f"⏳Заканчивается: {end_time}\n" 
                        f"💰Ставка: {bid:.2f} TON\n" 
                        f"Tonnel Floor: {min_price:.2f} TON\n" 
                        f"💵Прибыль: +{percent:.1f}% ({profit:.2f} TON)\n" 
                        f"🔗Прямая ссылка: {gift_link}" # Просто вставляем ссылку как текст
                    )
                    
                    # Отправляем сообщение пользователю без указания parse_mode
                    # Это означает, что будет использоваться режим "Plain Text"
                    await app.bot.send_message(chat_id=user_id, text=message) # ИЗМЕНЕНО: parse_mode удален
                    logger.info("Отправлено уведомление о подарке %s (прибыль %.1f%%) пользователю %s", gift_id, percent, user_id)
                    # Добавляем ID подарка в список уведомленных, чтобы не отправлять повторно
                    settings['notified_ids'].add(gift_id)

            except Exception as e:
                logger.error("[ERROR] Общая ошибка в check_auctions для пользователя %s: %s", user_id, e)

        # Ждем установленный пользователем интервал перед следующей проверкой
        await asyncio.sleep(settings.get('interval', DEFAULT_INTERVAL)) 

# --- Команды Telegram ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start. Активирует бота для пользователя.
    """
    user_id = update.effective_user.id
    # Инициализируем настройки для нового пользователя, если их нет
    if user_id not in user_settings:
        user_settings[user_id] = {
            'min_profit': DEFAULT_MIN_PROFIT,
            'interval': DEFAULT_INTERVAL,
            'price_range': (5, 25),
            'active': False,
            'notified_ids': set()
        }
    user_settings[user_id]['active'] = True
    # ИЗМЕНЕНО: Сообщение без MarkdownV2
    await update.message.reply_text("Бот запущен. Поиск арбитража каждые 30 сек...")
    logger.info("Бот запущен для пользователя %s", user_id)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /stop. Деактивирует бота для пользователя и очищает список уведомленных ID.
    """
    user_id = update.effective_user.id
    if user_id in user_settings:
        user_settings[user_id]['active'] = False
        user_settings[user_id]['notified_ids'].clear() # Очищаем список уведомленных ID при остановке
    # ИЗМЕНЕНО: Сообщение без MarkdownV2
    await update.message.reply_text("Уведомления остановлены.")
    logger.info("Бот остановлен для пользователя %s", user_id)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /settings. Показывает текущие настройки пользователя.
    """
    user_id = update.effective_user.id
    current_settings = user_settings.get(user_id, {
        'min_profit': DEFAULT_MIN_PROFIT,
        'interval': DEFAULT_INTERVAL,
        'price_range': (5, 25),
        'active': False
    })
    status = "активен" if current_settings['active'] else "остановлен"
    message = (
        f"Текущие настройки:\n"
        f"Статус: {status}\n"
        f"Интервал проверки: {current_settings['interval']} секунд\n"
        f"Минимальная прибыль: {current_settings['min_profit']}%\n"
        f"Диапазон ставок: от {current_settings['price_range'][0]} до {current_settings['price_range'][1]} TON\n\n"
        f"Для изменения настроек используйте:\n"
        f"/setprofit <процент>\n"
        f"/setinterval <секунды>\n"
        f"/setpricerange <мин_тон> <макс_тон>"
    )
    # ИЗМЕНЕНО: parse_mode удален
    await update.message.reply_text(message)
    logger.info("Настройки запрошены пользователем %s", user_id)

async def set_profit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /setprofit. Устанавливает минимальный процент прибыли.
    """
    user_id = update.effective_user.id
    if not context.args or not context.args[0].isdigit():
        # ИЗМЕНЕНО: Сообщение без MarkdownV2
        await update.message.reply_text("Пожалуйста, укажите процент прибыли. Пример: /setprofit 7")
        return
    try:
        profit = int(context.args[0])
        if profit < 0:
            await update.message.reply_text("Процент прибыли не может быть отрицательным.")
            return
        user_settings[user_id]['min_profit'] = profit
        await update.message.reply_text(f"Минимальная прибыль установлена на {profit}%.")
        logger.info("Пользователь %s установил мин. прибыль: %d%%", user_id, profit)
    except ValueError:
        await update.message.reply_text("Неверный формат числа. Пожалуйста, введите целое число.")

async def set_interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /setinterval. Устанавливает интервал проверки аукционов.
    """
    user_id = update.effective_user.id
    if not context.args or not context.args[0].isdigit():
        # ИЗМЕНЕНО: Сообщение без MarkdownV2
        await update.message.reply_text("Пожалуйста, укажите интервал в секундах. Пример: /setinterval 60")
        return
    try:
        interval = int(context.args[0])
        if interval < 5: # Устанавливаем минимальный интервал, чтобы не перегружать API
            await update.message.reply_text("Интервал не может быть меньше 5 секунд.")
            return
        user_settings[user_id]['interval'] = interval
        await update.message.reply_text(f"Интервал проверки установлен на {interval} секунд.")
        logger.info("Пользователь %s установил интервал: %d сек.", user_id, interval)
    except ValueError:
        await update.message.reply_text("Неверный формат числа. Пожалуйста, введите целое число.")

async def set_price_range_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /setpricerange. Устанавливает диапазон цен для ставок.
    """
    user_id = update.effective_user.id
    if len(context.args) != 2 or not all(arg.replace('.', '', 1).isdigit() for arg in context.args):
        # ИЗМЕНЕНО: Сообщение без MarkdownV2
        await update.message.reply_text("Пожалуйста, укажите минимальную и максимальную цену. Пример: /setpricerange 10 50")
        return
    try:
        min_price = float(context.args[0])
        max_price = float(context.args[1])
        if min_price < 0 or max_price < min_price:
            await update.message.reply_text("Неверный диапазон цен. Минимальная цена должна быть >= 0, а максимальная >= минимальной.")
            return
        user_settings[user_id]['price_range'] = (min_price, max_price)
        await update.message.reply_text(f"Диапазон цен установлен на от {min_price} до {max_price} TON.")
        logger.info("Пользователь %s установил диапазон цен: %.2f-%.2f TON", user_id, min_price, max_price)
    except ValueError:
        await update.message.reply_text("Неверный формат числа. Пожалуйста, введите числа.")


async def main():
    """
    Основная функция, запускающая Telegram-бота.
    """
    # Инициализируем Telegram-бота с помощью токена
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("setprofit", set_profit_command))
    app.add_handler(CommandHandler("setinterval", set_interval_command))
    app.add_handler(CommandHandler("setpricerange", set_price_range_command))

    # Создаем и запускаем фоновую задачу для проверки аукционов.
    # Она будет работать параллельно с обработчиком команд бота.
    asyncio.create_task(check_auctions(app))

    logger.info("Бот запущен и готов принимать команды...")
    # Запускаем опрос новых сообщений в Telegram
    await app.run_polling()

if __name__ == "__main__":
    # Запускаем основную функцию асинхронно
    asyncio.run(main())