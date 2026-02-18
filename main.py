import json
import logging
from datetime import datetime
from pathlib import Path


from src.utils import read_transactions_from_excel, get_user_settings
from src.views import main_page_view
from src.services import analyze_cashback_categories
from src.reports import spending_by_category, spending_by_weekday, spending_by_workday

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def run_views_functionality() -> None:
    """Запускает функциональность модуля views (Главная страница)."""
    print("\n" + "=" * 80)
    print("ЗАПУСК МОДУЛЯ VIEWS (ГЛАВНАЯ СТРАНИЦА)")
    print("=" * 80)

    try:
        # Используем текущую дату для примера
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Генерация главной страницы на дату: {current_date}")

        # Получаем JSON для главной страницы
        result_json = main_page_view(current_date)

        # Парсим JSON для красивого вывода
        result = json.loads(result_json)

        print("\n РЕЗУЛЬТАТ VIEWS:")
        print(f"Приветствие: {result.get('greeting')}")

        # Информация по картам
        print("\n ИНФОРМАЦИЯ ПО КАРТАМ:")
        for card in result.get("cards", []):
            print(f"  Карта *{card['last_digits']}:")
            print(f"    Потрачено: {card['total_spent']} ₽")
            print(f"    Кэшбэк: {card['cashback']} ₽")

        # Топ транзакций
        print("\n ТОП-5 ТРАНЗАКЦИЙ:")
        for i, trans in enumerate(result.get("top_transactions", []), 1):
            print(
                f"  {i}. {trans['date']} - {trans['description']}: {trans['amount']} ₽"
            )

        # Курсы валют
        print("\n💱 КУРСЫ ВАЛЮТ:")
        for currency in result.get("currency_rates", []):
            print(f"  {currency['currency']}: {currency['rate']} ₽")

        # Цены акций
        print("\n ЦЕНЫ АКЦИЙ:")
        for stock in result.get("stock_prices", []):
            print(f"  {stock['stock']}: ${stock['price']}")

        # Информация о расходах
        expenses = result.get("expenses", {})
        print("\n ИНФОРМАЦИЯ О РАСХОДАХ:")
        print(f"  Всего: {expenses.get('total', 0)} ₽")
        print(f"  Средний чек: {expenses.get('average', 0)} ₽")
        print("  Топ категории:")
        for cat in expenses.get("by_category", []):
            print(f"    - {cat['category']}: {cat['amount']} ₽")

        # Сохраняем результат в файл
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        output_file = (
            output_dir / f"views_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n Результат сохранен в: {output_file}")

    except Exception as e:
        logger.error(f"Ошибка при запуске модуля views: {e}", exc_info=True)
        print(f" Ошибка: {e}")


def run_services_functionality() -> None:
    """Запускает функциональность модуля services (Анализ кешбэка)."""
    print("\n" + "=" * 80)
    print("ЗАПУСК МОДУЛЯ SERVICES (АНАЛИЗ КЕШБЭКА)")
    print("=" * 80)

    try:
        # Загружаем транзакции
        df = read_transactions_from_excel()

        if df.empty:
            print(" Нет данных для анализа")
            return

        # Анализируем кешбэк за текущий месяц
        current_date = datetime.now()
        year = current_date.year
        month = current_date.month

        logger.info(f"Анализ кешбэка за {year}-{month:02d}")

        result_json = analyze_cashback_categories(df, year, month)
        result = json.loads(result_json)

        print(f"\n РЕЗУЛЬТАТ АНАЛИЗА КЕШБЭКА за {year}.{month:02d}:")

        if result:
            print("\n ПОТЕНЦИАЛЬНЫЙ КЕШБЭК ПО КАТЕГОРИЯМ:")
            for category, cashback in result.items():
                print(f"  {category}: {cashback} ₽")
        else:
            print("  Нет расходных операций за указанный период")

        # Сохраняем результат
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"cashback_analysis_{year}_{month:02d}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n Результат сохранен в: {output_file}")

    except Exception as e:
        logger.error(f"Ошибка при запуске модуля services: {e}", exc_info=True)
        print(f" Ошибка: {e}")


