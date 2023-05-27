import configparser

def get_telegram_token():
    # Чтение конфигурационного файла
    config = configparser.ConfigParser()
    config.read('config.ini')  # Предполагается, что у вас есть файл config.ini с настройками

    # Получение токена Telegram-бота из конфигурации
    telegram_token = config.get('Telegram', 'token')

    return telegram_token