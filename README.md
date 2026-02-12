# База знаний организации по ремонту и обслуживанию лифтового оборудования

## Обзор

Интегрированная система, объединяющая:
- 🎫 **Систему заявок на ремонт** (lift-repair-tickets)
- 📦 **Складское управление** (warehouse-management)
- 📚 **Базу знаний** по ремонту и обслуживанию

## Архитектура системы

```
┌─────────────────────────────────────────────────────────────┐
│                     БАЗА ЗНАНИЙ                             │
│              (Knowledge Base System)                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Заявки     │  │    Склад     │  │  База знаний     │  │
│  │   (8081)     │◄─┤   (8080)     │◄─┤   (8082)         │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│         │                  │                  │            │
│         └──────────────────┼──────────────────┘            │
│                            ▼                               │
│                   ┌──────────────────┐                     │
│                   │   MCP Сервер     │                     │
│                   │   (Интеграция)   │                     │
│                   └──────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

## Структура базы данных

### 1. Таблица знаний (knowledge_articles)
- `id` - уникальный ID
- `category` - категория (неисправность, инструкция, решение)
- `title` - название
- `content` - содержание
- `equipment_type` - тип оборудования
- `manufacturer` - производитель
- `symptoms` - симптомы (JSON)
- `solution` - решение
- `parts_used` - используемые запчасти (JSON)
- `created_at`, `updated_at` - даты

### 2. Таблица связи заявок и знаний (ticket_knowledge)
- `ticket_id` - ID заявки
- `knowledge_id` - ID статьи знаний
- `relevance_score` - оценка релевантности

### 3. Таблица объектов (objects)
- `id` - ID объекта
- `address` - адрес
- `client_id` - ID клиента
- `elevator_model` - модель лифта
- `elevator_id` - ID лифта
- `installation_date` - дата установки
- `last_maintenance` - последнее обслуживание

### 4. Таблица истории обслуживания (maintenance_history)
- `id` - ID записи
- `object_id` - ID объекта
- `ticket_id` - ID заявки
- `date` - дата работ
- `work_type` - тип работ
- `description` - описание
- `parts_used` - использованные запчасти
- `technician` - техник

### 5. Таблица типовых неисправностей (common_issues)
- `id` - ID
- `issue_code` - код неисправности
- `description` - описание
- `typical_causes` - типичные причины (JSON)
- `solutions` - решения (JSON)
- `priority` - приоритет

## Интеграция между системами

### Связь Заявки ↔ Склад
1. При создании заявки → проверка наличия запчастей на складе
2. При закрытии заявки → списание использованных запчастей
3. Приоритет заявки → автоматический резерв запчастей

### Связь Заявки ↔ База знаний
1. Автоматический поиск похожих решений при создании заявки
2. Рекомендации по ремонту на основе истории
3. Пополнение базы знаний из закрытых заявок

### Связь Склад ↔ База знаний
1. Каталог запчастей с привязкой к оборудованию
2. Рекомендуемые запчасти для типовых ремонтов
3. Прогнозирование потребности на основе статистики

## API Endpoints

### База знаний
- `GET /api/kb/search` - поиск по базе знаний
- `POST /api/kb/articles` - создание статьи
- `GET /api/kb/articles/<id>` - получение статьи
- `PUT /api/kb/articles/<id>` - обновление статьи
- `GET /api/kb/similar/<ticket_id>` - похожие решения для заявки

### Объекты
- `GET /api/objects` - список объектов
- `POST /api/objects` - создание объекта
- `GET /api/objects/<id>/history` - история обслуживания
- `GET /api/objects/<id>/stats` - статистика по объекту

### Интеграция
- `POST /api/integration/parts-for-ticket` - запчасти для заявки
- `POST /api/integration/consume-parts` - списание запчастей
- `GET /api/integration/stock-check` - проверка наличия

## Запуск системы

```bash
# 1. Установка зависимостей
pip install -r requirements.txt

# 2. Инициализация базы данных
python init_database.py

# 3. Запуск базы знаний (порт 8082)
python knowledge_base.py

# 4. Запуск интеграционного сервера
python integration_server.py
```

## Порты системы
- **8080** - Складское управление
- **8081** - Система заявок
- **8082** - База знаний

## Быстрый старт

### 1. Установка

```bash
# Клонирование репозиториев
git clone https://github.com/swiftskytex-coder/lift-repair-tickets.git
git clone https://github.com/swiftskytex-coder/warehouse-management.git

# Переход в директорию базы знаний
cd lift-repair-knowledge-base

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Инициализация

```bash
# Запуск интерактивного меню
python init_and_run.py

# Или пошагово:
# Инициализация БД
python -c "from knowledge_db import KnowledgeBaseDB; KnowledgeBaseDB()"

# Заполнение данными
python seed_data.py

# Запуск сервера
python knowledge_base.py
```

### 3. Запуск всех систем

```bash
# Терминал 1 - Склад (из warehouse-management)
python warehouse_system.py

# Терминал 2 - Заявки (из lift-repair-tickets)
python ticket_system.py

# Терминал 3 - База знаний
python knowledge_base.py
```

### 4. Доступ к системам

