"""Render a limited local SVG illustration as PNG and open it in Paint."""
from datetime import datetime
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ALLOWED_TAGS={"svg","g","path","rect","circle","ellipse","line","polygon","polyline","defs","linearGradient","radialGradient","stop"}
ALLOWED_ATTRS={"xmlns","width","height","viewBox","fill","stroke","stroke-width","stroke-linecap","stroke-linejoin",
"opacity","fill-opacity","stroke-opacity","d","x","y","x1","y1","x2","y2","cx","cy","r","rx","ry",
"points","transform","id","offset","stop-color","stop-opacity","gradientUnits","gradientTransform","spreadMethod",
"stroke-dasharray","stroke-dashoffset","fill-rule","clip-rule"}
SVG_NS="{http://www.w3.org/2000/svg}"

def safe_svg(svg):
    if not isinstance(svg,str) or not 20 <= len(svg) <= 60000:
        raise ValueError("SVG must be between 20 and 60000 characters")
    if re.search(r"<!DOCTYPE|<!ENTITY|<\?xml-stylesheet|url\s*\(\s*(?!\s*#)",svg,re.I):
        raise ValueError("External resources and XML entities are forbidden")
    try:
        root=ET.fromstring(svg)
    except ET.ParseError as error:
        raise ValueError("Invalid SVG XML") from error
    if root.tag not in ("svg",SVG_NS+"svg"):
        raise ValueError("Root must be svg")
    nodes=list(root.iter())
    if len(nodes)>350:
        raise ValueError("Too many SVG elements")
    for node in nodes:
        tag=node.tag.rsplit("}",1)[-1]
        if tag not in ALLOWED_TAGS:
            raise ValueError("Unsupported SVG element: "+tag)
        for key,value in node.attrib.items():
            attr=key.rsplit("}",1)[-1]
            if key.startswith("{") and not key.startswith(SVG_NS):
                raise ValueError("Namespaced attributes are blocked")
            if attr not in ALLOWED_ATTRS or len(value)>15000:
                raise ValueError("Unsupported SVG attribute: "+attr)
            if re.search(r"https?://|file:|data:|javascript:|@import|expression\s*\(",value,re.I):
                raise ValueError("External SVG content is forbidden")
            if "url(" in value.lower() and not re.fullmatch(r'url\(\s*["\']?#[A-Za-z0-9_-]+["\']?\s*\)',value.strip()):
                raise ValueError("Only local gradient references are supported")
    return svg

def draw_in_paint(svg,workspace,approval):
    svg=safe_svg(svg)
    if not approval("ליצור ציור באמצעות AI, לשמור קובץ PNG בתיקיית העבודה ולפתוח אותו בצייר?"):
        return {"cancelled":True}
    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QImage,QPainter
    from PySide6.QtSvg import QSvgRenderer
    renderer=QSvgRenderer(QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        raise ValueError("Unable to render SVG")
    width,height=1000,700
    image=QImage(width,height,QImage.Format.Format_ARGB32)
    image.fill(0xFFFFFFFF)
    painter=QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    folder=Path(workspace)
    folder.mkdir(parents=True,exist_ok=True)
    destination=folder/("drawing-"+datetime.now().strftime("%Y%m%d-%H%M%S-%f")+".png")
    if not image.save(str(destination),"PNG"):
        raise IOError("Failed to save PNG")
    subprocess.Popen(["mspaint.exe",str(destination)],shell=False)
    return {"created_png":str(destination),"opened_in":"paint","size":[width,height]}
