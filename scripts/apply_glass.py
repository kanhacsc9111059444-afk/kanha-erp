from pathlib import Path
import re

css = Path(r"c:\Users\HP\Projects\kanha-erp\frontend\css\app.css")
# Reuse previous full CSS from sibling write - load from a compact rebuild
css.write_text(Path(r"c:\Users\HP\Projects\kanha-erp\frontend\css\_glass_source.css").read_text(encoding="utf-8") if Path(r"c:\Users\HP\Projects\kanha-erp\frontend\css\_glass_source.css").exists() else "", encoding="utf-8")
print("placeholder")
