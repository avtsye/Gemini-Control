"""Local conversation history and reviewed capability proposals. No executable plugins."""
import json,os,sqlite3,uuid
from pathlib import Path
from datetime import datetime,timezone

def location():
    root=Path(os.environ.get("LOCALAPPDATA",Path.home()/".local/share"))/"AIControlDesktop"
    root.mkdir(parents=True,exist_ok=True)
    return root/"history.sqlite3"

class ConversationStore:
    def __init__(self,path=None):
        self.path=str(path or location())
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, created TEXT NOT NULL,
                    updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL, content TEXT NOT NULL, created TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id));
                CREATE TABLE IF NOT EXISTS proposals (
                    id TEXT PRIMARY KEY, conversation_id TEXT, description TEXT NOT NULL,
                    suggested_steps TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
                    created TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(conversation_id,id);
            """)
    def _db(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.execute("PRAGMA foreign_keys=ON")
        return db
    def create(self,title="שיחה חדשה"):
        identifier=str(uuid.uuid4())
        timestamp=datetime.now(timezone.utc).isoformat()
        with self._db() as db:
            db.execute("INSERT INTO conversations VALUES(?,?,?,?)",
                       (identifier,title[:120],timestamp,timestamp))
        return identifier
    def chats(self):
        with self._db() as db:
            return db.execute("SELECT id,title FROM conversations ORDER BY updated DESC").fetchall()
    def messages(self,chat_id):
        with self._db() as db:
            return db.execute("SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id",(chat_id,)).fetchall()
    def add(self,chat_id,role,content):
        if role not in ("user","assistant","system_note"):raise ValueError("Invalid message role")
        if not isinstance(content,str) or len(content)>200000:raise ValueError("Invalid message")
        timestamp=datetime.now(timezone.utc).isoformat()
        with self._db() as db:
            cursor=db.execute("INSERT INTO messages(conversation_id,role,content,created) VALUES(?,?,?,?)",
                              (chat_id,role,content,timestamp))
            if role=="user":
                count=db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=?",(chat_id,)).fetchone()[0]
                if count==1:
                    db.execute("UPDATE conversations SET title=? WHERE id=?",(content.replace("\n"," ")[:65],chat_id))
            db.execute("UPDATE conversations SET updated=? WHERE id=?",(timestamp,chat_id))
            return cursor.lastrowid
    def delete(self,chat_id):
        with self._db() as db:
            db.execute("DELETE FROM messages WHERE conversation_id=?",(chat_id,))
            db.execute("DELETE FROM proposals WHERE conversation_id=?",(chat_id,))
            db.execute("DELETE FROM conversations WHERE id=?",(chat_id,))
    def propose(self,chat_id,description,steps):
        if not isinstance(description,str) or not 1<=len(description)<=1000:raise ValueError("Invalid proposal")
        if not isinstance(steps,str) or len(steps)>12000:raise ValueError("Invalid plan")
        identifier=str(uuid.uuid4())
        with self._db() as db:
            db.execute("INSERT INTO proposals VALUES(?,?,?,?,?,?)",
                (identifier,chat_id,description,steps,"pending",datetime.now(timezone.utc).isoformat()))
        return identifier
    def proposals(self):
        with self._db() as db:
            return db.execute("SELECT id,description,suggested_steps,status FROM proposals ORDER BY created DESC").fetchall()
    def review(self,proposal_id,status):
        if status not in ("approved","rejected"):raise ValueError("Invalid status")
        with self._db() as db:
            db.execute("UPDATE proposals SET status=? WHERE id=? AND status='pending'",(status,proposal_id))
