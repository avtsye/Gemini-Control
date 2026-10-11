"""Persistent in-app scheduled agent tasks.

Jobs are only considered while the GUI is open and connected. Every run still
requires real-time user approval; never execute unattended privileged actions.
"""
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path
from conversation_store import location

class ScheduledAgentStore:
    def __init__(self,path=None):
        self.path=Path(path or location().parent/"scheduled-agents.sqlite3")
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, prompt TEXT NOT NULL, model TEXT NOT NULL,
                due REAL NOT NULL, repeat_seconds INTEGER NOT NULL, enabled INTEGER NOT NULL DEFAULT 1)""")
            db.commit()
    def add(self,prompt,model,delay_minutes,repeat_minutes=0):
        if not isinstance(prompt,str) or not 3<=len(prompt)<=8000:
            raise ValueError("Invalid agent task description")
        if not isinstance(model,str) or not 1<=len(model)<=120:
            raise ValueError("Invalid model name")
        if not isinstance(delay_minutes,int) or not 1<=delay_minutes<=525600:
            raise ValueError("Delay must be between 1 minute and a year")
        if not isinstance(repeat_minutes,int) or (repeat_minutes!=0 and not 15<=repeat_minutes<=525600):
            raise ValueError("Repeat must be zero or at least fifteen minutes")
        ident=str(uuid.uuid4())
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("INSERT INTO tasks VALUES(?,?,?,?,?,1)",
                (ident,prompt,model,time.time()+delay_minutes*60,repeat_minutes*60))
            db.commit()
        return {"id":ident,"due_in_minutes":delay_minutes,"repeat_minutes":repeat_minutes}
    def list(self):
        with closing(sqlite3.connect(self.path)) as db:
            rows=db.execute("SELECT id,prompt,model,due,repeat_seconds FROM tasks WHERE enabled=1 ORDER BY due").fetchall()
        return [{"id":i,"prompt":p,"model":m,"due":due,"repeat_minutes":repeat//60}
                for i,p,m,due,repeat in rows]
    def cancel(self,identifier):
        identifier=str(uuid.UUID(str(identifier)))
        with closing(sqlite3.connect(self.path)) as db:
            result=db.execute("UPDATE tasks SET enabled=0 WHERE id=? AND enabled=1",(identifier,))
            db.commit()
            return result.rowcount>0
    def due(self,now=None):
        moment=time.time() if now is None else float(now)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("BEGIN IMMEDIATE")
            rows=db.execute("SELECT id,prompt,model,repeat_seconds FROM tasks WHERE enabled=1 AND due<=? ORDER BY due LIMIT 1",(moment,)).fetchall()
            for identifier,prompt,model,repeat in rows:
                if repeat:
                    db.execute("UPDATE tasks SET due=? WHERE id=?",(moment+repeat,identifier))
                else:
                    db.execute("UPDATE tasks SET enabled=0 WHERE id=?",(identifier,))
            db.commit()
        return [{"id":ident,"prompt":p,"model":model} for ident,p,model,_ in rows]
