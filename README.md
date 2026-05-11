# Diploma

Проект состоит из desktop-интерфейса, backend-сервиса, отдельного ML-сервиса и PostgreSQL.

Основная логика разделена на пакеты:

- `packages/backend` - FastAPI backend, работа с базой данных, бизнес-логика, API для frontend и обмен с ML-сервисом.
- `packages/frontend` - desktop-приложение на PySide6.
- `packages/ml` - отдельный FastAPI ML-сервис с моделью компьютерного зрения.
- `docker-compose.yml` - локальный PostgreSQL.

Backend и frontend входят в корневой `uv workspace`. ML вынесен отдельно и имеет собственный `uv.lock`, потому что использует другой стек зависимостей и Python `>=3.11,<3.12`.

## Требования

Перед запуском должны быть установлены:

- Python 3.13 для backend/frontend;
- Python 3.11 для ML-сервиса;
- `uv`;
- Docker Desktop;
- Git.

Проверка:

```powershell
python --version
uv --version
docker --version
```

## Порты

По умолчанию используются такие адреса:

| Компонент | URL |
| --- | --- |
| ML-сервис | `http://localhost:8000` |
| Backend | `http://localhost:8001` |
| PostgreSQL | `localhost:5433` |

## Первичная установка

Команды ниже рассчитаны на PowerShell и выполняются из корня проекта, если не указано другое.

### 1. Установить зависимости backend/frontend

```powershell
uv sync
```

Корневой `pyproject.toml` подключает пакеты `backend` и `frontend` как workspace-пакеты.

### 2. Запустить PostgreSQL

```powershell
docker compose up -d postgres
```

Параметры локальной базы:

```text
Host: localhost
Port: 5433
Database: diploma
User: diploma
Password: diploma
```

Строка подключения:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://diploma:diploma@localhost:5433/diploma"
```

### 3. Применить миграции базы данных

```powershell
cd packages/backend
$env:DATABASE_URL = "postgresql+psycopg://diploma:diploma@localhost:5433/diploma"
uv run alembic upgrade head
cd ..\..
```

Миграции создают таблицы `input_sources`, `test_runs`, `detections` и `tracking_updates`.

### 4. Подготовить ML-сервис

ML-сервис ставится отдельно от корневого workspace.

```powershell
cd packages/ml
uv sync
```

Создайте файл `packages/ml/.env`:

```dotenv
ML_DATASET_ROOT=F:\path\to\dataset
BACKEND_URL=http://localhost:8001
ML_DEVICE=cpu
```

Если есть CUDA и модель должна работать на GPU, можно заменить:

```dotenv
ML_DEVICE=cuda
```

По умолчанию модель берется из:

```text
packages/ml/src/ml/inference/models/detect/train-2/weights/best.pt
```

Если нужно указать другой файл модели, добавьте в `.env`:

```dotenv
MODEL_PATH=F:\path\to\best.pt
```

После настройки вернитесь в корень:

```powershell
cd ..\..
```

## Запуск проекта

### Запуск одной командой

После первичной установки можно запустить основные сервисы через bat-файл из корня проекта:

```powershell
.\start_all.bat
```

Скрипт выполняет следующие действия:

- запускает PostgreSQL через Docker Compose;
- ждёт готовности базы данных;
- применяет Alembic-миграции;
- открывает отдельное окно для ML-сервиса;
- открывает отдельное окно для backend;
- открывает отдельное окно для frontend.

Перед запуском убедитесь, что создан файл `packages/ml/.env` и в нём задана переменная `ML_DATASET_ROOT`.

### Ручной запуск

Для полного запуска удобно открыть четыре терминала.

### Терминал 1: PostgreSQL

```powershell
docker compose up -d postgres
```

Проверить контейнер:

```powershell
docker compose ps
```

### Терминал 2: ML-сервис

```powershell
cd packages/ml
uv run uvicorn ml.main:app --host 127.0.0.1 --port 8000 --reload
```

Проверка:

```text
http://localhost:8000/health
http://localhost:8000/docs
```

### Терминал 3: Backend

```powershell
cd packages/backend
$env:DATABASE_URL = "postgresql+psycopg://diploma:diploma@localhost:5433/diploma"
$env:ML_URL = "http://localhost:8000"
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

Проверка:

```text
http://localhost:8001/health
http://localhost:8001/docs
```

