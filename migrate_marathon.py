import os
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SOURCE_DB = os.getenv("SOURCE_DB")
TARGET_DB = os.getenv("TARGET_DB")

def get_source():
    return psycopg2.connect(SOURCE_DB, sslmode="require")

def get_target():
    return psycopg2.connect(TARGET_DB, sslmode="require")

def migrate_table(src_cur, tgt_cur, tgt_conn, table_name, create_sql, insert_sql):
    try:
        tgt_cur.execute(create_sql)
        tgt_conn.commit()
        src_cur.execute(f"SELECT * FROM {table_name}")
        rows = src_cur.fetchall()
        if not rows:
            logger.info(f"Таблица {table_name}: пустая, пропускаем")
            return
        for row in rows:
            try:
                tgt_cur.execute(insert_sql, row)
            except Exception as e:
                logger.warning(f"Строка пропущена: {e}")
                tgt_conn.rollback()
                continue
        tgt_conn.commit()
        logger.info(f"Таблица {table_name}: перенесено {len(rows)} строк ✅")
    except Exception as e:
        logger.error(f"Ошибка таблицы {table_name}: {e}")
        tgt_conn.rollback()

def main():
    if not SOURCE_DB or not TARGET_DB:
        logger.error("Не заданы SOURCE_DB или TARGET_DB")
        return

    logger.info("Начинаем миграцию марафонного бота...")
    src = get_source()
    tgt = get_target()
    src_cur = src.cursor()
    tgt_cur = tgt.cursor()

    migrate_table(src_cur, tgt_cur, tgt,
        "marathon_users",
        """CREATE TABLE IF NOT EXISTS marathon_users (
            user_id BIGINT PRIMARY KEY,
            timezone TEXT NOT NULL,
            sleep_time TEXT NOT NULL,
            interval_hours REAL NOT NULL,
            day_number INTEGER DEFAULT 1,
            start_date DATE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        "INSERT INTO marathon_users VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING"
    )

    migrate_table(src_cur, tgt_cur, tgt,
        "marathon_checkins",
        """CREATE TABLE IF NOT EXISTS marathon_checkins (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            day_number INTEGER NOT NULL,
            messages JSONB DEFAULT '[]',
            checkin_count INTEGER DEFAULT 0,
            answered_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        "INSERT INTO marathon_checkins (id, user_id, day_number, messages, checkin_count, answered_count, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING"
    )

    migrate_table(src_cur, tgt_cur, tgt,
        "marathon_messages",
        """CREATE TABLE IF NOT EXISTS marathon_messages (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            day_number INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        "INSERT INTO marathon_messages (id, user_id, role, content, day_number, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING"
    )

    migrate_table(src_cur, tgt_cur, tgt,
        "marathon_state",
        """CREATE TABLE IF NOT EXISTS marathon_state (
            user_id BIGINT PRIMARY KEY,
            state TEXT NOT NULL,
            data JSONB DEFAULT '{}'
        )""",
        "INSERT INTO marathon_state VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
    )

    src.close()
    tgt.close()
    logger.info("Миграция марафонного бота завершена ✅")

if __name__ == "__main__":
    main()
