import pypdf
import json
import re

reader = pypdf.PdfReader("Fichas-Metodologicas-de-Indicadores-Financieros_V3.0.pdf")
fichas = json.load(open("data/raw/fichas_extracted.json", encoding="utf-8"))

extracted_syntax = {}

for idx, f in enumerate(fichas):
    f_num = f["num"]
    start_p = f["page"] - 1
    # End page is start of next ficha or end of document
    if idx + 1 < len(fichas):
        end_p = fichas[idx + 1]["page"] - 1
    else:
        end_p = len(reader.pages)
    
    full_text = ""
    for p in range(start_p, end_p):
        full_text += f"\n" + reader.pages[p].extract_text()
    
    # Extract D10 syntax
    syntax_match = re.search(r'D10\.\s*Sintaxis del Indicador:(.*?)(?=ANEXOS|FICHA METODOLÓGICA|$)', full_text, re.DOTALL | re.IGNORECASE)
    syntax_text = syntax_match.group(1).strip() if syntax_match else ""
    
    # Find CTA_ accounts
    ctas = re.findall(r'CTA_([0-9]+)', syntax_text)
    
    extracted_syntax[f_num] = {
        "num": f_num,
        "name": f["name"],
        "formula": f["formula"],
        "syntax": syntax_text,
        "cuentas": sorted(list(set(ctas)))
    }

with open("data/interim/all_fichas_syntax.json", "w", encoding="utf-8") as out:
    json.dump(extracted_syntax, out, indent=2, ensure_ascii=False)

print(f"Extracted syntax for {len(extracted_syntax)} fichas.")
for num in sorted(extracted_syntax.keys()):
    info = extracted_syntax[num]
    print(f"Ficha {num:02d}: {info['name']} -> {len(info['cuentas'])} cuentas: {info['cuentas'][:6]}")
