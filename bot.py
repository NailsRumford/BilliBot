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
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from user_manager.user_manager import UserManager
from core import settings
import asyncio
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=1)
user_manager = UserManager()
CHOOSING_SETTING, CHOOSING_GANRE, CHOOSING_WORLD, CHOOSING_CHARACTER, CHOOSING_START_POINT, HISTORY_IN_PROGRESS = range(
    6)


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
        self.gif_messages = {}

    async def send_message(self, update, context, text: str, user, start: bool = False):
        # обработка текстовых сообщений пользователя
        gif_message = self.gif_messages[user.id]
        await user.start_processing()
        response_dict = {}  # Значение по умолчанию для response_dict
        try:
            if start:
                logging.info(
                    f"Отправка запроса на обработку текста для пользователя {user.id}.")
                response_dict = await self.gpt_assistant.get_gpt_start_response(text, user.id)
            else:
                logging.info(
                    f"Отправка запроса на обработку текста для пользователя {user.id}.")
                response_dict = await self.gpt_assistant.get_gpt_hystory_response(text, user.id)
        except Exception as e:
            logging.error(
                f"Произошла ошибка при обработке запроса для пользователя {user.id}: {e}")
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, message_id=gif_message.message_id)
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f"Произошла ошибка обработки запроса, попробуйте отправить запрос повторно или перезагрузите игру")
            return  # Выход из функции, чтобы избежать обработки недействительного response_dict
        logging.info(f"Запрос для пользователя {user.id} успешно обработан.")

        await context.bot.delete_message(
            chat_id=update.effective_chat.id, message_id=gif_message.message_id)
        reply_markup = crate_keyboard(response_dict)
        text = f"Сделайте выбор или дайте свой вариант ответа:"
        try:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f"{response_dict['GAMEMASTER']}", reply_markup=reply_markup)
            await user.end_processing()
        except Exception as e:
            await user.end_processing()
            print(f"Ошибка при отправк сообщения с сценарием: {e}")

    async def process_start(self, update, context):
        # обработка команды /start
        user = update.effective_user
        user_history = load_user_profile(user.id)
        if user_history is not None:
            if not user_history.game_started:
                await update.message.reply_text('Игра уже запущена, если вы хотите начать новую игру нажмите Restart')
                return HISTORY_IN_PROGRESS
            elif user_history.game_settings_created:
                await update.message.reply_text('Завершите настройку игры')
                return HISTORY_IN_PROGRESS
        else:
            user_history = UserProfile(
                game_settings_created=True, user=user.id)
            save_user_profile(user_history)
            button_list = [KeyboardButton(s) for s in settings.START_BUTTON]
            reply_markup = ReplyKeyboardMarkup(build_menu(
                button_list, n_cols=2), resize_keyboard=True)
            await update.message.reply_text('Вы находетесь в главном меню:', reply_markup=reply_markup)
            return CHOOSING_SETTING

    async def process_restart(self, update, context):
        # обработка команды /restart
        user = update.effective_user
        user_history = load_user_profile(user.id)
        if user_history:
            user_history.delete(session)
        reply_markup = ReplyKeyboardMarkup(build_menu(
            ['/start',], n_cols=2), resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("История завершена, если вы хотите начать новую историю нажмите /start", reply_markup=reply_markup)
        return ConversationHandler.END

    async def process_help(self, update, context):
        # обработка команды /help
        help_text = settings.HELP_TEXT
        await update.message.reply_text(help_text)

    async def process_text(self, update, context):
        # обработка текстовых сообщений пользователя
        user = await self.user_manager.get_user(update.effective_user.id)
        user_history = load_user_profile(user.id)
        if user.is_processing:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Подождите, идет обработка.")
        elif not user_history.game_started:
            await update.message.reply_text('Запустите игру , или завершите ее настройку')
        else:

            remove_keyboard = ReplyKeyboardRemove()
            self.gif_messages[user.id] = await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation=settings.STORY_GIF,
                reply_markup=remove_keyboard
            )
            asyncio.create_task(self.send_message(update, context,
                                                  text=update.message.text,
                                                  user=user))
            return HISTORY_IN_PROGRESS

    async def process_start_setting_menu(self, update, context, buttons) -> None:
        user = update.effective_user
        user_history = load_user_profile(user.id)
        if user_history.game_started:
            await update.message.reply_text('Игра уже запущена, если вы хотите начать новую игру нажмите Restart')
        else:

            button_list = [KeyboardButton(s) for s in buttons]
            reply_markup = ReplyKeyboardMarkup(build_menu(
                button_list, n_cols=2), resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text('Выберите один из вариантов:', reply_markup=reply_markup)

    async def process_menu_choice(self, update, context):
        text = update.message.text
        user = update.effective_user
        user_history = load_user_profile(user.id)
        buttons = settings.GENRES
        if user_history.game_started:
            await update.message.reply_text('Игра уже запущена, если вы хотите начать новую игру нажмите Restart')
        else:
            user_history.start_setting = update.message.text
            save_user_profile(user_history)
            button_list = [KeyboardButton(s) for s in buttons]
            reply_markup = ReplyKeyboardMarkup(build_menu(
                button_list, n_cols=2), resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text('Выберите один из вариантов:', reply_markup=reply_markup)
        return CHOOSING_GANRE

    async def process_choosing_ganre(self, update, context):
        text = update.message.text
        user = update.effective_user
        user_history = load_user_profile(user.id)
        if user_history.start_setting == '📚 Продолжить книгу':

            worlds = settings.genres_dict[text]['books']
            world_list = list(worlds.keys())
            button_list = [KeyboardButton(s) for s in world_list]
            reply_markup = ReplyKeyboardMarkup(build_menu(
                button_list, n_cols=2), resize_keyboard=True, one_time_keyboard=True)
            choise_text = 'Выбирете мир или книгу:'
        elif user_history.start_setting == '🎭 Создать свою историю':
            reply_markup = ReplyKeyboardRemove()
            choise_text = 'Опишите мир в котором будет происходиться история'
        if user_history.game_started:
            await update.message.reply_text('Игра уже запущена, если вы хотите начать новую игру нажмите Restart')
        else:
            user_history.ganres = update.message.text
            save_user_profile(user_history)
            await update.message.reply_text(choise_text, reply_markup=reply_markup)
        return CHOOSING_WORLD

    async def process_choosing_world(self, update, context):
        text = update.message.text
        user = update.effective_user
        user_history = load_user_profile(user.id)
        worlds_dict = settings.genres_dict[user_history.ganres]
        try:
            if user_history.start_setting == '📚 Продолжить книгу':
                buttons = worlds_dict['books'][text]['characters']
            elif user_history.start_setting == '🎭 Создать свою историю':
                buttons = worlds_dict['worlds'][text]['characters']
        except:
            buttons = []
        if user_history.game_started:
            await update.message.reply_text('Игра уже запущена, если вы хотите начать новую игру нажмите Restart')
        else:
            user_history.world = update.message.text
            save_user_profile(user_history)
            button_list = [KeyboardButton(s) for s in buttons]
            reply_markup = ReplyKeyboardMarkup(build_menu(
                button_list, n_cols=2), resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text('Выберете персонажа или опешите его сами:', reply_markup=reply_markup)
        return CHOOSING_CHARACTER

    async def process_choosing_character(self, update, context):
        text = update.message.text
        user = update.effective_user
        user_history = load_user_profile(user.id)
        worlds_dict = settings.genres_dict[user_history.ganres]
        try:
            if user_history.start_setting == '📚 Продолжить книгу':
                buttons = worlds_dict['books'][user_history.world]['starting_points']
            elif user_history.start_setting == '🎭 Создать свою историю':
                buttons = worlds_dict['worlds'][user_history.world]['starting_points']
        except:
            await update.message.reply_text(f'Ваш персонаж {text} ')
            buttons = []
        if user_history.game_started:
            await update.message.reply_text('Игра уже запущена, если вы хотите начать новую игру нажмите Restart')
        else:
            user_history.character = update.message.text
            save_user_profile(user_history)
            button_list = [KeyboardButton(s) for s in buttons]
            reply_markup = ReplyKeyboardMarkup(build_menu(
                button_list, n_cols=2), resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text('Выберете с чего начнется история или предложите свой вариант:', reply_markup=reply_markup)
        return CHOOSING_START_POINT

    async def process_start_history(self, update, context):
        # обработка выбора пользователем старта истории
        text = update.message.text
        user = await self.user_manager.get_user(update.effective_user.id)
        user_history = load_user_profile(user.id)
        user_history.start_point = update.message.text
        save_user_profile(user_history)
        if user_history.start_setting == '📚 Продолжить книгу':
            prompt = self.get_book_promt(world=user_history.world,
                                         character=user_history.character,
                                         starting_point=user_history.start_point)
        elif user_history.start_setting == '🎭 Создать свою историю':
            prompt = self.get_world_promt(ganre=user_history.ganres,
                                          world=user_history.world,
                                          character=user_history.character,
                                         starting_point=user_history.start_point)
        remove_keyboard = ReplyKeyboardRemove()
        self.gif_messages[user.id] = await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=settings.START_GIF,
            reply_markup=remove_keyboard
        )
        asyncio.create_task(self.send_message(
            update, context, prompt, user=user, start=True))
        return HISTORY_IN_PROGRESS

    def get_book_promt(self, world, character, starting_point):
        template = settings.book_game_pront
        prompt = template.format(
            book_character=character, book_name=world, plot_start_point=starting_point)
        return prompt

    def get_world_promt(self, ganre, world, character, starting_point):
        template = settings.world_game_pront
        prompt = template.format(user_setting=world, user_character=character,
                                 user_genre=ganre, user_situation=starting_point)
        return prompt


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(settings.TELEGRAM_TOKEN).build()
    # Создаем экземпляр обработчика сообщений
    message_processor = MessageProcessor(
        user_manager, gpt_assistant=GPTAssistant())
    # on different commands - answer in Telegram
    # application.add_handler(CommandHandler(
    #    "start", message_processor.process_start))
    # application.add_handler(CommandHandler(
    #    "restart", message_processor.process_restart))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler(
            "start", message_processor.process_start)],
        fallbacks=[CommandHandler(
            'restart', message_processor.process_restart)],

        states={
            CHOOSING_SETTING: [MessageHandler(filters.Regex(f'^({start_button_regex})$'), message_processor.process_menu_choice)],
            CHOOSING_GANRE: [MessageHandler(filters.Regex(f'^({genres_regex})$'), message_processor.process_choosing_ganre)],
            CHOOSING_WORLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, message_processor.process_choosing_world)],
            CHOOSING_CHARACTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, message_processor.process_choosing_character)],
            CHOOSING_START_POINT: [MessageHandler(filters.TEXT & ~filters.COMMAND, message_processor.process_start_history)],
            HISTORY_IN_PROGRESS: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, message_processor.process_text)]
        },

    ))
    application.add_handler(CommandHandler(
        "help", message_processor.process_help))
#    application.add_handler(MessageHandler(filters.Regex(
#        f'^({start_button_regex})$'), message_processor.process_menu_choice))
#    application.add_handler(MessageHandler(filters.Regex(
#        f'^({combined_regex})$'), message_processor.process_start_history))
#    # on non command i.e message - echo the message on Telegram
#    application.add_handler(MessageHandler(
#        filters.TEXT & ~filters.COMMAND, message_processor.process_text))
#    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
