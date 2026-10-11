# AI Control Desktop

תוכנת Windows אחת, המשתמשת בחיבור לחשבון ChatGPT לצ'אט ולביצוע פעולות מחשב מוגבלות עם אישור המשתמש.

## מה כל קובץ עושה?

| קובץ | תפקיד |
| --- | --- |
| `desktop/app_openai.py` | **התוכנה הראשית**: ממשק משתמש בעברית, התחברות ושיחה |
| `desktop/openai_signin.py` | כניסה לחשבון ChatGPT דרך הדפדפן (OAuth) |
| `desktop/openai_agent.py` | ניהול בקשות הסוכן, עד חמישה צעדים לבקשה |
| `desktop/agent_core.py` | כלי מחשב מאושרים, הגבלת גישה וגיבוי קבצים |
| `desktop/drawing_tool.py` | יצירת תמונת PNG מהוראות ציור ופתיחתה ב־Paint |\n| `desktop/requirements.txt` | ספריות Python הדרושות להפעלה |
| `desktop/tests/` | בדיקות מקומיות |
| `.github/workflows/build-desktop.yml` | יצירת EXE ב־Actions **רק בהפעלה ידנית** |

כל קובצי Gemini, תוסף Chrome וגשר Windows הישן הוסרו מענף `main`. ניתן לשחזרם מהיסטוריית Git.

## הרצה באמצעות Python (ללא קימפול)

במסוף, בתוך תיקיית המאגר:

```bash
python -m pip install -r desktop/requirements.txt
python desktop/app_openai.py
```

בחלון התוכנה בחר `Continue with ChatGPT`, השלם את ההרשאה בדפדפן, ואז בחר מודל. כאשר אפשרות **סוכן מחשב** מסומנת, ניתן לבקש פעולות כגון ציור עקרב בצייר, פתיחת מחשבון או יצירת קובץ טקסט. קריאה ושינוי קבצים ופתיחת תוכנות דורשים אישור.

תיקיית הקבצים המוגבלת: `Documents/GeminiControl-Workspace`. תוכנות מותרות: Notepad, Calculator, Explorer, Paint.

## בדיקות מקומיות

```bash
python desktop/tests/test_agent.py -v
python desktop/tests/test_openai_agent.py -v
python desktop/tests/test_openai_signin.py -v\npython desktop/tests/test_drawing.py -v
```

## בניית EXE — רק אם צריך

```bash
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name AIControlDesktop --paths desktop desktop/app_openai.py
```

הקובץ יתקבל ב־`dist/AIControlDesktop.exe`. אין ריצות אוטומטיות ב־GitHub: ניתן להפעיל ידנית את תהליך הבנייה מתוך `Actions`.

## מגבלות

- הגישה לחשבון ChatGPT תלויה בזכאות למסלול ההתחברות ובהרשאות שניתנו; אין מפתח API נפרד, אך השימוש כפוף למכסות.
- אין שליטה מלאה בעכבר, במקלדת או בכל תוכנות Windows; מדובר בסוכן מוגבל. משימת ציור נעשית על ידי יצירת תמונת PNG מהציור שהמודל מספק ופתיחתה ב־Paint, ולא על ידי לחיצות עכבר המדמות ציור ידני.
- בדיקות היחידה אינן מוכיחות שההתחברות לחשבון אמיתי עובדת; יש לאמת זאת במחשב.
- אין השבתה של אימות תעודות HTTPS.
