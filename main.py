#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request
import os
import json
from datetime import datetime, time as dt_time
from ctypes import *
import threading
import time
from dotenv import load_dotenv
from db import db

# =============================
#   Коды статусов событий APB
# =============================

# Успешные операции
STATUS_SUCCESS_ENTRY = "SUCCESS_ENTRY"  # Успешный вход (outside -> inside)
STATUS_SUCCESS_EXIT = "SUCCESS_EXIT"  # Успешный выход (inside -> outside)
STATUS_ALLOWED_TIME_WINDOW = "ALLOWED_TIME_WINDOW"  # Разрешен вход в пределах временного окна

# Нарушения APB (is_violation = TRUE)
STATUS_DENIED_ALREADY_INSIDE = "DENIED_ALREADY_INSIDE"  # Запрещен вход - уже внутри (нарушение)
STATUS_DENIED_OUTSIDE_WINDOW = "DENIED_OUTSIDE_WINDOW"  # Запрещен вход - вне временного окна (нарушение)

# Предупреждения (не нарушения, но требует внимания)
STATUS_WARNING_EXIT_WITHOUT_ENTRY = "WARNING_EXIT_WITHOUT_ENTRY"  # Предупреждение - выход без входа

# =============================
#   Загрузка конфигурации
# =============================

load_dotenv()

# Терминалы входа (нечетные)
TERMINALS_IN = [
    os.getenv("TERMINAL_IN_1"),
    os.getenv("TERMINAL_IN_2"),
    os.getenv("TERMINAL_IN_3"),
    os.getenv("TERMINAL_IN_4"),
    os.getenv("TERMINAL_IN_5"),
    os.getenv("TERMINAL_IN_6"),
    os.getenv("TERMINAL_IN_7"),
    os.getenv("TERMINAL_IN_8"),
    os.getenv("TERMINAL_IN_9"),
]

# Терминалы выхода (четные)
TERMINALS_OUT = [
    os.getenv("TERMINAL_OUT_1"),
    os.getenv("TERMINAL_OUT_2"),
    os.getenv("TERMINAL_OUT_3"),
    os.getenv("TERMINAL_OUT_4"),
    os.getenv("TERMINAL_OUT_5"),
    os.getenv("TERMINAL_OUT_6"),
    os.getenv("TERMINAL_OUT_7"),
    os.getenv("TERMINAL_OUT_8"),
    os.getenv("TERMINAL_OUT_9"),
]

# Учетные данные терминалов
PORT = int(os.getenv("TERMINAL_PORT"))
USER = os.getenv("TERMINAL_USER").encode()
PASS = os.getenv("TERMINAL_PASSWORD").encode()

# Настройки APB
RESET_TIME = os.getenv("RESET_TIME")  # Время ежедневного сброса
DOOR_OPEN_TIME = int(os.getenv("DOOR_OPEN_TIME"))
ENTRY_WINDOW_SECONDS = int(os.getenv("ENTRY_WINDOW_SECONDS", "60"))  # Время окна для повторного входа (секунды)

# =============================
#   Инициализация SDK
# =============================

sdk = cdll.LoadLibrary("./lib/libhcnetsdk.so")
sdk.NET_DVR_Init()

# Словарь для хранения user_id подключений к терминалам входа
terminal_connections = {}
# Блокировка для потокобезопасного доступа к SDK
sdk_lock = threading.Lock()

print("=" * 60)
print("🔌 Подключение к терминалам входа...")
print("=" * 60)

# Список недоступных терминалов
unavailable_terminals = []

for terminal_ip in TERMINALS_IN:
    try:
        ip_bytes = terminal_ip.encode()
        user_id = sdk.NET_DVR_Login_V30(ip_bytes, PORT, USER, PASS, None)

        if user_id < 0:
            print(f"⚠️  Терминал {terminal_ip} недоступен - будет пропущен")
            unavailable_terminals.append(terminal_ip)
        else:
            terminal_connections[terminal_ip] = user_id
            print(f"✅ Подключено к {terminal_ip} (user_id: {user_id})")
    except Exception as e:
        print(f"⚠️  Ошибка подключения к {terminal_ip}: {e}")
        unavailable_terminals.append(terminal_ip)

