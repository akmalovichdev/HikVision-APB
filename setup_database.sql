-- Скрипт для создания базы данных APB System

-- Создание базы данных
CREATE DATABASE IF NOT EXISTS apb_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Использование базы
USE apb_system;

-- Таблица состояний пользователей
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица логов событий
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица конфигурации системы
CREATE TABLE IF NOT EXISTS system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Создание пользователя (опционально)
-- Раскомментируйте и измените пароль при необходимости
-- CREATE USER IF NOT EXISTS 'apb_user'@'localhost' IDENTIFIED BY 'your_strong_password';
-- GRANT ALL PRIVILEGES ON apb_system.* TO 'apb_user'@'localhost';
-- FLUSH PRIVILEGES;

SELECT 'Database setup completed successfully!' AS status;

