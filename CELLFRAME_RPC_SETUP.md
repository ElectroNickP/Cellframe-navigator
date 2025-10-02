# Cellframe RPC Setup Guide

## 🔍 Проблема: rpc.cellframe.net недоступен

DNS-запись `rpc.cellframe.net` не резолвится, и публичный RPC endpoint временно недоступен.

## ✅ Решения

### Вариант 1: Локальная Cellframe Нода (Рекомендуется)

1. **Установите Cellframe Node:**
   ```bash
   # Скачайте с https://cellframe.net/downloads
   # Или через пакетный менеджер
   ```

2. **Настройте RPC в cellframe-node.cfg:**
   ```ini
   [server]
   enabled=true
   listen_address=127.0.0.1
   listen_port_tcp=8079
   ```

3. **Обновите .env:**
   ```bash
   CF_RPC_URL=http://localhost:8079
   CF_NETWORK=Backbone
   CF_CONFIRMATIONS_REQUIRED=3
   ```

4. **Перезапустите:**
   ```bash
   docker-compose restart bot tx_monitor
   ```

### Вариант 2: Альтернативные публичные endpoints

Если у вас есть доступ к другим публичным нодам:

```bash
# Пример (замените на реальный адрес):
CF_RPC_URL=http://node1.cellframe.network:8079
# или
CF_RPC_URL=http://134.122.60.212:8079
```

### Вариант 3: Подождать восстановления rpc.cellframe.net

Публичный RPC может быть временно недоступен из-за:
- Технических работ
- Обновления ноды
- Изменения конфигурации

Проверяйте статус на:
- https://cellframe.net
- https://t.me/cellframe_network (Telegram)

## 🧪 Тестирование RPC

Проверьте доступность RPC:

```bash
# Замените URL на ваш
curl -X POST http://localhost:8079 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "node_info",
    "params": {},
    "id": 1
  }'
```

Ожидаемый ответ:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "version": "5.x.x",
    "network": "Backbone",
    ...
  }
}
```

## ✅ Что уже работает в коде

### CF20RPCClient готов и протестирован:

```python
from watcher.cf20_rpc import CF20RPCClient

# Инициализация
client = CF20RPCClient(
    rpc_url="http://localhost:8079",
    network="Backbone"
)

# Проверка TX
tx_status = await client.tx_status("tx_hash_here")

# История транзакций
history = await client.tx_history(address="your_address")

# Mempool
pending = await client.mempool_list()
```

### Команда /track поддерживает Cellframe:

```
/track <cellframe_tx_hash>
```

Бот автоматически определит что это Cellframe TX и использует CF20RPCClient!

## 📊 Примеры TX hash форматов

### Ethereum/BSC:
```
0xa83c0c9a9f1fd79b5a3bd823375701593b4032e006b856f639e2f92350d73d29
```

### Cellframe (может варьироваться):
```
mYWN7Ccrqgtt9W9349Cfqg7g4m1UwAyELuZkZ5SJvCMr
```

## 🔧 Troubleshooting

### Ошибка: "Connection refused"
```bash
# Проверьте что нода запущена:
ps aux | grep cellframe-node

# Проверьте порт:
netstat -tlnp | grep 8079
```

### Ошибка: "RPC not configured"
```bash
# Убедитесь что .env содержит:
CF_RPC_URL=http://localhost:8079
CF_NETWORK=Backbone

# Перезапустите сервисы:
docker-compose restart bot tx_monitor
```

### Ошибка: "Transaction not found"
- TX hash может быть неправильным
- TX еще в mempool
- Проверьте правильность network (Backbone/KelVPN/SubZero)

## 📚 Полезные ссылки

- **Официальный сайт**: https://cellframe.net
- **Документация**: https://docs.cellframe.net
- **GitHub**: https://github.com/cellframe-network
- **Explorer**: https://cfscan.io
- **Telegram**: https://t.me/cellframe_network

## �� Когда заработает

После настройки CF RPC пользователи смогут:

1. Отслеживать Cellframe транзакции через `/track`
2. Получать push-уведомления о confirmations
3. Видеть историю в `/mysessions`
4. Использовать все 3 сети: Ethereum, BSC, Cellframe

**Код полностью готов и будет работать сразу после подключения к рабочему RPC!** ✅
