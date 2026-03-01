# Vibe-Import: Подробная инструкция по использованию 🚀

## Что это такое?

**Vibe-Import** — это инструмент, который автоматически генерирует Python-пакеты на основе того, как вы их используете в коде. 

Идея простая: вы пишете код, импортируете пакет, который ещё не существует, используете его функции и классы — а Vibe-Import анализирует ваш код и генерирует этот пакет с помощью LLM (языковой модели).

## Быстрый старт

### 1. Установка

```bash
# Клонируем репозиторий
git clone <repo-url>
cd vibe-import

# Устанавливаем в режиме разработки
pip install -e .
```

### 2. Получение API ключа (бесплатно!)

Мы используем **OpenRouter** — это сервис, который предоставляет доступ к разным LLM, включая бесплатные модели.

1. Перейдите на https://openrouter.ai/
2. Зарегистрируйтесь (можно через Google/GitHub)
3. Перейдите в https://openrouter.ai/keys
4. Создайте новый API ключ
5. Скопируйте ключ

### 3. Настройка API ключа

**Способ 1: Через .env файл (рекомендуется)**

```bash
# Копируем пример
cp .env.example .env

# Редактируем .env и добавляем ключ
# OPENROUTER_API_KEY=sk-or-v1-ваш-ключ-здесь
```

**Способ 2: Через переменную окружения**

```bash
# Добавьте в ваш .bashrc или .zshrc
export OPENROUTER_API_KEY="sk-or-v1-ваш-ключ-здесь"
```

**Способ 3: Передать напрямую в CLI**

```bash
vibe-import generate my_app.py --api-key sk-or-v1-ваш-ключ-здесь
```

### 4. Пишем код с несуществующими импортами

Создайте файл `my_app.py`:

```python
# my_app.py
from magic_utils import calculate_magic, MagicProcessor

# Используем функцию
result = calculate_magic(42, mode="fast")
print(f"Результат: {result.value}")

# Используем класс
processor = MagicProcessor(config={"threads": 4})
data = processor.process([1, 2, 3, 4, 5])
processor.save("output.json")
```

### 5. Анализируем код

```bash
# Смотрим какие импорты отсутствуют
vibe-import analyze my_app.py

# С подробной информацией об использовании
vibe-import analyze my_app.py --show-usage
```

Вывод покажет:
- Какие импорты отсутствуют
- Как они используются (функции, классы, аргументы)

### 6. Генерируем пакет

```bash
# Сначала посмотрим что будет сгенерировано (dry-run)
vibe-import generate my_app.py --dry-run

# Генерируем пакет
vibe-import generate my_app.py --output ./generated
```

### 7. Используем сгенерированный пакет

```bash
# Добавляем путь к сгенерированному пакету
export PYTHONPATH="${PYTHONPATH}:./generated"

# Или копируем в проект
cp -r generated/magic_utils ./

# Теперь код работает!
python my_app.py
```

## Команды CLI

### `vibe-import analyze`

Анализирует код и показывает отсутствующие импорты.

```bash
# Анализ файла
vibe-import analyze my_app.py

# Анализ директории
vibe-import analyze ./src --recursive

# С подробностями
vibe-import analyze my_app.py --show-usage
```

### `vibe-import generate`

Генерирует отсутствующие пакеты.

```bash
# Базовое использование (OpenRouter с бесплатной моделью)
vibe-import generate my_app.py

# Указать выходную директорию
vibe-import generate my_app.py --output ./packages

# Использовать другую модель
vibe-import generate my_app.py --model google/gemma-2-9b-it:free

# Использовать OpenAI (нужен API ключ)
vibe-import generate my_app.py --provider openai --api-key sk-...

# Dry-run (показать что будет сгенерировано)
vibe-import generate my_app.py --dry-run

# Без документации
vibe-import generate my_app.py --no-docs

# Подробный прогресс (verbose режим)
vibe-import generate my_app.py --verbose
```

### Ускорение генерации

Если генерация занимает слишком много времени, попробуйте:

