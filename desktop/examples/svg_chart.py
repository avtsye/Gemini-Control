"""Render a simple SVG bar chart without external libraries."""
from pathlib import Path
from html import escape
import math

def run(payload,output_dir):
    values=payload.get("values",[])
    if not isinstance(values,list) or not 1<=len(values)<=24:
        raise ValueError("Use 1-24 numeric values")
    if not all(isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x) and x>=0 for x in values):
        raise ValueError("All values must be finite nonnegative numbers")
    labels=payload.get("labels",[str(i+1) for i in range(len(values))])
    if not isinstance(labels,list) or len(labels)!=len(values):
        raise ValueError("Labels must match values")
    maximum=max(values) or 1
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 480">','<rect width="900" height="480" fill="white"/>']
    step=800/len(values)
    for i,(label,value) in enumerate(zip(labels,values)):
        height=350*value/maximum
        x=60+i*step
        parts.append(f'<rect x="{x:.2f}" y="{390-height:.2f}" width="{step*.65:.2f}" height="{height:.2f}" fill="#4279b7"/>')
        parts.append(f'<text x="{x:.2f}" y="425" font-family="Arial" font-size="12">{escape(str(label)[:16])}</text>')
    parts.append('</svg>')
    target=Path(output_dir)/"chart.svg"
    target.write_text("".join(parts),encoding="utf-8")
    return {"file":str(target),"bars":len(values)}
