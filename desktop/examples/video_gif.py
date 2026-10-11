"""Example capability: animated GIF video clip, using Pillow when installed."""
import math
from pathlib import Path

def run(payload,output_dir):
    from PIL import Image, ImageDraw
    fps=int(payload.get("fps",10))
    duration=float(payload.get("seconds",3))
    if not 2<=fps<=20 or not 0.5<=duration<=10:
        raise ValueError("Invalid fps/duration")
    width,height=480,270
    count=int(fps*duration)
    images=[]
    for i in range(count):
        frame=Image.new("RGB",(width,height),(24,29,49))
        draw=ImageDraw.Draw(frame)
        x=int(40+(width-80)*(i/max(1,count-1)))
        y=int(height/2+55*math.sin(i*.22))
        draw.ellipse((x-26,y-26,x+26,y+26),fill=(70,195,220))
        draw.text((20,20),"AI Control animation",fill=(235,235,245))
        images.append(frame)
    output=Path(output_dir)/"animation.gif"
    images[0].save(output,format="GIF",save_all=True,append_images=images[1:],
                   duration=int(1000/fps),loop=0,optimize=True)
    return {"created_file":str(output),"frames":count,"format":"GIF",
            "note":"Animated GIF is not an MP4. An MP4 encoder must be installed separately."}
