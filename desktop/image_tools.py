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

def edit_image(workspace,source,target,approve,rotate=0,brightness=1.0,contrast=1.0,
               crop=None,grayscale=False):
    """Non-destructive basic image editing; always writes a new file."""
    src=safe_path(workspace,source)
    dst=safe_path(workspace,target)
    if not src.is_file() or src.suffix.lower() not in FORMATS or src.stat().st_size>MAX_INPUT:
        raise ValueError("Unsupported source image")
    if dst.suffix.lower() not in FORMATS or dst.exists() or dst.is_symlink():
        raise ValueError("Output must be a new supported image file")
    if not isinstance(rotate,(int,float)) or not -360<=rotate<=360:
        raise ValueError("Invalid rotation")
    if any(not isinstance(x,(int,float)) or not 0.1<=x<=4 for x in (brightness,contrast)):
        raise ValueError("Invalid enhancement factor")
    if crop is not None and (not isinstance(crop,list) or len(crop)!=4 or
                             not all(isinstance(x,int) and x>=0 for x in crop)):
        raise ValueError("Crop must be four nonnegative pixel coordinates")
    if not isinstance(grayscale,bool):
        raise ValueError("Invalid grayscale setting")
    if not approve("לערוך תמונה מקומית ולשמור עותק חדש בשם "+str(target)+"?"):
        return {"cancelled":True}
    from PIL import Image,ImageOps,ImageEnhance
    with Image.open(src) as loaded:
        if loaded.width*loaded.height>60_000_000:raise ValueError("Image too large")
        result=ImageOps.exif_transpose(loaded)
        if crop is not None:
            l,t,r,b=crop
            if not (l<r<=result.width and t<b<=result.height):
                raise ValueError("Crop lies outside image")
            result=result.crop((l,t,r,b))
        if rotate:
            result=result.rotate(rotate,expand=True)
        if brightness!=1:
            result=ImageEnhance.Brightness(result).enhance(brightness)
        if contrast!=1:
            result=ImageEnhance.Contrast(result).enhance(contrast)
        if grayscale:
            result=ImageOps.grayscale(result)
        if dst.suffix.lower() in {".jpeg",".jpg"} and result.mode not in {"RGB","L"}:
            canvas=Image.new("RGB",result.size,"white")
            if result.mode=="RGBA":
                canvas.paste(result,mask=result.getchannel("A"))
            else:
                canvas.paste(result.convert("RGB"))
            result=canvas
        dst.parent.mkdir(parents=True,exist_ok=True)
        with dst.open("xb") as stream:
            result.save(stream,format=FORMATS[dst.suffix.lower()])
        return {"edited_image":str(dst),"width":result.width,"height":result.height}
