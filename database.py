import aiosqlite
from config import DB_FILE, logger

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        # User state (Active subject)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_state (
                user_id INTEGER PRIMARY KEY,
                active_subject TEXT
            )
        ''')
        # Extracted PDF Text
        await db.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                user_id INTEGER,
                subject TEXT,
                extracted_text TEXT,
                PRIMARY KEY (user_id, subject)
            )
        ''')
        # Generated Content Cache
        await db.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                user_id INTEGER,
                subject TEXT,
                command TEXT,
                response_text TEXT,
                PRIMARY KEY (user_id, subject, command)
            )
        ''')
        await db.commit()
    logger.info("Database initialized successfully.")

async def set_active_subject(user_id: int, subject: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            'INSERT INTO user_state (user_id, active_subject) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET active_subject=?',
            (user_id, subject, subject)
        )
        await db.commit()

async def get_active_subject(user_id: int) -> str:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT active_subject FROM user_state WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def save_document_text(user_id: int, subject: str, text: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            'INSERT INTO documents (user_id, subject, extracted_text) VALUES (?, ?, ?) ON CONFLICT(user_id, subject) DO UPDATE SET extracted_text=?',
            (user_id, subject, text, text)
        )
        # Clear cache for this subject because new PDF arrived
        await db.execute('DELETE FROM cache WHERE user_id = ? AND subject = ?', (user_id, subject))
        await db.commit()

async def get_document_text(user_id: int, subject: str) -> str:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT extracted_text FROM documents WHERE user_id = ? AND subject = ?', (user_id, subject)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def save_to_cache(user_id: int, subject: str, command: str, response: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            'INSERT INTO cache (user_id, subject, command, response_text) VALUES (?, ?, ?, ?) ON CONFLICT(user_id, subject, command) DO UPDATE SET response_text=?',
            (user_id, subject, command, response, response)
        )
        await db.commit()

async def get_from_cache(user_id: int, subject: str, command: str) -> str:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT response_text FROM cache WHERE user_id = ? AND subject = ? AND command = ?', (user_id, subject, command)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_available_subjects(user_id: int) -> list:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT subject FROM documents WHERE user_id = ?', (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
