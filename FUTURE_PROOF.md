# KanhaERP — Future-proof change model

## Better idea (aapke sawal ka seedha jawab)

**AI ko poora ERP rewrite / “khud sudhaar” mat do.**  
Usse ek jagah change → poora system toot sakta hai.

**Behtar model:**

```
Core ERP code     = stable (sales, stock, GST engines)
Dynamic Rules     = time/season/business policy (data)
Rules Agent       = seekhta hai → PROPOSE karta hai
Human Approve     = sirf tab APPLY (scoped)
Version + Retire  = alter/delete accurate + reversible
```

Isse ERP **dynamic** bhi rehta hai, aur **safe** bhi.

## Principles

| Principle | Meaning |
|-----------|---------|
| **Scoped change** | Discount rule ≠ inventory schema. Sirf `SAFE_SCOPES` |
| **Time-based** | `effective_from/to`, `months`, `weekdays` |
| **Propose ≠ Apply** | Agent learn → proposal queue → Approve/Reject |
| **Version, don’t overwrite** | New save = v+1; old = `retired` (history) |
| **Soft delete** | Retire/Pause — hard wipe nahi |
| **Evaluate, don’t mutate core** | Modules call `evaluate(scope, context)` |

## Safe scopes (whitelist)

`pricing` · `discount` · `reorder` · `credit` · `reminder` · `pos_offer` · `gst_hint` · `sla` · `commission`

Blocked forever as “dynamic rewrite”: schema, security, RBAC core, accounting ledger math.

## UI / API

- **Automation → Rules Studio**
- `POST /api/rules/agent/learn` — seasonal proposals
- `POST /api/rules/proposals/{id}/approve|reject`
- `POST /api/rules` — manual versioned rule
- `POST /api/rules/evaluate` — dry-run
- Live wiring: POS offer/discount · purchase reorder_factor

## Update / upgrade / alter / delete (easy + accurate)

1. **Update behavior** → new rule version (same `code`)  
2. **Upgrade season** → Agent learn → approve Diwali/Monsoon packs  
3. **Alter** → edit via new version (diff in history)  
4. **Delete** → Retire (soft) or Pause  
5. **Accuracy** → evaluate before approve; audit every change  

## What NOT to do

- Agent that edits Python/JS of ERP automatically  
- One global “AI improve everything” button  
- Rules that can change `SECRET_KEY`, roles, or DB schema  

## Result

Future-proof = **config-driven + scoped + versioned + human-gated AI**.  
Wohi aapka “time based change + learn + sudhaar” — bina poora ERP todhe.
