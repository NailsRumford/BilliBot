import openai
import openai.error
import json
from database_manager.utils import save_user_profile, load_user_profile
from core import settings
import json
import logging


class GPTAssistant:

    def __init__(self):
        """
        Инициализация GPTAssistant и конфигурация API ключа OpenAI.
        """
        openai.api_key = settings.OPEN_API_KEY

    def check_json(self, json_data: dict, required_keys: list = None) -> None:
        """
        Проверяет, что все необходимые ключи присутствуют в JSON-ответе, и что их значения являются непустыми строками.

        Args:
            json_data (dict): JSON-ответ от модели GPT-3.
            required_keys (list): Список ключей, которые должны присутствовать в json_data.

        Raises:
            Exception: Если какой-либо ключ отсутствует или его значение не является строкой или пустой строкой.
        """
        if required_keys is None:
            required_keys = ["STATUS", "GAMEMASTER",
                             "OPTION 1", "OPTION 2", "OPTION 3"]

        for key in required_keys:
            if key not in json_data:
                raise Exception(f"Key {key} is missing in the JSON response.")
            if not isinstance(json_data[key], str):
                raise Exception(f"Value for {key} is not a string.")
            if not json_data[key]:
                raise Exception(f"Value for {key} is empty.")

    def get_instruction_pronts(self, pront_name: str) -> str:
        """
        Возвращает инструкции для модели GPT-3 на основе имени инструкции.

        Args:
            pront_name (str): Имя инструкции.

        Returns:
            str: Инструкция для модели GPT-3.
        """
        instruction_pront = settings.INSTRUCTION_PRONTS[pront_name]
        return instruction_pront

    async def get_gpt_response(self, conversation_history: list) -> tuple:
        """
        Получает ответ от модели GPT-3, используя историю разговора. Повторяет запрос до 5 раз, если происходит ошибка.
    
        Args:
            conversation_history (list): История разговора, содержащая сообщения от пользователя и ассистента.
    
        Returns:
            tuple: Словарь с ответом GPT-3 и обновленной историей разговора.
        """
        i = 0
        while i < 5:
            try:
                response = await openai.ChatCompletion.acreate(
                    model=settings.MODEL_FOR_GPT_ASSISTANT,
                    messages=conversation_history,
                    max_tokens=settings.MAX_TOKENS_FOR_GPT_ASSISTANT,
                    temperature=settings.TEMPERATURE_FOR_GPT_ASSISTANT
                )
                # Извлекаем полученный ответ из ответа API
                result = response.choices[0]
                response_dict = json.loads(result.message.content)
    
                # Проверяем ответ от GPT
                self.check_json(response_dict)
    
                # Добавляем ответ от GPT в историю разговора
                conversation_history.append(
                    {"role": "assistant", "content": result.message.content})
                return response_dict, conversation_history
    
            except Exception as e:
                logging.debug(f"Attempt {i+1} failed with error: {e}")
                if i == 4:  # это последняя попытка
                    logging.error(f"An error occurred during JSON check: {e}")
                    raise e
            finally:
                i += 1

    async def get_gpt_start_response(self, prompt_name: str, user_id: str) -> dict:
        """
        Инициирует новую игру, отправляя начальный запрос к модели GPT-3 и сохраняя историю разговора.

        Args:
            prompt_name (str): Имя инструкции для начала игры.
            user_id (str): Идентификатор пользователя.

        Returns:
            dict: Ответ GPT-3 на начальный запрос.
        """
        instruction_prompt = self.get_instruction_pronts(prompt_name)
        conversation_history = [
            {"role": "assistant", "content": instruction_prompt},]
        conversation_history.append({"role": "user", "content": 'Начнем игру'})

        response_dict, conversation_history = await self.get_gpt_response(conversation_history)
        user_profile = load_user_profile(user_id)
        user_profile.replace_history(conversation_history)
        user_profile.game_started = True
        save_user_profile(user_profile)
        return response_dict

    async def get_gpt_hystory_response(self, message: str, user_id: str) -> dict:
        """
        Обрабатывает сообщение пользователя, добавляет его в историю разговора и получает ответ от модели GPT-3.

        Args:
            message (str): Сообщение пользователя.
            user_id (str): Идентификатор пользователя.

        Returns:
            dict: Ответ GPT-3 на сообщение пользователя.
        """
        user_profile = load_user_profile(user_id)
        conversation_history = user_profile.history
        conversation_history.append({"role": "user", "content": message})

        response_dict, conversation_history = await self.get_gpt_response(conversation_history)
        user_profile.replace_history(conversation_history)
        save_user_profile(user_profile)
        return response_dict
