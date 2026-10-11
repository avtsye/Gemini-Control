"""Persistent local reminders; poll while the desktop app runs.

Never auto-executes agent actions, arbitrary Python, or shell commands.
"""
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path
from conversation_store import location

class ReminderStore:
    def __init__(self,path=None):
        self.path=Path(path or location().parent/"reminders.sqlite3")
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,title TEXT NOT NULL,
                due REAL NOT NULL,repeat_seconds INTEGER NOT NULL DEFAULT 0)""")
            db.commit()
    def add(self,title,delay_minutes,repeat_minutes=0):
        if not isinstance(title,str) or not 1<=len(title)<=250:
            raise ValueError("Invalid reminder")
        if not isinstance(delay_minutes,int) or not 1<=delay_minutes<=525600:
            raise ValueError("Delay must be between 1 minute and a year")
        if not isinstance(repeat_minutes,int) or (repeat_minutes!=0 and not 5<=repeat_minutes<=525600):
            raise ValueError("Repeat must be 0 or at least 5 minutes")
        identifier=str(uuid.uuid4())
        due=time.time()+delay_minutes*60
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("INSERT INTO reminders VALUES(?,?,?,?)",
                       (identifier,title,due,repeat_minutes*60))
            db.commit()
        return {"id":identifier,"title":title,"due":due,"repeat_minutes":repeat_minutes}
    def list(self):
        with closing(sqlite3.connect(self.path)) as db:
            rows=db.execute("SELECT id,title,due,repeat_seconds FROM reminders ORDER BY due").fetchall()
        return [{"id":i,"title":t,"due":d,"repeat_minutes":r//60} for i,t,d,r in rows]
    def cancel(self,identifier):
        identifier=str(uuid.UUID(str(identifier)))
        with closing(sqlite3.connect(self.path)) as db:
            result=db.execute("DELETE FROM reminders WHERE id=?",(identifier,))
            db.commit()
            return result.rowcount>0
    def due(self,now=None):
        now=time.time() if now is None else float(now)
        with closing(sqlite3.connect(self.path)) as db:
            rows=db.execute("SELECT id,title,due,repeat_seconds FROM reminders WHERE due<=? ORDER BY due LIMIT 25",(now,)).fetchall()
            for identifier,title,due,repeat in rows:
                if repeat>0:
                    next_time=due+(int((now-due)//repeat)+1)*repeat
                    db.execute("UPDATE reminders SET due=? WHERE id=?",(next_time,identifier))
                else:
                    db.execute("DELETE FROM reminders WHERE id=?",(identifier,))
            db.commit()
        return [{"id":identifier,"title":title} for identifier,title,_,_ in rows]
