import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


def get_user_settings() -> Dict[str, List[str]]:
    """
    Загружает пользовательские настройки из файла user_settings.json.

    Returns:
        Dict[str, List[str]]: Словарь с настройками пользователя
    """
    try:
        with open("user_settings.json", "r", encoding="utf-8") as file:
            settings = json.load(file)
        return settings
    except FileNotFoundError:
        logger.error("Файл user_settings.json не найден")
        return {"user_currencies": ["USD"], "user_stocks": ["AAPL"]}
    except json.JSONDecodeError:
        logger.error("Ошибка декодирования JSON в user_settings.json")
        return {"user_currencies": ["USD"], "user_stocks": ["AAPL"]}


def get_exchange_rate(currency: str) -> Optional[float]:
    """
    Получает текущий курс валюты к рублю через API.

    Args:
        currency: Код валюты (например, "USD", "EUR")

    Returns:
        Optional[float]: Курс валюты или None в случае ошибки
    """
    try:
        api_key = os.getenv("EXCHANGE_API_KEY")
        if not api_key:
            logger.error("EXCHANGE_API_KEY не найден в .env файле")
            return None

        # Пример использования API (замените на реальный API)
        url = "https://api.exchangerate-api.com/v4/latest/RUB"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        rate = data.get("rates", {}).get(currency)

        if rate:
            return round(1 / rate, 4)  # Конвертируем в RUB за 1 единицу валюты
        return None

    except requests.RequestException as e:
        logger.error(f"Ошибка при получении курса валюты {currency}: {e}")
        return None


def get_stock_price(symbol: str) -> Optional[float]:
    """
    Получает текущую цену акции через API.

    Args:
        symbol: Тикер акции (например, "AAPL", "GOOGL")

    Returns:
        Optional[float]: Цена акции или None в случае ошибки
    """
    try:
        api_key = os.getenv("STOCK_API_KEY")
        if not api_key:
            logger.error("STOCK_API_KEY не найден в .env файле")
            return None

        # Пример использования Alpha Vantage API
        url = "https://www.alphavantage.co/query"
        params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        price = data.get("Global Quote", {}).get("05. price")

        if price:
            return round(float(price), 2)
        return None

    except requests.RequestException as e:
        logger.error(f"Ошибка при получении цены акции {symbol}: {e}")
        return None
    except (ValueError, KeyError) as e:
        logger.error(f"Ошибка при обработке данных для {symbol}: {e}")
        return None


def read_transactions_from_excel(
    file_path: str = "data/operations.xlsx",
) -> pd.DataFrame:
    """
    Читает транзакции из Excel файла.

    Args:
        file_path: Путь к файлу с транзакциями

    Returns:
        pd.DataFrame: DataFrame с транзакциями
    """
    try:
        df = pd.read_excel(file_path)

        # Преобразование даты
        df["Дата операции"] = pd.to_datetime(
            df["Дата операции"], format="%d.%m.%Y %H:%M:%S"
        )

        if df["Сумма операции"].dtype == 'object':
            df["Сумма операции"] = df["Сумма операции"].str.replace(",", ".")

            # Преобразуем в числа, ошибки преобразуются в NaN
        df["Сумма операции"] = pd.to_numeric(df["Сумма операции"], errors='coerce')

        return df
    except Exception as e:
        logger.error(f"Ошибка при чтении файла {file_path}: {e}")
        return pd.DataFrame()


def filter_transactions_by_date(df: pd.DataFrame, date: datetime) -> pd.DataFrame:
    """
    Фильтрует транзакции от начала месяца до указанной даты.

    Args:
        df: DataFrame с транзакциями
        date: Дата, до которой нужно отфильтровать транзакции

    Returns:
        pd.DataFrame: Отфильтрованный DataFrame
    """
    start_of_month = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    mask = (df["Дата операции"] >= start_of_month) & (df["Дата операции"] <= date)
    filtered_df = df.loc[mask].copy()

    logger.info(f"Отфильтровано транзакций: {len(filtered_df)} из {len(df)}")
    return filtered_df


def get_greeting(date: datetime) -> str:
    """
    Возвращает приветствие в зависимости от времени суток.

    Args:
        date: Текущая дата и время

    Returns:
        str: Приветствие ("Доброе утро", "Добрый день", "Добрый вечер", "Доброй ночи")
    """
    hour = date.hour

    if 5 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"
