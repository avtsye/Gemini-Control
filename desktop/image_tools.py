"""Workspace-confined image conversion and metadata; Pillow is an optional dependency."""
from pathlib import Path
from workspace_data import safe_path

FORMATS={".png":"PNG",".jpg":"JPEG",".jpeg":"JPEG",".webp":"WEBP"}
MAX_INPUT=25_000_000

def image_info(workspace,name,approve):
    path=safe_path(workspace,name)
    if not path.is_file() or path.suffix.lower() not in FORMATS or path.stat().st_size>MAX_INPUT:
        raise ValueError("Unsupported image or file too large")
    if not approve("לבדוק מאפייני תמונה בתיקיית העבודה?"):
        return {"cancelled":True}
    from PIL import Image
    with Image.open(path) as im:
        return {"width":im.width,"height":im.height,"format":im.format,"mode":im.mode}

def convert_image(workspace,source,target,approve,max_width=1920,max_height=1920):
    src=safe_path(workspace,source)
    dest=safe_path(workspace,target)
    if (not src.is_file() or src.suffix.lower() not in FORMATS
        or dest.suffix.lower() not in FORMATS or src.stat().st_size>MAX_INPUT):
        raise ValueError("Unsupported image conversion")
    if dest.exists() or dest.is_symlink():raise FileExistsError("Output exists")
    if not isinstance(max_width,int) or not isinstance(max_height,int) or not 1<=max_width<=8192 or not 1<=max_height<=8192:
        raise ValueError("Invalid dimensions")
    if not approve("להמיר תמונה לקובץ "+str(target)+"?"):
        return {"cancelled":True}
    from PIL import Image,ImageOps
    dest.parent.mkdir(parents=True,exist_ok=True)
    with Image.open(src) as image:
        if image.width*image.height>60_000_000:raise ValueError("Image too large")
        resized=ImageOps.exif_transpose(image)
        resized.thumbnail((max_width,max_height))
        if dest.suffix.lower() in {".jpg",".jpeg"} and resized.mode not in {"RGB","L"}:
            background=Image.new("RGB",resized.size,"white")
            if resized.mode=="RGBA":background.paste(resized,mask=resized.getchannel("A"))
            else:background.paste(resized.convert("RGB"))
            resized=background
        with dest.open("xb") as out:
            resized.save(out,format=FORMATS[dest.suffix.lower()])
        return {"created_image":str(dest),"width":resized.width,"height":resized.height}
