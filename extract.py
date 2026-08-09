import argparse
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
   - page: null
   - excerpt: null
   - confidence: "low"

10. אם לא נמצאו תנאי סף ברורים, החזר עבור
    threshold_conditions מערך ריק.

11. אם לא נמצאה נקודה משמעותית לבדיקה, החזר עבורה:
    - value: null
    - page: null
    - excerpt: null
    - confidence: "low"

12. החזר JSON תקין בלבד.
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
    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.standard_b64encode(
            f.read()
        ).decode("utf-8")

    source_document = os.path.basename(pdf_path)

    prompt_with_filename = (
        f"שם מסמך המקור הוא: {source_document}\n\n"
        f"{PROMPT}"
    )

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

    text_blocks = [
        block.text
        for block in msg.content
        if block.type == "text"
    ]

    if not text_blocks:
        block_types = [block.type for block in msg.content]

        raise RuntimeError(
            "Claude returned no text. "
            f"stop_reason={msg.stop_reason}, "
            f"content_blocks={block_types}"
        )

    raw = "".join(text_blocks).strip()

    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "Claude returned text, but no JSON object was found.\n"
            f"Raw output:\n{raw}"
        )

    return raw[start:end + 1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract booklet fields using AI"
    )
    parser.add_argument(
        "michraz_id",
        type=int,
        help="RMI tender ID",
    )
    args = parser.parse_args()

    pdf_path = f"data/booklets/{args.michraz_id}.pdf"

    print(f"Sending {pdf_path} to Claude...")
    raw = extract_from_pdf(pdf_path)
    try:
        data = json.loads(raw)

        os.makedirs("data/extracted", exist_ok=True)

        output_path = (
            f"data/extracted/{args.michraz_id}.json"
        )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"OK -> {output_path}  (open it in VS Code)")

    except json.JSONDecodeError:
        print("Model did not return valid JSON. Raw output:\n")
        print(raw)
