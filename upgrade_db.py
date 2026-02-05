import sqlite3
import os

DB_FILE = "./backend/ai_chat.db"

def upgrade_db():
    if not os.path.exists(DB_FILE):
        print("Database file not found. It will be created on first run.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if 'mode' column exists in chat_sessions
    cursor.execute("PRAGMA table_info(chat_sessions)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'mode' not in columns:
        print("Adding 'mode' column to chat_sessions...")
        try:
            cursor.execute("ALTER TABLE chat_sessions ADD COLUMN mode TEXT DEFAULT 'casual'")
            conn.commit()
            print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("'mode' column already exists.")
        
    conn.close()

if __name__ == "__main__":
    upgrade_db()
