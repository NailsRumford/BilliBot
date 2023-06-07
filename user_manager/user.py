import asyncio


class User:
    """
    Класс User предназначен для отслеживания состояния обработки для каждого пользователя.
    """

    def __init__(self, user_id: str):
        """
        Инициализирует экземпляр класса User.

        Args:
            user_id: Уникальный идентификатор пользователя.
        """
        self.id: str = user_id
        self._is_processing: bool = False
        self._lock: asyncio.Lock = asyncio.Lock()

    async def start_processing(self) -> None:
        """
        Начинает обработку сообщения пользователя.
        """
        async with self._lock:
            self._is_processing = True

    async def end_processing(self) -> None:
        """
        Завершает обработку сообщения пользователя.
        """
        async with self._lock:
            self._is_processing = False

    @property
    def is_processing(self) -> bool:
        """
        Свойство, которое возвращает состояние обработки пользователя.

        Returns:
            Состояние обработки пользователя.
        """
        return self._is_processing