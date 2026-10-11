"""Format JSON payload into a readable UTF-8 file."""
import json
from pathlib import Path

def run(payload,output_dir):
    value=payload.get("data",payload)
    target=Path(output_dir)/"formatted.json"
    target.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2),encoding="utf-8")
    return {"file":str(target),"characters":target.stat().st_size}
