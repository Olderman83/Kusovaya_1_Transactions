import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict
from functools import wraps
from pathlib import Path

import pandas as pd

# Настройка логирования
logger = logging.getLogger(__name__)


def report_to_file(filename: Optional[str] = None) -> Callable:
    """Декоратор для функций-отчетов, который записывает результат в файл."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Выполняем функцию отчета
            result = func(*args, **kwargs)

            try:
                # Создаем директорию reports, если её нет
                reports_dir = Path("reports")
                reports_dir.mkdir(exist_ok=True)

                # Определяем имя файла для сохранения
                if filename is None:
                    # Формат: report_имя_функции_ГГГГММДД_ЧЧММСС.json
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = f"report_{func.__name__}_{timestamp}.json"
                else:
                    output_filename = filename
                    # Добавляем расширение .json, если его нет
                    if not output_filename.endswith(".json"):
                        output_filename += ".json"

                output_path = reports_dir / output_filename

                # Сохраняем результат в файл
                if isinstance(result, pd.DataFrame):
                    # Если результат DataFrame, сохраняем в JSON
                    if result.empty:
                        result_json = json.dumps([], ensure_ascii=False, indent=2)
                    else:
                        # Конвертируем DataFrame в список словарей и сохраняем
                        records = result.to_dict(orient="records")
                        # Преобразуем datetime в строки
                        for record in records:
                            for key, value in record.items():
                                if isinstance(value, (pd.Timestamp, datetime)):
                                    record[key] = value.strftime("%d.%m.%Y")
                        result_json = json.dumps(records, ensure_ascii=False, indent=2)

                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(result_json)

                elif isinstance(result, (dict, list)):
                    # Если результат словарь или список, сохраняем как JSON
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

                else:
                    # Иначе сохраняем строковое представление
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(str(result))

                logger.info(
                    f"Результат отчета '{func.__name__}' сохранен в файл: {output_path}"
                )

            except Exception as e:
                logger.error(f"Ошибка при сохранении результата отчета: {e}")

            return result

        return wrapper

    return decorator


# Для обратной совместимости: создаем экземпляр декоратора без параметров
report_to_file_default = report_to_file()


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Парсит строку с датой в разных форматах."""
    if date_str is None:
        return datetime.now()

    # Пробуем разные форматы даты
    formats = ["%d.%m.%Y", "%Y-%m-%d", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    logger.warning(
        f"Не удалось распарсить дату: {date_str}. Используется текущая дата."
    )
    return datetime.now()


def _get_date_range(end_date: datetime, months: int = 3) -> tuple[datetime, datetime]:
    """Возвращает диапазон дат: от end_date - months до end_date."""
    # Простой способ: вычитаем months * 30 дней
    start_date = end_date - timedelta(days=months * 30)
    return start_date, end_date


@report_to_file_default
def spending_by_category(
    transactions: pd.DataFrame, category: str, date: Optional[str] = None
) -> pd.DataFrame:
    """Возвращает траты по заданной категории за последние три месяца от указанной даты."""
    logger.info(f"Анализ трат по категории '{category}' от даты {date or 'текущая'}")

    try:
        # Копируем DataFrame для избежания предупреждений
        df = transactions.copy()

        # Проверяем наличие необходимых колонок
        required_columns = ["Сумма платежа", "Категория"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            logger.error(f"Отсутствуют необходимые колонки: {missing_columns}")
            return pd.DataFrame()

        # Парсим целевую дату
        target_date = _parse_date(date)
        logger.debug(f"Целевая дата: {target_date.strftime('%d.%m.%Y')}")

        # Получаем диапазон дат (последние 3 месяца)
        start_date, end_date = _get_date_range(target_date, months=3)
        logger.debug(
            f"Период анализа: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
        )

        # Преобразуем дату операции в datetime, если она еще не в этом формате
        date_column = None
        if "Дата операции" in df.columns:
            date_column = "Дата операции"
        elif "Дата платежа" in df.columns:
            date_column = "Дата платежа"
        else:
            logger.error("Не найден столбец с датой операции")
            return pd.DataFrame()

        # Приводим даты к единому формату
        if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
            df[date_column] = pd.to_datetime(
                df[date_column], format="%d.%m.%Y", errors="coerce"
            )

        # Удаляем строки с некорректными датами
        df = df.dropna(subset=[date_column])

        # Фильтруем по категории и диапазону дат
        category_mask = df["Категория"] == category
        date_mask = (df[date_column] >= start_date) & (df[date_column] <= end_date)

        filtered_df = df.loc[category_mask & date_mask].copy()

        # Фильтруем только расходные операции (отрицательные суммы)
        if not filtered_df.empty:
            filtered_df = filtered_df[filtered_df["Сумма платежа"] < 0]

        logger.info(
            f"Найдено {len(filtered_df)} транзакций по категории '{category}' за последние 3 месяца"
        )

        # Добавляем итоговую статистику как атрибут (не влияет на JSON)
        if not filtered_df.empty:
            total_spent = abs(filtered_df["Сумма платежа"].sum())
            avg_spent = abs(filtered_df["Сумма платежа"].mean())
            logger.info(f"Общие траты: {total_spent:.2f}, средний чек: {avg_spent:.2f}")

        return filtered_df

    except Exception as e:
        logger.error(
            f"Ошибка при анализе трат по категории '{category}': {e}", exc_info=True
        )
        return pd.DataFrame()


@report_to_file()
def spending_by_weekday(
    transactions: pd.DataFrame, date: Optional[str] = None
) -> pd.DataFrame:
    """Возвращает средние траты по дням недели за последние три месяца."""
    logger.info(f"Анализ трат по дням недели от даты {date or 'текущая'}")

    try:
        df = transactions.copy()

        # Проверяем наличие необходимых колонок
        if "Сумма платежа" not in df.columns:
            logger.error("Отсутствует колонка 'Сумма платежа'")
            return pd.DataFrame()

        # Определяем колонку с датой
        date_column = None
        for col in ["Дата операции", "Дата платежа"]:
            if col in df.columns:
                date_column = col
                break

        if date_column is None:
            logger.error("Не найден столбец с датой операции")
            return pd.DataFrame()

        # Приводим даты к единому формату
        if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
            df[date_column] = pd.to_datetime(
                df[date_column], format="%d.%m.%Y", errors="coerce"
            )

        # Удаляем строки с некорректными датами
        df = df.dropna(subset=[date_column])

        # Парсим целевую дату и получаем диапазон
        target_date = _parse_date(date)
        start_date, end_date = _get_date_range(target_date, months=3)

        # Фильтруем по дате
        date_mask = (df[date_column] >= start_date) & (df[date_column] <= end_date)
        filtered_df = df.loc[date_mask].copy()

        # Оставляем только расходные операции
        filtered_df = filtered_df[filtered_df["Сумма платежа"] < 0]

        if filtered_df.empty:
            logger.warning("Нет расходных операций за указанный период")
            return pd.DataFrame()

        # Добавляем день недели
        filtered_df["день_недели"] = filtered_df[date_column].dt.dayofweek
        # Локализованные названия дней недели
        days_map = {
            0: "Понедельник",
            1: "Вторник",
            2: "Среда",
            3: "Четверг",
            4: "Пятница",
            5: "Суббота",
            6: "Воскресенье",
        }
        filtered_df["название_дня"] = filtered_df["день_недели"].map(days_map)

        # Группируем по дню недели и считаем статистику
        result = (
            filtered_df.groupby(["день_недели", "название_дня"])["Сумма платежа"]
            .agg(
                [
                    ("средние_траты", lambda x: abs(x).mean()),
                    ("общие_траты", lambda x: abs(x).sum()),
                    ("количество_транзакций", "count"),
                ]
            )
            .round(2)
            .reset_index()
        )

        # Сортируем по дню недели
        result = result.sort_values("день_недели")

        logger.info(f"Анализ по дням недели завершен. Данных по {len(result)} дням")
        return result

    except Exception as e:
        logger.error(f"Ошибка при анализе трат по дням недели: {e}", exc_info=True)
        return pd.DataFrame()


@report_to_file()
def spending_by_workday(
    transactions: pd.DataFrame, date: Optional[str] = None
) -> Dict[str, Any]:
    """Сравнивает траты в рабочие и выходные дни за последние три месяца."""
    logger.info(f"Анализ трат в рабочие/выходные дни от даты {date or 'текущая'}")

    try:
        df = transactions.copy()

        # Проверяем наличие необходимых колонок
        if "Сумма платежа" not in df.columns:
            logger.error("Отсутствует колонка 'Сумма платежа'")
            return {}

        # Определяем колонку с датой
        date_column = None
        for col in ["Дата операции", "Дата платежа"]:
            if col in df.columns:
                date_column = col
                break

        if date_column is None:
            logger.error("Не найден столбец с датой операции")
            return {}

        # Приводим даты к единому формату
        if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
            df[date_column] = pd.to_datetime(
                df[date_column], format="%d.%m.%Y", errors="coerce"
            )

        # Удаляем строки с некорректными датами
        df = df.dropna(subset=[date_column])

        # Парсим целевую дату и получаем диапазон
        target_date = _parse_date(date)
        start_date, end_date = _get_date_range(target_date, months=3)

        # Фильтруем по дате
        date_mask = (df[date_column] >= start_date) & (df[date_column] <= end_date)
        filtered_df = df.loc[date_mask].copy()

        # Оставляем только расходные операции
        filtered_df = filtered_df[filtered_df["Сумма платежа"] < 0]

        if filtered_df.empty:
            logger.warning("Нет расходных операций за указанный период")
            return {
                "workday": {
                    "total_spent": 0,
                    "avg_spent": 0,
                    "transactions": 0,
                    "days": 0,
                },
                "weekend": {
                    "total_spent": 0,
                    "avg_spent": 0,
                    "transactions": 0,
                    "days": 0,
                },
                "comparison": {"workday_vs_weekend_ratio": 0},
            }

        # Определяем тип дня
        filtered_df["день_недели"] = filtered_df[date_column].dt.dayofweek
        filtered_df["тип_дня"] = filtered_df["день_недели"].apply(
            lambda x: "weekend" if x >= 5 else "workday"
        )
        filtered_df["тип_дня_рус"] = filtered_df["день_недели"].apply(
            lambda x: "Выходной" if x >= 5 else "Рабочий"
        )

        # Группируем по типу дня
        grouped = filtered_df.groupby("тип_дня")

        # Формируем результат
        result = {}

        for day_type, group in grouped:
            unique_days = group[date_column].dt.date.nunique()
            result[day_type] = {
                "total_spent": round(abs(group["Сумма платежа"].sum()), 2),
                "avg_spent_per_day": (
                    round(abs(group["Сумма платежа"].sum()) / unique_days, 2)
                    if unique_days > 0
                    else 0
                ),
                "avg_spent_per_transaction": round(
                    abs(group["Сумма платежа"].mean()), 2
                ),
                "transaction_count": len(group),
                "days_count": unique_days,
            }

        # Добавляем недостающие типы дней
        for day_type in ["workday", "weekend"]:
            if day_type not in result:
                result[day_type] = {
                    "total_spent": 0,
                    "avg_spent_per_day": 0,
                    "avg_spent_per_transaction": 0,
                    "transaction_count": 0,
                    "days_count": 0,
                }

        # Добавляем сравнение
        workday_avg = result["workday"]["avg_spent_per_day"]
        weekend_avg = result["weekend"]["avg_spent_per_day"]

        result["comparison"] = {
            "workday_vs_weekend_ratio": round(
                workday_avg / weekend_avg if weekend_avg > 0 else 0, 2
            ),
            "workday_percent": round(
                (
                    result["workday"]["total_spent"]
                    / (
                        result["workday"]["total_spent"]
                        + result["weekend"]["total_spent"]
                    )
                    * 100
                    if (
                        result["workday"]["total_spent"]
                        + result["weekend"]["total_spent"]
                    )
                    > 0
                    else 0
                ),
                2,
            ),
            "weekend_percent": round(
                (
                    result["weekend"]["total_spent"]
                    / (
                        result["workday"]["total_spent"]
                        + result["weekend"]["total_spent"]
                    )
                    * 100
                    if (
                        result["workday"]["total_spent"]
                        + result["weekend"]["total_spent"]
                    )
                    > 0
                    else 0
                ),
                2,
            ),
        }

        # Добавляем русские названия для читаемости
        result_rus = {
            "рабочие_дни": result["workday"],
            "выходные_дни": result["weekend"],
            "сравнение": {
                "соотношение_рабочие_к_выходным": result["comparison"][
                    "workday_vs_weekend_ratio"
                ],
                "доля_рабочих_дней_в_тратах": f"{result['comparison']['workday_percent']}%",
                "доля_выходных_дней_в_тратах": f"{result['comparison']['weekend_percent']}%",
            },
        }

        logger.info("Анализ по рабочим/выходным дням завершен")
        return result_rus

    except Exception as e:
        logger.error(
            f"Ошибка при анализе трат по рабочим/выходным дням: {e}", exc_info=True
        )
        return {}


def get_report_by_category(
    file_path: str, category: str, date: Optional[str] = None
) -> str:
    """Загружает данные из файла и формирует отчет по категории."""
    try:
        from src.utils import read_excel_file

        df = read_excel_file(file_path)
        result_df = spending_by_category(df, category, date)

        # Преобразуем результат в JSON
        if result_df.empty:
            return json.dumps(
                {
                    "category": category,
                    "period": "3 месяца",
                    "transactions": [],
                    "total_spent": 0,
                    "average_spent": 0,
                },
                ensure_ascii=False,
                indent=2,
            )

        # Форматируем даты
        result_df_display = result_df.copy()
        date_col = None
        for col in ["Дата операции", "Дата платежа"]:
            if col in result_df_display.columns:
                date_col = col
                break

        if date_col and pd.api.types.is_datetime64_any_dtype(
            result_df_display[date_col]
        ):
            result_df_display[date_col] = result_df_display[date_col].dt.strftime(
                "%d.%m.%Y"
            )

        # Выбираем нужные колонки
        display_columns = []
        for col in [date_col, "Сумма платежа", "Категория", "Описание", "MCC"]:
            if col and col in result_df_display.columns:
                display_columns.append(col)

        if display_columns:
            result_df_display = result_df_display[display_columns]

        # Формируем JSON-ответ
        response = {
            "category": category,
            "period": {
                "months": 3,
                "end_date": (
                    _parse_date(date).strftime("%d.%m.%Y")
                    if date
                    else datetime.now().strftime("%d.%m.%Y")
                ),
            },
            "total_spent": round(abs(result_df["Сумма платежа"].sum()), 2),
            "average_spent": round(abs(result_df["Сумма платежа"].mean()), 2),
            "transactions_count": len(result_df),
            "transactions": result_df_display.to_dict(orient="records"),
        }

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Ошибка при формировании отчета по категории: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
