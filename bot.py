
import logging


from modules.core import configuration_manager
from modules.gpt.integration import get_gpt_response, get_image
from telegram import __version__ as TG_VER

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
from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from modules.gpt.integration import get_gpt_response, get_image_promt, get_image

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.


def crate_keyboard(response_dict, keyboard_name):
    keyboard = [
        [
            InlineKeyboardButton(response_dict['OPTION 1'], callback_data=f'{keyboard_name}-1'),
        ],
        [
            InlineKeyboardButton(response_dict['OPTION 2'], callback_data=f'{keyboard_name}-2'),
        ],
        [
            InlineKeyboardButton(response_dict['OPTION 3'], callback_data=f'{keyboard_name}-3'),
        ],
        [
            InlineKeyboardButton(response_dict['OPTION 4'], callback_data=f'{keyboard_name}-4'),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup
    
game = 'Начнем игру: Игра будет на 1 человека, Опиши мне моего героя, скажи какая у меня цель, и начинаем играть.'

async def send_message(text, update, user, keyboard_name):
    await update.message.reply_text('Начинаю обработку')
    response_dict = get_gpt_response(text, user)
    await update.message.reply_text(f"СЛОВА ГЕЙМ МАСТЕРА\n\n{response_dict['GAMEMASTER']}")
    #await update.message.reply_text('Получаю информацию о изображении')
    #image_promt = get_image_promt(response_dict, user)
    #image_url= get_image(image_promt)
    #await update.message.reply_photo(photo=image_url, caption=image_promt)
    #reply_markup = crate_keyboard(response_dict, keyboard_name)
    #text = f"Делай выбор или дай свой вариант"
    #await update.message.reply_text(text,reply_markup=reply_markup)

async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await send_message(game, update, user, keyboard_name='Персонаж выбрал вариант')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    user = update.effective_user
    text = update.message.text
    image_url= get_image(text)
    await update.message.reply_photo(photo=image_url)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    text = query.data
    await send_message(text, query, user, keyboard_name='Персонаж выбрал вариант')
    #await query.message.reply_text('Начинаю обработку')
    #response_dict = get_gpt_response(reply_text, user)
    #await query.message.reply_text(f"СЛОВА ГЕЙМ МАСТЕРА\n\n{response_dict['GAMEMASTER']}")
    #await query.message.reply_text('Получаю информацию о изображении')
    #image_promt = get_image_promt(response_dict, user)
    #image_url= get_image(image_promt)
    #await query.message.reply_photo(photo=image_url, caption=image_promt)
    #reply_markup = crate_keyboard(response_dict)
    #text = f"Делай выбор или дай свой вариант"
    #await query.message.reply_text(text,reply_markup=reply_markup)
    #query.answer()


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    token = configuration_manager.get_telegram_token()
    application = Application.builder().token(token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))
    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()








