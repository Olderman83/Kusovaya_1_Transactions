import pytest
import pandas as pd
from datetime import datetime
import json
from pathlib import Path
from unittest.mock import patch

from src.reports import (
    report_to_file,
    spending_by_category,
    spending_by_weekday,
    spending_by_workday,
    _parse_date,
    _get_date_range,
)


@pytest.fixture
def sample_transactions():
    """Фикстура с тестовыми транзакциями."""
    data = {
        "Дата операции": [
            "01.10.2024",
            "15.10.2024",
            "01.11.2024",
            "15.11.2024",
            "01.12.2024",
            "15.12.2024",
            "01.09.2024",
            "20.12.2024",
        ],
        "Дата платежа": [
            "01.10.2024",
            "15.10.2024",
            "01.11.2024",
            "15.11.2024",
            "01.12.2024",
            "15.12.2024",
            "01.09.2024",
            "20.12.2024",
        ],
        "Категория": [
            "Супермаркеты",
            "Рестораны",
            "Супермаркеты",
            "Транспорт",
            "Супермаркеты",
            "Рестораны",
            "Супермаркеты",
            "Аптеки",
        ],
        "Сумма платежа": [
            -1000.50,
            -2500.75,
            -1500.30,
            -500.25,
            -2000.00,
            -3000.45,
            -800.20,
            -1200.60,
        ],
        "Описание": [
            "Продукты в Пятерочке",
            "Ужин в ресторане",
            "Закупка продуктов",
            "Поездка на такси",
            "Продукты в Ашане",
            "Обед в кафе",
            "Продукты в Магните",
            "Лекарства",
        ],
        "MCC": [5411, 5812, 5411, 4121, 5411, 5812, 5411, 5912],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_transactions_with_weekends():
    """Фикстура с транзакциями в разные дни недели."""
    # Создаем даты на разные дни недели
    dates = []
    # Понедельник (0)
    dates.append("02.12.2024")
    # Вторник (1)
    dates.append("03.12.2024")
    # Среда (2)
    dates.append("04.12.2024")
    # Четверг (3)
    dates.append("05.12.2024")
    # Пятница (4)
    dates.append("06.12.2024")
    # Суббота (5)
    dates.append("07.12.2024")
    # Воскресенье (6)
    dates.append("08.12.2024")
    # Еще одна суббота
    dates.append("14.12.2024")
    # Еще один понедельник
    dates.append("16.12.2024")

    data = {
        "Дата операции": dates * 2,  # Дублируем для большего количества транзакций
        "Категория": ["Супермаркеты"] * len(dates) + ["Рестораны"] * len(dates),
        "Сумма платежа": [-1000] * len(dates) + [-2000] * len(dates),
        "Описание": ["Покупки"] * len(dates) + ["Ресторан"] * len(dates),
    }
    return pd.DataFrame(data)


@pytest.fixture
def reports_dir():
    """Фикстура для работы с директорией отчетов."""
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    yield reports_dir
    # Очищаем после тестов
    for file in reports_dir.glob("test_*.json"):
        file.unlink()
    # Не удаляем саму директорию


# Тесты для вспомогательных функций
@pytest.mark.parametrize(
    "date_str,expected_type",
    [
        ("31.12.2024", datetime),
        ("2024-12-31", datetime),
        (None, datetime),
        ("invalid_date", datetime),  # Должен вернуть текущую дату
    ],
)
def test_parse_date(date_str, expected_type):
    """Тест парсинга даты с разными форматами."""
    result = _parse_date(date_str)
    assert isinstance(result, expected_type)


@pytest.mark.parametrize(
    "months,expected_days",
    [
        (3, 90),
        (1, 30),
        (6, 180),
    ],
)
def test_get_date_range(months, expected_days):
    """Тест получения диапазона дат."""
    end_date = datetime(2024, 12, 31)
    start_date, end = _get_date_range(end_date, months)

    assert end == end_date
    assert (end_date - start_date).days <= expected_days
    assert (end_date - start_date).days >= expected_days - 1


# Тесты для декоратора
def test_report_to_file_decorator_default(reports_dir):
    """Тест декоратора с именем файла по умолчанию."""
    # Очищаем reports_dir перед тестом
    for file in reports_dir.glob("*.json"):
        file.unlink()

    @report_to_file()
    def test_func():
        return {"test": "data"}

    result = test_func()
    assert result == {"test": "data"}

    # Проверяем, что файл создан
    files = list(reports_dir.glob("report_test_func_*.json"))
    assert len(files) == 1

    # Проверяем содержимое
    with open(files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data == {"test": "data"}


def test_report_to_file_decorator_with_filename(reports_dir):
    """Тест декоратора с указанным именем файла."""

    @report_to_file("test_custom_report.json")
    def test_func():
        return {"key": "value"}

    result = test_func()
    assert result == {"key": "value"}

    # Проверяем, что файл создан с правильным именем
    test_file = reports_dir / "test_custom_report.json"
    assert test_file.exists()

    # Очистка
    if test_file.exists():
        test_file.unlink()


def test_report_to_file_with_dataframe(reports_dir):
    """Тест декоратора с DataFrame."""
    test_df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})

    @report_to_file("test_dataframe.json")
    def test_func():
        return test_df

    result = test_func()
    assert isinstance(result, pd.DataFrame)

    # Проверяем файл
    test_file = reports_dir / "test_dataframe.json"
    assert test_file.exists()

    with open(test_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 2
        assert data[0]["col1"] == 1


# Тесты для функции spending_by_category
def test_spending_by_category_basic(sample_transactions):
    """Базовый тест функции трат по категории."""
    result = spending_by_category(sample_transactions, "Супермаркеты", "20.12.2024")

    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert len(result) == 3  # Должно быть 3 транзакции за 3 месяца
    assert all(result["Категория"] == "Супермаркеты")
    assert all(result["Сумма платежа"] < 0)

    total_spent = abs(result["Сумма платежа"].sum())
    assert round(total_spent, 2) == 4500.80  # 1000.50 + 1500.30 + 2000.00


def test_spending_by_category_no_date(sample_transactions):
    """Тест функции без указания даты."""
    with patch("src.reports.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 12, 20)
        mock_datetime.strptime.side_effect = datetime.strptime

        result = spending_by_category(sample_transactions, "Супермаркеты")

        assert isinstance(result, pd.DataFrame)
        # Должна использоваться текущая дата


@pytest.mark.parametrize(
    "date_format",
    [
        "20.12.2024",
        "2024-12-20",
    ],
)
def test_spending_by_category_different_formats(sample_transactions, date_format):
    """Тест функции с разными форматами даты."""
    result1 = spending_by_category(sample_transactions, "Супермаркеты", "20.12.2024")

    result2 = spending_by_category(sample_transactions, "Супермаркеты", "2024-12-20")

    assert len(result1) == len(result2)
    assert abs(result1["Сумма платежа"].sum()) == abs(result2["Сумма платежа"].sum())


def test_spending_by_category_no_transactions(sample_transactions):
    """Тест функции для категории без транзакций."""
    result = spending_by_category(
        sample_transactions, "Несуществующая категория", "20.12.2024"
    )

    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_spending_by_category_missing_columns():
    """Тест функции с отсутствующими колонками."""
    df = pd.DataFrame({"Неправильная колонка": [1, 2, 3]})
    result = spending_by_category(df, "Категория", "20.12.2024")
    assert isinstance(result, pd.DataFrame)
    assert result.empty


# Тесты для функции spending_by_weekday
def test_spending_by_weekday_basic(sample_transactions_with_weekends):
    """Базовый тест функции трат по дням недели."""
    result = spending_by_weekday(sample_transactions_with_weekends, "31.12.2024")

    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    assert "день_недели" in result.columns
    assert "название_дня" in result.columns
    assert "средние_траты" in result.columns
    assert "общие_траты" in result.columns

    # Проверяем, что все дни недели присутствуют
    assert len(result) == 7


def test_spending_by_weekday_no_date(sample_transactions_with_weekends):
    """Тест функции трат по дням недели без даты."""
    with patch("src.reports.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 12, 31)
        result = spending_by_weekday(sample_transactions_with_weekends)
        assert isinstance(result, pd.DataFrame)


def test_spending_by_weekday_empty():
    """Тест функции трат по дням недели с пустым DataFrame."""
    df = pd.DataFrame()
    result = spending_by_weekday(df, "31.12.2024")
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_spending_by_workday_comparison(sample_transactions_with_weekends):
    """Тест сравнения трат в рабочие и выходные дни."""
    result = spending_by_workday(sample_transactions_with_weekends, "31.12.2024")

    workday_total = result["рабочие_дни"]["total_spent"]
    weekend_total = result["выходные_дни"]["total_spent"]

    total = workday_total + weekend_total
    if total > 0:
        workday_percent = result["сравнение"]["доля_рабочих_дней_в_тратах"]
        assert "%" in workday_percent
        assert float(workday_percent.strip("%")) == pytest.approx(
            workday_total / total * 100, 0.1
        )
