#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для тестирования APB системы без реальных терминалов
Отправляет тестовые события на Flask сервер
"""

import requests
import json
import time

# URL сервера APB
SERVER_URL = "http://192.168.100.229:3000"

# Тестовые пользователи
USERS = ["Иван Иванов", "Петр Петров", "Анна Сидорова"]

# Терминалы
TERMINALS = {
    "entry": ["192.168.18.221", "192.168.18.223", "192.168.18.225", "192.168.18.227", "192.168.18.229"],
    "exit": ["192.168.18.222", "192.168.18.224", "192.168.18.226", "192.168.18.228", "192.168.18.230"]
}


def send_event(user_name, terminal_ip, sub_event_type=75):
    """Отправить тестовое событие на сервер"""
    
    event_data = {
        "AccessControllerEvent": {
            "subEventType": sub_event_type,  # 75 - карта, 117 - лицо
            "name": user_name,
            "cardNo": "1234567890",
            "majorEventType": 5,
            "dateTime": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    }
    
    # Отправляем как form-data (как делает Hikvision)
    data = {
        "AccessControllerEvent": json.dumps(event_data["AccessControllerEvent"])
    }
    
    try:
        # Эмулируем remote_addr через заголовок (в реальности Flask берет из request.remote_addr)
        # Для теста запускаем через прокси или модифицируем main.py для чтения X-Forwarded-For
        response = requests.post(
            f"{SERVER_URL}/event",
            data=data,
            headers={"X-Forwarded-For": terminal_ip}
        )
        
        if response.status_code == 200:
            print(f"✅ Событие отправлено: {user_name} → {terminal_ip}")
        else:
            print(f"❌ Ошибка: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")


def test_normal_flow():
    """Тест 1: Нормальный поток - вход и выход"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Нормальный поток - вход и выход")
    print("="*60)
    
    user = USERS[0]
    
    print(f"\n1. {user} входит через терминал 221...")
    send_event(user, TERMINALS["entry"][0])
    time.sleep(2)
    
    print(f"\n2. {user} выходит через терминал 222...")
    send_event(user, TERMINALS["exit"][0])
    time.sleep(2)


def test_double_entry_violation():
    """Тест 2: Попытка повторного входа (нарушение APB)"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Попытка повторного входа (должна быть заблокирована)")
    print("="*60)
    
    user = USERS[1]
    
    print(f"\n1. {user} входит через терминал 223...")
    send_event(user, TERMINALS["entry"][1])
    time.sleep(2)
    
    print(f"\n2. {user} пытается войти повторно через терминал 225 (НАРУШЕНИЕ)...")
    send_event(user, TERMINALS["entry"][2])
    time.sleep(2)
    
    print(f"\n3. {user} выходит через терминал 224...")
    send_event(user, TERMINALS["exit"][1])
    time.sleep(2)


def test_exit_without_entry():
    """Тест 3: Попытка выхода без входа"""
    print("\n" + "="*60)
    print("ТЕСТ 3: Попытка выхода без входа")
    print("="*60)
    
    user = USERS[2]
    
    print(f"\n1. {user} пытается выйти через терминал 226 (не входил)...")
    send_event(user, TERMINALS["exit"][2])
    time.sleep(2)


def test_multiple_terminals():
    """Тест 4: Разные терминалы для входа и выхода"""
    print("\n" + "="*60)
    print("ТЕСТ 4: Вход через один терминал, выход через другой")
    print("="*60)
    
    user = USERS[0]
    
    print(f"\n1. {user} входит через терминал 227...")
    send_event(user, TERMINALS["entry"][3])
    time.sleep(2)
    
    print(f"\n2. {user} выходит через терминал 230 (другой терминал)...")
    send_event(user, TERMINALS["exit"][4])
    time.sleep(2)


def test_face_recognition():
    """Тест 5: Распознавание лица (sub_event_type = 117)"""
    print("\n" + "="*60)
    print("ТЕСТ 5: Событие распознавания лица")
    print("="*60)
    
    user = USERS[1]
    
    print(f"\n1. {user} входит по лицу через терминал 229...")
    send_event(user, TERMINALS["entry"][4], sub_event_type=117)
    time.sleep(2)


def check_status():
    """Проверить текущий статус системы"""
    print("\n" + "="*60)
    print("ТЕКУЩИЙ СТАТУС СИСТЕМЫ")
    print("="*60)
    
    try:
        response = requests.get(f"{SERVER_URL}/status")
        if response.status_code == 200:
            data = response.json()
            print(f"\n📊 Пользователей внутри: {data['users_inside_count']}")
            
            if data['users_inside']:
                print("\n👥 Пользователи внутри:")
                for user in data['users_inside']:
                    print(f"   - {user['name']} (терминал: {user['last_terminal']}, время: {user['last_event']})")
            else:
                print("\n✅ Все снаружи")
        else:
            print(f"❌ Ошибка получения статуса: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def main():
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ APB СИСТЕМЫ")
    print("="*60)
    print("\n⚠️  Убедитесь, что сервер запущен: python main.py")
    print(f"📡 URL сервера: {SERVER_URL}")
    
    input("\nНажмите Enter для начала тестирования...")
    
    # Проверка доступности сервера
    try:
        response = requests.get(SERVER_URL)
        if response.status_code != 200:
            print(f"❌ Сервер недоступен!")
            return
    except:
        print(f"❌ Не удалось подключиться к серверу {SERVER_URL}")
        print("   Убедитесь, что main.py запущен!")
        return
    
    # Запуск тестов
    test_normal_flow()
    check_status()
    
    test_double_entry_violation()
    check_status()
    
    test_exit_without_entry()
    check_status()
    
    test_multiple_terminals()
    check_status()
    
    test_face_recognition()
    check_status()
    
    print("\n" + "="*60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60)
    print("\n📊 Проверьте логи в консоли main.py и таблицу event_logs в MySQL")
    print("   Также проверьте папку logs/ для детальных логов событий")


if __name__ == "__main__":
    main()

