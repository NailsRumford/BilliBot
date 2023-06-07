from typing import Dict
from .user import User
import asyncio

class UserManager:
    """
    Класс UserManager управляет экземплярами User и предоставляет методы для их создания и получения.
    """

    def __init__(self) -> None:
        """
        Инициализирует экземпляр класса UserManager.
        """
        self._users: Dict[int, User] = {}
        self._lock = asyncio.Lock()  # Лок для управления доступом к словарю _users

    async def get_user(self, user_id: int) -> User:
        """
        Асинхронно получает экземпляр класса User. Если пользователь еще не существует, он будет создан.

        Args:
            user_id: Уникальный идентификатор пользователя.

        Returns:
            Экземпляр класса User для данного пользователя.
        """
        async with self._lock:  # Блокируем доступ к _users на время операции
            if user_id not in self._users:
                self._users[user_id] = User(user_id)
            return self._users[user_id]