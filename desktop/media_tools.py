"""Conservative local media operations using an already-installed FFmpeg.

No downloads, system installation, arbitrary ffmpeg arguments or shell execution.
Only files within the user's workspace may be processed.
"""
import os
import shutil
import subprocess
import json
from pathlib import Path
from workspace_data import safe_path

INPUT_EXT={".mp3",".wav",".m4a",".ogg",".flac",".mp4",".mov",".mkv",".webm"}
OUTPUT_EXT={".mp3",".wav",".ogg",".flac",".mp4",".webm"}
MAX_MEDIA=750*1024*1024

def engines():
    return {"ffmpeg":bool(shutil.which("ffmpeg")),"ffprobe":bool(shutil.which("ffprobe"))}

def probe_media(workspace,name,approve):
    src=safe_path(workspace,name)
    if not src.is_file() or src.suffix.lower() not in INPUT_EXT or src.stat().st_size>MAX_MEDIA:
        raise ValueError("Unsupported media or file too large")
    executable=shutil.which("ffprobe")
    if not executable:return {"unavailable":"FFprobe is not installed"}
    if not approve("לקרוא מאפייני מדיה מתוך קובץ מקומי?"):
        return {"cancelled":True}
    try:
        result=subprocess.run([executable,"-v","error","-show_entries",
            "format=duration,size:stream=codec_name,codec_type,width,height",
            "-of","json",str(src)],capture_output=True,text=True,timeout=20,shell=False)
    except subprocess.TimeoutExpired:
        return {"error":"Media probing timed out"}
    if result.returncode:
        return {"error":"Media probing failed","details":result.stderr[-500:]}
    data=json.loads(result.stdout)
    return {"format":data.get("format",{}),"streams":data.get("streams",[])[:10]}

def convert_media(workspace,source,target,approve):
    src=safe_path(workspace,source)
    dst=safe_path(workspace,target)
    if not src.is_file() or src.suffix.lower() not in INPUT_EXT or dst.suffix.lower() not in OUTPUT_EXT:
        raise ValueError("Unsupported conversion")
    if src.stat().st_size>MAX_MEDIA:raise ValueError("Media too large")
    if dst.exists() or dst.is_symlink():raise FileExistsError("Output exists")
    executable=shutil.which("ffmpeg")
    if not executable:return {"unavailable":"FFmpeg is not installed"}
    if not approve("להמיר את קובץ המדיה "+str(source)+" לפורמט "+dst.suffix+"?"):
        return {"cancelled":True}
    dst.parent.mkdir(parents=True,exist_ok=True)
    # Prevent partial user-visible output; FFmpeg explicitly selects output format.
    temporary=dst.with_name(dst.stem+".partial"+dst.suffix)
    if temporary.exists():raise FileExistsError("Partial output exists")
    cmd=[executable,"-nostdin","-hide_banner","-loglevel","error","-y","-i",str(src)]
    if dst.suffix.lower() in {".wav",".mp3",".ogg",".flac"}:
        cmd+=["-vn"]
    cmd+=["-t","1800",str(temporary)]
    try:
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=180,shell=False)
        if result.returncode:
            return {"error":"Conversion failed","details":result.stderr[-700:]}
        if not temporary.is_file():return {"error":"Output was not created"}
        os.replace(temporary,dst)
        return {"converted_media":str(dst),"bytes":dst.stat().st_size}
    except subprocess.TimeoutExpired:
        return {"error":"Conversion timed out"}
    finally:
        temporary.unlink(missing_ok=True)
