git commit -m "feat: APB System v1.0 - Anti-Passback для Hikvision

Функционал:
- Поддержка 10 терминалов (5 входа + 5 выхода)
- Логика Anti-Passback (запрет двойного входа)
- Управление дверями через HCNetSDK
- MySQL база данных для состояний и логов
- REST API (status, reset endpoints)
- Автоматический ежедневный сброс состояний
- Полное логирование (консоль + файлы + БД)

Инструменты:
- check_system.py - диагностика системы
- test_system.py - тестирование без терминалов
- setup_database.sql - инициализация БД

Технологии:
- Python 3.8+, Flask 3.0
- MySQL 8.0+, mysql-connector-python
- HCNetSDK (Hikvision)

Версия: 1.0.0"