from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd

from src.utils import (
    filter_transactions_by_date,
    get_exchange_rate,
    get_greeting,
    get_stock_price,
    get_user_settings,
    read_transactions_from_excel,
)


def test_get_greeting():
    """Тест функции приветствия"""
    assert get_greeting(datetime(2024, 1, 1, 8, 0)) == "Доброе утро"
    assert get_greeting(datetime(2024, 1, 1, 14, 0)) == "Добрый день"
    assert get_greeting(datetime(2024, 1, 1, 20, 0)) == "Добрый вечер"
    assert get_greeting(datetime(2024, 1, 1, 2, 0)) == "Доброй ночи"


@patch("src.utils.requests.get")
def test_get_stock_price_success(mock_get):
    """Тест успешного получения цены акции"""
    mock_response = Mock()
    mock_response.json.return_value = {"Global Quote": {"05. price": "150.50"}}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    price = get_stock_price("AAPL")
    assert price == 150.50


def test_get_user_settings_file_not_found():
    """Тест обработки отсутствия файла настроек"""
    settings = get_user_settings()
    assert "user_currencies" in settings
    assert "user_stocks" in settings


def test_filter_transactions_by_date():
    """Тест фильтрации транзакций по дате"""
    # Создаем тестовые данные
    data = {
        "Дата операции": [
            datetime(2024, 1, 1, 10, 0),
            datetime(2024, 1, 15, 10, 0),
            datetime(2024, 2, 1, 10, 0),
        ],
        "Сумма операции": [-100, -200, -300],
    }
    df = pd.DataFrame(data)

    # Фильтруем до 15 января
    filtered = filter_transactions_by_date(df, datetime(2024, 1, 15, 23, 59))

    assert len(filtered) == 2
    assert filtered["Сумма операции"].iloc[0] == -100
    assert filtered["Сумма операции"].iloc[1] == -200