1. **Использовать более быструю модель**
```bash
# Самая быстрая бесплатная модель
vibe-import generate my_app.py --model meta-llama/llama-3.2-3b-instruct:free

# Или другую быструю модель
vibe-import generate my_app.py --model huggingfaceh4/zephyr-7b-beta:free
```

2. **Использовать verbose режим для отслеживания прогресса**
```bash
vibe-import generate my_app.py --verbose
```

3. **Проверить скорость интернета** - генерация зависит от скорости API

### `vibe-import inspect`

Показывает структуру Python файла.

```bash
vibe-import inspect my_app.py
vibe-import inspect my_app.py --format json
```

### `vibe-import spec`

Генерирует спецификацию в JSON формате.

```bash
vibe-import spec my_app.py --output spec.json
```

### `vibe-import config`

Показывает текущую конфигурацию.

```bash
vibe-import config
```

Выводит:
- Настройки LLM (провайдер, модель, температура)
- Настройки вывода (директория, документация)
- Настройки анализа (рекурсивный поиск, исключения)
- Статус API ключей

## Доступные модели

### Бесплатные модели (OpenRouter)

OpenRouter предоставляет несколько бесплатных моделей:

| Модель | Описание |
|--------|----------|
| `qwen/qwen3-coder:free` | Qwen 3 Coder - для кода (по умолчанию) |
| `meta-llama/llama-3.2-3b-instruct:free` | Llama 3.2 3B - маленькая, быстрая |
| `google/gemma-2-9b-it:free` | Google Gemma 2 9B - хороший баланс |
| `mistralai/mistral-7b-instruct:free` | Mistral 7B - популярная |
| `huggingfaceh4/zephyr-7b-beta:free` | Zephyr 7B - для чата |
| `openchat/openchat-7b:free` | OpenChat 7B - разговорная |

Использование:
```bash
vibe-import generate my_app.py --model google/gemma-2-9b-it:free
```

### Любые модели OpenRouter

Вы можете использовать **ЛЮБУЮ** модель из OpenRouter, не только бесплатные!

```bash
# Платные модели (лучшее качество)
vibe-import generate my_app.py --model meta-llama/llama-3.1-70b-instruct
vibe-import generate my_app.py --model anthropic/claude-3.5-sonnet
vibe-import generate my_app.py --model openai/gpt-4o

# Список всех моделей: https://openrouter.ai/models
```

### Как указать модель

**Способ 1: CLI параметр (приоритет выше всего)**
```bash
vibe-import generate my_app.py --model google/gemma-2-9b-it:free
```

**Способ 2: .env файл**
```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-...
VIBE_IMPORT_MODEL=google/gemma-2-9b-it:free
```

**Способ 3: Переменная окружения**
```bash
export VIBE_IMPORT_MODEL=google/gemma-2-9b-it:free
vibe-import generate my_app.py
```

**Способ 4: Конфиг vibe-import.toml**
```toml
[llm]
provider = "openrouter"
model = "google/gemma-2-9b-it:free"
```

**Приоритет:** CLI > .env > переменная окружения > конфиг

## Примеры использования

### Пример 1: Утилиты для работы с данными

```python
# data_app.py
from data_helpers import DataPipeline, clean_data, validate_schema

# Создаём пайплайн
pipeline = DataPipeline(source="database", batch_size=100)

# Обрабатываем данные
with pipeline:
    raw = pipeline.fetch()
    cleaned = clean_data(raw, remove_nulls=True)
    
    if validate_schema(cleaned, schema="user"):
        pipeline.save(cleaned, format="parquet")
```

```bash
vibe-import generate data_app.py --output ./libs
```

### Пример 2: HTTP клиент

```python
# api_client.py
from my_api_client import APIClient, RequestError

client = APIClient(base_url="https://api.example.com", timeout=30)

try:
    response = client.get("/users", params={"limit": 10})
    users = response.json()
    
    for user in users:
        client.post("/notifications", data={"user_id": user["id"]})
except RequestError as e:
    print(f"Ошибка: {e.message}")
```

```bash
vibe-import generate api_client.py
```

### Пример 3: Конфигурация приложения

