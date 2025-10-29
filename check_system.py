#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки готовности системы перед запуском
Проверяет: конфигурацию, БД, терминалы, SDK
"""

import os
import sys
from dotenv import load_dotenv
import socket

# Цветные выводы
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def check_env_file():
    """Проверка наличия .env файла"""
    print("\n" + "="*60)
    print("1. Проверка файла конфигурации")
    print("="*60)
    
    if not os.path.exists('.env'):
        print_error("Файл .env не найден!")
        print_info("Скопируйте .env.example в .env и настройте параметры")
        return False
    
    print_success("Файл .env найден")
    return True

def check_env_variables():
    """Проверка переменных окружения"""
    print("\n" + "="*60)
    print("2. Проверка переменных окружения")
    print("="*60)
    
    load_dotenv()
    
    required_vars = [
        "TERMINAL_IN_1", "TERMINAL_IN_2", "TERMINAL_IN_3", 
        "TERMINAL_IN_4", "TERMINAL_IN_5",
        "TERMINAL_OUT_1", "TERMINAL_OUT_2", "TERMINAL_OUT_3", 
        "TERMINAL_OUT_4", "TERMINAL_OUT_5",
        "TERMINAL_USER", "TERMINAL_PASSWORD",
        "DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
    
    if missing:
        print_error(f"Отсутствуют переменные: {', '.join(missing)}")
        return False
    
    print_success("Все необходимые переменные присутствуют")
    return True

def check_mysql():
    """Проверка подключения к MySQL"""
    print("\n" + "="*60)
    print("3. Проверка подключения к MySQL")
    print("="*60)
    
    try:
        import mysql.connector
        from mysql.connector import Error
        
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", 3306))
        database = os.getenv("DB_NAME", "apb_system")
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "")
        
        print_info(f"Подключение к {user}@{host}:{port}/{database}...")
        
        connection = mysql.connector.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        if connection.is_connected():
            print_success(f"Подключено к MySQL: {database}")
            
            # Проверка таблиц
            cursor = connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            required_tables = ['user_states', 'event_logs', 'system_config']
            existing_tables = [table[0] for table in tables]
            
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            if missing_tables:
                print_warning(f"Отсутствуют таблицы: {', '.join(missing_tables)}")
                print_info("Таблицы будут созданы автоматически при первом запуске")
            else:
                print_success("Все необходимые таблицы существуют")
            
            cursor.close()
            connection.close()
            return True
        
    except Exception as e:
        print_error(f"Не удалось подключиться к MySQL: {e}")
        print_info("Убедитесь, что MySQL запущен и пароль в .env правильный")
        return False

def check_sdk():
    """Проверка наличия HCNetSDK.dll"""
    print("\n" + "="*60)
    print("4. Проверка HCNetSDK.dll")
    print("="*60)
    
    dll_path = "./lib/HCNetSDK.dll"
    
    if not os.path.exists(dll_path):
        print_error("HCNetSDK.dll не найден в текущей директории")
        print_info("Скопируйте HCNetSDK.dll в папку lib")
        return False
    
    print_success("HCNetSDK.dll найден")
    
    # Проверка архитектуры
    file_size = os.path.getsize(dll_path)
    print_info(f"Размер файла: {file_size / 1024 / 1024:.2f} MB")
    
    return True

def check_network_connectivity(ip, port=8000):
    """Проверка доступности IP адреса"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def check_terminals():
    """Проверка доступности терминалов в сети"""
    print("\n" + "="*60)
    print("5. Проверка доступности терминалов")
    print("="*60)
    
    terminals_in = [
        os.getenv("TERMINAL_IN_1"),
        os.getenv("TERMINAL_IN_2"),
        os.getenv("TERMINAL_IN_3"),
        os.getenv("TERMINAL_IN_4"),
        os.getenv("TERMINAL_IN_5"),
    ]
    
    terminals_out = [
        os.getenv("TERMINAL_OUT_1"),
        os.getenv("TERMINAL_OUT_2"),
        os.getenv("TERMINAL_OUT_3"),
        os.getenv("TERMINAL_OUT_4"),
        os.getenv("TERMINAL_OUT_5"),
    ]
    
    port = int(os.getenv("TERMINAL_PORT", 8000))
    
    print("\n📥 Терминалы входа:")
    available_in = 0
    for ip in terminals_in:
        if check_network_connectivity(ip, port):
            print_success(f"{ip} доступен")
            available_in += 1
        else:
            print_warning(f"{ip} недоступен")
    
    print("\n📤 Терминалы выхода:")
    available_out = 0
    for ip in terminals_out:
        if check_network_connectivity(ip, port):
            print_success(f"{ip} доступен")
            available_out += 1
        else:
            print_warning(f"{ip} недоступен")
    
    print(f"\n📊 Доступно терминалов входа: {available_in}/5")
    print(f"📊 Доступно терминалов выхода: {available_out}/5")
    
    if available_in == 0:
        print_error("Ни один терминал входа недоступен!")
        return False
    elif available_in < 5:
        print_warning("Не все терминалы входа доступны")
    
    return True

def check_dependencies():
    """Проверка установленных зависимостей"""
    print("\n" + "="*60)
    print("6. Проверка зависимостей Python")
    print("="*60)
    
    required_packages = {
        'flask': 'Flask',
        'dotenv': 'python-dotenv',
        'mysql.connector': 'mysql-connector-python'
    }
    
    missing = []
    
    for module, package in required_packages.items():
        try:
            __import__(module)
            print_success(f"{package} установлен")
        except ImportError:
            print_error(f"{package} не установлен")
            missing.append(package)
    
    if missing:
        print_info(f"\nУстановите недостающие пакеты:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    return True

def check_logs_directory():
    """Проверка/создание директории для логов"""
    print("\n" + "="*60)
    print("7. Проверка директории логов")
    print("="*60)
    
    logs_dir = "logs"
    
    if not os.path.exists(logs_dir):
        try:
            os.makedirs(logs_dir)
            print_success("Директория logs создана")
        except Exception as e:
            print_error(f"Не удалось создать директорию logs: {e}")
            return False
    else:
        print_success("Директория logs существует")
    
    return True

def main():
    print("\n" + "="*60)
    print("🔍 ПРОВЕРКА ГОТОВНОСТИ APB СИСТЕМЫ")
    print("="*60)
    
    checks = [
        ("Файл конфигурации", check_env_file),
        ("Переменные окружения", check_env_variables),
        ("MySQL", check_mysql),
        ("SDK DLL", check_sdk),
        ("Доступность терминалов", check_terminals),
        ("Зависимости Python", check_dependencies),
        ("Директория логов", check_logs_directory),
    ]
    
    results = []
    
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Ошибка при проверке '{name}': {e}")
            results.append((name, False))
    
    # Итоговый отчет
    print("\n" + "="*60)
    print("📋 ИТОГОВЫЙ ОТЧЕТ")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {name}")
    
    print("\n" + "="*60)
    
    if passed == total:
        print_success(f"Все проверки пройдены ({passed}/{total})!")
        print_info("Система готова к запуску: python main.py")
        return 0
    else:
        print_warning(f"Пройдено проверок: {passed}/{total}")
        print_error("Исправьте ошибки перед запуском системы")
        return 1

if __name__ == "__main__":
    sys.exit(main())

