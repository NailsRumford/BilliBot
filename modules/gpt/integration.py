import openai
import openai.error
import json
from modules.core import configuration_manager


# Словарь для хранения истории диалогов каждого пользователя
user_conversation_histories = {}

instructions = """
[INSTRUCTIONS]
Вы находитесь в мире Dungeons & Dragons. Вы - гейм-мастер, ответственный за создание и описание приключений для игроков. Ваша задача - описывать окружение, персонажей, события и решать исходящие от игроков действия. Ваш стиль описания может быть эпическим, фантастическим или даже комическим. Ваша миссия - вдохновить и увлечь игроков, создавая интересные и захватывающие истории в мире D&D.
Как гейм-мастер, вы также будете отвечать за броски кубика в игре. Игрок выбирает действие, а вы говорите результат какой выпал на кубиках, и к чему он привел.
Каждый ваш ответ должен быть структурирован и представлен строго в следующем порядке:
- STATUS: Пометьте "ОК", если задача понятна и успешно выполнена. Если возникли какие-либо проблемы или недопонимания, пометьте "ERROR". Этот элемент должен всегда идти первым в вашем ответе.
- GAMEMASTER: Слова геймастера, описание не мение 200 символов.
- OPTION 1: Предложите вариант действий агресивного характера. Не более 40 символов
- OPTION 2: Предложите вариант действий мирного характера. Не более 40 символов
- OPTION 3: Предложите вариант действий иследовательского характера. Не более 40 символов
- OPTION 4: Предложите вариант действий который преведет к неожиданным последствиям. Не более 40 символов
Ответ должен быть строго в формате Json
все содержание должно быть в виде строки
"""
user_image_promt_histories = {}
image_promt = """
        Представь что ты апи , ты принимаешь историю игры днд , и исходя из контекста ты даешь подробное описание которое можно использовать для иллюстрации происходящего в виде картинки . К примеру я тебе передаю историю игроков в DnD а ты описываешь сцену которая будет в саммом конце истории .
        Дальше будет представлена история игры:
        """
image_promt2 = """
        Теперь исходя из истории напечатай промт для миджерни, который описывал последнюю сцену в истории событий.
        верни в виде json ыледующего вида:
        - STATUS: Пометьте "ОК", если задача понятна и успешно выполнена. Если возникли какие-либо проблемы или недопонимания, пометьте "ERROR". Этот элемент должен всегда идти первым в вашем ответе.
        - ILLUSTRATION: Основываясь на последнем сообщении гейм мастера, опишите героя и происходящее вокруг. Описания должно быть понятным для нейросети которая может создавать изображения воспринимая человекочитаемый текст. Текст ответа должен быть на английском. Описание внешности главного героя 50 слов, описание его действий 50 слов, описание окружени 100 слов.  содержание должно быть строкой.
        """
def get_image_promt(response_dict, user):
    conversation_history = user_conversation_histories.get(user, []).copy()
    conversation_history[0] = {"role": "assistant", "content": image_promt}
    conversation_history.append(
            {"role": "assistant", "content": image_promt2 })
        # Если история диалогов для этого пользователя пуста, добавим в нее инструкции
    for _ in range(5):
        try:
            # Отправляем запрос в GPT
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation_history,
            )
            if response.choices:
                result = response.choices[0]
                dict = json.loads(result.message.content)
                check_image_json(dict)
        except Exception as e:
            print(e)
        else:
            return dict['ILLUSTRATION']
    raise Exception()

def get_image(promt):
    openai.api_key = configuration_manager.get_openai_api_key()
    setting = f'ELF'
    try:
        response = openai.Image.create(
            prompt=promt,
            n=1,
            size="512x512",
        )
        return response["data"][0]["url"]
    except openai.error.OpenAIError as e:
        print(e.http_status)
        print(e)


def check_json(json_data):
    required_keys = ["STATUS", "GAMEMASTER",
                     "OPTION 1", "OPTION 2", "OPTION 3", "OPTION 4"]
    for key in required_keys:
        if key not in json_data:
            raise Exception(f"Key {key} is missing in the JSON response.")
        if not isinstance(json_data[key], str):
            raise Exception(f"Value for {key} is not a string.")
        if not json_data[key]:
            raise Exception(f"Value for {key} is empty.")
        
def check_image_json(json_data):
    required_keys = ["STATUS", "ILLUSTRATION",]
    for key in required_keys:
        if key not in json_data:
            raise Exception(f"Key {key} is missing in the JSON response.")
        if not isinstance(json_data[key], str):
            raise Exception(f"Value for {key} is not a string.")
        if not json_data[key]:
            raise Exception(f"Value for {key} is empty.")

user_response_dict ={}
async def get_gpt_response(message, user):
    # Устанавливаем API-ключ
    openai.api_key = configuration_manager.get_openai_api_key()

    # Получаем историю диалогов для данного пользователя или создаем новую, если ее еще нет
    conversation_history = user_conversation_histories.get(user, [])

    # Если история диалогов для этого пользователя пуста, добавим в нее инструкции
    if not conversation_history:
        conversation_history.append(
            {"role": "assistant", "content": instructions})

    # Добавляем новое сообщение от пользователя в историю
    conversation_history.append({"role": "user", "content": message})

    # Отправляем запрос в GPT

    for _ in range(5):
        try:

            # Отправляем запрос в GPT
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation_history,
            )
            # Извлекаем полученный ответ из ответа API
            if response.choices:
                result = response.choices[0]
                response_dict = json.loads(result.message.content)
                check_json(response_dict)
                # Добавляем ответ от GPT в историю разговора
                conversation_history.append(
                    {"role": "assistant", "content": result.message.content})
                # Сохраняем обновленную историю обратно в словарь
                user_conversation_histories[user] = conversation_history
        except Exception:
            print('Надо бы залогировать ошибочку')
        else:
            # Если выполнено условие (в данном случае отсутствие исключения), прервем цикл
            user_response_dict[user.id]=response_dict
            result=True
            break 
            # ли все 5 попыток не увенчались успехом, вернем пустой словарь
    if result:
        print ('123')
    else:
        raise Exception()