if terminal_connections:
    print(f"\n✅ Успешно подключено к {len(terminal_connections)}/{len(TERMINALS_IN)} терминалам входа")
    if unavailable_terminals:
        print(f"⚠️  Недоступные терминалы: {', '.join(unavailable_terminals)}")
        print("ℹ️  Система продолжит работу с доступными терминалами")
else:
    print("\n⚠️  Ни один терминал входа не подключен!")
    print("ℹ️  Система будет работать в режиме мониторинга (без управления дверями)")

print(f"📊 Активных подключений: {len(terminal_connections)}")

# =============================
#   Подключение к БД
# =============================

def wait_for_db(max_attempts=30, delay_seconds=2):
    """
    Ожидание готовности MySQL перед стартом приложения.
    Пытаемся подключиться несколько раз с паузой.
    """
    attempt = 1
    while attempt <= max_attempts:
        print(f"🔄 Подключение к базе данных (попытка {attempt}/{max_attempts})...")
        if db.connect():
            return True

        print(f"⚠️  База данных недоступна, следующая попытка через {delay_seconds} сек...")
        time.sleep(delay_seconds)
        attempt += 1

    print("❌ Не удалось подключиться к базе данных после множества попыток!")
    return False


if not wait_for_db():
    exit(1)

db.initialize_tables()

# =============================
#   Логика управления дверью
# =============================

def open_door(terminal_ip, door_no=1, open_time=DOOR_OPEN_TIME):
    """Открыть дверь на определенном терминале"""
    user_id = terminal_connections.get(terminal_ip)

    if user_id is None:
        print(f"⚠️  Терминал {terminal_ip} не подключен к SDK - управление дверью недоступно")
        print(f"ℹ️  Событие будет залогировано, но дверь не откроется")
        return False

    try:
        print(f"🔓 Открываем дверь на {terminal_ip} (дверь {door_no}) на {open_time} сек...")

        # Используем блокировку для потокобезопасного доступа к SDK
        with sdk_lock:
            result = sdk.NET_DVR_ControlGateway(user_id, door_no, 1)  # open door

        if result == 0:
            print(f"⚠️  Не удалось открыть дверь на {terminal_ip}")
            print(f"ℹ️  Возможно терминал отключился - проверьте подключение")
            return False

        time.sleep(open_time)

        # Используем блокировку для потокобезопасного доступа к SDK
        with sdk_lock:
            sdk.NET_DVR_ControlGateway(user_id, door_no, 3)  # close door

        print(f"🚪 Дверь на {terminal_ip} снова закрыта")
        return True
    except Exception as e:
        print(f"❌ Ошибка управления дверью на {terminal_ip}: {e}")
        print(f"ℹ️  Терминал может быть недоступен")
        return False


# =============================
#   Фоновая задача сброса состояний
# =============================

last_reset_date = datetime.now().date()

