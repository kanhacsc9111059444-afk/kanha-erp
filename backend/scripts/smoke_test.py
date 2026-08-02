import httpx

base = "http://127.0.0.1:8080"
r = httpx.post(base + "/api/auth/login", json={"email": "admin@kanhaerp.com", "password": "admin123"})
print("login", r.status_code)
r.raise_for_status()
tok = r.json()["access_token"]
h = {"Authorization": f"Bearer {tok}"}
print("health", httpx.get(base + "/api/health").json())
print("dash", httpx.get(base + "/api/dashboard", headers=h).json()["kpis"])
lead = httpx.post(
    base + "/api/crm/leads",
    headers=h,
    json={"name": "API Flow", "company_name": "API Co", "stage": "qualified", "value": 1},
).json()
q = httpx.post(base + f"/api/crm/flow/lead-to-quote/{lead['id']}", headers=h).json()
print("quote", q["quotation"]["number"])
o = httpx.post(base + f"/api/sales/flow/quote-to-order/{q['quotation']['id']}", headers=h).json()
print("order", o["number"])
inv = httpx.post(base + f"/api/sales/flow/order-to-invoice/{o['id']}", headers=h).json()
print("invoice", inv["invoice"]["number"], inv["invoice"]["total"])
print("modules", len(httpx.get(base + "/api/modules", headers=h).json()["modules"]))
print("ai", httpx.post(base + "/api/ai/chat", headers=h, json={"message": "sales revenue"}).json()["reply"][:60].encode("ascii", "replace").decode())
print("payroll", httpx.post(base + "/api/hrms/payroll/run", headers=h).json()["period"])
print("INDEX", httpx.get(base + "/").status_code, "css", httpx.get(base + "/assets/css/app.css").status_code)
print("ALL OK")