### Терминал 4: Frontend

```powershell
cd packages/frontend
$env:BACKEND_URL = "http://localhost:8001"
$env:ML_URL = "http://localhost:8000"
uv run python -m frontend.main
```

После этого откроется desktop-приложение.

## Быстрый повторный запуск

Если зависимости уже установлены, база создана и `.env` для ML уже настроен, достаточно:

1. Запустить PostgreSQL:

```powershell
docker compose up -d postgres
```

2. Запустить ML:

```powershell
cd packages/ml
uv run uvicorn ml.main:app --host 127.0.0.1 --port 8000 --reload
```

3. Запустить backend:

```powershell
cd packages/backend
$env:DATABASE_URL = "postgresql+psycopg://diploma:diploma@localhost:5433/diploma"
$env:ML_URL = "http://localhost:8000"
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

4. Запустить frontend:

```powershell
cd packages/frontend
$env:BACKEND_URL = "http://localhost:8001"
uv run python -m frontend.main
```

## Переменные окружения

### Backend

| Переменная | Значение по умолчанию | Назначение |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://diploma:diploma@localhost:5433/diploma` | Подключение к PostgreSQL |
| `ML_URL` | `http://localhost:8000` | Адрес ML-сервиса |
| `AUTO_CREATE_TABLES` | `0` | Автоматическое создание таблиц при запуске backend |
| `DETECTION_FRAMES_DIR` | `packages/backend/var/detection_frames` | Папка для сохраненных кадров детекций |

Для обычного запуска лучше использовать Alembic-миграции. `AUTO_CREATE_TABLES=1` удобно только для демонстрационного режима.

### ML

| Переменная | Значение по умолчанию | Назначение |
| --- | --- | --- |
| `ML_DATASET_ROOT` | нет | Путь к датасету, обязателен |
| `BACKEND_URL` | `http://localhost:8001` | Адрес backend-сервиса |
| `MODEL_PATH` | `packages/ml/src/ml/inference/models/detect/train-2/weights/best.pt` | Путь к весам модели |
| `ML_DEVICE` | `cuda` | Устройство для инференса: `cuda` или `cpu` |

### Frontend

| Переменная | Значение по умолчанию | Назначение |
| --- | --- | --- |
| `BACKEND_URL` | `http://localhost:8001` | Адрес backend-сервиса |
| `ML_URL` | `http://localhost:8000` | Адрес ML-сервиса |

## Работа с базой данных

Запустить PostgreSQL:

```powershell
docker compose up -d postgres
```

Остановить PostgreSQL:

```powershell
docker compose down
```

Посмотреть список таблиц:

```powershell
docker compose exec postgres psql -U diploma -d diploma -c "\dt"
```

Применить миграции:

```powershell
cd packages/backend
$env:DATABASE_URL = "postgresql+psycopg://diploma:diploma@localhost:5433/diploma"
uv run alembic upgrade head
```

## Архитектура запуска

Frontend не обращается напрямую к базе данных и ML-модели. Он работает с backend API.

Backend хранит данные в PostgreSQL, сохраняет кадры в `packages/backend/var`, вызывает ML-сервис по HTTP и отдает frontend уже подготовленные данные.

ML-сервис загружает модель YOLO, выполняет инференс и возвращает backend результаты детекции: класс объекта, уверенность модели, координаты рамки и время обработки.

Общий поток работы:

```text
Frontend -> Backend -> PostgreSQL
                 |
                 v
              ML-сервис
```

## Частые проблемы

### Backend не подключается к базе

Проверьте, что PostgreSQL запущен:

```powershell
docker compose ps
```

И что используется порт `5433`, а не стандартный `5432`.

### ML-сервис падает при старте

Проверьте файл `packages/ml/.env`. Переменная `ML_DATASET_ROOT` обязательна.

Если нет CUDA, установите:

```dotenv
ML_DEVICE=cpu
```

### Frontend не получает данные

Проверьте, что backend доступен:

```text
http://localhost:8001/health
```

И что frontend запущен с правильным адресом:

```powershell
$env:BACKEND_URL = "http://localhost:8001"
```

### Backend не видит ML-сервис

Проверьте:

```text
http://localhost:8000/health
```

И переменную:

```powershell
$env:ML_URL = "http://localhost:8000"
```