def reset_states_scheduler():
    """Фоновый поток для ежедневного сброса состояний"""
    global last_reset_date

    while True:
        try:
            now = datetime.now()
            current_date = now.date()
            current_time = now.time()

            # Парсим время сброса
            reset_hour, reset_minute = map(int, RESET_TIME.split(":"))
            reset_time = dt_time(reset_hour, reset_minute)

            # Проверяем, нужен ли сброс
            if current_date > last_reset_date and current_time >= reset_time:
                print("\n" + "=" * 60)
                print(f"🔄 Выполняется ежедневный сброс состояний в {now.strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 60)

                affected = db.reset_daily_states()
                last_reset_date = current_date

                print(f"✅ Сброс завершен. Обновлено записей: {affected}\n")

            # Проверяем каждую минуту
            time.sleep(60)

        except Exception as e:
            print(f"❌ Ошибка в планировщике сброса: {e}")
            time.sleep(60)


# Запускаем фоновый поток сброса
reset_thread = threading.Thread(target=reset_states_scheduler, daemon=True)
reset_thread.start()

# =============================
#   Логика APB
# =============================

def determine_terminal_type(device_ip):
    """Определить тип терминала по IP"""
    # Проверяем последнюю цифру IP
    last_octet = int(device_ip.split('.')[-1])

    if last_octet % 2 == 1:  # Нечетный - вход
        return "entry"
    else:  # Четный - выход
        return "exit"


def process_apb_event(user_name, device_ip, sub_event_type):
    """
    Обработка события с применением логики Anti-Passback

    Правила:
    - Если пользователь внутри, он не может войти повторно через терминал входа
      ИСКЛЮЧЕНИЕ: если с момента последней успешной аутентификации на терминале входа
      прошло менее ENTRY_WINDOW_SECONDS секунд (окно времени для прохода через турникет)
    - Если пользователь снаружи, он может войти через любой терминал входа
    - Если пользователь внутри, он может выйти через любой терминал выхода
    - Если пользователь снаружи, он не может выйти (предупреждение)
    """

    try:
        # Получаем текущее состояние пользователя из БД
        user_data = db.get_user_state(user_name)
        if not user_data:
            print(f"⚠️  Не удалось получить состояние пользователя {user_name}")
            return

        current_state = user_data.get('state', 'outside')
        last_entry_auth_time = user_data.get('last_entry_auth_time')
        terminal_type = determine_terminal_type(device_ip)

        print(f"\n{'='*60}")
        print(f"👤 Пользователь: {user_name}")
        print(f"📍 Терминал: {device_ip} ({terminal_type})")
        print(f"📊 Текущее состояние: {current_state}")
        if last_entry_auth_time:
            print(f"⏰ Последняя аутентификация на входе: {last_entry_auth_time}")
        print(f"{'='*60}")

        action_taken = None
        status_code = None
        is_violation = False
        door_opened = False
        new_state = current_state

        # ===== ТЕРМИНАЛ ВХОДА =====
        if terminal_type == "entry":
            # Обновляем время последней аутентификации на терминале входа
            # Это нужно для отслеживания временного окна (даже если вход будет запрещен)
            db.update_entry_auth_time(user_name, device_ip)

            # Получаем обновленное время для проверки окна
            updated_user_data = db.get_user_state(user_name)
            current_auth_time = updated_user_data.get('last_entry_auth_time')

            # Проверяем временное окно для повторного входа
            within_time_window = False
            if last_entry_auth_time and current_auth_time:
                # Используем старое время для проверки окна (до обновления)
                time_diff = (datetime.now() - last_entry_auth_time).total_seconds()
                within_time_window = time_diff < ENTRY_WINDOW_SECONDS
                if within_time_window:
                    print(f"⏱️  Временное окно: {time_diff:.1f} сек назад (окно: {ENTRY_WINDOW_SECONDS} сек)")

            status_code = None
            is_violation = False

            if current_state == "inside":
                if within_time_window:
                    # Пользователь уже внутри, но в пределах временного окна - разрешаем повторный вход
                    action_taken = f"ВХОД РАЗРЕШЕН - временное окно ({ENTRY_WINDOW_SECONDS} сек)"
                    status_code = STATUS_ALLOWED_TIME_WINDOW
                    is_violation = False
                    print(f"✅ {user_name} входит повторно через {device_ip} (в пределах временного окна)")

                    # Проверяем подключен ли терминал к SDK
                    if device_ip in terminal_connections:
                        # Открываем дверь в отдельном потоке
                        threading.Thread(target=open_door, args=(device_ip,)).start()
                        door_opened = True
                    else:
                        print(f"⚠️  Терминал {device_ip} не подключен к SDK")
                        print(f"ℹ️  Пользователю разрешен вход, но дверь не откроется автоматически")
                        door_opened = False
                else:
                    # Пользователь уже внутри и вне временного окна - запрещаем вход (НАРУШЕНИЕ APB)
                    action_taken = "ВХОД ЗАПРЕЩЕН - уже внутри"
                    status_code = STATUS_DENIED_ALREADY_INSIDE
                    is_violation = True  # Это нарушение APB!
                    print(f"⛔ {user_name} уже внутри здания - запрет повторного входа (НАРУШЕНИЕ APB)")
                    if last_entry_auth_time:
                        time_diff = (datetime.now() - last_entry_auth_time).total_seconds()
                        print(f"ℹ️  С момента последней аутентификации прошло {time_diff:.1f} сек (окно: {ENTRY_WINDOW_SECONDS} сек)")
                    door_opened = False

            else:  # current_state == "outside"
                # Пользователь снаружи - разрешаем вход
                action_taken = "ВХОД РАЗРЕШЕН"
                status_code = STATUS_SUCCESS_ENTRY
                is_violation = False
                print(f"✅ {user_name} входит в здание через {device_ip}")

                # Проверяем подключен ли терминал к SDK
                if device_ip in terminal_connections:
                    # Открываем дверь в отдельном потоке
                    threading.Thread(target=open_door, args=(device_ip,)).start()
                    door_opened = True
                else:
                    # Терминал не подключен - дверь не откроется
                    print(f"⚠️  Терминал {device_ip} не подключен к SDK")
                    print(f"ℹ️  Пользователю разрешен вход, но дверь не откроется автоматически")
                    door_opened = False

                new_state = "inside"

                # Обновляем состояние в БД
                db.update_user_state(user_name, new_state, device_ip)

        # ===== ТЕРМИНАЛ ВЫХОДА =====
        elif terminal_type == "exit":
            if current_state == "inside":
                # Пользователь внутри - разрешаем выход
                action_taken = "ВЫХОД РАЗРЕШЕН"
                status_code = STATUS_SUCCESS_EXIT
                is_violation = False
                print(f"🚪 {user_name} выходит из здания через {device_ip}")

                # На выходе мы не управляем дверью через SDK (только входы подключены)
                # Но логируем событие
                door_opened = False
                new_state = "outside"

                # Обновляем состояние в БД
                db.update_user_state(user_name, new_state, device_ip)

            else:  # current_state == "outside"
                # Пользователь снаружи пытается выйти - предупреждение (не нарушение)
                action_taken = "ВЫХОД ПРЕДУПРЕЖДЕНИЕ - не числится внутри"
                status_code = STATUS_WARNING_EXIT_WITHOUT_ENTRY
                is_violation = False
                print(f"⚠️ {user_name} пытается выйти, но не числится внутри здания")
                door_opened = False

        # Записываем событие в лог
        db.log_event(
            user_name=user_name,
            terminal_ip=device_ip,
            terminal_type=terminal_type,
            event_type="AccessControl",
            sub_event_type=sub_event_type,
            action_taken=action_taken,
            status_code=status_code,
            is_violation=is_violation,
            state_before=current_state,
            state_after=new_state,
            door_opened=door_opened
        )

        print(f"✏️  Действие: {action_taken}")
        print(f"🔄 Новое состояние: {new_state}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ Критическая ошибка при обработке события для {user_name}: {e}")
        import traceback
        traceback.print_exc()


# =============================
#   Flask сервер
# =============================

app = Flask(__name__)
os.makedirs("logs", exist_ok=True)


@app.route("/event", methods=["POST"])
def event():
    """Обработчик событий от терминалов Hikvision"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_dir = f"logs/{ts}"
    os.makedirs(log_dir, exist_ok=True)

    # Сохраняем заголовки
    with open(f"{log_dir}/headers.json", "w", encoding="utf-8") as f:
        json.dump(dict(request.headers), f, indent=4, ensure_ascii=False)

    # Сохраняем файлы (если есть)
    for key in request.files:
        file = request.files[key]
        file.save(os.path.join(log_dir, file.filename))

    # Обработка form-data
    for key, val in request.form.items():
        try:
            data = json.loads(val)
            with open(f"{log_dir}/{key}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            # ========== Проверка события AccessControllerEvent ==========
            # Проверяем либо ключ в данных, либо сам ключ = "AccessControllerEvent"
            if "AccessControllerEvent" in data:
                ev = data["AccessControllerEvent"]
            elif key == "AccessControllerEvent":
                # Данные уже распарсены и лежат в data напрямую
                ev = data
            else:
                continue  # Это не событие контроллера доступа

            sub_type = ev.get("subEventType")
            user = ev.get("name", "")

            # Получаем IP устройства (для тестирования поддерживаем X-Forwarded-For)
            device_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ',' in device_ip:
                device_ip = device_ip.split(',')[0].strip()

            # События успешной аутентификации: 75 (по карте) или 117 (по лицу)
            if sub_type in [75, 117]:
                process_apb_event(user, device_ip, sub_type)

        except Exception as e:
            # Если не JSON, сохраняем как текст
            with open(f"{log_dir}/{key}.txt", "w", encoding="utf-8") as f:
                f.write(val)
            print(f"⚠️ Ошибка обработки события: {e}")

    print(f"📝 Событие сохранено в {log_dir}")
    return "OK", 200


@app.route("/", methods=["GET"])
def index():
    """Главная страница - статус системы"""
    return "✅ Hikvision APB System Active", 200


@app.route("/status", methods=["GET"])
def status():
    """Статус системы и текущие пользователи внутри"""
    users_inside = db.get_all_users_inside()

    return {
        "status": "active",
        "terminals_connected": len(terminal_connections),
        "terminals_in": TERMINALS_IN,
        "terminals_out": TERMINALS_OUT,
        "users_inside_count": len(users_inside),
        "users_inside": [
            {
                "name": u[0],
                "last_terminal": u[1],
                "last_event": u[2].strftime("%Y-%m-%d %H:%M:%S") if u[2] else None
            }
            for u in users_inside
        ]
    }, 200


@app.route("/reset", methods=["POST"])
def manual_reset():
    """Ручной сброс всех состояний (для администратора)"""
    affected = db.reset_daily_states()
    return {
        "status": "success",
        "message": f"Сброшено состояний: {affected}"
    }, 200


@app.route("/violations", methods=["GET"])
def get_violations():
    """Получить все нарушения APB"""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    user_name = request.args.get("user_name")

    violations = db.get_apb_violations(
        start_date=start_date,
        end_date=end_date,
        user_name=user_name
    )

    return {
        "status": "success",
        "count": len(violations),
        "violations": violations
    }, 200


@app.route("/violations/stats", methods=["GET"])
def get_violation_stats():
    """Получить статистику нарушений APB"""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    stats = db.get_violation_statistics(
        start_date=start_date,
        end_date=end_date
    )

    return {
        "status": "success",
        "statistics": stats
    }, 200


@app.route("/violations/<status_code>", methods=["GET"])
def get_violations_by_status(status_code):
    """Получить нарушения по коду статуса"""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    violations = db.get_violations_by_status_code(
        status_code=status_code,
        start_date=start_date,
        end_date=end_date
    )

    return {
        "status": "success",
        "status_code": status_code,
        "count": len(violations),
        "violations": violations
    }, 200


# =============================
#   Запуск приложения
# =============================

if __name__ == "__main__":
    try:
        flask_host = os.getenv("FLASK_HOST", "0.0.0.0")
        flask_port = int(os.getenv("FLASK_PORT", 3000))

        print("\n" + "=" * 60)
        print(f"🚀 APB System запущен на {flask_host}:{flask_port}")
        print(f"📊 Подключено терминалов входа: {len(terminal_connections)}")
        print(f"🔄 Время сброса состояний: {RESET_TIME}")
        print("=" * 60 + "\n")

        app.run(host=flask_host, port=flask_port, debug=False)

    except KeyboardInterrupt:
        print("\n🛑 Завершение работы...")
    finally:
        # Отключаемся от всех терминалов
        for terminal_ip, user_id in terminal_connections.items():
            sdk.NET_DVR_Logout(user_id)
            print(f"🔌 Отключено от {terminal_ip}")

        sdk.NET_DVR_Cleanup()
        db.disconnect()
        print("✅ Система остановлена")
