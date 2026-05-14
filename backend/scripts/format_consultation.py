import re
from pathlib import Path

import pandas as pd

src = Path(r"c:\Users\Damian Motomboni\Downloads\Consultation.xlsx")
out_xlsx = Path(r"c:\Users\Damian Motomboni\Downloads\Consultation_formatted.xlsx")
out_csv = Path(r"c:\Users\Damian Motomboni\Downloads\Consultation_formatted.csv")

df = pd.read_excel(src)
df.columns = [str(c).strip() for c in df.columns]
name_col = "Name" if "Name" in df.columns else df.columns[0]
amt_col = "Amount" if "Amount" in df.columns else df.columns[1]

CONSULT_PATTERNS = [
    r"consultation",
    r"follow\s*up",
    r"\bgopd\b",
    r"gynaecolog",
    r"gynecolog",
    r"obstetric",
    r"haematolog",
    r"hematolog",
    r"paediatr",
    r"pediatr",
    r"peditric",
    r"orthopae",
    r"orthoped",
    r"endocrinolog",
    r"cardiolog",
    r"neurolog",
    r"urolog",
    r"dermatolog",
    r"plastic surgeon",
    r"general surgeon",
    r"\bent\b",
    r"ivf registration",
    r"visiting",
]

PROCEDURE_PATTERNS = [
    r"radiograph",
    r"film",
    r"x\s*ray",
    r"scaling",
    r"polishing",
    r"flushing",
    r"fluorid",
    r"extraction",
    r"surgical",
    r"enucleation",
    r"operculectomy",
    r"suturing",
    r"splinting",
    r"fixation",
    r"dressing",
    r"restoration",
    r"pulpotomy",
    r"pulpectomy",
    r"\brct\b",
    r"root canal",
    r"whitening",
    r"bleaching",
    r"study model",
    r"clasp",
    r"biteguard",
    r"panoramic",
    r"bitewing",
    r"occlusal",
    r"\btmj\b",
    r"sinus",
    r"wisdom",
    r"periapical",
    r"perioapical",
    r"decidous",
    r"healing colar",
    r"pin retained",
    r"znoe",
]


def classify(name: str):
    n = name.lower()
    if any(re.search(p, n) for p in CONSULT_PATTERNS):
        return "Consultation", "GOPD Consult"
    if any(re.search(p, n) for p in PROCEDURE_PATTERNS):
        return "Procedure", "Procedure Order"
    return "Consultation", "GOPD Consult"


cons_n = 1
dent_n = 43
rows = []
for _, row in df.iterrows():
    name = str(row[name_col]).strip()
    if not name or name.lower() == "nan":
        continue
    try:
        amount = float(row[amt_col])
    except (TypeError, ValueError):
        continue
    dept, workflow = classify(name)
    if dept == "Consultation":
        code = f"Cons-{cons_n:04d}"
        cons_n += 1
    else:
        code = f"Dent-{dent_n:04d}"
        dent_n += 1
    rows.append(
        {
            "Code": code,
            "Name": name,
            "Department": dept,
            "Workflow": workflow,
            "Amount": f"{amount:.2f}",
        }
    )

out = pd.DataFrame(rows, columns=["Code", "Name", "Department", "Workflow", "Amount"])
out.to_excel(out_xlsx, index=False, sheet_name="Sheet1")
out.to_csv(out_csv, index=False, lineterminator="\n")

print(f"Rows: {len(out)}")
print(out["Department"].value_counts().to_string())
print(f"XLSX: {out_xlsx}")
print(f"CSV: {out_csv}")