- **База знаний**: http://localhost:8082
- **Система заявок**: http://localhost:8081
- **Склад**: http://localhost:8080

## API Endpoints

### База знаний

#### Статьи
- `GET /api/kb/articles` - список статей
  - Query params: `q`, `category`, `equipment_type`, `manufacturer`, `limit`
- `POST /api/kb/articles` - создание статьи
- `GET /api/kb/articles/<id>` - получение статьи
- `POST /api/kb/search` - поиск по базе знаний

#### Объекты
- `GET /api/objects` - список объектов
- `POST /api/objects` - создание объекта
- `GET /api/objects/<id>` - получение объекта
- `GET /api/objects/<id>/history` - история обслуживания
- `POST /api/objects/<id>/history` - добавление записи обслуживания

#### Типовые неисправности
- `GET /api/issues` - список типовых неисправностей
- `POST /api/issues` - создание неисправности

#### Поиск решений
- `POST /api/solutions/find` - поиск решений для проблемы

### Интеграция

#### Заявки ↔ База знаний
- `GET /api/integration/ticket/<id>/context` - контекст заявки
- `GET /api/integration/ticket/<id>/suggest` - рекомендации для заявки
- `POST /api/integration/ticket/<id>/create-knowledge` - создание статьи из заявки

#### Склад ↔ База знаний
- `POST /api/integration/parts/check` - проверка наличия запчастей
- `POST /api/integration/parts/recommend` - рекомендации по запчастям
- `POST /api/integration/parts/consume` - списание запчастей

#### Отчеты
- `GET /api/reports/maintenance/<object_id>` - отчет по обслуживанию

### Статистика
- `GET /api/statistics` - статистика базы знаний
- `GET /api/integration/statistics` - статистика интеграции
- `GET /api/health` - проверка работоспособности

## Примеры использования API

### Поиск решения для проблемы
```bash
curl -X POST http://localhost:8082/api/solutions/find \
  -H "Content-Type: application/json" \
  -d '{
    "problem": "Не работает кнопка вызова",
    "elevator_model": "ЛП-0611"
  }'
```

### Проверка наличия запчастей
```bash
curl -X POST http://localhost:8082/api/integration/parts/check \
  -H "Content-Type: application/json" \
  -d '{
    "parts": ["768", "2498", "564"]
  }'
```

### Получение контекста заявки
```bash
curl http://localhost:8082/api/integration/ticket/123/context
```

### Создание статьи из заявки
```bash
curl -X POST http://localhost:8082/api/integration/ticket/123/create-knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Решение проблемы с кнопкой",
    "solution_text": "Заменить кнопку вызова",
    "parts_used": {"768": 1}
  }'
```

## Структура проекта

```
lift-repair-knowledge-base/
├── knowledge_db.py              # Модуль работы с БД
├── knowledge_base.py            # Веб-сервер (Flask)
├── integration_manager.py       # Менеджер интеграции
├── seed_data.py                 # Начальные данные
├── init_and_run.py              # Скрипт запуска
├── requirements.txt             # Зависимости
├── README.md                    # Документация
├── templates/
│   └── knowledge_dashboard.html # Веб-интерфейс
└── knowledge_base.db            # База данных SQLite
```

## Типовые неисправности (предустановленные)

Код | Описание | Приоритет
--- | --- | ---
LIFT-001 | Лифт не вызывается с этажа | Высокий
LIFT-002 | Двери кабины не открываются | Срочный
LIFT-003 | Лифт останавливается между этажами | Срочный
LIFT-004 | Посторонние шумы при работе | Обычный
LIFT-005 | Не горит освещение в кабине | Обычный
LIFT-006 | Лифт не закрывает двери | Высокий
LIFT-007 | Резкое торможение или рывки | Срочный
LIFT-008 | Не работает индикация этажей | Низкий
LIFT-009 | Аварийная остановка | Срочный
LIFT-010 | Лифт медленно движется | Высокий

## Интеграция с другими системами

### Система заявок (8081)
- Автоматический поиск решений при создании заявки
- Рекомендации по запчастям
- Сохранение решений в базу знаний

### Склад (8080)
- Проверка наличия запчастей
- Резервирование запчастей для заявок
- Списание использованных материалов

## Разработка

### Добавление новой статьи
```python
from knowledge_db import KnowledgeBaseDB

db = KnowledgeBaseDB()
article_id = db.create_knowledge_article({
    'category': 'инструкция',
    'title': 'Название статьи',
    'content': 'Содержание...',
    'equipment_type': 'пассажирский',
    'manufacturer': 'МЛЗ',
    'symptoms': ['симптом 1', 'симптом 2'],
    'solution': 'Описание решения',
    'parts_used': ['768', '2498'],
    'difficulty_level': 3,
    'estimated_time': 60
})
```

### Добавление объекта
```python
db = KnowledgeBaseDB()
object_id = db.create_object({
    'address': 'ул. Ленина, д. 1',
    'client_name': 'УК "Центральная"',
    'elevator_model': 'ЛП-0611',
    'elevator_id': 'ЛИФТ-001'
})
```

## Лицензия

MIT License - свободное использование
