# Industry profiles + Live Monitor

## One ERP, many company types

| Profile | Concept |
|---------|---------|
| **manufacturing** | BOM, work orders, machines, MRP, QC, stock |
| **trading** | Dealers, buy–sell, logistics, GST |
| **service** | Tickets, projects, AMC, light stock |
| **retail** | POS scan billing focus |
| **professional** | Solo / freelancer lean pack |
| **hybrid** | Sab modules |

Settings → **Company type / industry profile** → modules auto-scope.

Manufacturing company = manufacturing modules ON; service company unko hide — same kernel.

## Live Monitor (cameras)

**Policy: ERP video store nahi karta.**

- DVR/NVR recording alag rehti hai (aapke hardware/cloud pe)
- KanhaERP sirf **live stream URL** open karta hai (HLS / embed)
- Multi-site: HQ, plant, branches
- Ops **chat** while watching (text)
- Employee mobile cam = optional stream URL (kind=`employee_mobile`) — still no archive in ERP

### Why not store video in ERP?
Heavy size, legal retention on DVR, separate backup — ERP = **monitor kya ho raha hai**, not replace CCTV.

### Setup
1. Open **Live Monitor**
2. Add Site (office / plant)
3. Add Camera → paste NVR live HTTPS link
4. Watch + chat
