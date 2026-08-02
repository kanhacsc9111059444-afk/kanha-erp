"""Rough JS syntax gate: brace/paren balance after stripping literals + regex for common breaks."""
from pathlib import Path
import sys

path = Path(sys.argv[1] if len(sys.argv) > 1 else r"c:\Users\HP\Projects\kanha-erp\frontend\js\app.js")
s = path.read_text(encoding="utf-8")


def strip_literals(src: str) -> str:
    out = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c in "'\"":
            q = c
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == q:
                    i += 1
                    break
                i += 1
            out.append(" ")
            continue
        if c == "`":
            i += 1
            while i < n:
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == "`":
                    i += 1
                    break
                if src[i] == "$" and i + 1 < n and src[i + 1] == "{":
                    i += 2
                    depth = 1
                    while i < n and depth:
                        ch = src[i]
                        if ch == "{":
                            depth += 1
                            i += 1
                        elif ch == "}":
                            depth -= 1
                            i += 1
                        elif ch in "'\"":
                            qq = ch
                            i += 1
                            while i < n:
                                if src[i] == "\\":
                                    i += 2
                                    continue
                                if src[i] == qq:
                                    i += 1
                                    break
                                i += 1
                        else:
                            i += 1
                    continue
                i += 1
            out.append(" ")
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            i += 2
            while i + 1 < n and not (src[i] == "*" and src[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


code = strip_literals(s)
pairs = [("{", "}"), ("(", ")"), ("[", "]")]
ok = True
for a, b in pairs:
    diff = code.count(a) - code.count(b)
    print(f"{a}{b} diff={diff}")
    if diff != 0:
        ok = False

# line of first negative paren
bal = 0
line = 1
neg = None
for ch in code:
    if ch == "\n":
        line += 1
    elif ch == "(":
        bal += 1
    elif ch == ")":
        bal -= 1
        if bal < 0 and neg is None:
            neg = line
print("paren_final", bal, "first_neg_line", neg)
sys.exit(0 if ok else 1)
