import json, os, base64
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

PROMPT = """
אתה עוזר שמחלץ מידע מחוברת מכרז מקרקעין של רשות מקרקעי ישראל.
מצורפת חוברת המכרז כקובץ PDF.

חלץ אך ורק את השדות הבאים:

- plan_number:
  מספר התב"ע או מספר התכנית החלה על הקרקע.

- land_designation:
  ייעוד הקרקע או השימוש בקרקע, רק כאשר הוא מצוין במפורש
  בחוברת המכרז.
  אין להסיק את ייעוד הקרקע מתוך מטרת המכרז, סוג המכרז,
  ייעוד המכרז ברמ"י, היישוב, מספר התכנית או תיאור המגרש.
  אין להפוך תיאור כללי של עבודה או פרויקט לייעוד קרקע.
  אם כמה ייעודי קרקע חלים במפורש, יש לשמור את כולם בערך
  ואין להמציא קטגוריית סיכום אחת.

- threshold_conditions:
  תנאים מרכזיים להשתתפות במכרז או להגשת הצעה.
  יש להחזיר כל תנאי כאובייקט נפרד בתוך מערך.

- point_to_check:
  נקודה משמעותית אחת לפחות שמחייבת בדיקה לפני הגשת הצעה.

חוקים מחייבים:

1. השתמש אך ורק במידע שמופיע בחוברת.
   אל תמציא, אל תנחש ואל תשלים מידע ממקורות חיצוניים.

2. לכל נתון החזר את השדות הבאים:
   - value: הערך שחולץ.
   - source_document: שם קובץ ה-PDF שנמסר לך.
   - page: מספר העמוד בקובץ ה-PDF.
   - excerpt: ציטוט קצר, מילולי ומדויק מתוך החוברת.
   - confidence: אחד מהערכים "high", "medium" או "low".

3. מספר התכנית עשוי להופיע בניסוחים כגון:
   - "תב\"ע"
   - "תכנית"
   - "מגרש על פי תב\"ע"
   - "התכנית החלה"

   לדוגמה, כאשר כתוב:
   "הממכר מהווה מגרש על פי תב\"ע 4743"

   יש להחזיר את הערך:
   "4743"

4. אל תבלבל בין מספר תכנית או תב"ע לבין:
   - מספר גוש
   - מספר חלקה
   - מספר מגרש
   - מספר היתר
   - מספר סעיף
   - תאריך

   מספר ייחשב כמספר תכנית רק כאשר ההקשר בחוברת מקשר אותו
   במפורש למילים "תב\"ע" או "תכנית".

5. threshold_conditions חייב להיות מערך.
   כל תנאי יוחזר בנפרד עם העמוד והציטוט ששייכים אליו.

6. אל תאחד תנאים שמופיעים בעמודים או בסעיפים שונים
   בתוך טקסט אחד.

7. excerpt חייב להיות ציטוט מדויק מהחוברת.
   אין לנסח אותו מחדש ואין להוסיף אליו הסברים.

8. יש להבחין בין:
   - מספר ימים לבין אחוזים.
   - סכום כספי קבוע לבין אחוז מסכום ההצעה.
   - תוקף ערבות לבין סכום הערבות.

9. אם plan_number אינו מופיע בבירור, החזר עבורו:
   - value: null
   - source_document: שם קובץ ה-PDF שנמסר לך
   - page: null
   - excerpt: null
   - confidence: "low"

10. אם land_designation אינו נמצא במפורש ובבירור, החזר עבורו:
    - value: null
    - source_document: שם קובץ ה-PDF שנמסר לך
    - page: null
    - excerpt: null
    - confidence: "low"

11. אם לא נמצאו תנאי סף ברורים, החזר עבור
    threshold_conditions מערך ריק.

12. אם לא נמצאה נקודה משמעותית לבדיקה, החזר עבורה:
    - value: null
    - source_document: שם קובץ ה-PDF שנמסר לך
    - page: null
    - excerpt: null
    - confidence: "low"

13. החזר JSON תקין בלבד.
    אין להוסיף טקסט לפני ה-JSON או אחריו.
    אין להשתמש בסימוני Markdown.

מבנה התשובה:

{
  "plan_number": {
    "value": "מספר התכנית או null",
    "source_document": "שם המסמך",
    "page": 1,
    "excerpt": "ציטוט מדויק מהמסמך",
    "confidence": "high"
  },
  "land_designation": {
    "value": "ייעוד הקרקע המפורש או null",
    "source_document": "שם המסמך",
    "page": 1,
    "excerpt": "ציטוט מדויק מהמסמך",
    "confidence": "high"
  },
  "threshold_conditions": [
    {
      "value": "תנאי מרכזי אחד",
      "source_document": "שם המסמך",
      "page": 1,
      "excerpt": "ציטוט מדויק מהמסמך",
      "confidence": "high"
    }
  ],
  "point_to_check": {
    "value": "נקודה משמעותית לבדיקה",
    "source_document": "שם המסמך",
    "page": 1,
    "excerpt": "ציטוט מדויק מהמסמך",
    "confidence": "high"
  }
}
"""


