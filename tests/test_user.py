import pytest
import asyncio

from user_manager.user import User


@pytest.mark.asyncio
async def test_user_processing():
    user_id = "test_user"
    user = User(user_id)

    # Убеждаемся, что пользователь не обрабатывается сразу после создания
    assert user.is_processing == False

    # Начинаем обработку и убеждаемся, что состояние обработки изменилось
    await user.start_processing()
    assert user.is_processing == True

    # Завершаем обработку и убеждаемся, что состояние обработки вернулось к исходному
    await user.end_processing()
    assert user.is_processing == False