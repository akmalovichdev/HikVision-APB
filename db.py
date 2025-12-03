#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
import threading
from dotenv import load_dotenv

load_dotenv()


class Database:
    """Класс для работы с MySQL базой данных APB системы"""

    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", 3306))
        self.database = os.getenv("DB_NAME", "apb_system")
        self.user = os.getenv("DB_USER", "root")
        self.password = os.getenv("DB_PASSWORD", "")
        self.connection = None
        self.lock = threading.Lock()  # Блокировка для потокобезопасности

    def connect(self):
        """Подключение к базе данных"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                autocommit=True,
                connection_timeout=10,
                pool_reset_session=True,
                sql_mode='STRICT_TRANS_TABLES'
            )
            if self.connection.is_connected():
                print(f"✅ Подключено к MySQL базе: {self.database}")
                return True
        except Error as e:
            print(f"❌ Ошибка подключения к MySQL: {e}")
            return False

    def disconnect(self):
        """Отключение от базы данных"""
        with self.lock:
            if self.connection and self.connection.is_connected():
                self.connection.close()
                print("🔌 Отключено от MySQL")

    def _ensure_connection(self):
        """Проверка и восстановление подключения к БД"""
        try:
            if self.connection is None or not self.connection.is_connected():
                # Закрываем старое подключение если оно есть
                try:
                    if self.connection:
                        self.connection.close()
                except:
                    pass

                # Пытаемся переподключиться
                self.connection = mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    autocommit=True,
                    connection_timeout=10,
                    pool_reset_session=True,
                    sql_mode='STRICT_TRANS_TABLES'
                )
                if self.connection.is_connected():
                    return True
                else:
                    return False
            return True
        except Error as e:
            print(f"❌ Ошибка переподключения к MySQL: {e}")
            return False

    def initialize_tables(self):
        """Создание необходимых таблиц"""
        with self.lock:
            if not self._ensure_connection():
                print("❌ Не удалось подключиться к БД для инициализации таблиц")
                return False
            try:
                cursor = self.connection.cursor()

                # Таблица состояний пользователей (APB)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_states (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_name VARCHAR(255) NOT NULL UNIQUE,
                        state ENUM('inside', 'outside') NOT NULL DEFAULT 'outside',
                        last_terminal VARCHAR(50),
                        last_event_time DATETIME,
                        last_reset_date DATE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_user_name (user_name),
                        INDEX idx_state (state)
                    )
                """)

                # Таблица логов событий
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS event_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_name VARCHAR(255) NOT NULL,
                        terminal_ip VARCHAR(50) NOT NULL,
                        terminal_type ENUM('entry', 'exit') NOT NULL,
                        event_type VARCHAR(50),
                        sub_event_type INT,
                        action_taken VARCHAR(100),
                        state_before ENUM('inside', 'outside'),
                        state_after ENUM('inside', 'outside'),
                        door_opened BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_name (user_name),
                        INDEX idx_terminal (terminal_ip),
                        INDEX idx_created_at (created_at)
                    )
                """)

                # Таблица конфигурации системы
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_config (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        config_key VARCHAR(100) NOT NULL UNIQUE,
                        config_value TEXT,
                        description TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)

                cursor.close()
                print("✅ Таблицы инициализированы")
                return True
            except Error as e:
                print(f"❌ Ошибка создания таблиц: {e}")
                return False

    def get_user_state(self, user_name):
        """
        Получить состояние пользователя
        Возвращает: ('inside' | 'outside', last_terminal, last_event_time)
        """
        with self.lock:
            if not self._ensure_connection():
                print(f"❌ Ошибка получения состояния пользователя: MySQL Connection not available")
                return {'state': 'outside', 'last_terminal': None, 'last_event_time': None, 'last_reset_date': None}
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    "SELECT state, last_terminal, last_event_time, last_reset_date FROM user_states WHERE user_name = %s",
                    (user_name,)
                )
                result = cursor.fetchone()
                cursor.close()

                if result:
                    return {
                        'state': result[0],
                        'last_terminal': result[1],
                        'last_event_time': result[2],
                        'last_reset_date': result[3]
                    }
                else:
                    # Пользователь не найден - создаем запись
                    # Освобождаем блокировку перед рекурсивным вызовом
                    pass
            except Error as e:
                print(f"❌ Ошибка получения состояния пользователя: {e}")
                return {'state': 'outside', 'last_terminal': None, 'last_event_time': None, 'last_reset_date': None}

        # Если пользователь не найден, создаем запись (вне блокировки)
        return self.create_user_state(user_name)

    def create_user_state(self, user_name):
        """Создать новую запись пользователя"""
        with self.lock:
            if not self._ensure_connection():
                print(f"❌ Ошибка создания пользователя: MySQL Connection not available")
                return {'state': 'outside', 'last_terminal': None, 'last_event_time': None, 'last_reset_date': None}
            try:
                cursor = self.connection.cursor()
                today = datetime.now().date()
                cursor.execute(
                    """INSERT INTO user_states (user_name, state, last_reset_date)
                       VALUES (%s, 'outside', %s)""",
                    (user_name, today)
                )
                cursor.close()
                print(f"➕ Создан новый пользователь: {user_name}")
                return {'state': 'outside', 'last_terminal': None, 'last_event_time': None, 'last_reset_date': today}
            except Error as e:
                print(f"❌ Ошибка создания пользователя: {e}")
                return {'state': 'outside', 'last_terminal': None, 'last_event_time': None, 'last_reset_date': None}

    def update_user_state(self, user_name, new_state, terminal_ip):
        """Обновить состояние пользователя"""
        with self.lock:
            if not self._ensure_connection():
                print(f"❌ Ошибка обновления состояния: MySQL Connection not available")
                return False
            try:
                cursor = self.connection.cursor()
                now = datetime.now()
                today = now.date()
                cursor.execute(
                    """UPDATE user_states
                       SET state = %s, last_terminal = %s, last_event_time = %s, last_reset_date = %s
                       WHERE user_name = %s""",
                    (new_state, terminal_ip, now, today, user_name)
                )
                cursor.close()
                return True
            except Error as e:
                print(f"❌ Ошибка обновления состояния: {e}")
                return False

    def log_event(self, user_name, terminal_ip, terminal_type, event_type, sub_event_type,
                  action_taken, state_before, state_after, door_opened):
        """Записать событие в лог"""
        with self.lock:
            if not self._ensure_connection():
                print(f"❌ Ошибка записи лога: MySQL Connection not available")
                return False
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    """INSERT INTO event_logs
                       (user_name, terminal_ip, terminal_type, event_type, sub_event_type,
                        action_taken, state_before, state_after, door_opened)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (user_name, terminal_ip, terminal_type, event_type, sub_event_type,
                     action_taken, state_before, state_after, door_opened)
                )
                cursor.close()
                return True
            except Error as e:
                print(f"❌ Ошибка записи лога: {e}")
                return False

    def reset_daily_states(self):
        """Сброс всех состояний на 'outside' (вызывается раз в день)"""
        with self.lock:
            if not self._ensure_connection():
                print(f"❌ Ошибка сброса состояний: MySQL Connection not available")
                return 0
            try:
                cursor = self.connection.cursor()
                today = datetime.now().date()
                cursor.execute(
                    """UPDATE user_states
                       SET state = 'outside', last_reset_date = %s
                       WHERE last_reset_date < %s OR last_reset_date IS NULL""",
                    (today, today)
                )
                affected_rows = cursor.rowcount
                cursor.close()
                print(f"🔄 Сброшено состояний: {affected_rows}")
                return affected_rows
            except Error as e:
                print(f"❌ Ошибка сброса состояний: {e}")
                return 0

    def get_all_users_inside(self):
        """Получить всех пользователей внутри здания"""
        with self.lock:
            if not self._ensure_connection():
                print(f"❌ Ошибка получения пользователей внутри: MySQL Connection not available")
                return []
            try:
                cursor = self.connection.cursor()
                cursor.execute(
                    "SELECT user_name, last_terminal, last_event_time FROM user_states WHERE state = 'inside'"
                )
                results = cursor.fetchall()
                cursor.close()
                return results
            except Error as e:
                print(f"❌ Ошибка получения пользователей внутри: {e}")
                return []

    def get_statistics(self, start_date=None, end_date=None):
        """Получить статистику событий за период"""
        with self.lock:
            if not self._ensure_connection():
                print(f"❌ Ошибка получения статистики: MySQL Connection not available")
                return []
            try:
                cursor = self.connection.cursor(dictionary=True)
                query = """
                    SELECT
                        DATE(created_at) as date,
                        terminal_type,
                        COUNT(*) as total_events,
                        COUNT(DISTINCT user_name) as unique_users,
                        SUM(door_opened) as doors_opened
                    FROM event_logs
                """
                params = []

                if start_date and end_date:
                    query += " WHERE created_at BETWEEN %s AND %s"
                    params = [start_date, end_date]
                elif start_date:
                    query += " WHERE created_at >= %s"
                    params = [start_date]

                query += " GROUP BY DATE(created_at), terminal_type ORDER BY date DESC"

                cursor.execute(query, params)
                results = cursor.fetchall()
                cursor.close()
                return results
            except Error as e:
                print(f"❌ Ошибка получения статистики: {e}")
                return []


# Глобальный экземпляр базы данных
db = Database()

