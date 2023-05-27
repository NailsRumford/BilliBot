import telegram
from modules.telegram_module.interaction import handle_message
from modules.telegram_module import configuration_manager


def main():
    # Получение токена Telegram-бота из конфигурации
    # Здесь предполагается, что вы используете configuration_manager.py для управления настройками
    token = configuration_manager.get_telegram_token()

    # Создание экземпляра Telegram-бота
    bot = telegram.Bot(token=token)

    # Создание объекта для обработки входящих сообщений
    updater = telegram.ext.Updater(bot=bot, use_context=True)

    # Зарегистрировать функцию обработки сообщений
    updater.dispatcher.add_handler(telegram.ext.MessageHandler(
        telegram.ext.Filters.text, handle_message))

    # Запуск бота
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
