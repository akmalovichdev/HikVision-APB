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
    last_entry_auth_time DATETIME,
    last_reset_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_name (user_name),
    INDEX idx_state (state),
    INDEX idx_last_entry_auth_time (last_entry_auth_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Миграция: добавление поля last_entry_auth_time для существующих таблиц
-- (безопасно выполнять даже если поле уже существует)
SET @dbname = DATABASE();
SET @tablename = 'user_states';
SET @columnname = 'last_entry_auth_time';
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (COLUMN_NAME = @columnname)
    ) > 0,
    'SELECT 1',
    CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' DATETIME NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Таблица логов событий
CREATE TABLE IF NOT EXISTS event_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_name VARCHAR(255) NOT NULL,
    terminal_ip VARCHAR(50) NOT NULL,
    terminal_type ENUM('entry', 'exit') NOT NULL,
    event_type VARCHAR(50),
    sub_event_type INT,
    action_taken VARCHAR(100),
    status_code VARCHAR(50) NOT NULL,
    is_violation BOOLEAN DEFAULT FALSE,
    state_before ENUM('inside', 'outside'),
    state_after ENUM('inside', 'outside'),
    door_opened BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_name (user_name),
    INDEX idx_terminal (terminal_ip),
    INDEX idx_created_at (created_at),
    INDEX idx_status_code (status_code),
    INDEX idx_is_violation (is_violation),
    INDEX idx_violation_date (is_violation, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Миграция: добавление полей status_code и is_violation для существующих таблиц
SET @dbname = DATABASE();
SET @tablename = 'event_logs';
SET @columnname1 = 'status_code';
SET @columnname2 = 'is_violation';

-- Добавление status_code
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (COLUMN_NAME = @columnname1)
    ) > 0,
    'SELECT 1',
    CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname1, ' VARCHAR(50) NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Добавление is_violation
SET @preparedStatement = (SELECT IF(
    (
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE
            (TABLE_SCHEMA = @dbname)
            AND (TABLE_NAME = @tablename)
            AND (COLUMN_NAME = @columnname2)
    ) > 0,
    'SELECT 1',
    CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname2, ' BOOLEAN DEFAULT FALSE')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

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

