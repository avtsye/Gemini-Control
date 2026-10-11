"""Standalone approved local-model worker, run only by Gemini-Control's model_runtime.

The worker uses local model directories and never downloads weights.
It runs in a separate Python environment, not as an OS security sandbox.
"""
import json
import os
import sys
from pathlib import Path

os.environ["HF_HUB_OFFLINE"]="1"
os.environ["TRANSFORMERS_OFFLINE"]="1"
os.environ["HF_DATASETS_OFFLINE"]="1"

def execute(payload):
    if not isinstance(payload,dict):raise ValueError("Invalid worker request")
    operation=payload.get("operation")
    model=Path(payload.get("model",""))
    if not model.is_dir():raise ValueError("Local model directory missing")
    if operation=="embed":
        from sentence_transformers import SentenceTransformer
        texts=payload.get("texts")
        if (not isinstance(texts,list) or not 1<=len(texts)<=250 or
            any(not isinstance(text,str) or len(text)>2200 for text in texts)):
            raise ValueError("Invalid embedding inputs")
        encoder=SentenceTransformer(str(model),local_files_only=True)
        embeddings=encoder.encode(texts,normalize_embeddings=True)
        result=[[float(v) for v in vector] for vector in embeddings]
        if any(len(vector)>2048 for vector in result):
            raise ValueError("Embedding dimension too large")
        return {"vectors":result}
    if operation=="image":
        from diffusers import DiffusionPipeline
        prompt=payload.get("prompt")
        target=Path(payload.get("target",""))
        steps=payload.get("steps",20)
        if (not isinstance(prompt,str) or not 3<=len(prompt)<=1500 or
            not isinstance(steps,int) or not 1<=steps<=40 or
            target.suffix.lower()!=".png" or target.exists()):
            raise ValueError("Invalid image job")
        pipeline=DiffusionPipeline.from_pretrained(str(model),local_files_only=True)
        generated=pipeline(prompt,num_inference_steps=steps)
        if not generated.images:raise RuntimeError("No image returned")
        image=generated.images[0]
        if image.width*image.height>16_000_000:raise ValueError("Image too large")
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open("xb") as file:image.save(file,format="PNG")
        return {"created_image":str(target),"width":image.width,"height":image.height}
    if operation=="transcribe":
        from faster_whisper import WhisperModel
        source=Path(payload.get("source",""))
        lang=payload.get("language","he")
        if not source.is_file() or source.stat().st_size>100_000_000 or lang not in {"he","en"}:
            raise ValueError("Invalid audio request")
        engine=WhisperModel(str(model),device="cpu",compute_type="int8",local_files_only=True)
        segments,_=engine.transcribe(str(source),language=lang,beam_size=3)
        text="\n".join(segment.text.strip() for segment in segments)
        return {"transcript":text[:250000]}
    raise ValueError("Unknown worker operation")

if __name__=="__main__":
    try:
        raw=sys.stdin.buffer.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError("Worker input too large")
        result=execute(json.loads(raw.decode("utf-8")))
        sys.stdout.write(json.dumps(result,ensure_ascii=True,default=str))
    except Exception as exc:
        sys.stdout.write(json.dumps({"error":type(exc).__name__+": "+str(exc)[:320]},ensure_ascii=True))
        sys.exit(1)
