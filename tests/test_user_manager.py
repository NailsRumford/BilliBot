import asyncio
import pytest
from user_manager.user_manager import UserManager

@pytest.fixture
def user_manager() -> UserManager:
    """Создает экземпляр UserManager для каждого теста."""
    return UserManager()

@pytest.mark.asyncio
async def test_get_user_creates_new_user(user_manager: UserManager):
    """
    Проверяет, что get_user корректно создает нового пользователя и инициализирует его свойства.
    """
    user_id = "12345"
    user = await user_manager.get_user(user_id)
    assert user.id == user_id
    assert user.is_processing == False

@pytest.mark.asyncio
async def test_get_user_returns_existing_user(user_manager: UserManager):
    """
    Проверяет, что get_user возвращает существующий объект User, если он уже был создан для данного user_id.
    """
    user_id = "12345"
    user1 = await user_manager.get_user(user_id)
    user2 = await user_manager.get_user(user_id)
    assert user1 is user2

@pytest.mark.asyncio
async def test_users_are_independent(user_manager: UserManager):
    """
    Проверяет, что каждый объект User обрабатывает свое состояние независимо от других объектов User.
    """
    user1 = await user_manager.get_user("123")
    user2 = await user_manager.get_user("456")
    await user1.start_processing()
    assert user1.is_processing == True
    assert user2.is_processing == False