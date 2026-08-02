from pathlib import Path

t = Path(r"c:\Users\HP\Projects\kanha-erp\frontend\js\app.js").read_text(encoding="utf-8")
n = len(t)
i = 0
problems = []


def skip_string(src, idx, quote):
    idx += 1
    while idx < len(src):
        if src[idx] == "\\":
            idx += 2
            continue
        if src[idx] == quote:
            return idx + 1
        idx += 1
    return idx


while i < n:
    c = t[i]
    if c in "'\"":
        i = skip_string(t, i, c)
        continue
    if c == "`":
        start = i
        i += 1
        expr = False
        depth = 0
        expr_start = None
        while i < n:
            ch = t[i]
            if ch == "\\":
                i += 2
                continue
            if not expr and ch == "`":
                break
            if not expr and ch == "$" and i + 1 < n and t[i + 1] == "{":
                expr = True
                depth = 1
                expr_start = i
                i += 2
                continue
            if expr:
                if ch in "'\"":
                    i = skip_string(t, i, ch)
                    continue
                if ch == "`":
                    # nested template — naive scan until matching `
                    i += 1
                    while i < n:
                        if t[i] == "\\":
                            i += 2
                            continue
                        if t[i] == "`":
                            i += 1
                            break
                        # nested ${
                        if t[i] == "$" and i + 1 < n and t[i + 1] == "{":
                            i += 2
                            nd = 1
                            while i < n and nd:
                                if t[i] == "\\":
                                    i += 2
                                    continue
                                if t[i] in "'\"":
                                    i = skip_string(t, i, t[i])
                                    continue
                                if t[i] == "{":
                                    nd += 1
                                elif t[i] == "}":
                                    nd -= 1
                                i += 1
                            continue
                        i += 1
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        expr = False
                i += 1
                continue
            i += 1
        if expr and expr_start is not None:
            eline = t.count("\n", 0, expr_start) + 1
            snippet = t[expr_start : expr_start + 140].replace("\n", " ")
            problems.append((eline, snippet))
        i += 1
        continue
    i += 1

print("unclosed", len(problems))
for line, snip in problems[:30]:
    print(f"L{line}: {snip}")

# Also try bisect with dukpy / quickjs? Use binary search via subprocess chrome evaluate chunks
# Binary search line ranges that fail new Function when wrapped
low, high = 0, len(t.splitlines())
# Use a crude approach: find 'Missing }' by checking increasing prefixes is too heavy.
# Instead look for known bad patterns: ${... without }
import re

# Find ${ that aren't closed before next ` or ${
for m in re.finditer(r"\$\{", t):
    start = m.start()
    # skip if in comment roughly ignored
    j = start + 2
    depth = 1
    while j < n and depth:
        ch = t[j]
        if ch == "\\":
            j += 2
            continue
        if ch in "'\"":
            j = skip_string(t, j, ch)
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == "`" and depth:
            # hit end of template while still in expr — problem
            line = t.count("\n", 0, start) + 1
            problems.append((line, "HIT_BACKTICK " + t[start : start + 80].replace("\n", " ")))
            break
        j += 1
    else:
        if depth:
            line = t.count("\n", 0, start) + 1
            print("EOF_UNCLOSED", line, t[start : start + 80].replace("\n", " "))
