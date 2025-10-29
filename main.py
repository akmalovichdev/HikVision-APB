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
]

# Терминалы выхода (четные)
TERMINALS_OUT = [
    os.getenv("TERMINAL_OUT_1"),
    os.getenv("TERMINAL_OUT_2"),
    os.getenv("TERMINAL_OUT_3"),
    os.getenv("TERMINAL_OUT_4"),
    os.getenv("TERMINAL_OUT_5"),
]

# Учетные данные терминалов
PORT = int(os.getenv("TERMINAL_PORT"))
USER = os.getenv("TERMINAL_USER").encode()
PASS = os.getenv("TERMINAL_PASSWORD").encode()

# Настройки APB
RESET_TIME = os.getenv("RESET_TIME")  # Время ежедневного сброса
DOOR_OPEN_TIME = int(os.getenv("DOOR_OPEN_TIME"))

# =============================
#   Инициализация SDK
# =============================

sdk = cdll.LoadLibrary("./lib/HCNetSDK.dll")
sdk.NET_DVR_Init()

# Словарь для хранения user_id подключений к терминалам входа
terminal_connections = {}

print("=" * 60)
print("🔌 Подключение к терминалам входа...")
print("=" * 60)

for terminal_ip in TERMINALS_IN:
    ip_bytes = terminal_ip.encode()
    user_id = sdk.NET_DVR_Login_V30(ip_bytes, PORT, USER, PASS, None)
    
    if user_id < 0:
        print(f"❌ Не удалось подключиться к {terminal_ip}")
    else:
        terminal_connections[terminal_ip] = user_id
        print(f"✅ Подключено к {terminal_ip} (user_id: {user_id})")

if not terminal_connections:
    print("❌ Не удалось подключиться ни к одному терминалу!")
    exit(1)

print(f"\n✅ Успешно подключено к {len(terminal_connections)} терминалам входа")

# =============================
#   Подключение к БД
# =============================

if not db.connect():
    print("❌ Не удалось подключиться к базе данных!")
    exit(1)

db.initialize_tables()

# =============================
#   Логика управления дверью
# =============================

def open_door(terminal_ip, door_no=1, open_time=DOOR_OPEN_TIME):
    """Открыть дверь на определенном терминале"""
    user_id = terminal_connections.get(terminal_ip)
    
    if not user_id:
        print(f"⚠️ Терминал {terminal_ip} не подключен к SDK")
        return False
    
    try:
        print(f"🔓 Открываем дверь на {terminal_ip} (дверь {door_no}) на {open_time} сек...")
        result = sdk.NET_DVR_ControlGateway(user_id, door_no, 1)  # open door
        
        if result == 0:
            print(f"⚠️ Не удалось открыть дверь на {terminal_ip}")
            return False
        
        time.sleep(open_time)
        sdk.NET_DVR_ControlGateway(user_id, door_no, 3)  # close door
        print(f"🚪 Дверь на {terminal_ip} снова закрыта")
        return True
    except Exception as e:
        print(f"❌ Ошибка управления дверью на {terminal_ip}: {e}")
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
    - Если пользователь снаружи, он может войти через любой терминал входа
    - Если пользователь внутри, он может выйти через любой терминал выхода
    - Если пользователь снаружи, он не может выйти (предупреждение)
    """
    
    # Получаем текущее состояние пользователя из БД
    user_data = db.get_user_state(user_name)
    current_state = user_data['state']
    terminal_type = determine_terminal_type(device_ip)
    
    print(f"\n{'='*60}")
    print(f"👤 Пользователь: {user_name}")
    print(f"📍 Терминал: {device_ip} ({terminal_type})")
    print(f"📊 Текущее состояние: {current_state}")
    print(f"{'='*60}")
    
    action_taken = None
    door_opened = False
    new_state = current_state
    
    # ===== ТЕРМИНАЛ ВХОДА =====
    if terminal_type == "entry":
        if current_state == "inside":
            # Пользователь уже внутри - запрещаем вход
            action_taken = "ВХОД ЗАПРЕЩЕН - уже внутри"
            print(f"⛔ {user_name} уже внутри здания - запрет повторного входа")
            door_opened = False
            
        else:  # current_state == "outside"
            # Пользователь снаружи - разрешаем вход
            action_taken = "ВХОД РАЗРЕШЕН"
            print(f"✅ {user_name} входит в здание через {device_ip}")
            
            # Открываем дверь в отдельном потоке
            threading.Thread(target=open_door, args=(device_ip,)).start()
            door_opened = True
            new_state = "inside"
            
            # Обновляем состояние в БД
            db.update_user_state(user_name, new_state, device_ip)
    
    # ===== ТЕРМИНАЛ ВЫХОДА =====
    elif terminal_type == "exit":
        if current_state == "inside":
            # Пользователь внутри - разрешаем выход
            action_taken = "ВЫХОД РАЗРЕШЕН"
            print(f"🚪 {user_name} выходит из здания через {device_ip}")
            
            # На выходе мы не управляем дверью через SDK (только входы подключены)
            # Но логируем событие
            door_opened = False
            new_state = "outside"
            
            # Обновляем состояние в БД
            db.update_user_state(user_name, new_state, device_ip)
            
        else:  # current_state == "outside"
            # Пользователь снаружи пытается выйти - предупреждение
            action_taken = "ВЫХОД ПРЕДУПРЕЖДЕНИЕ - не числится внутри"
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
        state_before=current_state,
        state_after=new_state,
        door_opened=door_opened
    )
    
    print(f"✏️  Действие: {action_taken}")
    print(f"🔄 Новое состояние: {new_state}")
    print(f"{'='*60}\n")


# =============================
#   Flask сервер
# =============================

app = Flask(__name__)
os.makedirs("logs", exist_ok=True)


@app.route("/event", methods=["POST"])
def event():
    """Обработчик событий от терминалов Hikvision"""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
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
