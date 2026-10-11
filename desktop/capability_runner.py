"""Separate-process runner for user-reviewed Python capabilities; NOT a security sandbox."""
import importlib.util,json,sys,traceback
from pathlib import Path

def main():
    path=Path(sys.argv[1]).resolve()
    output=Path(sys.argv[2]).resolve()
    payload=json.loads(sys.stdin.read())
    spec=importlib.util.spec_from_file_location("reviewed_capability",str(path))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result=module.run(payload,str(output))
    print(json.dumps({"result":result},ensure_ascii=False,default=str))

if __name__=="__main__":
    try:main()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
