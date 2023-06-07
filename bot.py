import logging
from gpt.gpt_assistant import GPTAssistant
from telegram import __version__ as TG_VER
from database_manager.utils import save_user_profile, load_user_profile, session
from database_manager.models import UserProfile
from concurrent.futures import ThreadPoolExecutor
try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from user_manager.user_manager import UserManager
from core import settings

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=1)
user_manager = UserManager()
gif_messages = {}

def crate_keyboard(response_dict):
    keyboard = [
        [response_dict['OPTION 1']],
        [response_dict['OPTION 2']],
        [response_dict['OPTION 3']],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    return reply_markup

def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu

# Создайте регулярное выражение для главного меню после старта
start_button_regex = '|'.join(settings.START_BUTTON)
# Создайте регулярное выражение из списка жанров
genres_regex = '|'.join(settings.GENRES)
# Создайте регулярное выражение из списка миров
worlds_regex = '|'.join(settings.WORLDS)
# Создайте регулярное выражение для запуска истории
combined_regex = genres_regex + '|' + worlds_regex

class MessageProcessor:
    def __init__(self, user_manager, gpt_assistant):
        self.user_manager = user_manager
        self.gpt_assistant = gpt_assistant

    async def send_message(self, update, context, text: str, user_id, start: bool = False):
        # обработка текстовых сообщений пользователя
        gif_message = gif_messages[user_id]
        gpt_assistant = GPTAssistant()
        response_dict = {}  # Значение по умолчанию для response_dict
        try:
            if start:
                response_dict = await gpt_assistant.get_gpt_start_response(text, user_id)
            else:
                response_dict = await gpt_assistant.get_gpt_hystory_response(text, user_id)
        except:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, message_id=gif_message.message_id)
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                                text=f"Произошла ошибка обработки запроса, попробуйте отправить запрос повторно или перезагрузите игру")
            return  # Выход из функции, чтобы избежать обработки недействительного response_dict
        await context.bot.delete_message(
            chat_id=update.effective_chat.id, message_id=gif_message.message_id)
        reply_markup = crate_keyboard(response_dict)
        text = f"Сделайте выбор или дайте свой вариант ответа:"
        try:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                                text=f"{response_dict['GAMEMASTER']}", reply_markup=reply_markup)
        except Exception as e:
            print(f"Ошибка при отправк сообщения с сценарием: {e}")

    async def process_start(self,update , context):
        # обработка команды /start
        user = update.effective_user
        user_history = load_user_profile(user.id)
        if user_history is not None:
            if not user_history.game_started:
                await update.message.reply_text('Игра уже запущена, если вы хотите начать новую игру нажмите Restart')
            elif user_history.game_settings_created:
                await update.message.reply_text('Завершите настройку игры')
        else:
            user_history = UserProfile(
                game_settings_created=True, user=user.id)
            save_user_profile(user_history)
            button_list = [KeyboardButton(s) for s in settings.START_BUTTON]
            reply_markup = ReplyKeyboardMarkup(build_menu(
                button_list, n_cols=2), resize_keyboard=True)
            await update.message.reply_text('Вы находетесь в главном меню:', reply_markup=reply_markup)

    async def process_restart(self,update , context):
        # обработка команды /restart
        user = update.effective_user
        user_history = load_user_profile(user.id)
        if user_history:
            user_history.delete(session)
        await self.process_start(update , context)

    async def process_help(self,update , context):
        # обработка команды /help
        help_text = (
            "Привет! Я - Ролевой бот. Вот некоторые из команд, которые вы можете использовать со мной:\n\n"
            "/start: Запускает новую игру и позволяет вам выбрать расу для вашего персонажа.\n\n"
            "/restart: Сбрасывает вашу текущую игру и возвращает вас к выбору расы.\n\n"
            "Вы можете отправлять мне сообщения, и я отвечу в соответствии с вашими выборами и действиями в игре.\n\n"
            "Вы также можете выбирать опции ответа, когда я предлагаю их в ходе игры. Просто нажмите на одну из кнопок для выбора опции.\n\n"
            "Если вы хотите предложить свой собственный ответ вместо выбора из предложенных мною, просто отправьте мне его в сообщении.\n\n"
            "Удачной игры!"
        )
        await update.message.reply_text(help_text)

    async def process_text(self, update , context):
        # обработка текстовых сообщений пользователя
        user = await self.user_manager.get_user(update.effective_user.id)
        user_history = load_user_profile(user.id)
        if user.is_processing:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Подождите, идет обработка.")
        elif not user_history.game_started:
            await update.message.reply_text('Запустите игру , или завершите ее настройку')
        else:
            await user.start_processing()
            remove_keyboard = ReplyKeyboardRemove()
            gif_messages[user.id] = await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation='https://i.gifer.com/OVBs.gif',
                reply_markup=remove_keyboard
            )
            await self.send_message(update , context,
                                    text=update.message.text,
                                    user_id=user.id)
            await user.end_processing()

    async def process_start_setting_menu(self,update , context, buttons) -> None:
        user = update.effective_user
        user_history = load_user_profile(user.id)
        if user_history.game_started:
            await update.message.reply_text('Игра уже запущена, если вы хотите начать новую игру нажмите Restart')
        else:
            button_list = [KeyboardButton(s) for s in buttons]
            reply_markup = ReplyKeyboardMarkup(build_menu(
                button_list, n_cols=2), resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text('Выберите один из вариантов:', reply_markup=reply_markup)

    async def process_menu_choice(self,update , context):
        text = update.message.text
        user = update.effective_user
        if text == '📚 Авторские миры':
            await self.process_start_setting_menu(update , context, buttons=settings.WORLDS)
        elif text == '🎭 Жанры':
            await self.process_start_setting_menu(update , context,buttons=settings.GENRES)
        else:
            await self.send_message(update , context, text, user.id)

    async def process_start_history(self, update , context):
        # обработка выбора пользователем старта истории
        text = update.message.text
        user = update.effective_user
        await update.message.reply_text(f"Вы выбрали: {text}")
        remove_keyboard = ReplyKeyboardRemove()
        gif_messages[user.id] = await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation='https://i.gifer.com/OVBs.gif',
            reply_markup=remove_keyboard
        )
        await self.send_message(update, context, text, user_id=user.id, start=True)

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(settings.TELEGRAM_TOKEN).build()
    # Создаем экземпляр обработчика сообщений
    message_processor = MessageProcessor(user_manager, gpt_assistant = GPTAssistant())
    # on different commands - answer in Telegram
    application.add_handler(CommandHandler(
        "start", message_processor.process_start))
    application.add_handler(CommandHandler(
        "restart", message_processor.process_restart))
    application.add_handler(CommandHandler(
        "help", message_processor.process_help))
    application.add_handler(MessageHandler(filters.Regex(
        f'^({start_button_regex})$'), message_processor.process_menu_choice))
    application.add_handler(MessageHandler(filters.Regex(
        f'^({combined_regex})$'), message_processor.process_start_history))
    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, message_processor.process_text))
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()