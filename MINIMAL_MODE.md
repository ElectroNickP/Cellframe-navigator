# Minimal Mode - Bot Only Configuration

## 🎯 Цель

Запустить Telegram бота **только с токеном**, без настройки RPC endpoints для блокчейнов.

## ✅ Что работает в минимальном режиме

### Bot Commands (полностью работают)
- ✅ `/start` и `/help` - помощь и информация
- ✅ `/bridge` - создание bridge сессий (сохраняются в БД)
- ✅ `/bind` - привязка адресов
- ✅ `/fees` - показ информации о комиссиях (дефолтные оценки)
- ✅ `/mysessions` - список сессий пользователя

### Database & Storage
- ✅ PostgreSQL работает полностью
- ✅ Сессии сохраняются
- ✅ Пользователи регистрируются
- ✅ Адреса привязываются

### User Experience
- ✅ Пошаговый UX flow
- ✅ Inline клавиатуры
- ✅ Валидация формата адресов
- ✅ Сохранение всей информации

## ❌ Что НЕ работает без RPC

### Blockchain Monitoring
- ❌ Отслеживание реальных транзакций
- ❌ Подсчет подтверждений
- ❌ Проверка статуса транзакций
- ❌ `/status <tx_hash>` с реальной диагностикой

### Notifications
- ❌ Push-уведомления о статусе транзакций
- ❌ Автоматические алерты
- ❌ Прогресс подтверждений

### Diagnostics
- ❌ Умная диагностика транзакций
- ❌ Проблемы с транзакциями
- ❌ CFSCAN интеграция

## 🚀 Quick Start - Минимальный запуск

### Шаг 1: Получить токен бота

1. Открой Telegram
2. Найди [@BotFather](https://t.me/BotFather)
3. Отправь `/newbot`
4. Следуй инструкциям
5. Скопируй токен (выглядит как `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Шаг 2: Создать .env

```bash
cp env.minimal.example .env
```

Отредактируй `.env`:
```env
TELEGRAM_BOT_TOKEN=твой_токен_от_BotFather

# Остальное оставь как есть или удали
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/cellframe
REDIS_URL=redis://redis:6379/0
```

### Шаг 3: Запустить

```bash
docker-compose -f docker-compose.minimal.yml up --build
```

Или если хочешь в фоне:
```bash
docker-compose -f docker-compose.minimal.yml up -d
```

### Шаг 4: Проверить

1. Открой своего бота в Telegram
2. Отправь `/start`
3. Бот должен ответить!

## 📋 Что запускается

Только 4 сервиса (без watcher и worker):

```
✅ PostgreSQL  - База данных
✅ Redis       - Кеш и очереди
✅ Migration   - Создание таблиц (запускается 1 раз)
✅ Bot         - Telegram бот
```

## 💡 Когда это полезно

### 1. Тестирование бота
Проверить UX, команды, flow без настройки блокчейнов

### 2. Разработка
Работать над bot handlers без доступа к RPC

### 3. Демо
Показать интерфейс бота без реального моста

### 4. Быстрый старт
Запустить за 5 минут, настроить RPC позже

## ⚙️ Добавление мониторинга позже

Когда будешь готов добавить мониторинг:

### 1. Добавь RPC endpoints в .env

```env
# Раскомментируй нужные
ETH_RPC_URL=https://mainnet.infura.io/v3/твой_ключ
BSC_RPC_URL=https://bsc-dataseed1.ninicoin.io
CF_RPC_URL=http://твой-cellframe-node:8079
CF_NETWORK=backbone
```

### 2. Переключись на полный docker-compose

```bash
# Останови минимальный
docker-compose -f docker-compose.minimal.yml down

# Запусти полный
docker-compose up -d
```

Данные сохранятся (volumes не удаляются)!

## 🔧 Troubleshooting

### Бот не отвечает

1. **Проверь токен:**
```bash
# Посмотри логи
docker-compose -f docker-compose.minimal.yml logs bot

# Ищи ошибки типа "Unauthorized" или "Invalid token"
```

2. **Проверь, что сервисы запущены:**
```bash
docker-compose -f docker-compose.minimal.yml ps

# Все должны быть "Up"
```

3. **Проверь подключение к БД:**
```bash
docker-compose -f docker-compose.minimal.yml logs migration

# Должно быть "INFO  [alembic.runtime.migration] Running upgrade"
```

### База данных не создается

```bash
# Пересоздай volumes
docker-compose -f docker-compose.minimal.yml down -v
docker-compose -f docker-compose.minimal.yml up --build
```

### Redis ошибки

```bash
# Проверь Redis
docker-compose -f docker-compose.minimal.yml exec redis redis-cli ping
# Должен ответить: PONG
```

## 📊 Ресурсы

Минимальная конфигурация очень легкая:

- **RAM**: ~300MB
- **CPU**: минимальная нагрузка
- **Disk**: ~500MB (Docker images + volumes)

Можно запускать даже на слабом VPS!

## 🔄 Переход на полный режим

### Вариант 1: Постепенно

Добавляй RPC по одному:

```env
# День 1: Только Ethereum
ETH_RPC_URL=...

# День 2: Добавь BSC
BSC_RPC_URL=...

# День 3: Добавь Cellframe
CF_RPC_URL=...
```

Перезапускай:
```bash
docker-compose restart watcher
```

### Вариант 2: Сразу всё

Заполни все RPC и переключись на `docker-compose.yml`:

```bash
docker-compose down
docker-compose up -d
```

## 💬 Что говорить пользователям

Если бот работает в минимальном режиме, можно добавить в `/help`:

```
⚠️ Бот работает в режиме регистрации.
Мониторинг транзакций временно недоступен.

Вы можете:
✅ Создавать bridge сессии (/bridge)
✅ Привязывать адреса (/bind)
✅ Смотреть комиссии (/fees)

❌ Отслеживание транзакций будет добавлено позже
```

## 📝 Summary

**Минимальная конфигурация** = **Только токен бота**

```env
TELEGRAM_BOT_TOKEN=твой_токен
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/cellframe
REDIS_URL=redis://redis:6379/0
```

**Запуск:**
```bash
docker-compose -f docker-compose.minimal.yml up
```

**Результат:**
- ✅ Бот работает и отвечает
- ✅ Все команды доступны
- ✅ Данные сохраняются
- ❌ Мониторинг блокчейнов отключен

**Когда нужно больше:**
Добавь RPC endpoints и переключись на полный `docker-compose.yml`