def run_reports_functionality() -> None:
    """Запускает функциональность модуля reports (Отчеты)."""
    print("\n" + "=" * 80)
    print("ЗАПУСК МОДУЛЯ REPORTS (ОТЧЕТЫ)")
    print("=" * 80)

    try:
        # Загружаем транзакции
        df = read_transactions_from_excel()

        if df.empty:
            print(" Нет данных для формирования отчетов")
            return

        # 1. Отчет по категории
        print("\n ОТЧЕТ ПО КАТЕГОРИИ 'Супермаркеты':")
        category_result = spending_by_category(df, "Супермаркеты")

        if not category_result.empty:
            total = abs(category_result["Сумма платежа"].sum())
            count = len(category_result)
            print(f"  Найдено транзакций: {count}")
            print(f"  Общая сумма: {total:.2f} ₽")
            print("\n  Последние транзакции:")
            for _, row in category_result.head(3).iterrows():
                date = row.get("Дата операции", "Неизвестно")
                amount = abs(row.get("Сумма платежа", 0))
                desc = row.get("Описание", "")[:30]
                print(f"    {date} - {desc}: {amount:.2f} ₽")
        else:
            print("  Нет данных по категории 'Супермаркеты'")

        # 2. Отчет по дням недели
        print("\n ОТЧЕТ ПО ДНЯМ НЕДЕЛИ:")
        weekday_result = spending_by_weekday(df)

        if not weekday_result.empty:
            for _, row in weekday_result.iterrows():
                day = row.get("название_дня", "")
                avg = row.get("средние_траты", 0)
                total = row.get("общие_траты", 0)
                count = row.get("количество_транзакций", 0)
                print(f"  {day}:")
                print(f"    Средние траты: {avg:.2f} ₽")
                print(f"    Всего: {total:.2f} ₽ ({count} транзакций)")
        else:
            print("Нет данных для анализа по дням недели")

        # 3. Отчет по рабочим/выходным дням
        print("\n ОТЧЕТ ПО РАБОЧИМ/ВЫХОДНЫМ ДНЯМ:")
        workday_result = spending_by_workday(df)

        if workday_result:
            workdays = workday_result.get("рабочие_дни", {})
            weekends = workday_result.get("выходные_дни", {})
            comparison = workday_result.get("сравнение", {})

            print(" Рабочие дни:")
            print(f"Всего: {workdays.get('total_spent', 0):.2f} ₽")
            print(f"Средний чек: {workdays.get('avg_spent_per_transaction', 0):.2f} ₽")

            print("Выходные дни:")
            print(f"Всего: {weekends.get('total_spent', 0):.2f} ₽")
            print(f"Средний чек: {weekends.get('avg_spent_per_transaction', 0):.2f} ₽")

            print("Сравнение:")
            print(
                f"Доля рабочих дней: {comparison.get('доля_рабочих_дней_в_тратах', '0%')}"
            )
            print(
                f"Доля выходных дней: {comparison.get('доля_выходных_дней_в_тратах', '0%')}"
            )
            print(f"Соотношение: {comparison.get('соотношение_рабочие_к_выходным', 0)}")
        else:
            print("Нет данных для анализа по рабочим/выходным дням")

        # Отчеты автоматически сохраняются декоратором в папку reports/
        print("\n Отчеты автоматически сохранены в папку 'reports/'")

    except Exception as e:
        logger.error(f"Ошибка при запуске модуля reports: {e}", exc_info=True)
        print(f" Ошибка: {e}")


def check_environment() -> bool:
    """Проверяет наличие всех необходимых файлов и настроек."""
    print("\n ПРОВЕРКА ОКРУЖЕНИЯ")
    print("-" * 40)

    checks = []

    # Проверка файла с транзакциями
    data_file = Path("data/operations.xlsx")
    if data_file.exists():
        print(" Файл с транзакциями найден")
        checks.append(True)
    else:
        print(" Файл с транзакциями не найден (ожидается в data/operations.xlsx)")
        checks.append(False)

    # Проверка user_settings.json
    settings_file = Path("user_settings.json")
    if settings_file.exists():
        print(" Файл настроек пользователя найден")
        try:
            settings = get_user_settings()
            print(f"   Валюты: {settings.get('user_currencies', [])}")
            print(f"   Акции: {settings.get('user_stocks', [])}")
            checks.append(True)
        except Exception as e:
            print(f" Ошибка при чтении настроек: {e}")
            checks.append(False)
    else:
        print(" Файл настроек пользователя не найден (будет использован шаблон)")
        checks.append(False)

    # Проверка .env файла
    env_file = Path(".env")
    if env_file.exists():
        print(" .env файл найден")
        checks.append(True)
    else:
        print(" .env файл не найден (API для курсов валют и акций могут не работать)")
        print("   Создайте .env на основе .env_template")
        checks.append(False)

    # Проверка наличия API ключей (необязательно)
    from dotenv import load_dotenv

    load_dotenv()

    api_key_exchange = os.getenv("EXCHANGE_API_KEY")
    api_key_stock = os.getenv("STOCK_API_KEY")

    if api_key_exchange:
        print(" API ключ для валют найден")
    else:
        print("  API ключ для валют не найден (курсы могут быть недоступны)")

    if api_key_stock:
        print(" API ключ для акций найден")
    else:
        print("  API ключ для акций не найден (цены акций могут быть недоступны)")

    return all(checks[:2])  # Возвращаем True, если есть данные и настройки


def main():
    """Главная функция приложения."""
    print("\n" + " " * 40)
    print(" БАНКОВСКИЙ АНАЛИЗАТОР ТРАНЗАКЦИЙ ".center(60))
    print(" " * 40)

    # Создаем необходимые директории
    Path("output").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    # Проверяем окружение
    if not check_environment():
        print("\n  Некоторые проверки не пройдены, но продолжу работу...")

    # Запускаем все модули
    run_views_functionality()
    run_services_functionality()
    run_reports_functionality()

    print("\n" + "=" * 80)
    print(" ВСЕ ФУНКЦИОНАЛЬНОСТИ УСПЕШНО ВЫПОЛНЕНЫ")
    print("=" * 80)
    print("\n Результаты сохранены в папках:")
    print("  - output/ - результаты views и services")
    print("  - reports/ - результаты reports")
    print("  - app.log - лог выполнения")


if __name__ == "__main__":
    import os

    main()
