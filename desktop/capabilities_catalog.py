"""Truthful catalog for the 35 requested capability families.

Status is intentionally conservative: a partial adapter is not a completed feature.
The runtime only advertises executable tool names from this list and from approved plugins.
"""
CAPABILITIES = [
 ("windows_ui","שליטה בחלונות ותפריטים","partial",["windows_snapshot","inspect_window","activate_control","set_control_text"]),
 ("screen_vision","ניתוח מסך","partial",["observe_screen"]),
 ("multi_step","משימות מרובות שלבים","partial",["list_available_tools"]),
 ("software_management","התקנה והסרת תוכנות","missing",[]),
 ("powershell","PowerShell","missing",[]),
 ("office","Word Excel PowerPoint PDF","partial",["create_word","create_spreadsheet","create_presentation","create_pdf"]),
 ("hebrew_ocr","OCR עברי","partial",["ocr_engines","ocr_image","ocr_pdf"]),
 ("organize_files","איתור וארגון קבצים","partial",["workspace_files","search_workspace","compare_files"]),
 ("archives","ZIP ו-7z","partial",["create_zip","extract_zip"]),
 ("convert_documents","המרות קבצים","partial",["convert_data"]),
 ("transcription","תמלול עברי","partial",["speech_status","transcribe_local"]),
 ("speech","טקסט לדיבור","partial",["speech_status","text_to_speech"]),
 ("audio_edit","עריכת שמע","partial",["media_engines","convert_media"]),
 ("image_edit","עיבוד תמונות וגרפיקה","partial",["image_info","convert_image","edit_image","draw_paint"]),
 ("video_edit","וידאו וכתוביות","partial",["media_engines","probe_media","convert_media"]),
 ("browser_control","שליטה בדפדפן","partial",["open_browser","click","type_text"]),
 ("web_research","חיפוש וסיכום אתרים","partial",["fetch_page","research_pages"]),
 ("downloads","הורדות","partial",["download_file"]),
 ("browser_forms","מילוי טפסים","partial",["inspect_window","activate_control","set_control_text"]),
 ("external_api","API חיצוני","partial",["fetch_page"]),
 ("project_generation","יצירת פרויקטים","partial",["project_file"]),
 ("code_repair","תיקון קוד","partial",["project_file","inspect_python_project"]),
 ("test_build","בדיקות וקימפול","partial",["inspect_python_project","run_python_tests"]),
 ("github","ניהול GitHub","partial",["github_engine","github_issues","github_pull_requests"]),
 ("exe_builder","יצירת EXE","missing",[]),
 ("long_memory","זיכרון ארוך טווח","partial",[]),
 ("scheduling","תזמון","missing",[]),
 ("task_management","ניהול משימות","partial",[]),
 ("subagents","סוכני משנה","missing",[]),
 ("semantic_search","חיפוש סמנטי","partial",["index_workspace","search_knowledge","ranked_workspace_search"]),
 ("generate_python","יצירת הרחבות Python","partial",[]),
 ("deps_environment","ספריות וסביבה נפרדת","partial",[]),
 ("self_test_repair","בדיקה ותיקון של הרחבות","partial",[]),
 ("dynamic_registry","כלים דינמיים","partial",["list_available_tools"]),
 ("plugin_rollback","גרסאות ושחזור הרחבות","partial",[])
]

def catalog(native_tools):
    allowed=set(native_tools)
    return [{"id":key,"name":name,
             "status":status if all(tool in allowed for tool in tools) else "missing",
             "tools": [tool for tool in tools if tool in allowed]}
            for key,name,status,tools in CAPABILITIES]
