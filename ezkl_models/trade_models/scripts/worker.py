import redis
import json
import asyncio
import ezkl
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from sqlalchemy import text
from pathlib import Path
import time

# --- НАСТРОЙКА ПУТЕЙ ---
# Скрипт лежит в scripts/, поэтому .parent — это корень trade_models
BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_DIR = BASE_DIR / "settings"
KEYS_DIR = BASE_DIR / "keys"
PROOFS_DIR = BASE_DIR / "proofs"
DATA_DIR = BASE_DIR / "data"

# Создаем папку для доказательств, если она не существует
PROOFS_DIR.mkdir(parents=True, exist_ok=True)

# --- КОНФИГУРАЦИЯ ---
DATABASE_URL = "postgresql://zkml:123@localhost:5432/zkml_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Подключение к Redis (decode_responses=True преобразует байты в строки)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Файлы EZKL
MODEL_COMPILED = str(SETTINGS_DIR / "model.ezkl")
SETTINGS = str(SETTINGS_DIR / "settings.json")
SRS = str(SETTINGS_DIR / "kzg.srs")
PK = str(KEYS_DIR / "pk.key")
VK = str(KEYS_DIR / "vk.key")

async def process_task(task_id: str):
    print(f"\nStarting task: {task_id}")

# в начале process_task:
    start_total = time.time()
    
    # 1. Получаем данные из Redis
    task_data = r.hgetall(f"task:{task_id}")
    
    if not task_data:
        print(f"[Ошибка] Task {task_id} not found in Redis.")
        return

    if "features" not in task_data:
        print(f"[Ошибка] 'features' key missing for task {task_id}. Data: {task_data}")
        return

    try:
        features = json.loads(task_data["features"])
    except Exception as e:
        print(f"[Ошибка] Failed to decode features: {e}")
        return

    # 2. Обновляем статус в Redis и БД
    r.hset(f"task:{task_id}", "status", "processing")
    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE tasks SET status='processing' WHERE id=:id"),
            {"id": task_id}
        )
        db.commit()

        # Определение путей для файлов конкретной задачи
        input_path = str(PROOFS_DIR / f"input_{task_id}.json")
        witness_path = str(PROOFS_DIR / f"witness_{task_id}.json")
        proof_path_full = str(PROOFS_DIR / f"proof_{task_id}.json")
        proof_filename = f"proof_{task_id}.json"

        # 3. Подготовка входных данных
        print(f"[1/3] Preparing input data for EZKL...")
        print(features)
        
        with open(DATA_DIR / "stats.json") as f:
            stats = json.load(f)

        mean = stats["mean"]
        std = stats["std"]

        norm_features = [(features[i] - mean[i]) / (std[i] + 1e-8) for i in range(len(features))]
        with open(input_path, "w") as f:
            json.dump({"input_data": [norm_features]}, f)
        

        # 4. Генерация Witness (свидетельства)
        print(f"[2/3] Generating witness...")
        t1 = time.time()
        await ezkl.gen_witness(input_path, MODEL_COMPILED, witness_path)
        print(f"gen_witness: {time.time() - t1:.2f}s")
        with open(witness_path, 'r') as f:
            witness_data = json.load(f)

        output_value = float(witness_data["pretty_elements"]["rescaled_outputs"][0][0])
        input_values = [float(x) for x in witness_data["pretty_elements"]["rescaled_inputs"][0]]

        if output_value > 0.6:
            action = "buy"
        elif output_value < 0.4:
            action = "sell"
        else:
            action = "hold"

        print(f"[2/3] Model output: {output_value}, Action: {action}")

        # 5. Генерация Proof (доказательства)
        print(f"[3/3] Generating proof (this may take a while)...")
        t2 = time.time()
        ezkl.prove(witness_path, MODEL_COMPILED, PK, proof_path_full, srs_path=SRS)
        print(f"prove: {time.time() - t2:.2f}s")

        # 6. Быстрая проверка (Verify)
        print(f"[Проверка] Verifying proof...")
        t3 = time.time()
        verified = ezkl.verify(proof_path_full, SETTINGS, VK, srs_path=SRS)
        print(f"verify: {time.time() - t3:.2f}s")
        print(f"[Результат] Verified: {verified}")
        print(f"Total: {time.time() - start_total:.2f}s")

        os.remove(input_path)
        os.remove(witness_path)
        # 7. Финализация
        result_payload = {
            "verified": verified,
            "proof_path": proof_filename,
            "input_features": features, 
            "normalized_input": input_values,
            "model_output": output_value,
            "action": action
        }
        result_json = json.dumps(result_payload)

        # Обновляем Redis
        r.hset(f"task:{task_id}", mapping={
            "status": "completed",
            "result": result_json,
            "proof_path": proof_filename
        })

        # Обновляем БД
        db.execute(
            text("UPDATE tasks SET status='completed', result=:result, proof_path=:proof_path, completed_at=:now WHERE id=:id"),
            {
                "result": result_json,
                "proof_path": proof_filename, 
                "now": datetime.utcnow(), 
                "id": task_id
            }
        )
        db.commit()
        print(f"[Успех] Task {task_id} completed successfully.")

    except Exception as e:
        print(f"[Критическая ошибка] Task {task_id} failed: {str(e)}")
        r.hset(f"task:{task_id}", "status", "failed")
        db.execute(text("UPDATE tasks SET status='failed' WHERE id=:id"), {"id": task_id})
        db.commit()
    finally:
        db.close()

async def main():
    print("========================================")
    print("  ZKML WORKER IS RUNNING")
    print(f"  Monitoring queue: task_queue")
    print("========================================")
    
    while True:
        # brpop блокирует выполнение, пока в очереди не появится задача
        result = r.brpop("task_queue", timeout=0)
        if result:
            _, task_id = result
            try:
                await process_task(task_id)
            except Exception as e:
                print(f"Unhandled error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWorker stopped by user.")