"""Create CSV table from the supplied JSON payload."""
import csv
from pathlib import Path

def run(payload,output_dir):
    rows=payload.get("rows",[])
    if not isinstance(rows,list) or len(rows)>1000 or not all(isinstance(row,dict) for row in rows):
        raise ValueError("Expected up to 1000 dictionary rows")
    headers=list(dict.fromkeys(key for row in rows for key in row.keys()))
    if not all(isinstance(key,str) for key in headers) or len(headers)>40:
        raise ValueError("Invalid CSV columns")
    target=Path(output_dir)/"report.csv"
    with target.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key:("'"+str(value) if str(value).startswith(("=","+","-","@")) else value)
                             for key,value in row.items()})
    return {"file":str(target),"rows":len(rows),"columns":headers}
