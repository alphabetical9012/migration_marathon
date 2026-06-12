import os
import json
import psycopg2
from psycopg2.extras import Json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SOURCE_DB = os.getenv("SOURCE_DB")
TARGET_DB = os.getenv("TARGET_DB")

def get_source():
    return psycopg2.connect(SOURCE_DB, sslmode="require")

def get_target():
    return psycopg2.connect(TARGET_DB, sslmode="require")

def main():
    if not SOURCE_DB or not TARGET_DB:
        logger.error("Не заданы SOURCE_DB или TARGET_DB")
        return

    logger.info("Начинаем миграцию марафонного бота...")
    src = get_source()
    tgt = get_target()
    src_cur = src.cursor()
    tgt_cur = tgt.cursor()

    # marathon_users
    tgt_cur.execute("""CREATE TABLE IF NOT EXISTS marathon_users (
        user_id BIGINT PRIMARY KEY,
        timezone TEXT NOT NULL,
        sleep_time TEXT NOT NULL,
        interval_hours REAL NOT NULL,
        day_number INTEGER DEFAULT 1,
        start_date DATE,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW()
    )""")
    tgt.commit()
    src_cur.execute("SELECT * FROM marathon_users")
    rows = src_cur.fetchall()
    count = 0
    for row in rows:
        try:
            tgt_cur.execute(
                "INSERT INTO marathon_users VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                row
            )
            tgt.commit()
            count += 1
        except Exception as e:
            tgt.rollback()
            logger.warning(f"marathon_users строка пропущена: {e}")
    logger.info(f"Таблица marathon_users: перенесено {count} строк ✅")

    # marathon_checkins — JSONB поле messages конвертируем через Json()
    tgt_cur.execute("""CREATE TABLE IF NOT EXISTS marathon_checkins (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        day_number INTEGER NOT NULL,
        messages JSONB DEFAULT '[]',
        checkin_count INTEGER DEFAULT 0,
        answered_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW()
    )""")
    tgt.commit()
    src_cur.execute("SELECT id, user_id, day_number, messages, checkin_count, answered_count, created_at FROM marathon_checkins")
    rows = src_cur.fetchall()
    count = 0
    for row in rows:
        try:
            id_, user_id, day_number, messages, checkin_count, answered_count, created_at = row
            # Конвертируем messages в JSON если это dict или list
            if isinstance(messages, (dict, list)):
                messages = Json(messages)
            tgt_cur.execute(
                "INSERT INTO marathon_checkins (id, user_id, day_number, messages, checkin_count, answered_count, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (id_, user_id, day_number, messages, checkin_count, answered_count, created_at)
            )
            tgt.commit()
            count += 1
        except Exception as e:
            tgt.rollback()
            logger.warning(f"marathon_checkins строка пропущена: {e}")
    logger.info(f"Таблица marathon_checkins: перенесено {count} строк ✅")

    # marathon_messages
    tgt_cur.execute("""CREATE TABLE IF NOT EXISTS marathon_messages (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        day_number INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    )""")
    tgt.commit()
    src_cur.execute("SELECT id, user_id, role, content, day_number, created_at FROM marathon_messages")
    rows = src_cur.fetchall()
    count = 0
    for row in rows:
        try:
            tgt_cur.execute(
                "INSERT INTO marathon_messages (id, user_id, role, content, day_number, created_at) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                row
            )
            tgt.commit()
            count += 1
        except Exception as e:
            tgt.rollback()
            logger.warning(f"marathon_messages строка пропущена: {e}")
    logger.info(f"Таблица marathon_messages: перенесено {count} строк ✅")

    # marathon_state — JSONB поле data конвертируем через Json()
    tgt_cur.execute("""CREATE TABLE IF NOT EXISTS marathon_state (
        user_id BIGINT PRIMARY KEY,
        state TEXT NOT NULL,
        data JSONB DEFAULT '{}'
    )""")
    tgt.commit()
    src_cur.execute("SELECT user_id, state, data FROM marathon_state")
    rows = src_cur.fetchall()
    count = 0
    for row in rows:
        try:
            user_id, state, data = row
            if isinstance(data, (dict, list)):
                data = Json(data)
            tgt_cur.execute(
                "INSERT INTO marathon_state VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (user_id, state, data)
            )
            tgt.commit()
            count += 1
        except Exception as e:
            tgt.rollback()
            logger.warning(f"marathon_state строка пропущена: {e}")
    logger.info(f"Таблица marathon_state: перенесено {count} строк ✅")

    src.close()
    tgt.close()
    logger.info("Миграция марафонного бота завершена ✅")

if __name__ == "__main__":
    main()
