"""Discover the actual Windows software inventory and basic machine status."""
import platform

def installed_applications(limit=200):
    import winreg
    hives=(winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE)
    locations=(r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
               r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall")
    result={}
    for hive in hives:
        for location in locations:
            try:parent=winreg.OpenKey(hive,location)
            except OSError:continue
            with parent:
                index=0
                while index<1500:
                    try:name=winreg.EnumKey(parent,index)
                    except OSError:break
                    index+=1
                    try:
                        with winreg.OpenKey(parent,name) as item:
                            display=winreg.QueryValueEx(item,"DisplayName")[0]
                            if isinstance(display,str) and display.strip():
                                result[display.strip()[:120]]={"name":display.strip()[:120]}
                    except (OSError,ValueError):continue
    return {"installed_apps":list(result.values())[:limit],"truncated":len(result)>limit}

def system_status():
    try:
        import psutil
    except ImportError:
        return {"system":platform.system(),"release":platform.release(),
                "error":"psutil is missing from this installation",
                "action":"Install desktop/requirements.txt and rebuild the EXE"}
    memory=psutil.virtual_memory()
    return {"system":platform.system(),"release":platform.release(),
            "cpu_percent":psutil.cpu_percent(interval=0.1),
            "memory_available_gb":round(memory.available/1024**3,2),
            "memory_total_gb":round(memory.total/1024**3,2),
            "process_count":len(psutil.pids())}
