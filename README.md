# 🚪 APB System - Anti-Passback для Hikvision

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0-green.svg)
![MySQL](https://img.shields.io/badge/mysql-8.0+-orange.svg)

Система контроля доступа с функцией Anti-Passback для терминалов Hikvision. Предотвращает двойное проникновение - пользователь не может войти повторно, пока не выйдет.

## 🎯 Возможности

- ✅ **10 терминалов** - 5 входа + 5 выхода
- ✅ **APB логика** - запрет повторного входа без выхода
- ✅ **MySQL** - хранение состояний и полный аудит
- ✅ **Управление дверями** - через HCNetSDK
- ✅ **Автосброс** - каждый день в настраиваемое время
- ✅ **REST API** - статус и управление через HTTP
- ✅ **Логирование** - консоль + файлы + база данных

## 📋 Правила Anti-Passback

| Состояние | Терминал | Действие | Дверь |
|-----------|----------|----------|-------|
| outside | entry (вход) | ✅ РАЗРЕШЕНО | Открывается |
| outside | exit (выход) | ⚠️ ПРЕДУПРЕЖДЕНИЕ | Закрыта |
| inside | entry (вход) | ❌ ЗАПРЕЩЕНО | Закрыта |
| inside | exit (выход) | ✅ РАЗРЕШЕНО | Открывается |

## 🚀 Быстрый старт

### 1. Установка SDK Hikvision
SDK не включен в репозиторий. Скачайте и установите:
```bash
# См. инструкцию в SDK_INSTALL.md
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Настройка MySQL
```bash
mysql -u root -p < setup_database.sql
```

### 4. Конфигурация .env
```bash
cp .env.example .env
nano .env  # Отредактируйте настройки
```

**Обязательно настройте:**
- `DB_HOST`, `DB_USER`, `DB_PASSWORD` - подключение к MySQL
- `TERMINAL_IN_*` и `TERMINAL_OUT_*` - IP адреса ваших терминалов
- `TERMINAL_USER`, `TERMINAL_PASSWORD` - учетные данные терминалов

### 5. Запуск
```bash
python main.py
```

## 🔧 Конфигурация терминалов Hikvision

На **каждом терминале** (221-230) в веб-интерфейсе:

1. **Configuration** → **Network** → **Advanced Settings** → **HTTP Listening**
2. Включите **HTTP Listening**
3. URL: `http://YOUR_SERVER_IP:3000/event`
4. Protocol Version: **1.0**
5. Отметьте события:
   - ✅ **Face Recognition Success**
   - ✅ **Card Swiped**
6. Сохраните настройки

## 📡 API Endpoints

### `GET /`
Проверка статуса системы
```bash
curl http://localhost:3000/
```

### `GET /status`
Текущее состояние пользователей
```bash
curl http://localhost:3000/status
```
Возвращает JSON с информацией о пользователях внутри здания.

### `POST /reset`
Ручной сброс всех состояний (admin)
```bash
curl -X POST http://localhost:3000/reset
```

### `POST /event`
Прием событий от терминалов (автоматически)

## 🗄️ База данных

### Таблицы:

**user_states** - состояния пользователей
```sql
SELECT * FROM user_states WHERE state='inside';
```

**event_logs** - журнал всех событий
```sql
SELECT * FROM event_logs ORDER BY created_at DESC LIMIT 20;
```

**Полезные запросы** - см. файл `queries.sql`

## 🧪 Тестирование

### Проверка системы
```bash
python check_system.py
```

### Тестирование без терминалов
```bash
python test_system.py
```

## 📂 Структура проекта

```
apb/
├── main.py              # Основное приложение
├── db.py                # Модуль работы с MySQL
├── requirements.txt     # Python зависимости
├── .env                 # Конфигурация (создать!)
├── .env.example         # Пример конфигурации
├── setup_database.sql   # Создание БД
├── check_system.py      # Проверка готовности
├── test_system.py       # Тестирование
└── lib/
    └── HCNetSDK.dll     # SDK Hikvision
```

## ⚙️ Конфигурация (.env)

```env
# Терминалы входа (нечетные IP)
TERMINAL_IN_1=192.168.18.221
TERMINAL_IN_2=192.168.18.223
TERMINAL_IN_3=192.168.18.225
TERMINAL_IN_4=192.168.18.227
TERMINAL_IN_5=192.168.18.229

# Терминалы выхода (четные IP)
TERMINAL_OUT_1=192.168.18.222
TERMINAL_OUT_2=192.168.18.224
TERMINAL_OUT_3=192.168.18.226
TERMINAL_OUT_4=192.168.18.228
TERMINAL_OUT_5=192.168.18.230

# Учетные данные терминалов
TERMINAL_PORT=8000
TERMINAL_USER=admin
TERMINAL_PASSWORD=123456

# MySQL
DB_HOST=localhost
DB_NAME=apb_system
DB_USER=root
DB_PASSWORD=your_password

# Настройки APB
RESET_TIME=00:00         # Время сброса (HH:MM)
DOOR_OPEN_TIME=3         # Секунды открытия двери
```

## 📊 Мониторинг

### Логи в консоли
Все события отображаются в реальном времени:
```
============================================================
👤 Пользователь: Иван Иванов
📍 Терминал: 192.168.18.221 (entry)
📊 Текущее состояние: outside
============================================================
✅ Иван Иванов входит в здание через 192.168.18.221
✏️  Действие: ВХОД РАЗРЕШЕН
🔄 Новое состояние: inside
============================================================
```

### Логи файлы
Детальные логи в папке `logs/`:
```
logs/YYYYMMDD_HHMMSS_MMMMMM/
  ├── headers.json
  ├── AccessControllerEvent.json
  └── photo.jpg
```

### Логи в MySQL
```sql
-- События сегодня
SELECT * FROM event_logs WHERE DATE(created_at) = CURDATE();

-- Нарушения APB
SELECT * FROM event_logs WHERE action_taken LIKE '%ЗАПРЕЩЕН%';

-- Пользователи внутри
SELECT * FROM user_states WHERE state='inside';
```

## 🔒 Безопасность

- ✅ Секретные данные в `.env` (не в git!)
- ✅ `.gitignore` защищает конфиденциальные файлы
- ✅ Полный аудит всех событий
- ✅ Предотвращение двойного проникновения

## 🚨 Troubleshooting

### "Login failed" при подключении к терминалам
```bash
# Проверьте IP и доступность
ping 192.168.18.221

# Проверьте логин/пароль в .env
```

### "MySQL connection error"
```bash
# Запустите MySQL
net start MySQL80          # Windows
systemctl start mysql      # Linux

# Проверьте пароль в .env
```

### "HCNetSDK.dll not found"
```bash
# Убедитесь что DLL в папке lib/
ls lib/HCNetSDK.dll
```

### Терминал не отправляет события
- Проверьте настройки HTTP Listening на терминале
- Убедитесь что URL правильный
- Проверьте что порт 3000 доступен

## 🛠️ Технологии

- **Python 3.8+**
- **Flask 3.0** - веб-фреймворк
- **MySQL 8.0+** - база данных
- **mysql-connector-python** - драйвер БД
- **HCNetSDK.dll** - SDK Hikvision

## 📝 Требования

- Python 3.8 или выше
- MySQL 8.0 или выше
- Windows 10/11 или Linux
- HCNetSDK.dll от Hikvision
- Сетевой доступ к терминалам

## 🔄 Автоматический запуск

### Windows (Task Scheduler)
Создайте bat файл и добавьте в планировщик задач.

### Linux (systemd)
```bash
sudo nano /etc/systemd/system/apb.service
```
См. комментарии в коде для примера конфигурации.

## 🤝 Поддержка

При возникновении проблем:
1. Запустите `python check_system.py`
2. Проверьте логи в консоли
3. Проверьте `logs/` и таблицу `event_logs`
4. Убедитесь что терминалы настроены правильно

## 📄 Лицензия

akmalovichdev - Все права защищены © 2024

---

**Версия:** 1.0.0  
**Дата:** Октябрь 2024
