import json
import logging
from typing import List, Dict, Any, Union
import pandas as pd

logger = logging.getLogger(__name__)


def analyze_cashback_categories(
    data: Union[pd.DataFrame, List[Dict[str, Any]]], year: int, month: int
) -> str:
    """Анализирует, какие категории были наиболее выгодными для выбора
    в качестве категорий повышенного кешбэка за указанный месяц."""
    logger.info(f"Запуск анализа кешбэка за {year}-{month:02d}")

    try:
        # Быстрое преобразование данных
        df = pd.DataFrame(data) if isinstance(data, list) else data.copy()

        # Валидация колонок одной операцией
        required_columns = {"Дата операции", "Категория", "Сумма платежа", "Кешбэк"}
        if missing := required_columns - set(df.columns):
            logger.error(f"Отсутствуют необходимые колонки: {missing}")
            raise ValueError(f"В данных отсутствуют колонки: {missing}")

        # Оптимизированная фильтрация по дате
        df["Дата операции"] = pd.to_datetime(
            df["Дата операции"], format="%d.%m.%Y", errors="coerce"
        ).dropna()

        # Векторизованная фильтрация
        mask = (
            (df["Дата операции"].dt.year == year)
            & (df["Дата операции"].dt.month == month)
            & (df["Сумма платежа"] < 0)
        )

        filtered_df = df.loc[mask]

        if filtered_df.empty:
            logger.warning(f"Нет расходных операций за {year}-{month:02d}")
            return "{}"

        # Агрегация с вычислением кешбэка за один проход
        cashback_by_category = (
            filtered_df.groupby("Категория")["Сумма платежа"]
            .sum()
            .abs()
            .mul(0.01)
            .round(2)
            .sort_values(ascending=False)
            .to_dict()
        )

        # Прямая конвертация в JSON
        return json.dumps(cashback_by_category, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Ошибка при анализе кешбэка: {e}")
        raise
