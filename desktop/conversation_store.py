"""Local conversation history and reviewed capability proposals. No executable plugins."""
import json,os,sqlite3,uuid
from contextlib import contextmanager
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
            db.execute("""CREATE TABLE IF NOT EXISTS conversation_flags (
                conversation_id TEXT PRIMARY KEY, pinned INTEGER NOT NULL DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0, project TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(conversation_id) REFERENCES conversations(id))""")
    @contextmanager
    def _db(self):
        db=sqlite3.connect(self.path,timeout=10)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            with db:
                yield db
        finally:
            db.close()
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
    def search(self,query,limit=100):
        if not isinstance(query,str) or not query.strip() or len(query)>200:
            return []
        with self._db() as db:
            return db.execute("""SELECT c.id,c.title,m.role,substr(m.content,1,350)
                FROM messages m JOIN conversations c ON c.id=m.conversation_id
                WHERE instr(lower(m.content),lower(?))>0
                ORDER BY m.id DESC LIMIT ?""",(query,min(limit,200))).fetchall()
    def set_flags(self,chat_id,pinned=None,archived=None,project=None):
        if project is not None and (not isinstance(project,str) or len(project)>80):
            raise ValueError("Invalid project")
        with self._db() as db:
            if not db.execute("SELECT 1 FROM conversations WHERE id=?",(chat_id,)).fetchone():
                raise ValueError("Unknown conversation")
            db.execute("INSERT OR IGNORE INTO conversation_flags(conversation_id) VALUES(?)",(chat_id,))
            for field,value in (("pinned",pinned),("archived",archived),("project",project)):
                if value is not None:
                    db.execute("UPDATE conversation_flags SET "+field+"=? WHERE conversation_id=?",
                               ((str(value) if field=="project" else int(bool(value))),chat_id))
    def chats_detailed(self):
        with self._db() as db:
            return db.execute("""SELECT c.id,c.title,COALESCE(f.pinned,0),COALESCE(f.archived,0),
                        COALESCE(f.project,'')
                FROM conversations c LEFT JOIN conversation_flags f ON c.id=f.conversation_id
                ORDER BY COALESCE(f.pinned,0) DESC,c.updated DESC""").fetchall()
    def export_history(self):
        with self._db() as db:
            conversations=db.execute("SELECT id,title,created,updated FROM conversations").fetchall()
            messages=db.execute("SELECT conversation_id,role,content,created FROM messages ORDER BY id").fetchall()
            flags=self.chats_detailed()
        return {"version":1,"conversations":conversations,"messages":messages,"flags":flags}
    def restore_history(self,backup):
        if not isinstance(backup,dict) or backup.get("version")!=1:
            raise ValueError("Unsupported backup")
        conversations=backup.get("conversations")
        messages=backup.get("messages")
        flags=backup.get("flags",[])
        if (not isinstance(conversations,list) or not isinstance(messages,list)
            or not isinstance(flags,list) or len(conversations)>500
            or len(messages)>25000 or len(flags)>500):
            raise ValueError("Invalid backup size")
        mappings={}
        timestamp=datetime.now(timezone.utc).isoformat()
        with self._db() as db:
            for row in conversations:
                if not isinstance(row,(list,tuple)) or len(row)!=4:
                    raise ValueError("Invalid conversation record")
                old,title,*_=row
                if not isinstance(old,str) or not isinstance(title,str) or len(title)>120:
                    raise ValueError("Invalid title")
                if old in mappings:raise ValueError("Duplicate conversation")
                identifier=str(uuid.uuid4())
                mappings[old]=identifier
                db.execute("INSERT INTO conversations VALUES(?,?,?,?)",
                           (identifier,title,timestamp,timestamp))
            for row in messages:
                if not isinstance(row,(list,tuple)) or len(row)!=4:
                    raise ValueError("Invalid message record")
                old,role,content,*_=row
                if old not in mappings or role not in ("user","assistant","system_note"):
                    raise ValueError("Invalid message owner/role")
                if not isinstance(content,str) or len(content)>200000:
                    raise ValueError("Invalid message content")
                db.execute("INSERT INTO messages(conversation_id,role,content,created) VALUES(?,?,?,?)",
                           (mappings[old],role,content,timestamp))
            for row in flags:
                if not isinstance(row,(list,tuple)) or len(row)!=5:raise ValueError("Invalid flags")
                old,title,pin,arc,project=row
                if old not in mappings or not isinstance(project,str) or len(project)>80:
                    continue
                db.execute("INSERT INTO conversation_flags VALUES(?,?,?,?)",
                           (mappings[old],int(bool(pin)),int(bool(arc)),project))
        return {"restored_chats":len(mappings),"restored_messages":len(messages)}
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
    def edit_user_message(self,chat_id,index,new_text):
        if not isinstance(new_text,str) or not new_text.strip() or len(new_text)>25000:
            raise ValueError("Invalid edited message")
        if not isinstance(index,int) or index<0:raise ValueError("Invalid index")
        with self._db() as db:
            rows=db.execute("SELECT id,role FROM messages WHERE conversation_id=? ORDER BY id",(chat_id,)).fetchall()
            if index>=len(rows) or rows[index][1]!="user":raise ValueError("Only user messages may be edited")
            db.execute("UPDATE messages SET content=? WHERE id=?",(new_text,rows[index][0]))
            db.execute("DELETE FROM messages WHERE conversation_id=? AND id>?",(chat_id,rows[index][0]))
            db.execute("UPDATE conversations SET updated=? WHERE id=?",(datetime.now(timezone.utc).isoformat(),chat_id))
    def delete(self,chat_id):
        with self._db() as db:
            db.execute("DELETE FROM conversation_flags WHERE conversation_id=?",(chat_id,))
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
