"""Restricted local Windows tools for the ChatGPT desktop agent."""
from pathlib import Path

class DesktopAgent:
    def __init__(self, api_key, workspace=None, approval=None):
        self.api_key = api_key.strip()
        self.workspace = Path(workspace or Path.home() / "Documents" / "GeminiControl-Workspace")
        self.approval = approval or (lambda description: False)
        self.history = []
        self.enabled = True

    def _file(self, name):
        if not isinstance(name, str) or not name or len(name) > 100 or Path(name).name != name or name.startswith("."):
            raise ValueError("Invalid filename")
        if Path(name).suffix.lower() not in {".txt", ".md", ".json", ".csv", ".html", ".css", ".js", ".py"}:
            raise ValueError("Unsupported file extension")
        self.workspace.mkdir(parents=True, exist_ok=True)
        path = self.workspace / name
        if path.is_symlink():
            raise ValueError("Symlinks are not allowed")
        return path

    def execute(self, tool, arguments):
        if not self.enabled:
            raise PermissionError("Agent is paused")
        args = arguments if isinstance(arguments, dict) else {}
        if tool=="search_knowledge":
            from knowledge_search import search_knowledge
            return search_knowledge(self.workspace,args.get("query"),args.get("folder"),
                                    self.approval,args.get("limit",8))
        if tool in {"installed_apps","system_status"}:
            if not self.approval("לאסוף מידע על "+("התוכנות המותקנות" if tool=="installed_apps" else "מצב משאבי המחשב")+" ולשלוח אותו למודל?"):
                return {"cancelled":True}
            from computer_inventory import installed_applications,system_status
            return installed_applications() if tool=="installed_apps" else system_status()
        if tool in {"compare_files","create_zip","extract_zip"}:
            from workspace_archives import compare_files, create_zip, extract_zip
            if tool == "compare_files":
                return compare_files(self.workspace,args.get("left"),args.get("right"),self.approval)
            if tool == "create_zip":
                return create_zip(self.workspace,args.get("sources"),args.get("target"),self.approval)
            return extract_zip(self.workspace,args.get("archive"),args.get("destination"),self.approval)
        if tool=="diagnose_system":
            if not self.approval("לאסוף אבחון טכני של התקנת התוכנה ולשתף אותו עם המודל?"):
                return {"cancelled":True}
            from diagnostics import inspect_environment
            from capability_workshop import CapabilityWorkshop
            from conversation_store import location
            return inspect_environment(CapabilityWorkshop(),location())
        if tool in {"github_engine","github_issues","github_pull_requests"}:
            from github_cli_tools import github_engine,github_issues,github_pull_requests
            if tool=="github_engine":return github_engine()
            if tool=="github_issues":return github_issues(args.get("repository"),self.approval)
            return github_pull_requests(args.get("repository"),self.approval)
        if tool in {"git_engine","git_status","git_diff","git_commit"}:
            from git_tools import git_engine,git_status,git_diff,git_commit
            if tool=="git_engine":return git_engine()
            project=args.get("project")
            if tool=="git_status":return git_status(self.workspace,project,self.approval)
            if tool=="git_diff":return git_diff(self.workspace,project,self.approval)
            return git_commit(self.workspace,project,args.get("paths"),args.get("message"),self.approval)
        if tool=="schedule_reminder":
            from reminder_store import ReminderStore
            title=args.get("title")
            delay=args.get("delay_minutes")
            repeat=args.get("repeat_minutes",0)
            if not self.approval("ליצור תזכורת מקומית חדשה שתוצג כשהאפליקציה פתוחה?"):
                return {"cancelled":True}
            return ReminderStore().add(title,delay,repeat)
        if tool in {"index_workspace","search_knowledge"}:
            from knowledge_tools import index_workspace,search_knowledge
            if tool=="index_workspace":return index_workspace(self.workspace,self.approval)
            return search_knowledge(self.workspace,args.get("query"),self.approval)
        if tool in {"inspect_python_project","run_python_tests"}:
            from project_quality import inspect_python_project,run_python_tests
            if tool=="inspect_python_project":
                return inspect_python_project(self.workspace,args.get("project"),self.approval)
            return run_python_tests(self.workspace,args.get("project"),self.approval)
        if tool=="download_file":
            from internet_tools import download_file
            return download_file(self.workspace,args.get("url"),args.get("destination"),self.approval)
        if tool=="fetch_page":
            from internet_tools import fetch_page
            return fetch_page(args.get("url"),self.approval)
        if tool in {"move_workspace_file","sevenzip_status"}:
            from file_organizer import move_workspace_file,sevenzip_status
            if tool=="sevenzip_status":return sevenzip_status()
            return move_workspace_file(self.workspace,args.get("source"),
                                       args.get("destination"),self.approval)
        if tool in {"speech_status","text_to_speech","transcribe_local"}:
            from speech_tools import speech_status,text_to_speech,transcribe_local
            if tool=="speech_status":return speech_status()
            if tool=="text_to_speech":
                return text_to_speech(self.workspace,args.get("text"),args.get("target"),
                                      self.approval,args.get("rate",170))
            return transcribe_local(self.workspace,args.get("source"),args.get("model_directory"),
                                    args.get("target"),self.approval,args.get("language","he"))
        if tool in {"ocr_engines","ocr_image","ocr_pdf"}:
            from ocr_tools import ocr_engines,ocr_image,ocr_pdf
            if tool=="ocr_engines":return ocr_engines()
            if tool=="ocr_pdf":
                return ocr_pdf(self.workspace,args.get("source"),args.get("target"),self.approval,
                               args.get("language","heb+eng"),args.get("max_pages",12))
            return ocr_image(self.workspace,args.get("source"),args.get("target"),
                             self.approval,args.get("language","heb+eng"))
        if tool in {"media_engines","probe_media","convert_media"}:
            from media_tools import engines,probe_media,convert_media
            if tool=="media_engines":return engines()
            if tool=="probe_media":return probe_media(self.workspace,args.get("name"),self.approval)
            return convert_media(self.workspace,args.get("source"),args.get("target"),self.approval)
        if tool in {"image_info","convert_image"}:
            from image_tools import image_info,convert_image
            if tool=="image_info":
                return image_info(self.workspace,args.get("name"),self.approval)
            return convert_image(self.workspace,args.get("source"),args.get("target"),self.approval,
                                 args.get("max_width",1920),args.get("max_height",1920))
        if tool in {"search_workspace","convert_data"}:
            from workspace_data import search_workspace,convert_data
            if tool=="search_workspace":
                return search_workspace(self.workspace,args.get("query"),self.approval)
            return convert_data(self.workspace,args.get("source"),args.get("target"),self.approval)
        if tool in {"create_spreadsheet","create_presentation"}:
            from office_tools import create_spreadsheet,create_presentation
            if tool=="create_spreadsheet":
                return create_spreadsheet(self.workspace,args.get("name"),args.get("sheets"),self.approval)
            return create_presentation(self.workspace,args.get("name"),args.get("slides"),self.approval)
        if tool=="create_pdf":
            from pdf_tool import create_pdf
            return create_pdf(args.get("name"),args.get("content"),self.workspace,
                              self.approval,args.get("direction","rtl"))
        if tool=="windows_snapshot":
            if not self.approval("לאסוף כותרות חלונות פתוחים ולשלוח אותן למודל לצורך הבנת מצב המחשב?"):
                return {"cancelled":True}
            from windows_state import windows_snapshot
            return {"windows":windows_snapshot()}
        if tool=="inspect_window":
            if not self.approval("לקרוא רכיבי ממשק של חלון ולשלוח את שמותיהם למודל? מידע גלוי בחלון עשוי להיות אישי."):
                return {"cancelled":True}
            from windows_state import inspect_window
            return inspect_window(args.get("handle"))
        if tool=="set_control_text":
            from windows_state import set_control_text
            return set_control_text(args.get("handle"),args.get("automation_id"),args.get("expected_name"),args.get("text"),self.approval)
        if tool=="activate_control":
            from windows_state import activate_control
            return activate_control(args.get("handle"),args.get("automation_id"),args.get("expected_name"),self.approval)
        if tool in {"screenshot","click","type_text","hotkey","open_browser","create_word","project_file","email_draft","workspace_files","inspect_workspace_file","open_workspace_file"}:
            from computer_tools import computer_action
            return computer_action(tool,args,self.workspace,self.approval)
        if tool == "draw_paint":
            from drawing_tool import draw_in_paint
            return draw_in_paint(args.get("svg"), self.workspace, self.approval)
        if tool == "list_files":
            self.workspace.mkdir(parents=True, exist_ok=True)
            return {"files": [p.name for p in self.workspace.iterdir() if p.is_file() and not p.is_symlink()][:100]}
        if tool == "read_file":
            path = self._file(args.get("name"))
            if path.stat().st_size > 50000:
                raise ValueError("File exceeds read limit")
            if not self.approval("קריאת הקובץ " + path.name + " ושליחת התוכן למודל ChatGPT"):
                return {"cancelled": True}
            return {"name": path.name, "content": path.read_text(encoding="utf-8")}
        if tool == "write_file":
            path = self._file(args.get("name"))
            content = args.get("content")
            if not isinstance(content, str) or len(content) > 50000:
                raise ValueError("Invalid file content")
            if not self.approval("יצירה או החלפה של " + path.name + " (" + str(len(content)) + " תווים)"):
                return {"cancelled": True}
            if path.exists():
                import shutil
                from datetime import datetime
                backup = self.workspace / ".backups"
                backup.mkdir(exist_ok=True)
                shutil.copy2(path, backup / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-" + path.name))
            path.write_text(content, encoding="utf-8")
            return {"saved": path.name}
        if tool == "open_app":
            import subprocess
            apps = {"notepad": "notepad.exe", "calculator": "calc.exe", "explorer": "explorer.exe", "paint": "mspaint.exe"}
            app = args.get("app")
            if app not in apps:
                raise ValueError("Application is not approved")
            if not self.approval("פתיחת " + str(app)):
                return {"cancelled": True}
            subprocess.Popen([apps[app]], shell=False)
            return {"launched": app}
        raise ValueError("Unsupported tool: " + str(tool))

