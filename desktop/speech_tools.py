"""Optional local speech capabilities. Never downloads models automatically."""
from pathlib import Path
from workspace_data import safe_path

def speech_status():
    status={"tts_available":False,"transcription_available":False}
    try:
        import pyttsx3
        status["tts_available"]=True
    except ImportError:pass
    try:
        import faster_whisper
        status["transcription_available"]=True
    except ImportError:pass
    return status

def text_to_speech(workspace,text,target,approve,rate=170):
    if not isinstance(text,str) or not 1<=len(text)<=12000:raise ValueError("Invalid text")
    if not isinstance(rate,int) or not 80<=rate<=250:raise ValueError("Invalid speech rate")
    dst=safe_path(workspace,target)
    if dst.suffix.lower()!=".wav" or dst.exists():raise ValueError("Expected a new WAV file")
    try:import pyttsx3
    except ImportError:return {"unavailable":"pyttsx3 engine is not installed"}
    if not approve("ליצור קובץ קריינות באמצעות קול מקומי במחשב?"):
        return {"cancelled":True}
    engine=pyttsx3.init()
    try:
        engine.setProperty("rate",rate)
        dst.parent.mkdir(parents=True,exist_ok=True)
        engine.save_to_file(text,str(dst))
        engine.runAndWait()
    finally:engine.stop()
    if not dst.is_file() or dst.stat().st_size==0:
        return {"error":"Speech engine did not produce a WAV file; check installed voices and driver"}
    return {"created_audio":str(dst),"bytes":dst.stat().st_size}

def transcribe_local(workspace,source,model_directory,target,approve,language="he"):
    src=safe_path(workspace,source)
    dst=safe_path(workspace,target)
    model=safe_path(workspace,model_directory)
    if not src.is_file() or src.suffix.lower() not in {".wav",".mp3",".m4a",".flac",".ogg"}:
        raise ValueError("Unsupported local audio file")
    if not model.is_dir() or dst.suffix.lower()!=".txt" or dst.exists():
        raise ValueError("Expected a local model directory and new .txt")
    if src.stat().st_size>100_000_000:raise ValueError("Audio too large")
    if language not in {"he","en"}:raise ValueError("Language unsupported")
    try:from faster_whisper import WhisperModel
    except ImportError:return {"unavailable":"faster-whisper not installed; use a local supported model"}
    if not approve("לתמלל קובץ שמע במחשב באמצעות מודל מקומי?"):
        return {"cancelled":True}
    engine=WhisperModel(str(model),device="cpu",compute_type="int8",local_files_only=True)
    segments,_=engine.transcribe(str(src),language=language,beam_size=3)
    transcript="\n".join(seg.text.strip() for seg in segments)
    dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open("x",encoding="utf-8") as file:file.write(transcript)
    return {"created_transcript":str(dst),"characters":len(transcript)}
