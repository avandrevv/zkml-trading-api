from fastapi import FastAPI
from pydantic import BaseModel
import uuid
import json
import redis
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Настройка путей
BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_DIR = BASE_DIR / "settings"
KEYS_DIR = BASE_DIR / "keys"
PROOFS_DIR = BASE_DIR / "proofs"

DATABASE_URL = "postgresql://zkml:123@localhost:5432/zkml_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    status = Column(String, default="queued")
    input_hash = Column(String)
    result = Column(Text)
    proof_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

Base.metadata.create_all(engine)

app = FastAPI(title="ZK Trading API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class SubmitRequest(BaseModel):
    features: list[float]

@app.post("/submit")
async def submit(request: SubmitRequest):
    task_id = str(uuid.uuid4())
    r.lpush("task_queue", task_id)
    r.hset(f"task:{task_id}", mapping={
        "task_id": task_id,
        "features": json.dumps(request.features),
        "status": "queued"
    })
    
    db = SessionLocal()
    db.add(Task(id=task_id, status="queued", input_hash=str(hash(tuple(request.features)))))
    db.commit()
    db.close()
    return {"task_id": task_id, "status": "queued"}

@app.get("/result/{task_id}")
async def get_result(task_id: str):
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    db.close()
    
    if not task:
        return {"error": "Task not found"}
    
    return {
        "task_id": task.id,
        "status": task.status,
        "result": json.loads(task.result) if task.result else None,
        "proof_path": task.proof_path
    }

@app.get("/proof/{filename}")
async def get_proof(filename: str):
    # Теперь ищем файлы в папке proofs
    file_path = PROOFS_DIR / filename
    return FileResponse(file_path)

@app.post("/verify/{task_id}")
async def verify_task(task_id: str):
    import ezkl
    task = r.hgetall(f"task:{task_id}")
    if not task or not task.get("proof_path"):
        return {"verified": False}
    
    proof_file = PROOFS_DIR / task["proof_path"]
    try:
        verified = ezkl.verify(
            str(proof_file), 
            str(SETTINGS_DIR / "settings.json"), 
            str(KEYS_DIR / "vk.key"), 
            srs_path=str(SETTINGS_DIR / "kzg.srs")
        )
    except RuntimeError as e:
        # Логируем ошибку при необходимости
        print(f"Verification error for task {task_id}: {e}")
        verified = False
    
    return {"verified": verified}

@app.get("/tasks")
async def get_tasks(limit: int = 10, offset: int = 0):
    db = SessionLocal()
    tasks = db.query(Task).order_by(Task.created_at.desc()).offset(offset).limit(limit).all()
    db.close()
    return [{"task_id": t.id, "status": t.status, "result": json.loads(t.result) if t.result else None, "created_at": t.created_at, "completed_at": t.completed_at} for t in tasks]

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        db.close()
        return {"error": "Task not found"}
    
    # Удаляем файл proof, если есть
    if task.proof_path:
        proof_file = PROOFS_DIR / task.proof_path
        if proof_file.exists():
            proof_file.unlink()
    
    db.delete(task)
    db.commit()
    db.close()
    
    # Удаляем из Redis
    r.delete(f"task:{task_id}")
    
    return {"success": True}