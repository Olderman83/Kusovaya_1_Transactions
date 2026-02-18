import pytest
import pandas as pd
import json
from src.services import analyze_cashback_categories


class TestAnalyzeCashbackCategories:
    """Тесты для функции analyze_cashback_categories."""

    @pytest.fixture
    def sample_transactions_list(self):
        """Фикстура с тестовыми данными в формате списка словарей."""
        return [
            {
                "Дата операции": "2024-01-15 10:30:00",
                "Категория": "Супермаркеты",
                "Сумма платежа": -1500.50,
                "Кэшбэк": 15.01,
            },
            {
                "Дата операции": "2024-01-20 15:45:00",
                "Категория": "Кафе и рестораны",
                "Сумма платежа": -800.00,
                "Кэшбэк": 8.00,
            },
            {
                "Дата операции": "2024-01-25 09:15:00",
                "Категория": "Супермаркеты",
                "Сумма платежа": -500.25,
                "Кэшбэк": 5.00,
            },
            {
                "Дата операции": "2024-02-05 12:00:00",
                "Категория": "Транспорт",
                "Сумма платежа": -300.00,
                "Кэшбэк": 3.00,
            },
        ]

    @pytest.fixture
    def sample_transactions_df(self, sample_transactions_list):
        """Фикстура с тестовыми данными в формате DataFrame."""
        return pd.DataFrame(sample_transactions_list)

    @pytest.fixture
    def sample_transactions_with_income(self):
        """Фикстура с данными, включающими доходы."""
        return [
            {
                "Дата операции": "2024-01-15 10:30:00",
                "Категория": "Супермаркеты",
                "Сумма платежа": -1500.50,
                "Кэшбэк": 15.01,
            },
            {
                "Дата операции": "2024-01-20 09:00:00",
                "Категория": "Зарплата",
                "Сумма платежа": 50000.00,
                "Кэшбэк": 0,
            },
        ]

    def test_basic_functionality_with_list(self, sample_transactions_list):
        """Тест базовой функциональности с входными данными в виде списка."""
        result = analyze_cashback_categories(sample_transactions_list, 2024, 1)

        expected = {
            "Супермаркеты": 20.01,  # (1500.50 + 500.25) * 0.01
            "Кафе и рестораны": 8.00,  # 800.00 * 0.01
        }

        assert json.loads(result) == expected

    def test_basic_functionality_with_dataframe(self, sample_transactions_df):
        """Тест базовой функциональности с входными данными в виде DataFrame."""
        result = analyze_cashback_categories(sample_transactions_df, 2024, 1)

        expected = {"Супермаркеты": 20.01, "Кафе и рестораны": 8.00}

        assert json.loads(result) == expected

    def test_empty_result_for_no_transactions(self):
        """Тест возврата пустого словаря при отсутствии транзакций за период."""
        transactions = [
            {
                "Дата операции": "2024-02-15 14:20:00",
                "Категория": "Супермаркеты",
                "Сумма платежа": -1500.50,
                "Кэшбэк": 15.01,
            }
        ]

        result = analyze_cashback_categories(transactions, 2024, 1)
        assert result == "{}"
        assert json.loads(result) == {}

    def test_filter_by_year_and_month(self, sample_transactions_list):
        """Тест корректной фильтрации по году и месяцу."""
        result = analyze_cashback_categories(sample_transactions_list, 2024, 2)

        expected = {"Транспорт": 3.00}  # 300.00 * 0.01

        assert json.loads(result) == expected

    def test_rounding_to_two_decimals(self):
        """Тест округления результатов до двух знаков после запятой."""
        transactions = [
            {
                "Дата операции": "2024-01-15 08:30:00",
                "Категория": "Аптеки",
                "Сумма платежа": -123.45,
                "Кэшбэк": 1.23,
            }
        ]

        result = analyze_cashback_categories(transactions, 2024, 1)
        expected = {"Аптеки": 1.23}  # 123.45 * 0.01 = 1.2345 -> округлено до 1.23

        assert json.loads(result) == expected

    def test_sorting_descending_by_cashback(self):
        """Тест сортировки категорий по убыванию кешбэка."""
        transactions = [
            {
                "Дата операции": "2024-01-15 11:30:00",
                "Категория": "Категория А",
                "Сумма платежа": -1000.00,
                "Кэшбэк": 10.00,
            },
            {
                "Дата операции": "2024-01-16 12:45:00",
                "Категория": "Категория Б",
                "Сумма платежа": -2000.00,
                "Кэшбэк": 20.00,
            },
            {
                "Дата операции": "2024-01-17 09:15:00",
                "Категория": "Категория В",
                "Сумма платежа": -500.00,
                "Кэшбэк": 5.00,
            },
        ]

        result = analyze_cashback_categories(transactions, 2024, 1)
        result_dict = json.loads(result)

        # Проверяем порядок ключей в словаре (сортировка по убыванию)
        assert list(result_dict.keys()) == ["Категория Б", "Категория А", "Категория В"]
        assert result_dict["Категория Б"] == 20.00
        assert result_dict["Категория А"] == 10.00
        assert result_dict["Категория В"] == 5.00
