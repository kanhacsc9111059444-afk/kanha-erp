# Form: Kanha Extras (Chase · Meta · OCR · WhatsApp Login · PWA)

**Sources:**
- SBAC WhatsApp Login: https://erp.sbacindia.in/user/whatsappset.aspx (live 2026-08-02)  
- Kanha layer (MAP #8): AI · Automation · Chase · Mobile — not SBAC screen clones  

**Kanha UI:** `#/extras` · `#/whatsapp` · `#/automation` · `#/ai` · `#/apps` · `#/documents`  
**Status:** ✅ Complete — deepen 2026-08-02

## Locked
- Extras = Kanha design on top of parity  
- Demo adapters always work; Meta / LLM / GSP keys optional  
- No client data import  

## WhatsApp Login (SBAC `whatsappset.aspx`)
| Field | Control |
|-------|---------|
| Mobile No | `txtmobileno` |
| Type | `ddltype` Default / User |
| Create Instance | `btnInstance` |
| Get QR | `btnQrcode` |
| Reset | `btnReset` |
| User grid checkboxes | session list (Kanha: instance status) |

Kanha also: Meta Cloud webhook path (no QR needed when keys set).

## Meta inbound webhook
| Item | Notes |
|------|--------|
| URL | `GET/POST /api/meta/whatsapp/webhook` (public) |
| Verify | `hub.mode=subscribe` + `hub.verify_token` = `WHATSAPP_VERIFY_TOKEN` |
| Inbound | Meta Cloud payload → `CommsMessage` received + intent tags (YES/ORDER/PAY…) |

## Bill OCR (demo)
Paste invoice text → extract GSTIN · Invoice No · Amount · Date · Party · Phone  
`POST /api/extras/ocr/parse` — regex demo (no external OCR key). Review before save.

## Store / PWA slots
| Slot | API |
|------|-----|
| Android / iOS URLs | `GET/POST /api/extras/store-slots` |
| PWA Install | browser Add to Home Screen (working now) |

## Ops Chase Pack
```
Overdue AR → WhatsApp draft → Send one / Send all → outbox + bell
AI dock “Chase overdue” → same path
```

## Hub tiles
Chase · WhatsApp Login · OCR · AI/Agents · Automation · PWA/Store · Bridges · e-Invoice · Compliance · MIS · GPS · Documents

## APIs
- `GET/POST /api/extras/whatsapp-login`
- `GET/POST /api/extras/store-slots`
- `POST /api/extras/ocr/parse`
- `GET/POST /api/meta/whatsapp/webhook` (public)
- `GET /api/advanced/chase/overdue` · `POST …/chase/send` · `…/send-all`
- `POST /api/comms/whatsapp/send` · automation overdue / whatsapp runs

## Field track
Core SBAC deepen + Extras deepen **done**. Further polish optional (native store publish, cloud OCR vendor).
