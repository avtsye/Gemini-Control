"""Windows UI Automation: discover windows and controls without per-app adapters.
Windows-only; inspect first, then approve an action using a stable handle.
"""
def windows_snapshot(limit=30):
    from pywinauto import Desktop
    out=[]
    for window in Desktop(backend="uia").windows()[:limit]:
        try:
            if not window.is_visible():continue
            r=window.rectangle()
            out.append({"handle":window.handle,"title":window.window_text()[:160],
              "class":window.class_name(),"rect":[r.left,r.top,r.right,r.bottom]})
        except Exception:continue
    return out

def inspect_window(handle,limit=100):
    from pywinauto import Desktop
    handle=_handle(handle)
    target=Desktop(backend="uia").window(handle=handle)
    if not target.exists(timeout=1):raise ValueError("Window no longer exists")
    items=[]
    for item in target.descendants()[:limit]:
        try:
            info=item.element_info
            r=item.rectangle()
            items.append({"id":info.automation_id[:100] if info.automation_id else "",
                          "name":item.window_text()[:180],"type":info.control_type,
                          "rect":[r.left,r.top,r.right,r.bottom],"enabled":item.is_enabled()})
        except Exception:continue
    return {"handle":handle,"title":target.window_text()[:160],"controls":items}

def _handle(value):
    if type(value)!=int or value<=0:raise ValueError("Invalid window handle")
    return value

def activate_control(handle,automation_id,expected_name,approve):
    from pywinauto import Desktop
    handle=_handle(handle)
    if not isinstance(automation_id,str) or not 1<=len(automation_id)<=100:
        raise ValueError("Automation ID required")
    if not isinstance(expected_name,str) or len(expected_name)>180:
        raise ValueError("Expected label invalid")
    window=Desktop(backend="uia").window(handle=handle)
    if not window.exists(timeout=1):raise ValueError("Window no longer exists")
    matches=[]
    for child in window.descendants()[:500]:
        try:
            if child.element_info.automation_id==automation_id and child.window_text()==expected_name and child.is_enabled():
                matches.append(child)
        except Exception:continue
    if len(matches)!=1:raise ValueError("Control changed or is ambiguous; inspect again")
    control=matches[0]
    if control.element_info.control_type not in ("Button","CheckBox","RadioButton"):
        raise ValueError("Control type not approved")
    if not approve("להפעיל רכיב בממשק: "+window.window_text()[:100]+" / "+expected_name+"?"):
        return {"cancelled":True}
    control.invoke()
    return {"invoked":automation_id,"window":handle}
