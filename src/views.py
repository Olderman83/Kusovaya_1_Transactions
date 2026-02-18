import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from src.utils import (
    filter_transactions_by_date,
    get_exchange_rate,
    get_greeting,
    get_stock_price,
    get_user_settings,
    read_transactions_from_excel,
)

logger = logging.getLogger(__name__)


def main_page_view(date_str: str) -> str:
    """
    Главная функция для генерации JSON-ответа для страницы "Главная".

    Args:
        date_str: Строка с датой и временем в формате "YYYY-MM-DD HH:MM:SS"

    Returns:
        str: JSON-строка с данными для отображения на главной странице
    """
    try:
        # Парсим дату
        current_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

        # Читаем транзакции
        df = read_transactions_from_excel()

        if df.empty:
            return json.dumps({"error": "Нет данных о транзакциях"}, ensure_ascii=False)

        # Фильтруем транзакции за период
        filtered_df = filter_transactions_by_date(df, current_date)

        # Получаем настройки пользователя
        settings = get_user_settings()

        # Формируем JSON-ответ
        response = {
            "greeting": get_greeting(current_date),
            "cards": get_cards_info(filtered_df),
            "top_transactions": get_top_transactions(filtered_df),
            "currency_rates": get_currency_rates(settings.get("user_currencies", [])),
            "stock_prices": get_stock_prices(settings.get("user_stocks", [])),
            "expenses": get_expenses_info(filtered_df),
        }

        return json.dumps(response, ensure_ascii=False, indent=2)

    except ValueError as e:
        logger.error(f"Ошибка при парсинге даты: {e}")
        return json.dumps({"error": "Неверный формат даты"}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return json.dumps({"error": "Внутренняя ошибка сервера"}, ensure_ascii=False)


def get_cards_info(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Получает информацию по картам.

    Args:
        df: DataFrame с транзакциями

    Returns:
        List[Dict[str, Any]]: Список с информацией по картам
    """
    if df.empty:
        return []

    # Группируем по картам
    cards_data = []

    for card_number in df["Номер карты"].unique():
        if pd.isna(card_number) or not card_number:
            continue

        card_df = df[df["Номер карты"] == card_number]

        # Сумма расходов (отрицательные транзакции)
        expenses = card_df[card_df["Сумма операции"] < 0]["Сумма операции"].sum()

        # Кэшбэк (обычно 1% от расходов)
        cashback = round(abs(expenses) * 0.01, 2)

        # Последние 4 цифры карты
        last_digits = str(card_number).replace("*", "")[-4:]

        cards_data.append(
            {
                "last_digits": last_digits,
                "total_spent": round(abs(expenses), 2),
                "cashback": cashback,
            }
        )

    return cards_data


def get_top_transactions(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Получает топ-5 транзакций по сумме.

    Args:
        df: DataFrame с транзакциями

    Returns:
        List[Dict[str, Any]]: Список с топ-5 транзакциями
    """
    if df.empty:
        return []

    # Берем только расходы (отрицательные суммы) и сортируем по убыванию
    expenses = df[df["Сумма операции"] < 0].copy()
    expenses["abs_sum"] = expenses["Сумма операции"].abs()

    top_5 = expenses.nlargest(5, "abs_sum")

    transactions = []
    for _, row in top_5.iterrows():
        transactions.append(
            {
                "date": row["Дата операции"].strftime("%d.%m.%Y"),
                "amount": round(abs(row["Сумма операции"]), 2),
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )

    return transactions


def get_currency_rates(currencies: List[str]) -> List[Dict[str, Any]]:
    """
    Получает текущие курсы валют.

    Args:
        currencies: Список кодов валют

    Returns:
        List[Dict[str, Any]]: Список с курсами валют
    """
    rates = []

    for currency in currencies:
        rate = get_exchange_rate(currency)
        if rate:
            rates.append({"currency": currency, "rate": rate})

    return rates


def get_stock_prices(stocks: List[str]) -> List[Dict[str, Any]]:
    """
    Получает текущие цены акций.

    Args:
        stocks: Список тикеров акций

    Returns:
        List[Dict[str, Any]]: Список с ценами акций
    """
    prices = []

    for stock in stocks:
        price = get_stock_price(stock)
        if price:
            prices.append({"stock": stock, "price": price})

    return prices


def get_expenses_info(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Получает информацию о расходах.

    Args:
        df: DataFrame с транзакциями

    Returns:
        Dict[str, Any]: Информация о расходах
    """
    if df.empty:
        return {"total": 0, "average": 0, "by_category": []}

    # Только расходы (отрицательные суммы)
    expenses = df[df["Сумма операции"] < 0].copy()
    expenses["abs_sum"] = expenses["Сумма операции"].abs()

    total_expenses = expenses["abs_sum"].sum()
    avg_transaction = expenses["abs_sum"].mean() if not expenses.empty else 0

    # Топ категорий расходов
    category_expenses = (
        expenses.groupby("Категория")["abs_sum"].sum().sort_values(ascending=False)
    )
    top_categories = []

    for category, amount in category_expenses.head(3).items():
        top_categories.append({"category": category, "amount": round(amount, 2)})

    return {
        "total": round(total_expenses, 2),
        "average": round(avg_transaction, 2) if not pd.isna(avg_transaction) else 0,
        "by_category": top_categories,
    }
