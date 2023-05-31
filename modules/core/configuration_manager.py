import configparser

def get_telegram_token():
    # Чтение конфигурационного файла
    config = configparser.ConfigParser()
    config.read('config.ini')  # Предполагается, что у вас есть файл config.ini с настройками

    # Получение токена Telegram-бота из конфигурации
    telegram_token = config.get('Telegram', 'token')

    return telegram_token

def get_openai_api_key():
    # Чтение конфигурационного файла
    config = configparser.ConfigParser()
    config.read('config.ini')  # Предполагается, что у вас есть файл config.ini с настройками

    # Получение API-ключа OpenAI из конфигурации
    openai_api_key = config.get('OpenAI', 'api_key')

    return openai_api_key