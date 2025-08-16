import curl_cffi
import json # Импортируем модуль json для обработки потенциальных ошибок декодирования

headers = {
    # Обновлен User-Agent, чтобы соответствовать тому, что видно на скриншотах (Chrome/Opera)
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    # 'Accept-Encoding': 'gzip, deflate, br, zstd', # Оставлено закомментированным, curl_cffi обычно обрабатывает это
    # ИСПРАВЛЕНО: Referer теперь соответствует скриншотам
    "Referer": "https://market.tonnel.network/",
    "Content-Type": "application/json",
    # ИСПРАВЛЕНО: Origin теперь соответствует скриншотам
    "Origin": "https://market.tonnel.network",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "Sec-GPC": "1",
    "Priority": "u=4",
    # 'TE': 'trailers', # Оставлено закомментированным
}

json_data = {
    "page": 1,
    "limit": 30,
    "sort": '{"message_post_time":-1,"gift_id":-1}',
    "filter": '{"price":{"$exists":true},"refunded":{"$ne":true},"buyer":{"$exists":false},"export_at":{"$exists":true},"asset":"TON"}',
    "ref": 0,
    "price_range": [15, 20],
    # Обновлено user_auth с заполнителем. Вам нужно вставить сюда ваш реальный токен!
    "user_auth": "user=%7B%22id%22%3A1291677325%2C%22first_name%22%3A%22%D0%94%D0%B8%D0%BC%D0%B0%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22otcseller132%22%2C%22language_code%22%3A%22ru%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2Fi_6TgYWBnuSgDGilK8pmZuIUf-kC7SV2VP9GETs7WwU.svg%22%7D&chat_instance=8370872738174365064&chat_type=sender&auth_date=1751722177&signature=duBioXksZJiZTCpo8piGJBK-EnxXMLqrFen58V3fS7voQWEwiBXM_vq73hLr0NZheuWbjhYi7B4WUR_asIl6BA&hash=5f61305b56acfda600e24c57668110ea80a3ece4a25be79e2189527b3d06f011",
}

# Инициализируем сессию curl_cffi с имитацией Chrome
session = curl_cffi.Session(impersonate="chrome131")

try:
    # Выполняем POST-запрос
    # verify=False оставлено для обхода предыдущей ошибки SSL.
    # ВНИМАНИЕ: Отключение проверки SSL не рекомендуется для производственных сред!
    response = session.post(
        "https://gifts3.tonnel.network/api/pageGifts",
        headers=headers,
        json=json_data,
        verify=False  # <--- Отключает проверку SSL-сертификата
    )

    # Проверяем статус ответа HTTP. Если он 4xx или 5xx, будет вызвано исключение.
    response.raise_for_status()

    # Печатаем JSON-ответ
    print(response.json())

except curl_cffi.requests.exceptions.RequestException as e:
    # Обработка ошибок, связанных с запросом (например, проблемы с сетью, HTTP-ошибки)
    print(f"Произошла ошибка во время запроса: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Код состояния ответа: {e.response.status_code}")
        print(f"Текст ответа: {e.response.text}")
except json.JSONDecodeError:
    # Обработка ошибок, если ответ не является действительным JSON
    print("Ошибка: Не удалось декодировать JSON из ответа.")
    print(f"Исходный текст ответа: {response.text}")
except Exception as e:
    # Обработка любых других неожиданных ошибок
    print(f"Произошла непредвиденная ошибка: {e}")
