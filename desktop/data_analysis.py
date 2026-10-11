"""Offline CSV profiling and SVG charts; no external web requests."""
import csv
import math
import statistics
from pathlib import Path
from xml.sax.saxutils import escape
from workspace_data import safe_path

MAX_FILE_BYTES=4_000_000
MAX_ROWS=10000
MAX_COLUMNS=48

def _load(workspace,source):
    path=safe_path(workspace,source)
    if not path.is_file() or path.suffix.lower()!=".csv" or path.stat().st_size>MAX_FILE_BYTES:
        raise ValueError("Expected a CSV file below 4 MB")
    with path.open(encoding="utf-8-sig",newline="") as handle:
        reader=csv.DictReader(handle)
        fields=reader.fieldnames or []
        if len(fields)>MAX_COLUMNS or not fields or len(set(fields))!=len(fields):
            raise ValueError("Invalid CSV headers")
        rows=[]
        for row in reader:
            if len(rows)>=MAX_ROWS:raise ValueError("CSV has too many rows")
            if None in row:raise ValueError("Malformed CSV row")
            rows.append(row)
    return fields,rows

def analyze_csv(workspace,source,approve):
    if not approve("לנתח את העמודות והנתונים בקובץ CSV מקומי?"):
        return {"cancelled":True}
    fields,rows=_load(workspace,source)
    columns=[]
    for field in fields:
        values=[(row.get(field) or "").strip() for row in rows]
        present=[v for v in values if v]
        numbers=[]
        for value in present:
            try:
                num=float(value.replace(",",""))
                if math.isfinite(num):numbers.append(num)
            except ValueError:pass
        stat={"name":field,"filled":len(present),"empty":len(values)-len(present),
              "distinct":len(set(present))}
        if present and len(numbers)==len(present):
            stat.update({"type":"numeric","min":min(numbers),"max":max(numbers),
                         "mean":round(statistics.fmean(numbers),4),
                         "sum":round(math.fsum(numbers),4)})
        else:
            stat.update({"type":"text","examples":list(dict.fromkeys(present))[:5]})
        columns.append(stat)
    return {"rows":len(rows),"columns":columns,"source":str(source)}

def chart_csv(workspace,source,target,label_column,value_column,approve):
    fields,rows=_load(workspace,source)
    dst=safe_path(workspace,target)
    if dst.suffix.lower()!=".svg" or dst.exists() or dst.is_symlink():
        raise ValueError("Expected a new SVG output")
    if label_column not in fields or value_column not in fields or label_column==value_column:
        raise ValueError("Choose distinct existing label and value columns")
    samples=[]
    for row in rows[:24]:
        try:
            number=float((row[value_column] or "").replace(",",""))
            if not math.isfinite(number) or number<0:continue
            samples.append((str(row[label_column])[:48],number))
        except (ValueError,TypeError):continue
    if not samples or max(v for _,v in samples)<=0:
        raise ValueError("At least one positive numeric value is required")
    if not approve("ליצור תרשים SVG מתוך הנתונים בקובץ CSV מקומי?"):
        return {"cancelled":True}
    n=len(samples);peak=max(v for _,v in samples)
    height=110+45*n
    parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 940 '+str(height)+'">',
           '<rect width="940" height="'+str(height)+'" fill="#ffffff"/>',
           '<text x="900" y="35" font-family="Arial" font-size="22" text-anchor="end">'+
           escape(value_column)+'</text>']
    for index,(label,value) in enumerate(samples):
        y=60+index*45
        width=round(value/peak*610,2)
        parts.append('<text x="910" y="'+str(y+23)+'" font-size="15" font-family="Arial" text-anchor="end">'+escape(label)+'</text>')
        parts.append('<rect x="170" y="'+str(y)+'" width="'+str(width)+'" height="30" rx="5" fill="#357ebd"/>')
        parts.append('<text x="165" y="'+str(y+22)+'" font-family="Arial" font-size="13" text-anchor="end">'+str(round(value,2))+'</text>')
    parts.append("</svg>")
    dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open("x",encoding="utf-8") as out:out.write("\n".join(parts))
    return {"created_chart":str(dst),"bars":n}
