
import logging
import asyncio

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
from modules.gpt.integration import get_gpt_response, get_image_promt, get_image, user_response_dict, user_conversation_histories

#Create a task queue
queue = asyncio.Queue()
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


user_game = {}
user_race = {}
user_history_create = {}



# Define a few command handlers. These usually take the two arguments update and
# context.

def is_active(user_id, user_dict):
    """Checks if there is an active  for the user."""
    return user_dict.get(user_id, False)

def set_inactive(user_id,user_dict):
    """Sets the status to inactive for the user."""
    user_dict[user_id] = False
    return True

def set_active(user_id,user_dict):
    """Sets the status to active for the user."""
    user_dict[user_id] = True
    return True

   
def crate_keyboard(response_dict, keyboard_name):
    keyboard = [
        [
            InlineKeyboardButton(response_dict['OPTION 1'], callback_data=f'{keyboard_name}_1'),
        ],
        [
            InlineKeyboardButton(response_dict['OPTION 2'], callback_data=f'{keyboard_name}_2'),
        ],
        [
            InlineKeyboardButton(response_dict['OPTION 3'], callback_data=f'{keyboard_name}_3'),
        ],
        [
            InlineKeyboardButton(response_dict['OPTION 4'], callback_data=f'{keyboard_name}_4'),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup
    



async def send_message(text, update, user, keyboard_name):
    set_active(user.id, user_history_create)
    await update.message.reply_text('Идет создание истории')
    try:
        await get_gpt_response(text, user)
        response_dict=user_response_dict[user.id]
    except:
        await update.message.reply_text(f"Произошла ошибка обработки запроса, попробуйте отправить запрос повторно или перезагрузите игру")
    await update.message.reply_text(f"--GameMaster--\n\n{response_dict['GAMEMASTER']}")
    #await update.message.reply_text('Получаю информацию о изображении')
    #image_promt = get_image_promt(response_dict, user)
    #image_url= get_image(image_promt)
    #await update.message.reply_photo(photo=image_url, caption=image_promt)
    reply_markup = crate_keyboard(response_dict, keyboard_name)
    text = f"Сделайте выбор или дайте свой вариант ответа:"
    set_inactive(user.id, user_history_create)
    await update.message.reply_text(text,reply_markup=reply_markup)

async def start_game (text, update, user, keyboard_name='Персонаж выбрал вариант'):
    await update.message.reply_text('Cоздаем персонажа')
    start_game_text = f'Начнем игру: Игра будет на 1 человека, Мой герой {text}, Опиши мне моего героя, скажи какая у меня цель, и начинаем играть.'
    await queue.put((start_game_text, update, user, 'Персонаж выбрал вариант'))

        
async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    if is_active(user.id, user_game):
        await update.message.reply_text('Игра уже запущена')
    else:
        set_active(user.id, user_game)
        keyboard = [
            [
                InlineKeyboardButton('Человек', callback_data=f'race_Человек'),
            ],
            [
                InlineKeyboardButton('Эльф', callback_data='race_Эльф'),
            ],
            [
                InlineKeyboardButton('Орк', callback_data=f'race_Орк'),
            ],
            [
                InlineKeyboardButton('Гном', callback_data=f'race_Гном'),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выбирете или опишите свою расу',reply_markup=reply_markup)


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Сбросить данные и состояние игры только для указанного пользователя
    user = update.effective_user
    user_game.pop(user.id, None)
    user_race.pop(user.id, None)
    user_history_create.pop(user.id, None)
    user_conversation_histories.pop(user.id, None)
    user_response_dict.pop(user.id, None)
    await start(update, context)
       

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
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


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    user = update.effective_user
    
    text = update.message.text
    if is_active(user.id, user_game) and is_active(user.id, user_race):
        if is_active(user.id, user_history_create):
            await update.message.reply_text('Подождите идет создание истории')
        else:
            await queue.put((text, update, user,'Персонаж выбрал вариант'))
    elif is_active(user.id, user_race) is not True:
        await start_game(text, update, user, 'Персонаж выбрал вариант')
        set_active(user.id, user_race)
    else:
        await update.message.reply_text('Игра не запущена, или вы не выбрали расу запустите игру.')


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if is_active(user.id, user_history_create):
        await query.message.reply_text('Подождите идет создание истории')
    elif is_active(user.id, user_game):
        callback_data = query.data
        keyboard_name, start_game_text = callback_data.split('_')
        if is_active(user.id, user_history_create):
            await query.message.reply_text('Подождите идет создание истории')
        else:
            if keyboard_name == 'race' and is_active(user.id, user_race) is not True:
                await start_game(start_game_text,query, user, 'Персонаж выбрал вариант')
                set_active(user.id, user_race)
            elif keyboard_name == 'race' and is_active(user.id, user_race) is True:
                await query.message.reply_text('Вы уже выбрали расу персонажа')
            else:
                await queue.put((callback_data, query, user, 'Персонаж выбрал вариант'))
    else:
        await query.message.reply_text('Игра не запущена, запустите игру.')
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
    application.add_handler(CommandHandler("restart", restart))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))
    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

async def process_queue():
    while True:
        task, update, user, keyboard_name = await queue.get()
        await send_message(task, update, user, keyboard_name)
        queue.task_done()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(process_queue())
    loop.run_until_complete(main())
    loop.close()