```python
# config_example.py
from app_config import Config, load_config, ConfigError

# Загружаем конфигурацию
config = load_config("settings.yaml")

# Используем
print(config.database.host)
print(config.database.port)
print(config.api.secret_key)

# Валидация
if not config.is_valid():
    raise ConfigError("Invalid configuration")
```

## Конфигурационный файл

Создайте `vibe-import.toml` в корне проекта:

```toml
[llm]
provider = "openrouter"
model = "meta-llama/llama-3.2-3b-instruct:free"
temperature = 0.2

[output]
directory = "./generated"
include_docs = true
docstring_style = "google"

[analysis]
recursive = true
exclude_patterns = ["**/venv/**", "**/__pycache__/**"]
```

## Переменные окружения и .env файл

Вы можете настроить Vibe-Import через `.env` файл в корне проекта:

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-ваш-ключ-здесь
VIBE_IMPORT_PROVIDER=openrouter
VIBE_IMPORT_MODEL=qwen/qwen3-coder:free
VIBE_IMPORT_TEMPERATURE=0.2
```

| Переменная | Описание |
|------------|----------|
| `OPENROUTER_API_KEY` | API ключ для OpenRouter |
| `OPENAI_API_KEY` | API ключ для OpenAI |
| `ANTHROPIC_API_KEY` | API ключ для Anthropic |
| `VIBE_IMPORT_PROVIDER` | Провайдер (openrouter, openai, anthropic) |
| `VIBE_IMPORT_MODEL` | Модель для генерации |
| `VIBE_IMPORT_TEMPERATURE` | Температура генерации (0-1) |
| `VIBE_IMPORT_MAX_TOKENS` | Максимальное количество токенов |

## Как это работает?

1. **Парсинг**: Vibe-Import парсит ваш Python код с помощью AST (Abstract Syntax Tree)

2. **Обнаружение**: Находит все импорты, которые не существуют (не установлены и не в стандартной библиотеке)

3. **Анализ использования**: Для каждого отсутствующего импорта анализирует:
   - Вызовы функций и их аргументы
   - Создание экземпляров классов
   - Вызовы методов
   - Доступ к атрибутам
   - Использование как context manager (`with`)
   - Использование как итератор (`for`)

4. **Вывод типов**: На основе использования выводит:
   - Сигнатуры функций (параметры и типы)
   - Структуру классов (init, методы, атрибуты)
   - Возвращаемые типы

5. **Генерация**: Отправляет спецификацию в LLM и получает готовый код

6. **Документация**: Автоматически создаёт README и документацию API

## Советы

1. **Пишите понятный код** — чем яснее вы используете функции и классы, тем лучше будет результат

2. **Используйте говорящие имена** — `calculate_total(items)` лучше чем `calc(x)`

3. **Добавляйте типы где возможно** — `process(data: list[int])` даст больше информации

4. **Проверяйте dry-run** — всегда смотрите что будет сгенерировано перед генерацией

5. **Редактируйте результат** — сгенерированный код — это отправная точка, не финальный результат

## Ограничения

- Бесплатные модели могут генерировать код худшего качества чем платные (GPT-4, Claude)
- Сложная логика может потребовать ручной доработки
- Не все паттерны использования могут быть правильно распознаны

## Troubleshooting

### "API key not found"
```bash
# Проверьте .env файл
cat .env

# Или установите переменную окружения
export OPENROUTER_API_KEY="ваш-ключ"
```

### Ошибка 429 (Rate Limit)
Если вы получаете ошибку 429, это значит что вы превысили лимит запросов. Vibe-Import автоматически делает retry с экспоненциальной задержкой (до 5 попыток).

**Решения:**
1. Подождите немного и попробуйте снова
2. Используйте другую бесплатную модель
3. Получите платный план на OpenRouter

### "Module not found" после генерации
```bash
export PYTHONPATH="${PYTHONPATH}:./generated"
# или
cp -r generated/package_name ./
```

### Плохое качество генерации
Попробуйте другую модель:
```bash
vibe-import generate my_app.py --model google/gemma-2-9b-it:free
```

### Установка зависимостей
```bash
# Переустановите с зависимостями
pip install -e ".[dev]"
```

## Поддержка

Если у вас возникли проблемы, создайте issue в репозитории проекта.