from datetime import datetime
from unittest.mock import patch

import pandas as pd


from src.views import (
    get_cards_info,
    get_currency_rates,
    get_expenses_info,
    get_stock_prices,
    get_top_transactions,
    main_page_view,
)


def test_get_cards_info():
    """Тест получения информации по картам"""
    data = {
        "Номер карты": ["*7197", "*7197", "*5091"],
        "Сумма операции": [-100, -200, -300],
    }
    df = pd.DataFrame(data)

    cards = get_cards_info(df)

    assert len(cards) == 2
    assert cards[0]["last_digits"] == "7197"
    assert cards[0]["total_spent"] == 300
    assert cards[0]["cashback"] == 3.0


def test_get_top_transactions():
    """Тест получения топ транзакций"""
    data = {
        "Дата операции": [
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            datetime(2024, 1, 3),
        ],
        "Сумма операции": [-1000, -500, -200],
        "Категория": ["Еда", "Транспорт", "Развлечения"],
        "Описание": ["Ресторан", "Такси", "Кино"],
    }
    df = pd.DataFrame(data)

    top = get_top_transactions(df)

    assert len(top) == 3
    assert top[0]["amount"] == 1000
    assert top[0]["category"] == "Еда"


def test_get_expenses_info():
    """Тест получения информации о расходах"""
    data = {
        "Сумма операции": [-100, -200, -300, 500],  # 500 - доход
        "Категория": ["Еда", "Транспорт", "Еда", "Зарплата"],
    }
    df = pd.DataFrame(data)

    expenses = get_expenses_info(df)

    assert expenses["total"] == 600
    assert expenses["average"] == 200
    assert len(expenses["by_category"]) == 2
    assert expenses["by_category"][0]["category"] == "Еда"
    assert expenses["by_category"][0]["amount"] == 400


@patch("src.views.get_exchange_rate")
def test_get_currency_rates(mock_get_rate):
    """Тест получения курсов валют"""
    mock_get_rate.side_effect = [75.5, 90.2]

    rates = get_currency_rates(["USD", "EUR"])

    assert len(rates) == 2
    assert rates[0]["currency"] == "USD"
    assert rates[0]["rate"] == 75.5


@patch("src.views.get_stock_price")
def test_get_stock_prices(mock_get_price):
    """Тест получения цен акций"""
    mock_get_price.side_effect = [150.5, 2500.75]

    prices = get_stock_prices(["AAPL", "GOOGL"])

    assert len(prices) == 2
    assert prices[0]["stock"] == "AAPL"
    assert prices[0]["price"] == 150.5


@patch("src.views.read_transactions_from_excel")
@patch("src.views.get_user_settings")
def test_main_page_view(mock_get_settings, mock_read_excel):
    """Тест главной функции"""
    # Настройка моков
    mock_get_settings.return_value = {
        "user_currencies": ["USD"],
        "user_stocks": ["AAPL"],
    }

    data = {
        "Дата операции": [datetime(2024, 1, 15)],
        "Номер карты": ["*7197"],
        "Сумма операции": [-150.50],
        "Категория": ["Супермаркеты"],
        "Описание": ["Продукты"],
    }
    mock_read_excel.return_value = pd.DataFrame(data)

    # Тестируем
    result = main_page_view("2024-01-15 14:30:00")

    # Проверяем результат
    assert isinstance(result, str)
    import json

    data = json.loads(result)

    assert "greeting" in data
    assert data["greeting"] == "Добрый день"
    assert "cards" in data
    assert "top_transactions" in data
