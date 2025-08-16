import curl_cffi
import json
import requests # Импортируем библиотеку requests для отправки сообщений в Telegram Bot API

# --- Конфигурация Telegram Бота ---
# ЗАМЕНИТЕ ЭТО: Токен вашего Telegram бота, полученный от @BotFather
TELEGRAM_BOT_TOKEN = '7478514610:AAGxgAcectD6dLG0JBluiSAmBYoe99-FqgQ'
# ЗАМЕНИТЕ ЭТО: ID чата, куда бот будет отправлять сообщения
# (например, ваш личный ID чата, ID группы или канала)
TELEGRAM_CHAT_ID = '1291677325'

def escape_markdown_v2(text):
    """
    Экранирует специальные символы для форматирования MarkdownV2 в Telegram.
    """
    if text is None:
        return 'N/A'
    text = str(text) # Убедимся, что это строка
    # Полный список символов, которые нужно экранировать в MarkdownV2:
    # _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., !
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text

def send_telegram_message(chat_id, text):
    """
    Отправляет текстовое сообщение в указанный Telegram чат.
    Использует parse_mode='MarkdownV2' для форматирования.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Ошибка: Токен Telegram бота или ID чата не настроены. Сообщение не отправлено.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'MarkdownV2',
        'disable_web_page_preview': True # Отключаем предпросмотр ссылок в текстовых сообщениях
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() # Вызывает исключение для плохих ответов (4xx или 5xx)
        print("Текстовое сообщение успешно отправлено в Telegram.")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке текстового сообщения в Telegram: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Код состояния ответа Telegram: {e.response.status_code}")
            print(f"Текст ответа Telegram: {e.response.text}")

def send_telegram_photo(chat_id, photo_url, caption_text):
    """
    Отправляет фото с подписью в указанный Telegram чат.
    Подпись форматируется с помощью MarkdownV2.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Ошибка: Токен Telegram бота или ID чата не настроены. Фото не отправлено.")
        return
    if not photo_url:
        print("Ошибка: URL фотографии отсутствует. Фото не отправлено.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        'chat_id': chat_id,
        'photo': photo_url,
        'caption': caption_text,
        'parse_mode': 'MarkdownV2'
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Фото успешно отправлено в Telegram.")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке фото в Telegram: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Код состояния ответа Telegram: {e.response.status_code}")
            print(f"Текст ответа Telegram: {e.response.text}")

# --- Конфигурация API Подарков ---
headers = {
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
}

json_data = {
    "page": 1,
    "limit": 5,
    "sort": '{"message_post_time":-1,"gift_id":-1}',
    "filter": '{"price":{"$exists":true},"refunded":{"$ne":true},"buyer":{"$exists":false},"export_at":{"$exists":true},"asset":"TON"}',
    "ref": 0,
    "price_range": [143, 145],
    # ЗАМЕНИТЕ ЭТО: Ваш реальный токен user_auth из сетевого запроса на скриншоте
    "user_auth": "",
}

# Инициализируем сессию curl_cffi с имитацией Chrome
session = curl_cffi.Session(impersonate="chrome131")

try:
    print("Отправка запроса на получение подарков...")
    response = session.post(
        "https://gifts3.tonnel.network/api/pageGifts",
        headers=headers,
        json=json_data,
        verify=False  # ВНИМАНИЕ: Отключение проверки SSL-сертификата не рекомендуется для производственных сред!
    )

    response.raise_for_status() # Вызывает исключение для плохих ответов (4xx или 5xx)

    gifts_data = response.json()

    if gifts_data and isinstance(gifts_data, list):
        print(f"Получено {len(gifts_data)} подарков. Подготовка к отправке в Telegram...")
        for gift in gifts_data:
            # Извлечение необходимых полей из данных о подарке
            # Используем .get() с 'N/A' по умолчанию, чтобы избежать ошибок,
            # если поле отсутствует, и явно преобразуем в строку.
            name = gift.get('name', 'N/A')
            model = gift.get('model', 'N/A')
            symbol = gift.get('symbol', 'N/A')
            # Предполагаем, что поле для "backdrop" называется 'backdrop' или 'background_name'
            backdrop = gift.get('backdrop', gift.get('background_name', 'N/A'))
            gift_num = gift.get('gift_id', 'N/A')
            # Предполагаем, что поле для цены называется 'price' или 'current_price'
            price = gift.get('price', gift.get('price', 'N/A'))

            # Попытка найти URL изображения. Частые названия полей: 'image_url', 'preview_url', 'photo_url', 'cover_url'
            image_url = gift.get('https://nft.fragment.com/gift/', '')
            if not image_url:
                image_url = gift.get('preview_url', '')
            if not image_url:
                image_url = gift.get('photo_url', '')
            if not image_url:
                image_url = gift.get('cover_url', '') # Может быть, 'cover' из предыдущего кода было URL?

            # Формирование прямой ссылки на подарок
            gift_link = f"https://t.me/tonnel_network_bot/gift?startapp={gift_num}" if gift_num != 'N/A' else 'Ссылка недоступна'

            # Формирование подписи сообщения для Telegram в формате MarkdownV2
            caption_text = (
                f"\\*Информация о подарке\\*\n"
                f"имя: {escape_markdown_v2(name)}\n"
                f"\\`model\\`: {escape_markdown_v2(model)}\n"
                f"\\`symbol\\`: {escape_markdown_v2(symbol)}\n"
                f"\\`backdrop\\`: {escape_markdown_v2(backdrop)}\n"
                f"\\`gift\\_num\\`: {escape_markdown_v2(gift_num)}\n"
                f"\\`price\\`: {escape_markdown_v2(price)} TON\n"
                f"Прямая ссылка: [Подарок \\#{escape_markdown_v2(gift_num)}]({escape_markdown_v2(gift_link)})"
            )

            # Отправляем фото, если URL изображения найден, иначе только текстовое сообщение
            if image_url and image_url != 'N/A': # Убедимся, что URL не пустой и не 'N/A'
                send_telegram_photo(TELEGRAM_CHAT_ID, image_url, caption_text)
            else:
                print(f"URL изображения для подарка {name} не найден. Отправка только текстового сообщения.")
                send_telegram_message(TELEGRAM_CHAT_ID, caption_text)
    else:
        print("Ответ API не содержит данных о подарках или имеет неожиданный формат.")
        print(gifts_data)

except curl_cffi.requests.exceptions.RequestException as e:
    print(f"Произошла ошибка во время запроса к API подарков: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Код состояния ответа API: {e.response.status_code}")
        print(f"Текст ответа API: {e.response.text}")
except json.JSONDecodeError:
    print("Ошибка: Не удалось декодировать JSON из ответа API подарков.")
    print(f"Исходный текст ответа API: {response.text}")
except Exception as e:
    print(f"Произошла непредвиденная ошибка: {e}")

