import sqlite3
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "database.db")


def get_db():
    os.makedirs(DATABASE_DIR, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    cursor = conn.cursor()

    # =========================
    # COMPTES
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL UNIQUE,

            password TEXT NOT NULL,

            role TEXT NOT NULL DEFAULT 'public',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # =========================
    # PUBLICATIONS
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS publications (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            content TEXT NOT NULL,

            type TEXT NOT NULL,

            image TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
    """)


    # =========================
    # COMMENTAIRES
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            publication_id INTEGER NOT NULL,

            user_id INTEGER,

            author_name TEXT NOT NULL,

            content TEXT,

            voice TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (publication_id)
                REFERENCES publications(id),

            FOREIGN KEY (user_id)
                REFERENCES users(id)

        )
    """)


    # =========================
    # RÉACTIONS
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reactions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            publication_id INTEGER NOT NULL,

            user_id INTEGER,

            reaction TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(publication_id, user_id, reaction),

            FOREIGN KEY (publication_id)
                REFERENCES publications(id),

            FOREIGN KEY (user_id)
                REFERENCES users(id)

        )
    """)


    # =========================
    # RÉPONSES AUX COMMENTAIRES
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS replies (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            comment_id INTEGER NOT NULL,

            user_id INTEGER,

            author_name TEXT NOT NULL,

            content TEXT,

            voice TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (comment_id)
                REFERENCES comments(id),

            FOREIGN KEY (user_id)
                REFERENCES users(id)

        )
    """)


    conn.commit()

    conn.close()


if __name__ == "__main__":

    init_db()

    print("Base de données créée avec succès !")

    print(f"Emplacement : {DATABASE_PATH}")