def extract_from_pdf(pdf_path):
    """Extracts structured tender facts from a PDF using Claude"""

    # Step 1: Read the PDF and prepare it for Claude
    with open(pdf_path, "rb") as f:
        # The document block accepts PDF bytes as a base64 string
        pdf_b64 = base64.standard_b64encode(
            f.read()
        ).decode("utf-8")

    # Give Claude only the file name so it can report a clear source_document
    source_document = os.path.basename(pdf_path)

    prompt_with_filename = (
        f"שם מסמך המקור הוא: {source_document}\n\n"
        f"{PROMPT}"
    )

    # Step 2: Send the PDF and extraction instructions to Claude
    msg = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=4000,
        thinking={"type": "disabled"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt_with_filename,
                    },
                ],
            }
        ],
    )

    # Step 3: Collect the text returned by Claude
    text_blocks = []
    for block in msg.content:
        if block.type == "text":
            text_blocks.append(block.text)

    if not text_blocks:
        block_types = [block.type for block in msg.content]

        raise RuntimeError(
            "Claude returned no text. "
            f"stop_reason={msg.stop_reason}, "
            f"content_blocks={block_types}"
        )

    raw = "".join(text_blocks).strip() #The all text that Claude returned, including any extra text before or after the JSON.

    # Step 4: Extract the JSON from Claude's text and convert it to a dictionary
    # Allow extra text around the JSON, but let json.loads validate the result.
    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "Claude returned text, but no JSON object was found.\n"
            f"Raw output:\n{raw}"
        )

    data = json.loads(raw[start:end + 1])

    # Step 5: Validate that the extracted data has the structure expected by the system
    if not isinstance(data, dict):
        raise ValueError("Claude JSON output must be an object")

    required_fields = {
        "plan_number",
        "land_designation",
        "threshold_conditions",
        "point_to_check",
    }
    missing_fields = required_fields - data.keys()

    if missing_fields:
        names = ", ".join(sorted(missing_fields))
        raise ValueError(
            f"Claude JSON output is missing required fields: {names}"
        )

    if not isinstance(data["plan_number"], dict):
        raise ValueError("plan_number must be an object")

    if not isinstance(data["land_designation"], dict):
        raise ValueError("land_designation must be an object")

    if not isinstance(data["threshold_conditions"], list):
        raise ValueError("threshold_conditions must be a list")

    if not all(
        isinstance(condition, dict)
        for condition in data["threshold_conditions"]
    ):
        raise ValueError(
            "Each threshold condition must be an object"
        )

    if not isinstance(data["point_to_check"], dict):
        raise ValueError("point_to_check must be an object")

    return data
