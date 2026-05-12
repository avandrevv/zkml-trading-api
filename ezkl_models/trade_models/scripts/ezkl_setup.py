
import ezkl
import os
import json
import asyncio
from pathlib import Path
import time

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_DIR = BASE_DIR / "settings"
KEYS_DIR = BASE_DIR / "keys"
DATA_DIR = BASE_DIR / "data"

model_onnx = str(SETTINGS_DIR / "model.onnx")
model_compiled = str(SETTINGS_DIR / "model.ezkl")
settings_json = str(SETTINGS_DIR / "settings.json")
srs_path = str(SETTINGS_DIR / "kzg.srs")
pk_path = str(KEYS_DIR / "pk.key")
vk_path = str(KEYS_DIR / "vk.key")
input_json = str(DATA_DIR / "input_setup.json")

async def main():
    
    start_total = time.time()
    for f in [settings_json, model_compiled, pk_path, vk_path, srs_path]:
        if os.path.exists(f):
            os.remove(f)

    # Изменение: настройка видимости — вход и выход публичны, веса приватны
    run_args = ezkl.PyRunArgs()
    run_args.input_visibility = "public"
    run_args.output_visibility = "public"
    run_args.param_visibility = "private"

    # Передаём run_args в gen_settings
    ezkl.gen_settings(model_onnx, settings_json, py_run_args=run_args)

    with open(settings_json) as f:
        settings = json.load(f)
    settings["run_args"]["logrows"] = 17
    settings["run_args"]["ignore_range_check_inputs_outputs"] = True
    with open(settings_json, "w") as f:
        json.dump(settings, f)

    ezkl.compile_circuit(model_onnx, model_compiled, settings_json)

    ezkl.gen_srs(srs_path, 17)

    ezkl.setup(model_compiled, vk_path, pk_path, srs_path=srs_path)
    print(f"Total: {time.time() - start_total:.2f}s")

    print("Setup complete (all regenerated)")

if __name__ == "__main__":
    asyncio.run(main())
