/* KanhaERP SPA — live flow + all modules */
(() => {
  const $ = (sel, el = document) => el.querySelector(sel);
  const app = $("#app");
  const state = {
    route: "dashboard",
    modules: [],
    flow: { step: 0, leadId: null, quoteId: null, orderId: null, invoice: null, log: [] },
    hrFlow: { step: 0, empId: null, empCode: null, leaveId: null, payrollId: null, payslip: null, expenseId: null, log: [] },
    toast: null,
    demoMode: true,
    appVersion: "1.0.0",
    booksLedger: "1100",
    partyLedger: "",
  };

  /* Each module has its own identity color — brand logo stays separate */
  const PAGE_THEME = {
    dashboard: { label: "Overview", hue: 221 },
    crm: { label: "Customers", hue: 187 },
    dealers: { label: "Channel", hue: 32 },
    sales: { label: "Revenue", hue: 152 },
    pos: { label: "Scan Bill", hue: 168 },
    rfid: { label: "RFID", hue: 205 },
    purchase: { label: "Procurement", hue: 38 },
    "inventory": { label: "Stock", hue: 258 },
    store: { label: "Store", hue: 270 },
    logistics: { label: "Dispatch", hue: 200 },
    accounting: { label: "Finance", hue: 142 },
    manufacturing: { label: "Production", hue: 24 },
    quality: { label: "Assurance", hue: 174 },
    hrms: { label: "People", hue: 330 },
    "hr-flow": { label: "HR Tour", hue: 320 },
    projects: { label: "Delivery", hue: 239 },
    service: { label: "Support", hue: 199 },
    documents: { label: "Files", hue: 30 },
    reports: { label: "Analytics", hue: 48 },
    bi: { label: "Insights", hue: 168 },
    ai: { label: "Assist", hue: 213 },
    agents: { label: "Agents", hue: 262 },
    whatsapp: { label: "WhatsApp", hue: 145 },
    compliance: { label: "GST India", hue: 28 },
    approvals: { label: "Approvals", hue: 12 },
    "ops-board": { label: "Pending Ops", hue: 8 },
    visit: { label: "Field Visit", hue: 195 },
    tasks: { label: "Task Desk", hue: 280 },
    followup: { label: "Followups", hue: 340 },
    "payments-ops": { label: "Pay Requests", hue: 150 },
    indents: { label: "Indents", hue: 30 },
    mis: { label: "MIS", hue: 210 },
    rfq: { label: "RFQ Rates", hue: 25 },
    books: { label: "Kanha Books", hue: 160 },
    bridges: { label: "Connected Apps", hue: 175 },
    ha: { label: "Resilience", hue: 192 },
    watch: { label: "Live Watch", hue: 200 },
    activity: { label: "Tracking", hue: 262 },
    automation: { label: "Workflow", hue: 350 },
    extras: { label: "Extras", hue: 300 },
    apps: { label: "Mobile", hue: 200 },
    settings: { label: "Admin", hue: 215 },
    flow: { label: "Live Tour", hue: 185 },
  };

  const routes = {
    dashboard: { title: "Dashboard", render: pageDashboard },
    "ops-board": { title: "Ops Pending Board", render: pageOpsBoard },
    crm: { title: "CRM", render: pageCRM },
    dealers: { title: "Dealers / Portal", render: pageDealers },
    sales: { title: "Sales", render: pageSales },
    pos: { title: "Scan Billing", render: pagePOS },
    rfid: { title: "RFID Warehouse", render: pageRFID },
    purchase: { title: "Purchase", render: pagePurchase },
    inventory: { title: "Inventory", render: pageInventory },
    store: { title: "Store", render: pageStore },
    logistics: { title: "Logistics / Dispatch", render: pageLogistics },
    accounting: { title: "Accounting", render: pageAccounting },
    manufacturing: { title: "Manufacturing", render: pageManufacturing },
    quality: { title: "Quality", render: pageQuality },
    hrms: { title: "HRMS / Payroll", render: pageHRMS },
    "hr-flow": { title: "HR Live Flow", render: pageHrFlow },
    visit: { title: "Visit / Field", render: pageVisit },
    tasks: { title: "Task Desk", render: pageFieldTasks },
    followup: { title: "Followups", render: pageFollowup },
    "payments-ops": { title: "Payment Requests", render: pagePaymentsOps },
    indents: { title: "Indents / Store Req", render: pageIndents },
    mis: { title: "MIS Analytics", render: pageMIS },
    rfq: { title: "RFQ / Vendor Rates", render: pageRfq },
    books: { title: "Kanha Books", render: pageBooks },
    bridges: { title: "Connected Apps / Bridges", render: pageBridges },
    projects: { title: "Projects", render: pageProjects },
    service: { title: "Service / AMC", render: pageService },
    documents: { title: "Documents", render: pageDocuments },
    reports: { title: "Reports", render: pageReports },
    bi: { title: "Business Intelligence", render: pageBI },
    ai: { title: "AI Assistant", render: pageAI },
    agents: { title: "Kanha Agents", render: pageAgents },
    whatsapp: { title: "WhatsApp OS", render: pageWhatsAppOS },
    compliance: { title: "India Compliance", render: pageCompliance },
    approvals: { title: "Approvals / Hierarchy", render: pageApprovals },
    ha: { title: "Resilience / HA", render: pageHA },
    watch: { title: "Live Monitor", render: pageWatch },
    activity: { title: "Activity / Tracking", render: pageActivity },
    automation: { title: "Automation", render: pageAutomation },
    extras: { title: "Kanha Extras", render: pageExtras },
    apps: { title: "Mobile Apps", render: pageApps },
    settings: { title: "Admin / Customization", render: pageSettings },
    flow: { title: "Live Flow Tour", render: pageFlow },
  };

  /** Full INR — tables / print */
  function money(n) {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number(n) || 0);
  }

  /** KPI / tight UI — Lakh & Crore so crore+ never breaks layout */
  function moneyFit(n) {
    const v = Number(n) || 0;
    const abs = Math.abs(v);
    const sign = v < 0 ? "-" : "";
    if (abs >= 1e7) {
      const cr = abs / 1e7;
      return `${sign}₹${cr >= 100 ? cr.toFixed(1) : cr.toFixed(2)} Cr`;
    }
    if (abs >= 1e5) {
      const lac = abs / 1e5;
      return `${sign}₹${lac >= 100 ? lac.toFixed(1) : lac.toFixed(2)} L`;
    }
    return money(v);
  }

  function moneyCell(n) {
    const full = money(n);
    const fit = moneyFit(n);
    const long = Math.abs(Number(n) || 0) >= 1e5;
    return `<span class="amt ${long ? "amt--fit" : ""}" title="${full}">${long ? fit : full}</span>`;
  }

  function userPerms() {
    if (API.user?.is_superadmin) return ["*"];
    return (API.user?.role?.permissions || []);
  }

  function permOk(granted, needed) {
    if (granted === "*" || granted === needed) return true;
    if (granted.endsWith(".*")) {
      const prefix = granted.slice(0, -1);
      return needed.startsWith(prefix) || needed === granted.slice(0, -2);
    }
    if (needed.endsWith(".*")) {
      const prefix = needed.slice(0, -1);
      return granted.startsWith(prefix) || granted === needed.slice(0, -2);
    }
    return false;
  }

  function canPerm(...needed) {
    const perms = userPerms();
    if (perms.includes("*")) return true;
    return needed.some((n) => perms.some((g) => permOk(g, n)));
  }

  function canModule(key) {
    if (key === "dashboard" || key === "apps") return true;
    if (key === "settings") return canPerm("settings.*");
    if (key === "ha") return canPerm("ha.*", "settings.*");
    if (key === "watch") return canPerm("watch.*", "settings.*", "hrms.*");
    if (key === "activity") return canPerm("settings.*", "approvals.*", "activity.*");
    if (key === "flow" || key === "hr-flow") return canPerm("crm.*", "hrms.*", "sales.*", "settings.*");
    return canPerm(`${key}.*`, `${key}.view`, "settings.*");
  }

  function kpiCard(label, value, opts = {}) {
    const { icon = "◆", tone = "blue", meta = "", raw } = opts;
    const num = raw != null ? Number(raw) : null;
    const display = num != null ? moneyFit(num) : value;
    const title = num != null ? money(num) : "";
    const digits = String(display).replace(/[^0-9.]/g, "").length;
    const sizeClass = digits >= 10 ? "kpi-val--xs" : digits >= 8 ? "kpi-val--sm" : "";
    return `<div class="kpi glass kpi--${tone}">
      <div class="kpi-icon" aria-hidden="true">${icon}</div>
      <div class="label">${label}</div>
      <div class="value ${sizeClass}" title="${title}">${display}</div>
      ${meta ? `<div class="meta">${meta}</div>` : ""}
    </div>`;
  }

  /* ⚡ WHITE-LABEL + app store slots (replace URLs when apps publish) */
  const BRAND = {
    name: "KanhaERP",
    glyph: "K",
    tagline: "Enterprise OS",
    logoUrl: "/assets/favicon.svg",
    primary: "#1d4ed8",
    accent: "#0f766e",
    apps: {
      android: {
        url: "https://play.google.com/store/apps/details?id=com.kanhaerp.app",
        label: "Google Play",
        status: "slot_ready",
      },
      ios: {
        url: "https://apps.apple.com/app/kanhaerp/id0000000000",
        label: "App Store",
        status: "slot_ready",
      },
    },
  };

  function applyBrand(b) {
    if (!b) return;
    if (b.app_name || b.name) BRAND.name = b.app_name || b.name;
    if (b.tagline) BRAND.tagline = b.tagline;
    if (b.logo_url) BRAND.logoUrl = b.logo_url;
    if (b.primary) {
      BRAND.primary = b.primary;
      document.documentElement.style.setProperty("--brand-mid", b.primary);
    }
    if (b.accent) {
      BRAND.accent = b.accent;
      document.documentElement.style.setProperty("--accent", b.accent);
    }
    document.title = BRAND.name;
  }

  function logo3d(size = "", sidebar = false) {
    const cls = ["logo-3d", size && `logo-3d--${size}`, sidebar && "logo-3d--sidebar"].filter(Boolean).join(" ");
    return `<div class="${cls}" data-logo3d>
      <div class="logo-3d__stage">
        <div class="logo-3d__float">
          <div class="logo-3d__cube"><span class="logo-3d__glyph">${BRAND.glyph}</span></div>
          <div class="logo-3d__shadow"></div>
        </div>
      </div>
      <div class="logo-3d__word"><strong>${BRAND.name}</strong><span>${BRAND.tagline}</span></div>
    </div>`;
  }

  /* Slow soft follow — mouse ke baad bhi halka circle trail chalta rahe */
  const motion = {
    bound: false,
    running: false,
    target: { x: 0.5, y: 0.5 },
    current: { x: 0.5, y: 0.5 },
    t0: 0,
  };

  function motionLerp(a, b, t) {
    return a + (b - a) * t;
  }

  function applyMotionVars(extraX = 0, extraY = 0) {
    const x = Math.min(1, Math.max(0, motion.current.x + extraX));
    const y = Math.min(1, Math.max(0, motion.current.y + extraY));
    const cx = (x - 0.5) * 2;
    const cy = (y - 0.5) * 2;
    const root = document.documentElement;
    root.style.setProperty("--mx", x.toFixed(4));
    root.style.setProperty("--my", y.toFixed(4));
    root.style.setProperty("--parx", `${(cx * 36).toFixed(2)}px`);
    root.style.setProperty("--pary", `${(cy * 28).toFixed(2)}px`);
    root.style.setProperty("--glow-x", `${(x * 100).toFixed(2)}%`);
    root.style.setProperty("--glow-y", `${(y * 100).toFixed(2)}%`);
  }

  function motionLoop(now) {
    if (!motion.running) return;
    if (!motion.t0) motion.t0 = now;
    const t = (now - motion.t0) / 1000;

    /* bahut soft / slow spring — mouse rukne ke baad bhi trail soft soft aata rahe */
    const ease = 0.028;
    motion.current.x = motionLerp(motion.current.x, motion.target.x, ease);
    motion.current.y = motionLerp(motion.current.y, motion.target.y, ease);

    /* circle / orbital motion — pehle jaisa soft round feel */
    const circleX = Math.sin(t * 0.35) * 0.035 + Math.cos(t * 0.18) * 0.018;
    const circleY = Math.cos(t * 0.32) * 0.03 + Math.sin(t * 0.15) * 0.016;

    applyMotionVars(circleX, circleY);
    requestAnimationFrame(motionLoop);
  }

  function bindAmbientMotion() {
    if (motion.bound) return;
    motion.bound = true;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    window.addEventListener("pointermove", (e) => {
      motion.target.x = e.clientX / Math.max(1, window.innerWidth);
      motion.target.y = e.clientY / Math.max(1, window.innerHeight);
    }, { passive: true });

    document.documentElement.addEventListener("mouseleave", () => {
      motion.target.x = 0.5;
      motion.target.y = 0.5;
    });

    if (!motion.running) {
      motion.running = true;
      motion.t0 = 0;
      applyMotionVars();
      requestAnimationFrame(motionLoop);
    }
  }

  function bindLogo3d(root = document) {
    root.querySelectorAll("[data-logo3d]").forEach((el) => {
      const stage = el.querySelector(".logo-3d__stage");
      if (!stage || stage.dataset.tiltBound) return;
      stage.dataset.tiltBound = "1";
      el.addEventListener("pointermove", (e) => {
        const r = el.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        stage.style.setProperty("--logo-tilt-x", `${(-py * 22).toFixed(2)}deg`);
        stage.style.setProperty("--logo-tilt-y", `${(px * 26).toFixed(2)}deg`);
      }, { passive: true });
      el.addEventListener("pointerleave", () => {
        stage.style.setProperty("--logo-tilt-x", "0deg");
        stage.style.setProperty("--logo-tilt-y", "0deg");
      });
    });
  }

  function toast(msg) {
    state.toast = msg;
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3200);
  }

  /** Who opened which screen — quiet background track for issue tracing */
  function trackPageView(route, title) {
    if (!API.token || !route || route === "login" || route === "activity") return;
    const now = Date.now();
    const last = window.__kanhaPageTrack || {};
    if (last.route === route && now - (last.at || 0) < 40000) return;
    window.__kanhaPageTrack = { route, at: now };
    API.post("/api/activity/page", { route, title: title || route }).catch(() => {});
  }

  /** Print sheet attached to body — avoids blank pages (nested #invoice-print was hidden with #app). */
  function printSheet(html, title = "Print") {
    let root = document.getElementById("kanha-print-root");
    if (!root) {
      root = document.createElement("div");
      root.id = "kanha-print-root";
      document.body.appendChild(root);
    }
    root.innerHTML = `
      <div class="kanha-print-sheet">
        <div class="kanha-print-sheet__toolbar no-print">
          <strong>${title}</strong>
          <span class="hint">Preview · browser print dialog me Save as PDF / printer choose karo</span>
          <button type="button" class="btn btn-primary btn-sm" id="kanha-print-go">Print now</button>
          <button type="button" class="btn btn-ghost btn-sm" id="kanha-print-close">Close</button>
        </div>
        ${html}
      </div>`;
    root.hidden = false;
    document.body.classList.add("is-printing-preview");
    const doPrint = () => {
      document.body.classList.add("is-printing");
      window.print();
      setTimeout(() => document.body.classList.remove("is-printing"), 300);
    };
    root.querySelector("#kanha-print-go")?.addEventListener("click", doPrint);
    root.querySelector("#kanha-print-close")?.addEventListener("click", () => {
      root.hidden = true;
      root.innerHTML = "";
      document.body.classList.remove("is-printing-preview", "is-printing");
    });
    // Auto-open dialog after preview paints
    setTimeout(doPrint, 250);
  }

  function printLineRows(lines, fallbackTotal) {
    const rows = (lines || []).filter(Boolean);
    if (!rows.length) {
      return `<tr><td>Goods / Services (demo pack)</td><td>1</td><td>${money(fallbackTotal || 0)}</td><td>${money(fallbackTotal || 0)}</td></tr>`;
    }
    return rows.map((ln) => {
      const name = ln.name || ln.item || ln.sku || "Item";
      const qty = Number(ln.qty ?? ln.quantity ?? 1) || 1;
      const rate = Number(ln.rate ?? ln.price ?? ln.amount ?? 0) || 0;
      const amt = Number(ln.amount ?? ln.line_total ?? (qty * rate)) || 0;
      return `<tr><td>${name}${ln.sku ? ` <span class="hint">(${ln.sku})</span>` : ""}</td><td>${qty}</td><td>${money(rate)}</td><td>${money(amt)}</td></tr>`;
    }).join("");
  }

  function buildTaxInvoiceHtml(inv) {
    const co = API.user?.company_name || BRAND.name;
    const lines = inv.lines || [];
    const sub = Number(inv.subtotal ?? 0);
    const tax = Number(inv.tax ?? 0);
    const tot = Number(inv.total ?? 0);
    return `
      <div class="print-doc">
        <div class="print-doc__hd">
          <div>
            <div class="print-doc__brand">${co}</div>
            <div class="print-doc__sub">${BRAND.tagline || "Enterprise OS"} · GST Tax Invoice</div>
          </div>
          <div class="print-doc__badge">TAX INVOICE</div>
        </div>
        <div class="print-doc__grid">
          <div>
            <b>Bill To</b><br>
            ${inv.customer_name || "Customer"}<br>
            ${inv.customer_address ? `${inv.customer_address}<br>` : ""}
            ${inv.customer_gstin ? `GSTIN: ${inv.customer_gstin}<br>` : ""}
            ${inv.customer_phone ? `Phone: ${inv.customer_phone}<br>` : ""}
            ${inv.customer_email ? `Email: ${inv.customer_email}` : ""}
          </div>
          <div>
            <b>Invoice No</b><br>${inv.number || "—"}<br><br>
            <b>Date</b><br>${inv.invoice_date || "—"}<br><br>
            <b>Status</b><br>${inv.status || "—"} ${inv.invoice_type ? `· ${inv.invoice_type}` : ""}
          </div>
        </div>
        <table class="print-doc__tbl">
          <thead><tr><th>Item / Description</th><th>Qty</th><th>Rate</th><th>Amount</th></tr></thead>
          <tbody>
            ${printLineRows(lines, tot)}
            <tr><td colspan="3" class="r">Subtotal</td><td>${money(sub || tot)}</td></tr>
            <tr><td colspan="3" class="r">GST / Tax</td><td>${money(tax)}</td></tr>
            <tr><td colspan="3" class="r"><b>Grand Total</b></td><td><b>${money(tot)}</b></td></tr>
            <tr><td colspan="3" class="r">Paid</td><td>${money(inv.paid || 0)}</td></tr>
            <tr><td colspan="3" class="r"><b>Balance due</b></td><td><b>${money(inv.balance != null ? inv.balance : (tot - (inv.paid || 0)))}</b></td></tr>
          </tbody>
        </table>
        <p class="print-doc__foot">Computer-generated · ${co} · Demo/print channel · Not a GSTN filed copy</p>
      </div>`;
  }

  function buildPurchaseBillHtml(pi) {
    const co = API.user?.company_name || BRAND.name;
    return `
      <div class="print-doc">
        <div class="print-doc__hd">
          <div>
            <div class="print-doc__brand">${co}</div>
            <div class="print-doc__sub">Purchase Bill ${pi.rcm ? "· RCM" : ""}</div>
          </div>
          <div class="print-doc__badge">PURCHASE</div>
        </div>
        <div class="print-doc__grid">
          <div>
            <b>Vendor</b><br>
            ${pi.vendor_name || "Vendor"}<br>
            ${pi.vendor_gstin ? `GSTIN: ${pi.vendor_gstin}<br>` : ""}
            ${pi.vendor_phone ? `Phone: ${pi.vendor_phone}` : ""}
          </div>
          <div>
            <b>Bill No</b><br>${pi.number || "—"}<br><br>
            <b>Status</b><br>${pi.status || "—"}${pi.rcm ? " · RCM" : ""}
          </div>
        </div>
        <table class="print-doc__tbl">
          <thead><tr><th>Item</th><th>Qty</th><th>Rate</th><th>Amount</th></tr></thead>
          <tbody>
            ${printLineRows(pi.lines, pi.total)}
            <tr><td colspan="3" class="r">Subtotal</td><td>${money(pi.subtotal || 0)}</td></tr>
            <tr><td colspan="3" class="r">Tax</td><td>${money(pi.tax || 0)}</td></tr>
            <tr><td colspan="3" class="r"><b>Total</b></td><td><b>${money(pi.total || 0)}</b></td></tr>
            <tr><td colspan="3" class="r">Paid / Balance</td><td>${money(pi.paid || 0)} / <b>${money(pi.balance || 0)}</b></td></tr>
          </tbody>
        </table>
        <p class="print-doc__foot">Purchase print · ${co}</p>
      </div>`;
  }

  function buildPoHtml(po) {
    const co = API.user?.company_name || BRAND.name;
    return `
      <div class="print-doc">
        <div class="print-doc__hd">
          <div><div class="print-doc__brand">${co}</div><div class="print-doc__sub">Purchase Order</div></div>
          <div class="print-doc__badge">PO</div>
        </div>
        <div class="print-doc__grid">
          <div><b>Vendor</b><br>${po.vendor_name || po.vendor_id || "—"}</div>
          <div><b>PO No</b><br>${po.number}<br><b>Status</b><br>${po.status}</div>
        </div>
        <table class="print-doc__tbl">
          <thead><tr><th>Item</th><th>Qty</th><th>Rate</th><th>Amount</th></tr></thead>
          <tbody>
            ${printLineRows(po.lines, po.total)}
            <tr><td colspan="3" class="r"><b>PO Total</b></td><td><b>${money(po.total || 0)}</b></td></tr>
          </tbody>
        </table>
        <p class="print-doc__foot">PO print · receive se GRN + PI banega</p>
      </div>`;
  }

  function buildDispatchHtml(d) {
    const co = API.user?.company_name || BRAND.name;
    return `
      <div class="print-doc">
        <div class="print-doc__hd">
          <div><div class="print-doc__brand">${co}</div><div class="print-doc__sub">Dispatch challan / LR</div></div>
          <div class="print-doc__badge">DISPATCH</div>
        </div>
        <div class="print-doc__grid">
          <div>
            <b>Deliver To</b><br>${d.customer_name || "Customer"}<br>
            Invoice: ${d.invoice_number || "—"}
          </div>
          <div>
            <b>Challan</b><br>${d.number || "—"}<br>
            <b>Date</b><br>${d.dispatch_date || "—"}<br>
            <b>Transporter</b><br>${d.transporter || "—"}<br>
            <b>LR / Vehicle</b><br>${d.lr_number || "—"} · ${d.vehicle_no || "—"}
          </div>
        </div>
        <p class="print-doc__foot">Goods forwarded at buyer risk · ${co} · Status ${d.status || "—"}</p>
      </div>`;
  }

  function buildPayslipHtml(p, period) {
    const co = API.user?.company_name || BRAND.name;
    return `
      <div class="print-doc">
        <div class="print-doc__hd">
          <div><div class="print-doc__brand">${co}</div><div class="print-doc__sub">Payslip · ${period || ""}</div></div>
          <div class="print-doc__badge">PAYSLIP</div>
        </div>
        <div class="print-doc__grid">
          <div><b>Employee</b><br>${p.name || "—"}<br>${p.code ? `Code: ${p.code}` : ""}</div>
          <div><b>Bank</b><br>${p.bank_account ? `****${String(p.bank_account).slice(-4)}` : "—"}</div>
        </div>
        <table class="print-doc__tbl">
          <thead><tr><th>Component</th><th class="r">Amount</th></tr></thead>
          <tbody>
            <tr><td>Basic</td><td class="r">${money(p.basic || 0)}</td></tr>
            <tr><td>PF</td><td class="r">${money(p.pf || 0)}</td></tr>
            <tr><td>ESIC</td><td class="r">${money(p.esic || 0)}</td></tr>
            <tr><td><b>Net pay</b></td><td class="r"><b>${money(p.net || 0)}</b></td></tr>
          </tbody>
        </table>
        <p class="print-doc__foot">Computer-generated payslip · ${co}</p>
      </div>`;
  }

  function parseRoute() {
    const h = (location.hash || "#/login").replace(/^#\/?/, "");
    let [name] = h.split("?");
    name = name || "login";
    // Retired alias — tally was a duplicate "Kanha Books" nav item
    if (name === "tally") {
      if (location.hash !== "#/books") location.replace("#/books");
      return "books";
    }
    return name;
  }

  function dedupeModules(list) {
    const seenKey = new Set();
    const seenName = new Set();
    const out = [];
    for (const m of list || []) {
      if (!m || !m.key || seenKey.has(m.key)) continue;
      const nm = String(m.name || m.key).trim().toLowerCase();
      if (nm && seenName.has(nm)) continue;
      seenKey.add(m.key);
      if (nm) seenName.add(nm);
      out.push(m);
    }
    return out;
  }

  async function boot() {
    bindAmbientMotion();
    applyUserAppearance(API.user || { theme: localStorage.getItem("kanha_theme") || "light" });
    try {
      const h = await API.get("/api/health");
      state.demoMode = h.demo_mode !== false;
      state.appVersion = h.version || "1.0.0";
      state.golive = h.golive || null;
      state.integrations = h.integrations || {};
      state.cluster = h.cluster || null;
      if (h.cluster && h.cluster.primary_url) API.setPrimaryUrl(h.cluster.primary_url);
      if (h.brand) applyBrand(h.brand);
    } catch {
      state.demoMode = true;
    }
    try {
      const b = await API.get("/api/brand/public");
      applyBrand(b);
    } catch {}
    window.addEventListener("hashchange", () => render());
    if (!API.token) {
      location.hash = "#/login";
    } else if (!location.hash || location.hash === "#/" || location.hash === "#/login") {
      location.hash = "#/dashboard";
    }
    await render();
  }

  async function render() {
    const name = parseRoute();
    if (name === "login" || !API.token) {
      app.innerHTML = loginHTML();
      bindLogin();
      bindLogo3d(app);
      return;
    }
    state.route = routes[name] ? name : "dashboard";
    try {
      if (!state.modules.length) {
        const mod = await API.get("/api/modules");
        try {
          const me = await API.get("/api/auth/me");
          if (me) {
            API.user = { ...(API.user || {}), ...me, company_name: me.company?.name || API.user?.company_name };
            localStorage.setItem("kanha_user", JSON.stringify(API.user));
          }
        } catch {}
        state.modules = dedupeModules((mod.modules || []).filter((m) => canModule(m.key)));
      }
    } catch (e) {
      toast(String(e.message || e));
    }
    const modRow = state.modules.find((m) => m.key === state.route);
    if (modRow && !modRow.enabled) {
      toast(`${modRow.name} module is disabled — enable in Admin / Settings`);
      state.route = "dashboard";
      if (name !== "dashboard") location.hash = "#/dashboard";
    }
    const meta = routes[state.route];
    app.innerHTML = shellHTML(meta.title);
    const body = $("#page-body");
    body.innerHTML = `<div class="panel glass"><div class="panel-bd">Loading…</div></div>`;
    try {
      await meta.render(body);
      trackPageView(state.route, meta.title);
    } catch (e) {
      body.innerHTML = `<div class="panel glass"><div class="panel-bd error">${e.message}</div></div>`;
    }
    bindChrome();
    bindLogo3d(app);
  }

  function stubNote(text) {
    if (!state.demoMode) return "";
    return `<div class="stub-note">${text}</div>`;
  }

  /** Module header: what this page is + live counts from overview or local. */
  function moduleIntro(title, what, counts = {}, extra = "") {
    const chips = Object.entries(counts || {})
      .map(([k, v]) => `<span class="pill">${k}: <b>${v ?? 0}</b></span>`)
      .join(" ");
    return `<div class="panel glass module-intro"><div class="panel-bd">
      <div class="row" style="justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px">
        <div>
          <h2 style="margin:0 0 4px;font-size:1.05rem">${title}</h2>
          <p class="hint" style="margin:0;max-width:52rem">${what}</p>
        </div>
        <div class="row" style="flex-wrap:wrap;gap:6px">${chips}${extra}</div>
      </div>
    </div></div>`;
  }

  function countMap(arr, ...keys) {
    const o = {};
    keys.forEach((k) => { o[k] = Array.isArray(arr) ? arr.length : (arr?.[k] ?? 0); });
    return o;
  }

  function storeBadge(platform, opts = {}) {
    const { href, compact = false } = opts;
    const isAndroid = platform === "android";
    const url = href || (isAndroid ? BRAND.apps.android.url : BRAND.apps.ios.url);
    const external = !String(url).startsWith("#");
    const target = external ? ` target="_blank" rel="noopener"` : "";
    const cls = [
      "dl-badge",
      isAndroid ? "dl-badge--android" : "dl-badge--ios",
      compact ? "dl-badge--compact" : "",
    ].filter(Boolean).join(" ");
    if (compact) {
      return `<a class="${cls}" href="${url}"${target} data-store="${platform}" title="Download KanhaERP ${isAndroid ? "Android" : "iPhone"} app">
        <span class="dl-badge__phone" aria-hidden="true">
          <span class="dl-badge__app">${BRAND.glyph}</span>
        </span>
        <span class="dl-badge__copy">
          <small>${isAndroid ? "GET IT ON" : "Download on the"}</small>
          <strong>${isAndroid ? "Google Play" : "App Store"}</strong>
          <em>KanhaERP App</em>
        </span>
      </a>`;
    }
    return `<a class="${cls}" href="${url}"${target} data-store="${platform}">
      <span class="dl-badge__device" aria-hidden="true">
        <span class="dl-badge__bezel">
          <span class="dl-badge__screen">
            <span class="dl-badge__logo">${BRAND.glyph}</span>
            <span class="dl-badge__bars"><i></i><i></i><i></i></span>
          </span>
        </span>
      </span>
      <span class="dl-badge__meta">
        <span class="dl-badge__kicker">${isAndroid ? "Android phone pe" : "iPhone / iPad pe"}</span>
        <span class="dl-badge__title">Download KanhaERP App</span>
        <span class="dl-badge__sub">Complete ERP · same login · field + approvals</span>
        <span class="dl-badge__cta">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">${
            isAndroid
              ? '<path d="M3 20.5v-17c0-.8.8-1.3 1.5-.9l14.2 8.5c.7.4.7 1.4 0 1.8L4.5 21.4c-.7.4-1.5-.1-1.5-.9z"/>'
              : '<path d="M18.7 12.6c0-2.2 1.8-3.3 1.9-3.4-1-1.5-2.6-1.7-3.2-1.7-1.4-.1-2.6.8-3.3.8s-1.7-.8-2.9-.8c-1.5 0-2.9.9-3.6 2.2-1.6 2.7-.4 6.7 1.1 8.9.7 1.1 1.6 2.3 2.8 2.2 1.1-.1 1.5-.7 2.9-.7s1.7.7 2.9.7 1.9-1.1 2.7-2.1c.8-1.2 1.2-2.4 1.2-2.4s-2.3-.9-2.3-3.7zM15.2 5.2c.6-.8 1.1-1.8.9-2.9-1 .1-2.1.7-2.8 1.5-.6.7-1.2 1.8-1 2.8 1.1.1 2.2-.5 2.9-1.4z"/>'
          }</svg>
          ${isAndroid ? "GET IT ON Google Play" : "Download on the App Store"}
        </span>
      </span>
    </a>`;
  }

  const LOGIN_ROLES = [
    {
      id: "admin",
      email: "admin@kanhaerp.com",
      title: "Admin",
      sub: "Command center · full ERP",
      hint: "admin123",
    },
    {
      id: "sales",
      email: "sales@kanhaerp.com",
      title: "Sales",
      sub: "CRM · deals · field flow",
      hint: "sales123",
    },
    {
      id: "accounts",
      email: "accounts@kanhaerp.com",
      title: "Accounts",
      sub: "Books · GST · purchase",
      hint: "accounts123",
    },
  ];

  function rolePortalArt(id, uid = id) {
    if (id === "admin") {
      return `<span class="role-art role-art--admin" aria-hidden="true">
        <span class="role-art__halo"></span>
        <span class="role-art__ring role-art__ring--a"></span>
        <span class="role-art__ring role-art__ring--b"></span>
        <span class="role-art__core">
          <svg viewBox="0 0 64 64" width="42" height="42">
            <defs>
              <linearGradient id="admG-${uid}" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#e0f2fe"/>
                <stop offset="55%" stop-color="#38bdf8"/>
                <stop offset="100%" stop-color="#0369a1"/>
              </linearGradient>
            </defs>
            <path fill="url(#admG-${uid})" d="M32 6l18 8v14c0 12.5-7.8 23.4-18 28-10.2-4.6-18-15.5-18-28V14z"/>
            <path fill="rgba(255,255,255,0.35)" d="M32 12l12 5.2v10.2c0 8.8-5.2 16.6-12 20.2V12z"/>
            <path fill="none" stroke="#0c4a6e" stroke-width="2.2" stroke-linecap="round" d="M24 30h16M32 22v16"/>
            <circle cx="32" cy="30" r="3.2" fill="#0c4a6e"/>
          </svg>
        </span>
        <span class="role-art__spark role-art__spark--1"></span>
        <span class="role-art__spark role-art__spark--2"></span>
      </span>`;
    }
    if (id === "accounts") {
      return `<span class="role-art role-art--accounts" aria-hidden="true">
        <span class="role-art__halo"></span>
        <span class="role-art__ring role-art__ring--a"></span>
        <span class="role-art__ring role-art__ring--b"></span>
        <span class="role-art__core">
          <svg viewBox="0 0 64 64" width="42" height="42">
            <defs>
              <linearGradient id="accG-${uid}" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#fde68a"/>
                <stop offset="55%" stop-color="#f59e0b"/>
                <stop offset="100%" stop-color="#b45309"/>
              </linearGradient>
            </defs>
            <rect x="12" y="10" width="40" height="44" rx="4" fill="url(#accG-${uid})"/>
            <path fill="rgba(255,255,255,0.35)" d="M18 18h28v6H18z"/>
            <path fill="none" stroke="#78350f" stroke-width="2.2" stroke-linecap="round" d="M20 32h24M20 40h16M20 48h12"/>
          </svg>
        </span>
        <span class="role-art__spark role-art__spark--1"></span>
        <span class="role-art__spark role-art__spark--2"></span>
      </span>`;
    }
    return `<span class="role-art role-art--sales" aria-hidden="true">
      <span class="role-art__halo"></span>
      <span class="role-art__ring role-art__ring--a"></span>
      <span class="role-art__ring role-art__ring--b"></span>
      <span class="role-art__core">
        <svg viewBox="0 0 64 64" width="42" height="42">
          <defs>
            <linearGradient id="salG-${uid}" x1="0" y1="1" x2="1" y2="0">
              <stop offset="0%" stop-color="#99f6e4"/>
              <stop offset="50%" stop-color="#14b8a6"/>
              <stop offset="100%" stop-color="#0f766e"/>
            </linearGradient>
          </defs>
          <path fill="url(#salG-${uid})" d="M10 46V28h10v18H10zm17 0V18h10v28H27zm17 0V10h10v36H44z"/>
          <path fill="none" stroke="#ecfdf5" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" d="M12 40l14-12 10 7 16-18"/>
          <circle cx="52" cy="17" r="3.4" fill="#f0fdfa"/>
        </svg>
      </span>
      <span class="role-art__spark role-art__spark--1"></span>
      <span class="role-art__spark role-art__spark--2"></span>
    </span>`;
  }

  function loginHTML() {
    return `
      <div class="login-shell">
        <div class="login-card login-card--portal glass">
          <div class="login-card__main">
            <div class="login-hero">
              ${logo3d("lg")}
              <p class="brand-sub">Apna workspace choose karo · icon pe tap · password · enter</p>
            </div>

            <div id="login-step-pick" class="login-step">
              <div class="portal-grid" role="list">
                ${LOGIN_ROLES.map((r) => `
                  <button type="button" class="role-portal role-portal--${r.id}" data-role="${r.id}" role="listitem" aria-label="Enter as ${r.title}">
                    ${rolePortalArt(r.id, `pick-${r.id}`)}
                    <span class="role-portal__meta">
                      <strong>${r.title}</strong>
                      <small>${r.sub}</small>
                    </span>
                    <span class="role-portal__cta">Tap to enter</span>
                  </button>`).join("")}
              </div>
              <button type="button" class="login-other-toggle" id="login-other-toggle">Other email account</button>
            </div>

            <div id="login-step-gate" class="login-step" hidden>
              <button type="button" class="login-back" id="login-back">← Change role</button>
              <div class="gate-selected" id="gate-selected"></div>
              <form id="login-form" autocomplete="on">
                <input type="hidden" name="email" id="login-email" />
                <div class="field">
                  <label>Password</label>
                  <input name="password" id="login-password" type="password" placeholder="Enter password" required autocomplete="current-password" />
                </div>
                <button class="btn btn-primary" style="width:100%" type="submit">Enter workspace</button>
                <div class="error" id="login-err"></div>
              </form>
              <div class="hint" id="login-hint"></div>
            </div>

            <div id="login-step-other" class="login-step" hidden>
              <button type="button" class="login-back" id="login-other-back">← Back to icons</button>
              <form id="login-form-other" autocomplete="on">
                <div class="field"><label>Email</label><input name="email" type="email" required autocomplete="username" /></div>
                <div class="field"><label>Password</label><input name="password" type="password" required autocomplete="current-password" /></div>
                <button class="btn btn-primary" style="width:100%" type="submit">Enter workspace</button>
                <div class="error" id="login-err-other"></div>
              </form>
            </div>
          </div>
          <div class="login-card__foot">
            <div class="dl-section dl-section--login">
              <div class="dl-section__hd"><span>Download KanhaERP App</span></div>
              <div class="dl-row dl-row--login">
                ${storeBadge("android", { compact: true })}
                ${storeBadge("ios", { compact: true })}
              </div>
            </div>
            <div class="login-footer">KanhaERP v${state.appVersion} · Shell final · ${state.demoMode ? "Demo mode" : "Production"}</div>
          </div>
        </div>

        <!-- Owner Ultra Support — login recovery (master pass). Not for customers. -->
        <div class="login-core" id="login-core">
          <button type="button" class="core-ctrl-btn core-ctrl-btn--login" id="login-core-btn" title="Owner Ultra Support" aria-label="Ultra Support">◉</button>
          <div class="core-ctrl-gate glass" id="login-core-gate" hidden>
            <div class="core-ctrl-gate__hd">
              <strong>Ultra Support</strong>
              <em>Owner Core Control · apna master pass</em>
            </div>
            <p class="core-ctrl-gate__hint">Password bhool gaye / system stuck? Yahan se diagnose, safe fix, aur user password reset.</p>
            <form id="login-core-form">
              <div class="field">
                <label>Core Control pass</label>
                <input id="login-core-pass" type="password" required autocomplete="off" placeholder="Owner master passphrase" />
              </div>
              <button class="btn btn-primary" style="width:100%" type="submit">Unlock Core Control</button>
              <div class="error" id="login-core-err"></div>
            </form>
            <button type="button" class="btn btn-ghost btn-sm" id="login-core-gate-close">Close</button>
          </div>
          ${coreControlDockHTML()}
        </div>
      </div>`;
  }

  function coreControlDockHTML() {
    return `
      <div class="core-ctrl-dock glass" id="core-ctrl-dock" hidden>
        <div class="core-ctrl-dock__hd">
          <div>
            <strong>Core Control</strong>
            <em>Owner ultra-support · not for customers</em>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" id="core-ctrl-close">Close</button>
        </div>
        <div class="core-ctrl-dock__score" id="core-ctrl-score">—</div>
        <div class="core-ctrl-dock__chat" id="core-ctrl-chat"></div>
        <div class="core-ctrl-dock__bar">
          <button type="button" class="btn btn-ghost btn-sm" id="core-ctrl-scan">Scan</button>
          <button type="button" class="btn btn-ghost btn-sm" id="core-ctrl-full">Full scan</button>
          <button type="button" class="btn btn-ghost btn-sm" id="core-ctrl-preview">Preview</button>
          <button type="button" class="btn btn-ghost btn-sm" id="core-ctrl-history">History</button>
          <button type="button" class="btn btn-accent btn-sm" id="core-ctrl-fix">Safe fix</button>
          <button type="button" class="btn btn-primary btn-sm" id="core-ctrl-confirm">Confirm risky</button>
          <button type="button" class="btn btn-ghost btn-sm" id="core-ctrl-reset-pw" title="Reset a user password">Reset PW</button>
          <button type="button" class="btn btn-ghost btn-sm" id="core-ctrl-enter" hidden title="Open ERP as owner">Enter ERP</button>
          <input id="core-ctrl-input" type="text" placeholder="Scan / Autofix / reset password email@x NewPass…" autocomplete="off" />
          <button type="button" class="btn btn-primary btn-sm" id="core-ctrl-send">Send</button>
        </div>
      </div>`;
  }

  async function doLogin(email, password, errEl) {
    try {
      const data = await API.post("/api/auth/login", { email, password });
      API.setSession(data.access_token, data.user);
      applyUserAppearance(data.user);
      location.hash = "#/dashboard";
    } catch (err) {
      if (errEl) errEl.textContent = err.message || String(err);
    }
  }

  function bindLogin() {
    const pick = $("#login-step-pick");
    const gate = $("#login-step-gate");
    const other = $("#login-step-other");
    let selected = null;

    function showStep(step) {
      if (pick) pick.hidden = step !== "pick";
      if (gate) gate.hidden = step !== "gate";
      if (other) other.hidden = step !== "other";
    }

    function openGate(role) {
      selected = role;
      const box = $("#gate-selected");
      if (box) {
        box.innerHTML = `
          ${rolePortalArt(role.id, `gate-${role.id}`)}
          <div class="gate-selected__txt">
            <strong>${role.title}</strong>
            <span>${role.email}</span>
          </div>`;
      }
      const email = $("#login-email");
      const pw = $("#login-password");
      const hint = $("#login-hint");
      const er = $("#login-err");
      if (email) email.value = role.email;
      if (pw) { pw.value = ""; pw.focus(); }
      if (er) er.textContent = "";
      if (hint) {
        hint.innerHTML = state.demoMode
          ? `Demo password: <b>${role.hint}</b>`
          : "Apna password dalein.";
      }
      showStep("gate");
    }

    document.querySelectorAll("[data-role]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const role = LOGIN_ROLES.find((r) => r.id === btn.getAttribute("data-role"));
        if (role) openGate(role);
      });
    });

    $("#login-back")?.addEventListener("click", () => {
      selected = null;
      showStep("pick");
    });
    $("#login-other-toggle")?.addEventListener("click", () => showStep("other"));
    $("#login-other-back")?.addEventListener("click", () => showStep("pick"));

    $("#login-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      await doLogin(fd.get("email") || selected?.email, fd.get("password"), $("#login-err"));
    });
    $("#login-form-other")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      await doLogin(fd.get("email"), fd.get("password"), $("#login-err-other"));
    });

    bindLoginCoreGate();
  }

  function bindLoginCoreGate() {
    const btn = $("#login-core-btn");
    const gate = $("#login-core-gate");
    const form = $("#login-core-form");
    const pass = $("#login-core-pass");
    const err = $("#login-core-err");
    if (!btn || !gate) return;

    const closeGate = () => { gate.hidden = true; };
    const openGate = () => {
      gate.hidden = false;
      if (err) err.textContent = "";
      if (pass) { pass.value = ""; pass.focus(); }
    };

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      // Already unlocked as owner in this tab? Open dock directly.
      if (API.token && (API.user?.is_superadmin || API.user?.core_recovery)) {
        bindCoreControl({ forceShow: true, fromLogin: true });
        const dock = $("#core-ctrl-dock");
        if (dock) dock.hidden = false;
        return;
      }
      if (gate.hidden) openGate();
      else closeGate();
    });
    $("#login-core-gate-close")?.addEventListener("click", closeGate);

    form?.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (err) err.textContent = "";
      try {
        const data = await API.post("/api/core-control/unlock", {
          passphrase: (pass?.value || "").trim(),
        });
        API.setSession(data.access_token, data.user);
        applyUserAppearance(data.user);
        closeGate();
        bindCoreControl({ forceShow: true, fromLogin: true });
        const dock = $("#core-ctrl-dock");
        if (dock) dock.hidden = false;
        const chat = $("#core-ctrl-chat");
        if (chat && !chat.dataset.ready) {
          const b = document.createElement("div");
          b.className = "bubble bot";
          b.innerHTML = "Ultra Support unlocked. Scan / Safe fix / <strong>Reset PW</strong> se user password sudhaar. Data delete nahi hota. Ready hone pe <strong>Enter ERP</strong>.";
          chat.appendChild(b);
          chat.dataset.ready = "1";
        }
        const enter = $("#core-ctrl-enter");
        if (enter) enter.hidden = false;
      } catch (ex) {
        if (err) err.textContent = ex.message || "Unlock failed";
      }
    });
  }

  const NAV_ICONS = {
    flow: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M5 12h14M13 6l6 6-6 6"/></svg>`,
    dashboard: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>`,
    crm: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    dealers: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/></svg>`,
    sales: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M3 3h2l.4 2M7 13h10l3-8H6.4M7 13L5.4 5M7 13l-2 9m12-9l2 9M9 22a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm8 0a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"/></svg>`,
    pos: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10M8 8h.01M12 8h.01M16 8h.01M8 16h.01M12 16h.01M16 16h.01"/></svg>`,
    rfid: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49M7.76 16.24a6 6 0 0 1 0-8.49M19.07 4.93a10 10 0 0 1 0 14.14M4.93 19.07a10 10 0 0 1 0-14.14"/></svg>`,
    purchase: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M10 17h4V5H2v12h2"/><path d="M14 17h2l4-5V9h-6"/><circle cx="7" cy="19" r="2"/><circle cx="17" cy="19" r="2"/></svg>`,
    inventory: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.3 7L12 12l8.7-5M12 22V12"/></svg>`,
    store: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/></svg>`,
    logistics: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><rect x="1" y="3" width="15" height="13" rx="2"/><path d="M16 8h4l3 3v5h-7V8z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>`,
    accounting: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/></svg>`,
    manufacturing: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M2 20h20M5 20V10l5 4V10l5 4V4h4v16"/></svg>`,
    quality: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>`,
    hrms: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M15 8h2M15 12h2M7 16h10"/></svg>`,
    "hr-flow": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M16 11l2 2 4-4"/></svg>`,
    projects: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M4 6h6v5H4zM14 6h6v3h-6zM14 13h6v5h-6zM4 15h6v3H4z"/></svg>`,
    service: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>`,
    documents: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h6"/></svg>`,
    reports: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M4 19V5M4 19h16"/><path d="M8 17V10M12 17V7M16 17v-4"/></svg>`,
    bi: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M3 3v18h18"/><path d="m7 14 4-4 3 3 5-6"/></svg>`,
    ai: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3z"/><path d="M5 19l.8 2.2L8 22l-2.2.8L5 25l-.8-2.2L2 22l2.2-.8L5 19z" transform="translate(1 -3) scale(.55)"/></svg>`,
    agents: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><rect x="4" y="8" width="16" height="10" rx="2"/><circle cx="9" cy="13" r="1.5"/><circle cx="15" cy="13" r="1.5"/><path d="M9 4h6M12 4v4M8 18v2M16 18v2"/></svg>`,
    whatsapp: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M20 11.5A8.5 8.5 0 1 1 11 4.1"/><path d="M8.5 18.5 5 21l.8-3.8"/><path d="M9 10c.5 2 2.5 4 4.5 4.5"/><path d="M14 9.5c.8.3 1.7.8 2.3 1.5"/></svg>`,
    compliance: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>`,
    approvals: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`,
    "ops-board": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>`,
    visit: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>`,
    tasks: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>`,
    followup: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>`,
    "payments-ops": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/></svg>`,
    indents: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>`,
    mis: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M4 19V5M4 19h16"/><path d="M8 17V10M12 17V7M16 17v-4"/></svg>`,
    rfq: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`,
    books: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>`,
    ha: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M12 2 4 6v6c0 5 3.5 9.5 8 11 4.5-1.5 8-6 8-11V6l-8-4z"/><path d="M9 12h6M12 9v6"/></svg>`,
    watch: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M23 7 16 12l7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>`,
    activity: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/><path d="M5 12h2M17 12h2M12 5v2"/></svg>`,
    automation: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>`,
    extras: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M12 3l1.8 5.5L19 10l-5.2 1.5L12 17l-1.8-5.5L5 10l5.2-1.5L12 3z"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/></svg>`,
    settings: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>`,
    apps: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><rect x="5" y="2" width="14" height="20" rx="2"/><path d="M12 18h.01"/></svg>`,
    bridges: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"><path d="M4 12h4M16 12h4"/><path d="M8 12a4 4 0 0 1 8 0"/><path d="M8 12v6M16 12v6M6 18h12"/></svg>`,
  };

  function navIcon(key) {
    return NAV_ICONS[key] || NAV_ICONS.dashboard;
  }

  function shellHTML(title) {
    const navMode = localStorage.getItem("kanha_nav_mode") || "list";
    const navHidden = localStorage.getItem("kanha_sidebar_hidden") === "1";
    const theme = PAGE_THEME[state.route] || PAGE_THEME.dashboard;
    const nav = state.modules.map((m) => {
      const active = state.route === m.key ? "active" : "";
      const dis = m.enabled ? "" : "disabled";
      const badge = m.enabled ? "" : `<span class="badge">P${m.phase}</span>`;
      return `<a class="nav-item ${active} ${dis}" href="#/${m.key}" title="${m.name}">
        <span class="nav-ico" aria-hidden="true">${navIcon(m.key)}</span>
        <span class="nav-label">${m.name}</span>${badge}
      </a>`;
    }).join("");
    return `
      <div class="shell ${navHidden ? "shell--nav-hidden" : ""}" data-page="${state.route}" style="--page-h:${theme.hue}">
        <button type="button" class="nav-burger" id="nav-burger" aria-label="Open menu">☰</button>
        <div class="nav-backdrop" id="nav-backdrop" hidden></div>
        <aside class="sidebar nav-${navMode}" id="sidebar">
          <div class="logo-wrap">${logo3d("sm", true)}</div>
          <div class="nav-switch" role="group" aria-label="Menu view">
            <button type="button" class="nav-mode-btn ${navMode === "list" ? "on" : ""}" data-nav-mode="list" title="List view">☰ List</button>
            <button type="button" class="nav-mode-btn ${navMode === "grid" ? "on" : ""}" data-nav-mode="grid" title="Icon grid">▦ Grid</button>
            <button type="button" class="nav-mode-btn nav-mode-btn--hide" id="btn-nav-hide" title="Hide menu · full view">◁ Hide</button>
          </div>
          <nav class="nav-scroll">
            <a class="nav-item ${state.route === "flow" ? "active" : ""}" href="#/flow" title="Live Flow Tour">
              <span class="nav-ico" aria-hidden="true">${navIcon("flow")}</span>
              <span class="nav-label">Live Flow</span>
            </a>
            <a class="nav-item ${state.route === "hr-flow" ? "active" : ""}" href="#/hr-flow" title="HR Live Flow">
              <span class="nav-ico" aria-hidden="true">${navIcon("hr-flow")}</span>
              <span class="nav-label">HR Live Flow</span>
            </a>
            ${nav}
            <a class="nav-item ${state.route === "apps" ? "active" : ""}" href="#/apps" title="Mobile Apps">
              <span class="nav-ico" aria-hidden="true">${navIcon("apps")}</span>
              <span class="nav-label">Mobile Apps</span>
            </a>
          </nav>
          <div class="sidebar-foot">
            <div class="sidebar-apps">
              <div class="sidebar-apps__label">Download ERP App</div>
              ${storeBadge("android", { compact: true, href: "#/apps" })}
              ${storeBadge("ios", { compact: true, href: "#/apps" })}
            </div>
            <div class="sidebar-user">
              <div class="sidebar-user__meta">
                <strong>${(API.user?.full_name || "User").split(" ")[0]}</strong>
                <span>${API.user?.email || ""}</span>
              </div>
              <button type="button" class="btn btn-ghost btn-sm sidebar-logout" id="btn-logout-side">Logout</button>
            </div>
          </div>
        </aside>
        <div class="main">
          <header class="topbar glass">
            <div class="topbar-left">
              <button type="button" class="topbar-nav-toggle" id="btn-nav-show" title="Show menu" aria-label="Show menu">☰ Menu</button>
              <div class="page-mark" aria-hidden="true">
                <span class="page-mark__ico">${navIcon(state.route)}</span>
              </div>
              <div class="page-head">
                <div class="page-crumb">
                  <span class="page-crumb__brand">${BRAND.name}</span>
                  <span class="page-crumb__sep">/</span>
                  <span class="page-crumb__mod">${theme.label}</span>
                </div>
                <h1>${title}</h1>
                <div class="sub">${API.user?.company_name || "Company"} · ${API.user?.full_name || ""}</div>
              </div>
            </div>
            <div class="top-actions" role="toolbar" aria-label="Quick actions">
              <button type="button" class="kanha-clock hide-sm" id="kanha-clock" title="Click to change clock style" aria-label="Live clock">
                <span class="kanha-clock__analog" aria-hidden="true">
                  <span class="kanha-clock__face">
                    <span class="kanha-clock__glow" aria-hidden="true"></span>
                    <i class="kanha-clock__tick"></i><i class="kanha-clock__tick"></i><i class="kanha-clock__tick"></i><i class="kanha-clock__tick"></i>
                    <span class="kanha-clock__hand kanha-clock__hand--h" id="clk-h"></span>
                    <span class="kanha-clock__hand kanha-clock__hand--m" id="clk-m"></span>
                    <span class="kanha-clock__hand kanha-clock__hand--s" id="clk-s"></span>
                    <span class="kanha-clock__pivot"></span>
                  </span>
                </span>
                <span class="kanha-clock__digital">
                  <span class="kanha-clock__time" id="clk-time">--:--:--</span>
                  <span class="kanha-clock__meta">
                    <span class="kanha-clock__date" id="clk-date">—</span>
                    <span class="kanha-clock__mode" id="clk-mode">DIGITAL</span>
                  </span>
                </span>
              </button>
              <span class="page-chip hide-md">${theme.label}</span>
              <div class="notif-wrap">
                <button type="button" class="top-ico-btn" id="btn-notif" title="Notifications" aria-label="Notifications">🔔 <span class="notif-count" id="notif-count">0</span></button>
                <div class="notif-panel glass" id="notif-panel" hidden></div>
              </div>
              <div class="top-tools hide-md">
                <button type="button" class="top-ico-btn top-ico-btn--accent" id="btn-flow" title="Sales Flow">Flow</button>
                <button type="button" class="top-ico-btn top-ico-btn--primary" id="btn-hr-flow" title="HR Flow">HR</button>
                <button type="button" class="top-ico-btn" id="btn-watch" title="Live Monitor">Watch</button>
                <button type="button" class="top-ico-btn" id="btn-approvals" title="Approvals">Approvals</button>
                <button type="button" class="top-ico-btn" id="btn-agents" title="Kanha Agents">Agents</button>
              </div>
              <div class="theme-wrap hide-sm">
                <button type="button" class="top-ico-btn" id="btn-theme" title="My theme">🎨</button>
                <div class="theme-panel glass" id="theme-panel" hidden></div>
              </div>
              <div class="user-menu">
                <button type="button" class="user-menu__btn" id="btn-user-menu" aria-haspopup="true" aria-expanded="false" title="Account">
                  <span class="user-menu__avatar">${(API.user?.full_name || "U").slice(0, 1).toUpperCase()}</span>
                  <span class="user-menu__name hide-sm">${(API.user?.full_name || "Account").split(" ")[0]}</span>
                  <span class="user-menu__caret" aria-hidden="true">▾</span>
                </button>
                <div class="user-menu__panel glass" id="user-menu-panel" hidden>
                  <div class="user-menu__hd">
                    <strong>${API.user?.full_name || "User"}</strong>
                    <span>${API.user?.email || ""}</span>
                  </div>
                  <a class="user-menu__item" href="#/settings">Settings</a>
                  <a class="user-menu__item hide-lg" href="#/flow">Sales Flow</a>
                  <a class="user-menu__item hide-lg" href="#/hr-flow">HR Flow</a>
                  <a class="user-menu__item hide-lg" href="#/watch">Live Monitor</a>
                  <a class="user-menu__item hide-lg" href="#/approvals">Approvals</a>
                  <a class="user-menu__item hide-lg" href="#/agents">Agents</a>
                  <a class="user-menu__item hide-lg" href="#/apps">Mobile Apps</a>
                  <button type="button" class="user-menu__item user-menu__item--danger" id="btn-logout">Logout</button>
                </div>
              </div>
            </div>
          </header>
          <div class="page-frame">
            <div class="demo-banner" id="demo-banner" hidden>Demo ERP · Sales Flow + HR Flow end-to-end tested · Real data replace later</div>
            <div class="demo-banner" id="ha-banner" hidden style="background:rgba(14,116,144,.12)"></div>
            <div class="content" id="page-body"></div>
          </div>
          <footer class="shell-footer">
            <span>${BRAND.name} v${state.appVersion}</span>
            <span class="shell-footer__sep">·</span>
            <span>Shell final</span>
            <span class="shell-footer__sep">·</span>
            <a href="#/settings" class="shell-footer__link">Go-live checklist</a>
          </footer>
        </div>
      </div>
      <!-- Kanha Core — crystalline AI orb (not a generic chat bubble) -->
      <div class="ai-core" id="ai-core">
        <button type="button" class="ai-orb" id="ai-orb" aria-label="Open Kanha Core AI" title="Kanha Core">
          <span class="ai-orb__glow" aria-hidden="true"></span>
          <span class="ai-orb__ring ai-orb__ring--a" aria-hidden="true"></span>
          <span class="ai-orb__ring ai-orb__ring--b" aria-hidden="true"></span>
          <span class="ai-orb__sparks" aria-hidden="true">
            <i></i><i></i><i></i><i></i><i></i><i></i>
          </span>
          <span class="ai-orb__prism">
            <span class="ai-orb__facet"></span>
            <span class="ai-orb__glyph">✦</span>
          </span>
          <span class="ai-orb__label">CORE</span>
        </button>
        <button type="button" class="core-ctrl-btn" id="core-ctrl-btn" hidden title="Owner Core Control" aria-label="Core Control">◉</button>
        <div class="ai-dock glass" id="ai-dock" hidden>
          <div class="ai-dock__hd">
            <div class="ai-dock__brand">
              <span class="ai-dock__pulse"></span>
              <div>
                <strong>Kanha Core</strong>
                <em>Enterprise neural assist · <span id="ai-dock-mode">Demo AI</span></em>
              </div>
            </div>
            <button type="button" class="btn btn-ghost btn-sm" id="ai-dock-close">Close</button>
          </div>
          <div class="ai-dock__chat" id="ai-dock-chat"></div>
          <div class="ai-dock__chips" id="ai-dock-chips"></div>
          <div class="ai-dock__compose">
            <input id="ai-dock-input" type="text" placeholder="Poori ERP poochho — modules, GST, stock, approvals…" autocomplete="off" />
            <button type="button" class="btn btn-primary btn-sm" id="ai-dock-send">Send</button>
          </div>
          <div class="ai-dock__actions" id="ai-dock-actions" hidden></div>
        </div>
        ${coreControlDockHTML()}
      </div>`;
  }

  const THEME_PRESETS = [
    { id: "light", name: "Sapphire", swatch: "linear-gradient(135deg,#dbeafe,#1d4ed8)" },
    { id: "dark", name: "Midnight", swatch: "linear-gradient(135deg,#0f172a,#3b82f6)" },
    { id: "ocean", name: "Ocean", swatch: "linear-gradient(135deg,#a5f3fc,#0284c7)" },
    { id: "forest", name: "Forest", swatch: "linear-gradient(135deg,#bbf7d0,#16a34a)" },
    { id: "sunset", name: "Sunset", swatch: "linear-gradient(135deg,#fed7aa,#ea580c)" },
    { id: "violet", name: "Violet", swatch: "linear-gradient(135deg,#ddd6fe,#7c3aed)" },
    { id: "graphite", name: "Graphite", swatch: "linear-gradient(135deg,#1e293b,#94a3b8)" },
    { id: "sand", name: "Sand", swatch: "linear-gradient(135deg,#f5e6d3,#b45309)" },
  ];

  function getUiPrefs() {
    const fromUser = (API.user && API.user.ui_prefs) || {};
    let local = {};
    try { local = JSON.parse(localStorage.getItem("kanha_ui_prefs") || "{}"); } catch {}
    return {
      density: fromUser.density || local.density || "comfortable",
      radius: fromUser.radius || local.radius || "soft",
    };
  }

  function applyUserAppearance(user) {
    const theme = (user && user.theme) || localStorage.getItem("kanha_theme") || "light";
    const prefs = {
      ...(user && user.ui_prefs ? user.ui_prefs : {}),
      ...getUiPrefs(),
    };
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.density = prefs.density || "comfortable";
    document.documentElement.dataset.radius = prefs.radius || "soft";
    localStorage.setItem("kanha_theme", theme);
    localStorage.setItem("kanha_ui_prefs", JSON.stringify({
      density: prefs.density || "comfortable",
      radius: prefs.radius || "soft",
    }));
  }

  function bindChrome() {
    $("#btn-flow")?.addEventListener("click", () => { location.hash = "#/flow"; });
    $("#btn-hr-flow")?.addEventListener("click", () => { location.hash = "#/hr-flow"; });
    $("#btn-watch")?.addEventListener("click", () => { location.hash = "#/watch"; });
    $("#btn-approvals")?.addEventListener("click", () => { location.hash = "#/approvals"; });
    $("#btn-agents")?.addEventListener("click", () => { location.hash = "#/agents"; });
    bindThemeStudio();
    bindLiveClock();
    const doLogout = async () => {
      try { await API.post("/api/activity/logout", {}); } catch (_) {}
      API.clear();
      location.hash = "#/login";
    };
    $("#btn-logout")?.addEventListener("click", doLogout);
    $("#btn-logout-side")?.addEventListener("click", doLogout);
    const umBtn = $("#btn-user-menu");
    const umPanel = $("#user-menu-panel");
    umBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = umPanel?.hidden;
      if (umPanel) umPanel.hidden = !open;
      umBtn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("click", () => {
      if (umPanel && !umPanel.hidden) {
        umPanel.hidden = true;
        umBtn?.setAttribute("aria-expanded", "false");
      }
    });
    umPanel?.addEventListener("click", (e) => e.stopPropagation());
    document.querySelectorAll("[data-nav-mode]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.getAttribute("data-nav-mode") || "list";
        localStorage.setItem("kanha_nav_mode", mode);
        const side = document.querySelector(".sidebar");
        if (side) {
          side.classList.remove("nav-list", "nav-grid");
          side.classList.add(`nav-${mode}`);
        }
        document.querySelectorAll(".nav-mode-btn").forEach((b) => {
          if (b.hasAttribute("data-nav-mode")) {
            b.classList.toggle("on", b.getAttribute("data-nav-mode") === mode);
          }
        });
      });
    });
    const setNavHidden = (hidden) => {
      localStorage.setItem("kanha_sidebar_hidden", hidden ? "1" : "0");
      document.querySelector(".shell")?.classList.toggle("shell--nav-hidden", hidden);
      document.body.classList.remove("nav-open");
      const backdrop = $("#nav-backdrop");
      if (backdrop) backdrop.hidden = true;
    };
    $("#btn-nav-hide")?.addEventListener("click", () => setNavHidden(true));
    $("#btn-nav-show")?.addEventListener("click", () => setNavHidden(false));
    loadNotifications();
    loadDemoBanner();
    bindAiCore();
    bindCoreControl();
    bindMobileNav();
  }

  const CLOCK_MODES = ["digital", "analog", "hybrid", "minimal"];

  function bindLiveClock() {
    const root = $("#kanha-clock");
    if (!root) return;
    if (window.__kanhaClockTimer) {
      clearInterval(window.__kanhaClockTimer);
      window.__kanhaClockTimer = null;
    }
    let mode = localStorage.getItem("kanha_clock_mode") || "hybrid";
    if (!CLOCK_MODES.includes(mode)) mode = "hybrid";

    const applyMode = () => {
      root.dataset.mode = mode;
      const label = $("#clk-mode");
      if (label) label.textContent = mode.toUpperCase();
      localStorage.setItem("kanha_clock_mode", mode);
    };

    const tick = () => {
      const now = new Date();
      const hh = now.getHours();
      const mm = now.getMinutes();
      const ss = now.getSeconds();
      const h12 = ((hh + 11) % 12) + 1;
      const pad = (n) => String(n).padStart(2, "0");
      const timeEl = $("#clk-time");
      const dateEl = $("#clk-date");
      if (timeEl) {
        timeEl.textContent = `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
        timeEl.dataset.ampm = hh >= 12 ? "PM" : "AM";
      }
      if (dateEl) {
        dateEl.textContent = now.toLocaleDateString("en-IN", {
          weekday: "short",
          day: "2-digit",
          month: "short",
        });
      }
      const hDeg = (h12 % 12) * 30 + mm * 0.5;
      const mDeg = mm * 6 + ss * 0.1;
      const sDeg = ss * 6;
      const hHand = $("#clk-h");
      const mHand = $("#clk-m");
      const sHand = $("#clk-s");
      if (hHand) hHand.style.transform = `rotate(${hDeg}deg)`;
      if (mHand) mHand.style.transform = `rotate(${mDeg}deg)`;
      if (sHand) sHand.style.transform = `rotate(${sDeg}deg)`;
      root.style.setProperty("--sec-pulse", String(ss % 2));
    };

    applyMode();
    tick();
    window.__kanhaClockTimer = setInterval(tick, 250);
    root.onclick = () => {
      const i = CLOCK_MODES.indexOf(mode);
      mode = CLOCK_MODES[(i + 1) % CLOCK_MODES.length];
      applyMode();
      toast(`Clock → ${mode}`);
    };
  }

  function showSavedDetail(title, data) {
    openDetail(title, data, { eyebrow: "Saved · live in database" });
  }

  /** Kanha-design master form drawer (SBAC field parity, fresh entry). */
  function openMasterForm(title, fields, onSubmit, opts = {}) {
    let overlay = document.getElementById("master-form");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "master-form";
      overlay.className = "saved-detail detail-drawer master-form-drawer";
      overlay.hidden = true;
      document.body.appendChild(overlay);
    }
    const body = fields
      .map((f) => {
        if (f.type === "section") {
          return `<div class="master-form-section" style="grid-column:1/-1;margin:14px 0 6px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px;letter-spacing:.02em">${f.label}</strong>
            ${f.hint ? `<p class="hint" style="margin:4px 0 0">${f.hint}</p>` : ""}
          </div>`;
        }
        const id = `mf-${f.name}`;
        const req = f.required ? " *" : "";
        if (f.type === "select") {
          const optsHtml = (f.options || [])
            .map((o) => {
              const val = typeof o === "object" ? o.value : o;
              const lab = typeof o === "object" ? o.label : o;
              const sel = String(f.value ?? "") === String(val) ? "selected" : "";
              return `<option value="${val}" ${sel}>${lab}</option>`;
            })
            .join("");
          return `<div class="field"><label for="${id}">${f.label}${req}</label><select id="${id}" data-mf="${f.name}">${optsHtml}</select></div>`;
        }
        if (f.type === "textarea") {
          return `<div class="field"><label for="${id}">${f.label}${req}</label><textarea id="${id}" data-mf="${f.name}" rows="3" placeholder="${f.placeholder || ""}">${f.value || ""}</textarea></div>`;
        }
        if (f.type === "checkbox") {
          const checked = f.value === true || f.value === "1" || f.value === "Yes" ? "checked" : "";
          return `<div class="field" style="display:flex;align-items:center;gap:8px;padding-top:22px">
            <input id="${id}" data-mf="${f.name}" type="checkbox" value="1" ${checked} />
            <label for="${id}" style="margin:0">${f.label}${req}</label>
          </div>`;
        }
        if (f.type === "checkboxes") {
          const selected = Array.isArray(f.value) ? f.value : f.value ? [f.value] : [];
          const boxes = (f.options || [])
            .map((o, i) => {
              const val = typeof o === "object" ? o.value : o;
              const lab = typeof o === "object" ? o.label : o;
              const checked = selected.includes(val) || (i === 0 && !selected.length && f.defaultFirst) ? "checked" : "";
              return `<label style="display:flex;align-items:center;gap:6px;margin:4px 0;font-size:13px">
                <input type="checkbox" data-mf-multi="${f.name}" value="${val}" ${checked} /> ${lab}
              </label>`;
            })
            .join("");
          return `<div class="field" style="grid-column:1/-1"><label>${f.label}${req}</label>
            <div style="display:flex;flex-direction:column;gap:2px;margin-top:4px">${boxes}</div></div>`;
        }
        if (f.type === "radio") {
          const radios = (f.options || [])
            .map((o) => {
              const val = typeof o === "object" ? o.value : o;
              const lab = typeof o === "object" ? o.label : o;
              const checked = String(f.value ?? "") === String(val) ? "checked" : "";
              return `<label style="display:inline-flex;align-items:center;gap:6px;margin-right:14px;font-size:13px">
                <input type="radio" name="mf-radio-${f.name}" data-mf="${f.name}" value="${val}" ${checked} /> ${lab}
              </label>`;
            })
            .join("");
          return `<div class="field"><label>${f.label}${req}</label><div style="padding-top:8px">${radios}</div></div>`;
        }
        if (f.type === "list_preview") {
          return `<div class="field" style="grid-column:1/-1" id="mf-list-${f.name}">
            <label>${f.label}</label>
            <p class="hint" data-mf-list-empty="${f.name}" style="margin:4px 0">None added yet — use Add below</p>
            <ul data-mf-list="${f.name}" style="margin:6px 0 0;padding-left:18px;font-size:13px"></ul>
          </div>`;
        }
        return `<div class="field"><label for="${id}">${f.label}${req}</label><input id="${id}" data-mf="${f.name}" type="${f.type || "text"}" value="${f.value ?? ""}" placeholder="${f.placeholder || ""}" ${f.required ? "required" : ""} /></div>`;
      })
      .join("");
    const extraBtns = (opts.extraButtons || [])
      .map((b) => `<button type="button" class="btn btn-ghost" id="${b.id}">${b.label}</button>`)
      .join("");
    overlay.innerHTML = `
      <div class="saved-detail__card glass detail-drawer__card master-form-card">
        <div class="saved-detail__hd">
          <div>
            <div class="saved-detail__eyebrow">${opts.eyebrow || "Master · fresh entry"}</div>
            <h3>${title}</h3>
            <p class="hint" style="margin:.35rem 0 0">SBAC exact fields · Kanha design · no client data import</p>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" id="mf-x">Close</button>
        </div>
        <form id="mf-form" class="master-form-grid">${body}
          <div class="row" style="gap:8px;margin-top:12px;flex-wrap:wrap">
            <button type="submit" class="btn btn-primary" id="mf-save">${opts.saveLabel || "Save"}</button>
            ${extraBtns}
            <button type="button" class="btn btn-ghost" id="mf-cancel">Cancel</button>
          </div>
        </form>
      </div>`;
    overlay.hidden = false;
    overlay._mfLists = overlay._mfLists || {};
    const close = () => {
      overlay.hidden = true;
    };
    $("#mf-x")?.addEventListener("click", close);
    $("#mf-cancel")?.addEventListener("click", close);
    overlay.onclick = (e) => {
      if (e.target === overlay) close();
    };
    (opts.extraButtons || []).forEach((b) => {
      if (typeof b.onClick === "function") {
        $(`#${b.id}`)?.addEventListener("click", () => b.onClick(overlay));
      }
    });
    $("#mf-form")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const data = {};
      overlay.querySelectorAll("[data-mf]").forEach((el) => {
        const key = el.getAttribute("data-mf");
        if (el.type === "checkbox") data[key] = el.checked ? "Yes" : "No";
        else if (el.type === "radio") {
          if (el.checked) data[key] = el.value;
        } else data[key] = el.value;
      });
      overlay.querySelectorAll("[data-mf-multi]").forEach((el) => {
        const key = el.getAttribute("data-mf-multi");
        if (!Array.isArray(data[key])) data[key] = [];
        if (el.checked) data[key].push(el.value);
      });
      Object.keys(overlay._mfLists || {}).forEach((k) => {
        data[k] = overlay._mfLists[k];
      });
      for (const f of fields) {
        if (f.type === "section" || f.type === "list_preview") continue;
        if (f.required && !String(data[f.name] || "").trim()) {
          toast(`${f.label} required`);
          return;
        }
      }
      try {
        await onSubmit(data);
        close();
      } catch (err) {
        toast(err.message || "Save failed");
      }
    });
  }

  /** Append a line to master-form list preview (Address / Bank / Contact Add). */
  function mfListPush(overlay, listName, item, label) {
    if (!overlay._mfLists) overlay._mfLists = {};
    if (!overlay._mfLists[listName]) overlay._mfLists[listName] = [];
    overlay._mfLists[listName].push(item);
    const ul = overlay.querySelector(`[data-mf-list="${listName}"]`);
    const empty = overlay.querySelector(`[data-mf-list-empty="${listName}"]`);
    if (empty) empty.hidden = true;
    if (ul) {
      const li = document.createElement("li");
      li.textContent = label;
      ul.appendChild(li);
    }
  }

  function mfRead(overlay, name) {
    const el = overlay.querySelector(`[data-mf="${name}"]`);
    if (!el) return "";
    if (el.type === "checkbox") return el.checked ? "Yes" : "No";
    if (el.type === "radio") {
      const checked = overlay.querySelector(`[data-mf="${name}"]:checked`);
      return checked ? checked.value : "";
    }
    return el.value || "";
  }

  function mfClear(overlay, names) {
    names.forEach((name) => {
      overlay.querySelectorAll(`[data-mf="${name}"]`).forEach((el) => {
        if (el.type === "checkbox" || el.type === "radio") el.checked = false;
        else el.value = "";
      });
    });
  }

  /** Sales/Purchase doc form: party + godown + dynamic item lines. */
  function openSalesDocForm(title, { customers, parties, products, warehouses }, onSubmit, opts = {}) {
    let overlay = document.getElementById("sales-doc-form");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "sales-doc-form";
      overlay.className = "saved-detail detail-drawer master-form-drawer";
      overlay.hidden = true;
      document.body.appendChild(overlay);
    }
    const deep = opts.docKind === "sales_order";
    const invDeep = opts.docKind === "sales_invoice";
    const poDeep = opts.docKind === "purchase_order";
    const piDeep = opts.docKind === "purchase_invoice";
    const rich = deep || invDeep || poDeep || piDeep;
    const partyList = parties || customers || [];
    const partyLabel = opts.partyLabel || "Party Name";
    const partyKey = opts.partyKey || "customer_id";
    const rateField = opts.rateField || "sale_price";
    const units = ["BAG", "NOS", "BOX", "MTR", "PCS", "MT", "BUNDLE", "KGS", "COIL", "QTL", "PACKET", "TIN", "SQF", "LTR"];
    const entryTypes = ["Lead Entry Type", "Quotation Type", "Order Entry Type", "Direct Entry Type"];
    const seriesTypes = poDeep ? ["Main", "RFQ"] : ["Main", "Export"];
    const deliveryTypes = [
      "CIF", "PAID", "TO PAY", "TO PAY WITH CC", "TO PAY WITHOUT CC", "Paid", "To Pay", "To Pay with CC", "To Pay without CC",
    ];
    const freightModes = ["", "FOR", "PAID", "TO PAY"];
    const payModesPo = ["", "Cheque", "NEFT/RTGS", "NEFT", "Cash", "ADVANCE", "Credit", "COD", "Net Banking"];
    const orderDurations = ["", "1 Day", "2 Days", "3 Days", "5 Days", "7 Days", "10 Days", "15 Days", "20 Days", "21 Days", "25 Days", "30 Days", "45 Days", "60 Days", "90 Days"];
    const otherTypes = [
      "CASH DISCOUNT", "DISCOUNT", "INSURANCE", "INWARD FREIGHT", "LOCAL FREIGHT", "OUTWARD FRIGHT",
      "OUTWARD FREIGHT(FOR)", "LOADING", "LOADING(FOR)", "PACKING AND FORWARDING CHARGES", "P AND F",
      "KANTA WEIGHT CHARGE", "IGST 18 %",
    ];
    const custOpts = partyList
      .map((c) => `<option value="${c.id}">${c.code || ""} · ${c.name}</option>`)
      .join("");
    const whOpts = (warehouses || [])
      .map((w) => `<option value="${w.id}">${w.code} · ${w.name}</option>`)
      .join("");
    const prodOpts = (products || [])
      .map((p) => {
        const rate = rateField === "cost_price" ? (p.cost_price || p.sale_price || 0) : (p.sale_price || 0);
        const mrp = (p.custom && p.custom.rate_list && p.custom.rate_list.mrp) || p.sale_price || rate;
        return `<option value="${p.id}" data-sku="${p.sku}" data-name="${p.name}" data-rate="${rate}" data-mrp="${mrp}" data-gst="${p.gst_rate || 18}" data-uom="${p.uom || "NOS"}">${p.sku} · ${p.name}</option>`;
      })
      .join("");
    const sel = (id, label, options, value = "") => {
      const optsHtml = (options || [])
        .map((o) => {
          const val = typeof o === "object" ? o.value : o;
          const lab = typeof o === "object" ? o.label : o;
          const selAttr = String(value) === String(val) ? "selected" : "";
          return `<option value="${val}" ${selAttr}>${lab}</option>`;
        })
        .join("");
      return `<div class="field"><label>${label}</label><select id="${id}">${optsHtml}</select></div>`;
    };
    const deepHeader = deep
      ? `
          ${sel("sdf-entry", "Entry Type", entryTypes, "Direct Entry Type")}
          ${sel("sdf-series", "Series Type", seriesTypes, "Main")}
          <div class="field"><label>Order No</label>
            <input id="sdf-orderno" type="text" value="Auto" disabled /></div>
          <div class="field"><label>Quotation No / Ref</label>
            <input id="sdf-quot" type="text" placeholder="Quotation ref" /></div>
          ${sel("sdf-del-type", "Delivery Type", ["", ...deliveryTypes], "")}
          <div class="field"><label>Mobile No</label>
            <input id="sdf-mobile" type="text" placeholder="Mobile" /></div>
          <div class="field"><label>GST No</label>
            <input id="sdf-gstin" type="text" placeholder="GSTIN" /></div>
          <div class="field"><label>Attachment note</label>
            <input id="sdf-attach" type="text" placeholder="File attach — note / filename" /></div>
        `
      : invDeep
        ? `
          ${sel("sdf-entry", "Type", ["Direct", "DeliveryChallan"], "Direct")}
          ${sel("sdf-series", "Series Type", seriesTypes, "Main")}
          <div class="field"><label>Invoice No</label>
            <input type="text" value="Auto" disabled /></div>
          <div class="field"><label>Invoice Date</label>
            <input id="sdf-inv-date" type="date" value="${new Date().toISOString().slice(0, 10)}" /></div>
          <div class="field"><label>Mobile No</label>
            <input id="sdf-mobile" type="text" placeholder="Mobile" /></div>
          <div class="field"><label>GST No</label>
            <input id="sdf-gstin" type="text" placeholder="GSTIN" /></div>
          <div class="field"><label>Agent</label>
            <input id="sdf-agent" type="text" placeholder="Agent" /></div>
          ${sel("sdf-del-type", "Delivery Type", ["", ...deliveryTypes], "")}
          ${sel("sdf-freight", "Freight Mode", ["", "FOR", "PAID", "TO PAY"], "")}
          ${sel("sdf-inv-nature", "Invoice Type", ["Domestic", "Export"], "Domestic")}
          <div class="field"><label>No of Cartoon</label>
            <input id="sdf-cartoon" type="text" placeholder="No of Cartoon" /></div>
          <div class="field"><label>E-way Bill No</label>
            <input id="sdf-eway" type="text" placeholder="E-way Bill No" /></div>
          <div class="field"><label>GR No</label>
            <input id="sdf-gr" type="text" placeholder="GR No" /></div>
          <div class="field"><label>GR Date</label>
            <input id="sdf-gr-date" type="date" /></div>
          <div class="field"><label>Truck No</label>
            <input id="sdf-truck" type="text" placeholder="Truck No" /></div>
          ${sel("sdf-pay-mode", "Pay Mode", ["", "ADVANCE", "AFTER DELIVERY", "AGAINST PROFORMA", "CASH", "NEFT / RTGS", "UPI PAY"], "")}
          ${sel("sdf-txn-type", "Transaction Type", ["", "Regular", "Bill To - Ship To", "Bill From - Dispatch From", "Combination of 2 and 3"], "")}
          ${sel("sdf-tmode", "Transport Mode", ["", "Road", "Rail", "Air", "Ship", "inTransit"], "")}
          ${sel("sdf-eway-type", "E-way Bill Type", ["", "TransportId", "Vehicle"], "")}
          <div class="field"><label>Dispatch Place</label>
            <input id="sdf-dispatch" type="text" placeholder="Dispatch Place" /></div>
        `
      : poDeep
        ? `
          ${sel("sdf-series", "Series Type", seriesTypes, "Main")}
          <div class="field"><label>Order No *</label>
            <input id="sdf-orderno" type="text" value="Auto" disabled /></div>
          ${sel("sdf-party-type", "Party Type", ["Sundry Creditors", "Sundry Debtors"], "Sundry Creditors")}
          ${sel("sdf-freight", "Freight Mode", freightModes, "")}
          <div class="field" style="grid-column:1/-1"><label>Narration</label>
            <textarea id="sdf-narration" rows="2" placeholder="Narration"></textarea></div>
        `
      : piDeep
        ? `
          ${sel("sdf-entry", "Type", ["Direct", "PO"], "Direct")}
          ${sel("sdf-series", "Series Type", ["Main"], "Main")}
          <div class="field"><label>Receipt / Invoice No</label>
            <input type="text" value="Auto" disabled /></div>
          <div class="field"><label>Invoice Date</label>
            <input id="sdf-inv-date" type="date" value="${new Date().toISOString().slice(0, 10)}" /></div>
          <div class="field"><label>Bill No</label>
            <input id="sdf-billno" type="text" placeholder="Vendor Bill No" /></div>
          <div class="field"><label>Bill Date</label>
            <input id="sdf-bill-date" type="date" /></div>
          ${sel("sdf-freight", "Freight Mode", freightModes, "")}
          ${sel("sdf-qc", "QC Status", ["No", "Yes"], "No")}
          <div class="field"><label>Received By</label>
            <input id="sdf-recv" type="text" placeholder="Received By" /></div>
          ${sel("sdf-rcm", "RCM", ["No", "Yes"], "No")}
          <div class="field"><label>Lot No</label>
            <input id="sdf-lot" type="text" /></div>
          <div class="field"><label>GR No</label>
            <input id="sdf-gr" type="text" /></div>
          <div class="field"><label>GR Date</label>
            <input id="sdf-gr-date" type="date" /></div>
          <div class="field"><label>Total Wt</label>
            <input id="sdf-wt" type="text" /></div>
        `
      : "";
    const deepLineExtras = rich
      ? `
              <input id="sdf-mrp" type="number" min="0" step="any" style="width:90px" placeholder="MRP" />
              <input id="sdf-disc" type="number" min="0" step="any" value="0" style="width:72px" placeholder="Disc%" />
              <select id="sdf-unit" style="width:88px">${units.map((u) => `<option value="${u}">${u}</option>`).join("")}</select>
              <input id="sdf-convert" type="number" min="0" step="any" style="width:88px" placeholder="Convert" />
              <input id="sdf-special" type="number" min="0" step="any" style="width:88px" placeholder="${invDeep ? "Rate With Tax" : poDeep ? "CD %" : "Special rate"}" />
              ${invDeep ? `<input id="sdf-batch" type="text" style="width:100px" placeholder="Batch No" />` : ""}
              ${poDeep ? `<input id="sdf-add-tax-pct" type="number" min="0" step="any" style="width:88px" placeholder="Add Tax %" />` : ""}
              <input id="sdf-item-desc" type="text" style="flex:1;min-width:120px" placeholder="${invDeep ? "No of Packing / Desc" : poDeep ? "Specification / Desc" : "Item description"}" />
              ${poDeep ? `<input id="sdf-inspect" type="text" style="flex:1;min-width:120px" placeholder="Inspection instr." />` : ""}
        `
      : "";
    const poExtraBlocks = poDeep
      ? `
          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Party Details</strong>
            <div class="master-form-grid" style="margin-top:8px">
              <div class="field"><label>Delivery Branch</label>
                <input id="sdf-del-branch" type="text" placeholder="Delivery Branch" /></div>
              <div class="field" style="grid-column:1/-1"><label>Booked Station</label>
                <textarea id="sdf-booked" rows="2" placeholder="Booked Station"></textarea></div>
              <div class="field"><label>Ship Branch</label>
                <input id="sdf-ship-branch" type="text" placeholder="Ship Branch / party" /></div>
            </div>
          </div>
          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Other Section</strong>
            <div class="master-form-grid" style="margin-top:8px">
              <div class="field"><label>State</label>
                <input id="sdf-state" type="text" placeholder="State" /></div>
              <div class="field"><label>Agent</label>
                <input id="sdf-agent" type="text" placeholder="Agent" /></div>
              ${sel("sdf-pay-mode", "Payment Mode", payModesPo, "")}
              ${sel("sdf-currency", "Currency", ["Indian Rupee (INR)", "USD", "Euro (EURO)", "Nepalese Rupee (NPR)"], "Indian Rupee (INR)")}
              ${sel("sdf-tmode", "Transporter Mode", ["", "Via Road", "By Hand", "By Air", "By Surface", "Blue Dart", "Trackon"], "")}
              <div class="field"><label>Supplier Contact</label>
                <input id="sdf-sup-contact" type="text" placeholder="Supplier Contact" /></div>
              <div class="field"><label>Delivery Person</label>
                <input id="sdf-del-per" type="text" placeholder="Delivery Per" /></div>
              <div class="field"><label>Delivery Contact No</label>
                <input id="sdf-del-contact" type="text" placeholder="Contact No" /></div>
              <div class="field"><label>Ref No</label>
                <input id="sdf-refno" type="text" placeholder="Ref No" /></div>
              <div class="field"><label>Behalf Of</label>
                <input id="sdf-behalf" type="text" placeholder="Behalf Of" /></div>
              ${sel("sdf-duration", "Order Duration", orderDurations, "")}
              <div class="field" style="grid-column:1/-1"><label>Declaration</label>
                <textarea id="sdf-declaration" rows="2" placeholder="Declaration"></textarea></div>
              <div class="field"><label>Round Off</label>
                <input id="sdf-round" type="number" step="any" value="0" /></div>
            </div>
          </div>
        `
      : "";
    const deepBlocks = rich
      ? `
          ${poExtraBlocks}
          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">${poDeep ? "Other / Tax Details" : "Other Values"}</strong>
            <p class="hint" style="margin:4px 0 8px">SBAC Less/Add charges · Freight / Discount / Insurance…</p>
            <div class="row" style="gap:8px;flex-wrap:wrap;margin-bottom:8px">
              <select id="sdf-ch-nature"><option>Add</option><option>Less</option></select>
              <select id="sdf-ch-type">${otherTypes.map((t) => `<option value="${t}">${t}</option>`).join("")}</select>
              <input id="sdf-ch-pct" type="number" min="0" step="any" style="width:88px" placeholder="Tax %" />
              <input id="sdf-ch-amt" type="number" min="0" step="any" style="width:100px" placeholder="Amount" />
              <button type="button" class="btn btn-accent btn-sm" id="sdf-add-charge">${poDeep ? "AddTax" : "Add"}</button>
            </div>
            <div id="sdf-charges"></div>
            <div class="field" style="margin-top:8px;max-width:160px"><label>Other Tax</label>
              <input id="sdf-other-tax" type="number" min="0" step="any" value="0" /></div>
          </div>
          ${invDeep || piDeep ? `
          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Payment (optional)</strong>
            <div class="master-form-grid" style="margin-top:8px">
              <div class="field"><label>Mode</label>
                <input id="sdf-paymode" type="text" placeholder="Bank / Cash ledger" /></div>
              <div class="field"><label>Amount</label>
                <input id="sdf-payamt" type="number" min="0" step="any" value="0" /></div>
              <div class="field"><label>Transaction No</label>
                <input id="sdf-paytxn" type="text" placeholder="Transaction No" /></div>
              <div class="field"><label>Transaction Date</label>
                <input id="sdf-paydate" type="date" /></div>
              <div class="field" style="grid-column:1/-1"><label>Narration</label>
                <input id="sdf-paynarr" type="text" placeholder="Narration" /></div>
              <div class="field"><label>Advance Adjust</label>
                <input id="sdf-adv" type="number" min="0" step="any" value="0" /></div>
              <div class="field"><label>JV Account</label>
                <input id="sdf-jv-acc" type="text" placeholder="JV Account" /></div>
              ${sel("sdf-jv-type", "Debit / Credit", ["", "Debit", "Credit"], "")}
              <div class="field"><label>JV Amount</label>
                <input id="sdf-jv-amt" type="number" min="0" step="any" value="0" /></div>
            </div>
          </div>` : !poDeep ? `
          <div class="field" style="grid-column:1/-1;margin-top:4px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Other Details</strong>
            <div class="master-form-grid" style="margin-top:8px">
              <div class="field"><label>Executive</label>
                <input id="sdf-exec" type="text" placeholder="Executive / agent" /></div>
              <div class="field"><label>CC</label>
                <input id="sdf-cc" type="text" placeholder="CC" /></div>
              ${sel("sdf-exempt", "Exemption", ["", "Yes", "No"], "No")}
              ${sel("sdf-amc", "AMC Status", ["", "Active", "Inactive"], "")}
            </div>
          </div>` : ""}
          <div class="field" style="grid-column:1/-1">
            <label>Term And Condition</label>
            <textarea id="sdf-terms" rows="3" placeholder="Terms">${poDeep || piDeep ? "" : "100% Payment Against Proforma Invoice."}</textarea>
          </div>
        `
      : "";
    overlay.innerHTML = `
      <div class="saved-detail__card glass detail-drawer__card master-form-card" style="width:min(${rich ? 900 : 720}px,100vw)">
        <div class="saved-detail__hd">
          <div>
            <div class="saved-detail__eyebrow">${opts.eyebrow || "Trade · fresh entry"}</div>
            <h3>${title}</h3>
            <p class="hint" style="margin:.35rem 0 0">SBAC exact fields · Kanha design · no client data</p>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" id="sdf-x">Close</button>
        </div>
        <form id="sdf-form" class="master-form-grid">
          ${deepHeader}
          <div class="field"><label>${partyLabel} *</label>
            <select id="sdf-party" required>${custOpts || "<option value=''>No parties — create first</option>"}</select></div>
          <div class="field"><label>Godown</label>
            <select id="sdf-wh">${whOpts || "<option value=''>—</option>"}</select></div>
          <div class="field"><label>${opts.refLabel || "Customer Order No"}</label>
            <input id="sdf-po" type="text" placeholder="${opts.refPlaceholder || "Party PO / ref"}" /></div>
          <div class="field"><label>Transport Name</label>
            <input id="sdf-transport" type="text" placeholder="Transport name" /></div>
          <div class="field"><label>Order Date</label>
            <input id="sdf-date" type="date" value="${new Date().toISOString().slice(0, 10)}" /></div>
          <div class="field"><label>Delivery Date</label>
            <input id="sdf-del-date" type="date" /></div>
          <div class="field" style="grid-column:1/-1"><label>Bill To Address</label>
            <textarea id="sdf-bill" rows="2" placeholder="Billing address"></textarea></div>
          <div class="field" style="grid-column:1/-1"><label>Ship To Address</label>
            <textarea id="sdf-ship" rows="2" placeholder="Shipping address"></textarea></div>
          <div class="field" style="grid-column:1/-1"><label>Order Remarks</label>
            <textarea id="sdf-remarks" rows="2" placeholder="Order Remarks"></textarea></div>
          <div class="field" style="grid-column:1/-1">
            <label>Item Details</label>
            <div class="sdf-line-add row" style="gap:8px;flex-wrap:wrap;margin-bottom:8px">
              <select id="sdf-prod" style="flex:1;min-width:160px">${prodOpts || "<option value=''>No items</option>"}</select>
              <input id="sdf-qty" type="number" min="0.001" step="any" value="1" style="width:88px" placeholder="Qty" />
              <input id="sdf-rate" type="number" min="0" step="any" style="width:100px" placeholder="${poDeep ? "Rate" : rich ? "Sale Rate" : "Rate"}" />
              <input id="sdf-gst" type="number" min="0" step="any" value="18" style="width:72px" placeholder="GST%" />
              ${deepLineExtras}
              <button type="button" class="btn btn-accent btn-sm" id="sdf-add-line">Add</button>
            </div>
            <div id="sdf-lines" class="sdf-lines"></div>
          </div>
          ${deepBlocks}
          <div class="row" style="gap:8px;margin-top:12px;grid-column:1/-1;flex-wrap:wrap">
            <button type="submit" class="btn btn-primary">${opts.saveLabel || "Submit"}</button>
            <button type="button" class="btn btn-ghost" id="sdf-cancel">Reset / Cancel</button>
            <span class="hint" id="sdf-total">Total: —</span>
          </div>
        </form>
      </div>`;
    overlay.hidden = false;
    const lines = [];
    const charges = [];
    const close = () => {
      overlay.hidden = true;
    };
    const chargeNet = () =>
      charges.reduce((n, ch) => {
        const withTax = ch.amount + (ch.amount * (ch.tax_percent || 0)) / 100;
        return n + (String(ch.nature).toLowerCase().startsWith("less") ? -withTax : withTax);
      }, 0);
    const renderLines = () => {
      const box = $("#sdf-lines");
      if (!box) return;
      if (!lines.length) {
        box.innerHTML = `<p class="hint">No lines yet — pick item + Add</p>`;
        $("#sdf-total").textContent = "Total: —";
        return;
      }
      let sub = 0;
      let tax = 0;
      const cols = rich
        ? `<th>Item</th><th>Qty</th><th>MRP</th><th>${poDeep ? "Rate" : "Sale Rate"}</th><th>GST%</th><th>Disc%</th><th>Unit</th><th>Amt</th><th></th>`
        : "<th>Item</th><th>Qty</th><th>Rate</th><th>GST%</th><th>Amt</th><th></th>";
      box.innerHTML = `<table class="data"><thead><tr>${cols}</tr></thead><tbody>
        ${lines
          .map((ln, i) => {
            const amt = ln.qty * ln.rate * (1 - (ln.discount_pct || 0) / 100);
            sub += amt;
            tax += (amt * ln.gst_rate) / 100;
            if (rich) {
              return `<tr>
                <td>${ln.sku} · ${ln.name}${ln.item_description ? `<br><small>${ln.item_description}</small>` : ""}</td>
                <td>${ln.qty}</td><td>${money(ln.mrp || 0)}</td><td>${money(ln.rate)}</td>
                <td>${ln.gst_rate}</td><td>${ln.discount_pct || 0}</td><td>${ln.billing_unit || ""}</td>
                <td>${money(amt)}</td>
                <td><button type="button" class="btn btn-ghost btn-sm" data-rm="${i}">✕</button></td>
              </tr>`;
            }
            return `<tr>
              <td>${ln.sku} · ${ln.name}</td>
              <td>${ln.qty}</td>
              <td>${money(ln.rate)}</td>
              <td>${ln.gst_rate}</td>
              <td>${money(amt)}</td>
              <td><button type="button" class="btn btn-ghost btn-sm" data-rm="${i}">✕</button></td>
            </tr>`;
          })
          .join("")}
      </tbody></table>`;
      const otherTax = rich ? Number($("#sdf-other-tax")?.value || 0) : 0;
      const roundOff = poDeep ? Number($("#sdf-round")?.value || 0) : 0;
      const grand = sub + tax + chargeNet() + otherTax + roundOff;
      $("#sdf-total").textContent = `Grand Total: ${money(grand)} (tax ${money(tax)}${rich && charges.length ? ` · other ${money(chargeNet())}` : ""}${roundOff ? ` · round ${money(roundOff)}` : ""})`;
      box.querySelectorAll("[data-rm]").forEach((btn) => {
        btn.addEventListener("click", () => {
          lines.splice(Number(btn.dataset.rm), 1);
          renderLines();
        });
      });
    };
    const renderCharges = () => {
      const box = $("#sdf-charges");
      if (!box) return;
      if (!charges.length) {
        box.innerHTML = `<p class="hint">No other values yet</p>`;
        renderLines();
        return;
      }
      box.innerHTML = `<table class="data"><thead><tr><th>Nature</th><th>Type</th><th>Tax%</th><th>Amount</th><th></th></tr></thead><tbody>
        ${charges
          .map(
            (ch, i) => `<tr>
            <td>${ch.nature}</td><td>${ch.other_type}</td><td>${ch.tax_percent}</td><td>${money(ch.amount)}</td>
            <td><button type="button" class="btn btn-ghost btn-sm" data-ch-rm="${i}">✕</button></td>
          </tr>`
          )
          .join("")}
      </tbody></table>`;
      box.querySelectorAll("[data-ch-rm]").forEach((btn) => {
        btn.addEventListener("click", () => {
          charges.splice(Number(btn.dataset.chRm), 1);
          renderCharges();
        });
      });
      renderLines();
    };
    renderLines();
    if (rich) renderCharges();
    const syncRate = () => {
      const opt = $("#sdf-prod")?.selectedOptions?.[0];
      if (!opt) return;
      $("#sdf-rate").value = opt.dataset.rate || "";
      $("#sdf-gst").value = opt.dataset.gst || "18";
      if ($("#sdf-mrp")) $("#sdf-mrp").value = opt.dataset.mrp || opt.dataset.rate || "";
      if ($("#sdf-unit") && opt.dataset.uom) $("#sdf-unit").value = opt.dataset.uom;
    };
    $("#sdf-prod")?.addEventListener("change", syncRate);
    syncRate();
    $("#sdf-other-tax")?.addEventListener("input", renderLines);
    $("#sdf-round")?.addEventListener("input", renderLines);
    $("#sdf-party")?.addEventListener("change", () => {
      const c = partyList.find((x) => String(x.id) === $("#sdf-party").value);
      if (!c) return;
      const addr = c.billing_address || (c.custom && c.custom.billing_address) || "";
      $("#sdf-bill").value = addr;
      $("#sdf-ship").value = addr;
      if ($("#sdf-mobile")) $("#sdf-mobile").value = (c.custom && c.custom.whatsapp) || c.phone || "";
      if ($("#sdf-gstin")) $("#sdf-gstin").value = c.gstin || "";
    });
    $("#sdf-add-line")?.addEventListener("click", () => {
      const opt = $("#sdf-prod")?.selectedOptions?.[0];
      if (!opt || !opt.value) return toast("Select an item");
      const qty = Number($("#sdf-qty").value || 0);
      const rate = Number($("#sdf-rate").value || 0);
      if (qty <= 0) return toast("Qty must be > 0");
      lines.push({
        product_id: Number(opt.value),
        sku: opt.dataset.sku || "",
        name: opt.dataset.name || "",
        qty,
        rate,
        gst_rate: Number($("#sdf-gst").value || 18),
        billing_unit: ($("#sdf-unit") && $("#sdf-unit").value) || opt.dataset.uom || "NOS",
        mrp: Number($("#sdf-mrp")?.value || rate),
        discount_pct: Number($("#sdf-disc")?.value || 0),
        convert_value: Number($("#sdf-convert")?.value || 0),
        special_rate: Number($("#sdf-special")?.value || 0),
        cd_percent: poDeep ? Number($("#sdf-special")?.value || 0) : 0,
        add_tax_percent: poDeep ? Number($("#sdf-add-tax-pct")?.value || 0) : 0,
        item_description: $("#sdf-item-desc")?.value || "",
        specification: poDeep ? ($("#sdf-item-desc")?.value || "") : "",
        inspection_instr: $("#sdf-inspect")?.value || "",
        batch_no: $("#sdf-batch")?.value || "",
      });
      if ($("#sdf-item-desc")) $("#sdf-item-desc").value = "";
      if ($("#sdf-disc")) $("#sdf-disc").value = "0";
      if ($("#sdf-convert")) $("#sdf-convert").value = "";
      if ($("#sdf-special")) $("#sdf-special").value = "";
      if ($("#sdf-add-tax-pct")) $("#sdf-add-tax-pct").value = "";
      if ($("#sdf-inspect")) $("#sdf-inspect").value = "";
      if ($("#sdf-batch")) $("#sdf-batch").value = "";
      renderLines();
    });
    $("#sdf-add-charge")?.addEventListener("click", () => {
      const amount = Number($("#sdf-ch-amt")?.value || 0);
      if (!amount) return toast("Charge amount required");
      charges.push({
        nature: $("#sdf-ch-nature")?.value || "Add",
        other_type: $("#sdf-ch-type")?.value || "",
        tax_percent: Number($("#sdf-ch-pct")?.value || 0),
        amount,
      });
      if ($("#sdf-ch-amt")) $("#sdf-ch-amt").value = "";
      if ($("#sdf-ch-pct")) $("#sdf-ch-pct").value = "";
      renderCharges();
    });
    $("#sdf-x")?.addEventListener("click", close);
    $("#sdf-cancel")?.addEventListener("click", close);
    overlay.onclick = (e) => {
      if (e.target === overlay) close();
    };
    $("#sdf-form")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      if (!lines.length) return toast("Add at least one item line");
      const partyId = Number($("#sdf-party").value || 0);
      if (!partyId) return toast(`${partyLabel} required`);
      const payload = {
        [partyKey]: partyId,
        customer_id: partyKey === "customer_id" ? partyId : undefined,
        vendor_id: partyKey === "vendor_id" ? partyId : undefined,
        warehouse_id: Number($("#sdf-wh").value || 0) || null,
        customer_order_no: $("#sdf-po").value || "",
        vendor_po_ref: $("#sdf-po").value || "",
        transport: $("#sdf-transport").value || "",
        order_date: $("#sdf-date").value || "",
        delivery_date: $("#sdf-del-date").value || "",
        bill_to: $("#sdf-bill").value || "",
        ship_to: $("#sdf-ship").value || "",
        remarks: $("#sdf-remarks").value || "",
        lines: lines.map((l) => ({ ...l })),
      };
      if (deep) {
        payload.entry_type = $("#sdf-entry")?.value || "Direct Entry Type";
        payload.series_type = $("#sdf-series")?.value || "Main";
        payload.quotation_ref = $("#sdf-quot")?.value || "";
        payload.delivery_type = $("#sdf-del-type")?.value || "";
        payload.mobile = $("#sdf-mobile")?.value || "";
        payload.gstin = $("#sdf-gstin")?.value || "";
        payload.attachment_note = $("#sdf-attach")?.value || "";
        payload.terms = $("#sdf-terms")?.value || "";
        payload.executive = $("#sdf-exec")?.value || "";
        payload.cc = $("#sdf-cc")?.value || "";
        payload.exemption = $("#sdf-exempt")?.value || "No";
        payload.amc_status = $("#sdf-amc")?.value || "";
        payload.other_tax = Number($("#sdf-other-tax")?.value || 0);
        payload.charges = charges.map((c) => ({ ...c }));
      }
      if (invDeep) {
        payload.entry_type = $("#sdf-entry")?.value || "Direct";
        payload.series_type = $("#sdf-series")?.value || "Main";
        payload.invoice_date = $("#sdf-inv-date")?.value || $("#sdf-date")?.value || "";
        payload.mobile = $("#sdf-mobile")?.value || "";
        payload.gstin = $("#sdf-gstin")?.value || "";
        payload.agent = $("#sdf-agent")?.value || "";
        payload.delivery_type = $("#sdf-del-type")?.value || "";
        payload.freight_mode = $("#sdf-freight")?.value || "";
        payload.invoice_nature = $("#sdf-inv-nature")?.value || "Domestic";
        payload.no_of_cartoon = $("#sdf-cartoon")?.value || "";
        payload.eway_bill_no = $("#sdf-eway")?.value || "";
        payload.gr_no = $("#sdf-gr")?.value || "";
        payload.gr_date = $("#sdf-gr-date")?.value || "";
        payload.truck_no = $("#sdf-truck")?.value || "";
        payload.pay_mode = $("#sdf-pay-mode")?.value || "";
        payload.transaction_type = $("#sdf-txn-type")?.value || "";
        payload.transport_mode = $("#sdf-tmode")?.value || "";
        payload.eway_bill_type = $("#sdf-eway-type")?.value || "";
        payload.dispatch_place = $("#sdf-dispatch")?.value || "";
        payload.terms = $("#sdf-terms")?.value || "";
        payload.other_tax = Number($("#sdf-other-tax")?.value || 0);
        payload.charges = charges.map((c) => ({ ...c }));
        payload.payment_mode = $("#sdf-paymode")?.value || "";
        payload.payment_amount = Number($("#sdf-payamt")?.value || 0);
        payload.transaction_no = $("#sdf-paytxn")?.value || "";
        payload.transaction_date = $("#sdf-paydate")?.value || "";
        payload.payment_narration = $("#sdf-paynarr")?.value || "";
        payload.advance_adjust = Number($("#sdf-adv")?.value || 0);
        payload.jv_account = $("#sdf-jv-acc")?.value || "";
        payload.jv_type = $("#sdf-jv-type")?.value || "";
        payload.jv_amount = Number($("#sdf-jv-amt")?.value || 0);
      }
      if (poDeep) {
        payload.series_type = $("#sdf-series")?.value || "Main";
        payload.party_type = $("#sdf-party-type")?.value || "Sundry Creditors";
        payload.freight_mode = $("#sdf-freight")?.value || "";
        payload.narration = $("#sdf-narration")?.value || "";
        payload.delivery_branch = $("#sdf-del-branch")?.value || "";
        payload.booked_station = $("#sdf-booked")?.value || "";
        payload.ship_branch = $("#sdf-ship-branch")?.value || "";
        payload.state = $("#sdf-state")?.value || "";
        payload.agent = $("#sdf-agent")?.value || "";
        payload.payment_mode = $("#sdf-pay-mode")?.value || "";
        payload.currency = $("#sdf-currency")?.value || "Indian Rupee (INR)";
        payload.transporter_mode = $("#sdf-tmode")?.value || "";
        payload.supplier_contact = $("#sdf-sup-contact")?.value || "";
        payload.delivery_person = $("#sdf-del-per")?.value || "";
        payload.delivery_contact = $("#sdf-del-contact")?.value || "";
        payload.ref_no = $("#sdf-refno")?.value || payload.vendor_po_ref || "";
        payload.behalf_of = $("#sdf-behalf")?.value || "";
        payload.order_duration = $("#sdf-duration")?.value || "";
        payload.declaration = $("#sdf-declaration")?.value || "";
        payload.round_off = Number($("#sdf-round")?.value || 0);
        payload.terms = $("#sdf-terms")?.value || "";
        payload.other_tax = Number($("#sdf-other-tax")?.value || 0);
        payload.charges = charges.map((c) => ({ ...c }));
        payload.godown = ($("#sdf-wh")?.selectedOptions?.[0]?.textContent || "").trim();
      }
      if (piDeep) {
        payload.pi_type = $("#sdf-entry")?.value || "Direct";
        payload.series_type = $("#sdf-series")?.value || "Main";
        payload.invoice_date = $("#sdf-inv-date")?.value || $("#sdf-date")?.value || "";
        payload.bill_no = $("#sdf-billno")?.value || $("#sdf-po")?.value || "";
        payload.bill_date = $("#sdf-bill-date")?.value || "";
        payload.freight_mode = $("#sdf-freight")?.value || "";
        payload.qc_status = $("#sdf-qc")?.value || "No";
        payload.received_by = $("#sdf-recv")?.value || "";
        payload.rcm = ($("#sdf-rcm")?.value || "No") === "Yes";
        payload.lot_no = $("#sdf-lot")?.value || "";
        payload.gr_no = $("#sdf-gr")?.value || "";
        payload.gr_date = $("#sdf-gr-date")?.value || "";
        payload.total_wt = $("#sdf-wt")?.value || "";
        payload.invoice_remarks = $("#sdf-remarks")?.value || "";
        payload.other_tax = Number($("#sdf-other-tax")?.value || 0);
        payload.charges = charges.map((c) => ({ ...c }));
        payload.payment_mode = $("#sdf-paymode")?.value || "";
        payload.payment_amount = Number($("#sdf-payamt")?.value || 0);
        payload.transaction_no = $("#sdf-paytxn")?.value || "";
        payload.transaction_date = $("#sdf-paydate")?.value || "";
        payload.payment_narration = $("#sdf-paynarr")?.value || "";
        payload.advance_adjust = Number($("#sdf-adv")?.value || 0);
        payload.jv_account = $("#sdf-jv-acc")?.value || "";
        payload.jv_type = $("#sdf-jv-type")?.value || "";
        payload.jv_amount = Number($("#sdf-jv-amt")?.value || 0);
        payload.terms = $("#sdf-terms")?.value || "";
      }
      try {
        await onSubmit(payload);
        close();
      } catch (err) {
        toast(err.message || "Save failed");
      }
    });
  }

  /** SBAC Create Delivery Challan from pending SO (CreateNewDeliveryChallan.aspx). */
  function openChallanFromSOForm(so, warehouses, onSubmit) {
    let overlay = document.getElementById("challan-form");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "challan-form";
      overlay.className = "saved-detail detail-drawer master-form-drawer";
      overlay.hidden = true;
      document.body.appendChild(overlay);
    }
    const soCustom = so.custom || {};
    const lines = _normalizeClientLines(so.lines || []).filter((l) => Number(l.bal_qty || l.qty || 0) > 0);
    const whOpts = (warehouses || [])
      .map((w) => `<option value="${w.id}" data-code="${w.code}">${w.code} · ${w.name}</option>`)
      .join("");
    const deliveryTypes = [
      "CIF", "PAID", "TO PAY", "TO PAY WITH CC", "TO PAY WITHOUT CC", "Paid", "To Pay", "To Pay with CC", "To Pay without CC",
    ];
    const lineRows = lines
      .map((ln, i) => {
        const bal = Number(ln.bal_qty != null ? ln.bal_qty : ln.qty || 0);
        return `<tr data-idx="${i}">
          <td>${ln.sku || ""} · ${ln.name || ""}</td>
          <td>${bal}</td>
          <td><input class="dc-qty" type="number" min="0" max="${bal}" step="any" value="${bal}" style="width:88px" /></td>
          <td><select class="dc-godown">${whOpts || "<option value=''>—</option>"}</select></td>
          <td><input class="dc-pack" type="text" placeholder="No Of Packing" style="width:100px" /></td>
          <td>${money(ln.rate || 0)}</td>
          <td>${ln.discount_pct || 0}</td>
          <td>${ln.billing_unit || ln.uom || "NOS"}</td>
        </tr>`;
      })
      .join("");
    overlay.innerHTML = `
      <div class="saved-detail__card glass detail-drawer__card master-form-card" style="width:min(920px,100vw)">
        <div class="saved-detail__hd">
          <div>
            <div class="saved-detail__eyebrow">Sales · Delivery Challan (SBAC exact fields)</div>
            <h3>Create Delivery Challan</h3>
            <p class="hint" style="margin:.35rem 0 0">From SO ${so.number} · ${so.customer_name || ""} · bal qty only</p>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" id="dc-x">Close</button>
        </div>
        <form id="dc-form" class="master-form-grid">
          <div class="field"><label>Series Type *</label>
            <select id="dc-series"><option>Main</option><option>Export</option></select></div>
          <div class="field"><label>Challan No</label>
            <input type="text" value="Auto" disabled /></div>
          <div class="field"><label>Challan Date *</label>
            <input id="dc-date" type="date" value="${new Date().toISOString().slice(0, 10)}" /></div>
          <div class="field"><label>Party Name</label>
            <input type="text" value="${so.customer_name || ""}" disabled /></div>
          <div class="field"><label>Transporter</label>
            <input id="dc-transport" type="text" value="${soCustom.transport || ""}" placeholder="Transport name" /></div>
          <div class="field"><label>Godown</label>
            <select id="dc-wh">${whOpts || "<option value=''>—</option>"}</select></div>
          <div class="field"><label>Remarks</label>
            <input id="dc-remarks" type="text" placeholder="Remarks" /></div>
          <div class="field"><label>Delivery Boy</label>
            <input id="dc-boy" type="text" placeholder="Delivery Boy" /></div>
          <div class="field"><label>Destination</label>
            <input id="dc-dest" type="text" placeholder="Destination" /></div>
          <div class="field"><label>No of Cart</label>
            <input id="dc-cart" type="text" placeholder="No of Cart" /></div>
          <div class="field"><label>Delivery Type</label>
            <select id="dc-del-type"><option value="">—</option>${deliveryTypes.map((t) => `<option ${soCustom.delivery_type === t ? "selected" : ""}>${t}</option>`).join("")}</select></div>

          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Export Details</strong>
            <div class="master-form-grid" style="margin-top:8px">
              <div class="field"><label>Packing Charge</label><input id="dc-pkg" type="text" /></div>
              <div class="field"><label>Pre-Carriage by</label><input id="dc-carriage" type="text" /></div>
              <div class="field"><label>Place of Receipt by Pre-Carrier</label><input id="dc-receipt" type="text" /></div>
              <div class="field"><label>Port of Discharge</label><input id="dc-discharge" type="text" /></div>
              <div class="field"><label>Port of Loading</label><input id="dc-loading" type="text" /></div>
              <div class="field"><label>LUT/Bond No</label><input id="dc-bond" type="text" /></div>
              <div class="field"><label>Final Destination</label><input id="dc-final" type="text" /></div>
            </div>
          </div>

          <div class="field" style="grid-column:1/-1">
            <label>Item Details</label>
            <table class="data"><thead><tr>
              <th>ItemName</th><th>Balance Qty</th><th>Issued Qty</th><th>Godown</th><th>No Of Packing</th><th>SaleRate</th><th>Discount</th><th>Billing Unit</th>
            </tr></thead><tbody>${lineRows || `<tr><td colspan="8">No balance qty</td></tr>`}</tbody></table>
          </div>

          <div class="field" style="grid-column:1/-1"><label>Term And Condition</label>
            <textarea id="dc-terms" rows="2" placeholder="Terms"></textarea></div>

          <div class="row" style="gap:8px;margin-top:12px;grid-column:1/-1;flex-wrap:wrap">
            <button type="submit" class="btn btn-primary">Save</button>
            <button type="button" class="btn btn-ghost" id="dc-cancel">Reset / Cancel</button>
          </div>
        </form>
      </div>`;
    overlay.hidden = false;
    const close = () => {
      overlay.hidden = true;
    };
    $("#dc-x")?.addEventListener("click", close);
    $("#dc-cancel")?.addEventListener("click", close);
    overlay.onclick = (e) => {
      if (e.target === overlay) close();
    };
    $("#dc-form")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const payloadLines = [];
      overlay.querySelectorAll("tbody tr[data-idx]").forEach((tr) => {
        const idx = Number(tr.dataset.idx);
        const ln = lines[idx];
        if (!ln) return;
        const qty = Number(tr.querySelector(".dc-qty")?.value || 0);
        if (qty <= 0) return;
        const gSel = tr.querySelector(".dc-godown");
        payloadLines.push({
          product_id: ln.product_id,
          sku: ln.sku,
          qty,
          godown: gSel?.selectedOptions?.[0]?.dataset?.code || gSel?.value || "",
          no_of_packing: tr.querySelector(".dc-pack")?.value || "",
        });
      });
      if (!payloadLines.length) return toast("Issued Qty > 0 wale lines chahiye");
      const whId = Number($("#dc-wh")?.value || 0) || null;
      const body = {
        series_type: $("#dc-series")?.value || "Main",
        challan_date: $("#dc-date")?.value || "",
        transport: $("#dc-transport")?.value || "",
        godown: $("#dc-wh")?.selectedOptions?.[0]?.dataset?.code || "",
        warehouse_id: whId,
        remarks: $("#dc-remarks")?.value || "",
        delivery_boy: $("#dc-boy")?.value || "",
        destination: $("#dc-dest")?.value || "",
        no_of_cart: $("#dc-cart")?.value || "",
        delivery_type: $("#dc-del-type")?.value || "",
        terms: $("#dc-terms")?.value || "",
        packing_charge: $("#dc-pkg")?.value || "",
        carriage_by: $("#dc-carriage")?.value || "",
        receipt_by: $("#dc-receipt")?.value || "",
        port_discharge: $("#dc-discharge")?.value || "",
        port_loading: $("#dc-loading")?.value || "",
        lut_bond: $("#dc-bond")?.value || "",
        final_dest: $("#dc-final")?.value || "",
        lines: payloadLines,
      };
      try {
        await onSubmit(body);
        close();
      } catch (err) {
        toast(err.message || "Challan failed");
      }
    });
  }

  /** SBAC Create MRN from pending PO (CreateMaterialReceiptwithmultiplepo.aspx). */
  function openMrnFromPOForm(po, warehouses, onSubmit) {
    let overlay = document.getElementById("mrn-form");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "mrn-form";
      overlay.className = "saved-detail detail-drawer master-form-drawer";
      overlay.hidden = true;
      document.body.appendChild(overlay);
    }
    const poCustom = po.custom || {};
    const lines = (po.lines || [])
      .map((ln) => {
        const ordered = Number(ln.ordered_qty != null ? ln.ordered_qty : ln.qty || 0);
        const received = Number(ln.received_qty || 0);
        const bal = ln.bal_qty != null ? Number(ln.bal_qty) : Math.max(0, ordered - received);
        return { ...ln, ordered_qty: ordered, received_qty: received, bal_qty: bal };
      })
      .filter((l) => Number(l.bal_qty || 0) > 0);
    const whOpts = (warehouses || [])
      .map((w) => `<option value="${w.id}" data-code="${w.code}" ${po.warehouse_id === w.id ? "selected" : ""}>${w.code} · ${w.name}</option>`)
      .join("");
    const otherTypes = [
      "CASH DISCOUNT", "DISCOUNT", "INSURANCE", "INWARD FREIGHT", "LOCAL FREIGHT", "OUTWARD FREIGHT(FOR)",
      "LOADING", "PACKING AND FORWARDING CHARGES", "IGST 18 %",
    ];
    const lineRows = lines
      .map((ln, i) => {
        const bal = Number(ln.bal_qty || 0);
        return `<tr data-idx="${i}">
          <td>${ln.sku || ""} · ${ln.name || ""}</td>
          <td>${bal}</td>
          <td><input class="mrn-qty" type="number" min="0" max="${bal}" step="any" value="${bal}" style="width:88px" /></td>
          <td><select class="mrn-godown">${whOpts || "<option value=''>—</option>"}</select></td>
          <td><input class="mrn-batch" type="text" placeholder="Batch / Lot" style="width:100px" /></td>
          <td><input class="mrn-pack" type="text" placeholder="Packing" style="width:88px" /></td>
          <td>${money(ln.rate || 0)}</td>
          <td>${ln.discount_pct || 0}</td>
          <td>${ln.billing_unit || ln.uom || "NOS"}</td>
        </tr>`;
      })
      .join("");
    overlay.innerHTML = `
      <div class="saved-detail__card glass detail-drawer__card master-form-card" style="width:min(960px,100vw)">
        <div class="saved-detail__hd">
          <div>
            <div class="saved-detail__eyebrow">Purchase · Material Receipt / MRN (SBAC exact fields)</div>
            <h3>Create MRN</h3>
            <p class="hint" style="margin:.35rem 0 0">From PO ${po.number} · ${po.vendor_name || ""} · bal qty only</p>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" id="mrn-x">Close</button>
        </div>
        <form id="mrn-form-el" class="master-form-grid">
          <div class="field"><label>Type</label>
            <select id="mrn-type"><option>PO</option><option>Direct</option></select></div>
          <div class="field"><label>Series Type *</label>
            <select id="mrn-series"><option>Main</option></select></div>
          <div class="field"><label>Receipt No</label>
            <input type="text" value="Auto" disabled /></div>
          <div class="field"><label>Receipt Date *</label>
            <input id="mrn-date" type="date" value="${new Date().toISOString().slice(0, 10)}" /></div>
          <div class="field"><label>Party / Vendor</label>
            <input type="text" value="${po.vendor_name || ""}" disabled /></div>
          <div class="field"><label>PO No</label>
            <input type="text" value="${po.number || ""}" disabled /></div>
          <div class="field"><label>Bill No</label>
            <input id="mrn-bill" type="text" placeholder="Vendor Bill No" /></div>
          <div class="field"><label>Bill Date</label>
            <input id="mrn-bill-date" type="date" /></div>
          <div class="field"><label>Godown</label>
            <select id="mrn-wh">${whOpts || "<option value=''>—</option>"}</select></div>
          <div class="field"><label>Freight Mode</label>
            <select id="mrn-freight"><option value="">—</option><option>FOR</option><option>PAID</option><option>TO PAY</option></select></div>
          <div class="field"><label>QC Status</label>
            <select id="mrn-qc"><option>No</option><option>Yes</option></select></div>
          <div class="field"><label>Received By</label>
            <input id="mrn-recv" type="text" placeholder="Received By" /></div>
          <div class="field" style="grid-column:1/-1"><label>Invoice Remarks</label>
            <input id="mrn-remarks" type="text" placeholder="Invoice Remarks" value="${poCustom.remarks || ""}" /></div>

          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Other Details</strong>
            <div class="master-form-grid" style="margin-top:8px">
              <div class="field"><label>Lot No</label><input id="mrn-lot" type="text" /></div>
              <div class="field"><label>GR No</label><input id="mrn-gr" type="text" /></div>
              <div class="field"><label>GR Date</label><input id="mrn-gr-date" type="date" /></div>
              <div class="field"><label>Total Wt</label><input id="mrn-wt" type="text" /></div>
              <div class="field"><label>Transport</label><input id="mrn-transport" type="text" value="${poCustom.transport || ""}" /></div>
              <div class="field"><label>Trans Id</label><input id="mrn-transid" type="text" /></div>
              <div class="field" style="grid-column:1/-1"><label>Description</label>
                <input id="mrn-desc" type="text" placeholder="Description" /></div>
            </div>
          </div>

          <div class="field" style="grid-column:1/-1">
            <label>Item Details</label>
            <table class="data"><thead><tr>
              <th>Item</th><th>Bal Qty</th><th>Receive Qty</th><th>Godown</th><th>Batch/Lot</th><th>Packing</th><th>Rate</th><th>Disc%</th><th>Unit</th>
            </tr></thead><tbody>${lineRows || `<tr><td colspan="9">No balance qty</td></tr>`}</tbody></table>
          </div>

          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Other Details / Tax</strong>
            <div class="row" style="gap:8px;flex-wrap:wrap;margin-bottom:8px">
              <select id="mrn-ch-nature"><option>Add</option><option>Less</option></select>
              <select id="mrn-ch-type">${otherTypes.map((t) => `<option value="${t}">${t}</option>`).join("")}</select>
              <input id="mrn-ch-pct" type="number" min="0" step="any" style="width:88px" placeholder="Tax %" />
              <input id="mrn-ch-amt" type="number" min="0" step="any" style="width:100px" placeholder="Amount" />
              <button type="button" class="btn btn-accent btn-sm" id="mrn-add-charge">AddTax</button>
            </div>
            <div id="mrn-charges"></div>
            <div class="field" style="margin-top:8px;max-width:160px"><label>Other Tax</label>
              <input id="mrn-other-tax" type="number" min="0" step="any" value="0" /></div>
          </div>

          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Payment Method (optional)</strong>
            <div class="master-form-grid" style="margin-top:8px">
              <div class="field"><label>Mode</label><input id="mrn-paymode" type="text" placeholder="Bank / Cash" /></div>
              <div class="field"><label>Amount</label><input id="mrn-payamt" type="number" min="0" step="any" value="0" /></div>
              <div class="field"><label>Transaction No</label><input id="mrn-paytxn" type="text" /></div>
              <div class="field"><label>Transaction Date</label><input id="mrn-paydate" type="date" /></div>
              <div class="field" style="grid-column:1/-1"><label>Narration</label><input id="mrn-paynarr" type="text" /></div>
              <div class="field"><label>Advance Adjust</label><input id="mrn-adv" type="number" min="0" step="any" value="0" /></div>
            </div>
          </div>

          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Journal Voucher (optional)</strong>
            <div class="master-form-grid" style="margin-top:8px">
              <div class="field"><label>Account</label><input id="mrn-jv-acc" type="text" /></div>
              <div class="field"><label>Debit / Credit</label>
                <select id="mrn-jv-type"><option value="">—</option><option>Debit</option><option>Credit</option></select></div>
              <div class="field"><label>Amount</label><input id="mrn-jv-amt" type="number" min="0" step="any" value="0" /></div>
              <div class="field"><label>Txn No</label><input id="mrn-jv-txn" type="text" /></div>
              <div class="field"><label>Txn Date</label><input id="mrn-jv-date" type="date" /></div>
              <div class="field" style="grid-column:1/-1"><label>Narration</label><input id="mrn-jv-narr" type="text" /></div>
            </div>
          </div>

          <div class="row" style="gap:8px;margin-top:12px;grid-column:1/-1;flex-wrap:wrap">
            <button type="submit" class="btn btn-primary">Save MRN</button>
            <button type="button" class="btn btn-ghost" id="mrn-cancel">Reset / Cancel</button>
          </div>
        </form>
      </div>`;
    overlay.hidden = false;
    const charges = [];
    const close = () => {
      overlay.hidden = true;
    };
    const renderCharges = () => {
      const box = $("#mrn-charges");
      if (!box) return;
      if (!charges.length) {
        box.innerHTML = `<p class="hint">No other tax rows</p>`;
        return;
      }
      box.innerHTML = `<table class="data"><thead><tr><th>Nature</th><th>Type</th><th>Tax%</th><th>Amount</th><th></th></tr></thead><tbody>
        ${charges
          .map(
            (ch, i) => `<tr>
            <td>${ch.nature}</td><td>${ch.other_type}</td><td>${ch.tax_percent}</td><td>${money(ch.amount)}</td>
            <td><button type="button" class="btn btn-ghost btn-sm" data-mrn-ch-rm="${i}">✕</button></td>
          </tr>`
          )
          .join("")}
      </tbody></table>`;
      box.querySelectorAll("[data-mrn-ch-rm]").forEach((btn) => {
        btn.addEventListener("click", () => {
          charges.splice(Number(btn.dataset.mrnChRm), 1);
          renderCharges();
        });
      });
    };
    renderCharges();
    $("#mrn-add-charge")?.addEventListener("click", () => {
      const amount = Number($("#mrn-ch-amt")?.value || 0);
      if (!amount) return toast("Charge amount required");
      charges.push({
        nature: $("#mrn-ch-nature")?.value || "Add",
        other_type: $("#mrn-ch-type")?.value || "",
        tax_percent: Number($("#mrn-ch-pct")?.value || 0),
        amount,
      });
      if ($("#mrn-ch-amt")) $("#mrn-ch-amt").value = "";
      if ($("#mrn-ch-pct")) $("#mrn-ch-pct").value = "";
      renderCharges();
    });
    $("#mrn-x")?.addEventListener("click", close);
    $("#mrn-cancel")?.addEventListener("click", close);
    overlay.onclick = (e) => {
      if (e.target === overlay) close();
    };
    $("#mrn-form-el")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const payloadLines = [];
      overlay.querySelectorAll("tbody tr[data-idx]").forEach((tr) => {
        const idx = Number(tr.dataset.idx);
        const ln = lines[idx];
        if (!ln) return;
        const qty = Number(tr.querySelector(".mrn-qty")?.value || 0);
        if (qty <= 0) return;
        const gSel = tr.querySelector(".mrn-godown");
        payloadLines.push({
          product_id: ln.product_id,
          sku: ln.sku,
          qty,
          godown: gSel?.selectedOptions?.[0]?.dataset?.code || gSel?.value || "",
          batch_no: tr.querySelector(".mrn-batch")?.value || "",
          no_of_packing: tr.querySelector(".mrn-pack")?.value || "",
        });
      });
      if (!payloadLines.length) return toast("Receive Qty > 0 wale lines chahiye");
      const whId = Number($("#mrn-wh")?.value || 0) || null;
      const body = {
        mrn_type: $("#mrn-type")?.value || "PO",
        series_type: $("#mrn-series")?.value || "Main",
        receipt_date: $("#mrn-date")?.value || "",
        bill_no: $("#mrn-bill")?.value || "",
        bill_date: $("#mrn-bill-date")?.value || "",
        warehouse_id: whId,
        freight_mode: $("#mrn-freight")?.value || "",
        qc_status: $("#mrn-qc")?.value || "No",
        received_by: $("#mrn-recv")?.value || "",
        invoice_remarks: $("#mrn-remarks")?.value || "",
        remarks: $("#mrn-remarks")?.value || "",
        lot_no: $("#mrn-lot")?.value || "",
        gr_no: $("#mrn-gr")?.value || "",
        gr_date: $("#mrn-gr-date")?.value || "",
        total_wt: $("#mrn-wt")?.value || "",
        transport: $("#mrn-transport")?.value || "",
        trans_id: $("#mrn-transid")?.value || "",
        description: $("#mrn-desc")?.value || "",
        order_no: po.number || "",
        other_tax: Number($("#mrn-other-tax")?.value || 0),
        charges: charges.map((c) => ({ ...c })),
        payment_mode: $("#mrn-paymode")?.value || "",
        payment_amount: Number($("#mrn-payamt")?.value || 0),
        transaction_no: $("#mrn-paytxn")?.value || "",
        transaction_date: $("#mrn-paydate")?.value || "",
        payment_narration: $("#mrn-paynarr")?.value || "",
        advance_adjust: Number($("#mrn-adv")?.value || 0),
        jv_account: $("#mrn-jv-acc")?.value || "",
        jv_type: $("#mrn-jv-type")?.value || "",
        jv_amount: Number($("#mrn-jv-amt")?.value || 0),
        jv_txn_no: $("#mrn-jv-txn")?.value || "",
        jv_txn_date: $("#mrn-jv-date")?.value || "",
        jv_narration: $("#mrn-jv-narr")?.value || "",
        lines: payloadLines,
      };
      try {
        await onSubmit(body);
        close();
      } catch (err) {
        toast(err.message || "MRN failed");
      }
    });
  }

  /** SBAC Purchase Invoice from pending MRN (CreateMaterialReceipt.aspx mid=1747 — live page errors; fields from Material Receipt + Cash). */
  function openPiFromMrnForm(grn, onSubmit, opts = {}) {
    let overlay = document.getElementById("pi-form");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "pi-form";
      overlay.className = "saved-detail detail-drawer master-form-drawer";
      overlay.hidden = true;
      document.body.appendChild(overlay);
    }
    const gCustom = grn.custom || {};
    const lines = grn.lines || [];
    const rcmDefault = !!opts.rcm;
    const otherTypes = [
      "CASH DISCOUNT", "DISCOUNT", "INSURANCE", "INWARD FREIGHT", "LOCAL FREIGHT", "OUTWARD FREIGHT(FOR)",
      "LOADING", "PACKING AND FORWARDING CHARGES", "IGST 18 %",
    ];
    const lineRows = lines
      .map(
        (ln) => `<tr>
          <td>${ln.sku || ""} · ${ln.name || ""}</td>
          <td>${ln.qty || 0}</td>
          <td>${money(ln.rate || 0)}</td>
          <td>${ln.gst_rate || 0}</td>
          <td>${ln.discount_pct || 0}</td>
          <td>${ln.billing_unit || ln.uom || "NOS"}</td>
          <td>${money((ln.qty || 0) * (ln.rate || 0) * (1 - (ln.discount_pct || 0) / 100))}</td>
        </tr>`
      )
      .join("");
    overlay.innerHTML = `
      <div class="saved-detail__card glass detail-drawer__card master-form-card" style="width:min(960px,100vw)">
        <div class="saved-detail__hd">
          <div>
            <div class="saved-detail__eyebrow">Purchase · Invoice from MRN (SBAC exact fields)</div>
            <h3>Create Purchase Invoice${rcmDefault ? " (RCM)" : ""}</h3>
            <p class="hint" style="margin:.35rem 0 0">From MRN ${grn.number} · ${grn.vendor_name || ""} · books only (stock already in)</p>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" id="pi-x">Close</button>
        </div>
        <form id="pi-form-el" class="master-form-grid">
          <div class="field"><label>Series Type</label>
            <select id="pi-series"><option>Main</option></select></div>
          <div class="field"><label>Invoice No</label>
            <input type="text" value="Auto" disabled /></div>
          <div class="field"><label>Invoice Date *</label>
            <input id="pi-date" type="date" value="${new Date().toISOString().slice(0, 10)}" /></div>
          <div class="field"><label>Vendor</label>
            <input type="text" value="${grn.vendor_name || ""}" disabled /></div>
          <div class="field"><label>MRN / PO</label>
            <input type="text" value="${grn.number || ""} / ${grn.po_number || ""}" disabled /></div>
          <div class="field"><label>Bill No</label>
            <input id="pi-bill" type="text" value="${gCustom.bill_no || ""}" placeholder="Vendor Bill No" /></div>
          <div class="field"><label>Bill Date</label>
            <input id="pi-bill-date" type="date" value="${gCustom.bill_date || ""}" /></div>
          <div class="field"><label>Freight Mode</label>
            <select id="pi-freight"><option value="">—</option><option ${gCustom.freight_mode === "FOR" ? "selected" : ""}>FOR</option><option ${gCustom.freight_mode === "PAID" ? "selected" : ""}>PAID</option><option ${gCustom.freight_mode === "TO PAY" ? "selected" : ""}>TO PAY</option></select></div>
          <div class="field"><label>QC Status</label>
            <select id="pi-qc"><option ${gCustom.qc_status !== "Yes" ? "selected" : ""}>No</option><option ${gCustom.qc_status === "Yes" ? "selected" : ""}>Yes</option></select></div>
          <div class="field"><label>Received By</label>
            <input id="pi-recv" type="text" value="${gCustom.received_by || ""}" /></div>
          <div class="field"><label>RCM</label>
            <select id="pi-rcm"><option value="false" ${!rcmDefault ? "selected" : ""}>No</option><option value="true" ${rcmDefault ? "selected" : ""}>Yes</option></select></div>
          <div class="field" style="grid-column:1/-1"><label>Invoice Remarks</label>
            <input id="pi-remarks" type="text" value="${gCustom.invoice_remarks || gCustom.remarks || ""}" /></div>

          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Other Details</strong>
            <div class="master-form-grid" style="margin-top:8px">
              <div class="field"><label>Lot No</label><input id="pi-lot" type="text" value="${gCustom.lot_no || ""}" /></div>
              <div class="field"><label>GR No</label><input id="pi-gr" type="text" value="${gCustom.gr_no || ""}" /></div>
              <div class="field"><label>GR Date</label><input id="pi-gr-date" type="date" value="${gCustom.gr_date || ""}" /></div>
              <div class="field"><label>Total Wt</label><input id="pi-wt" type="text" value="${gCustom.total_wt || ""}" /></div>
              <div class="field"><label>Transport</label><input id="pi-transport" type="text" value="${gCustom.transport || ""}" /></div>
              <div class="field" style="grid-column:1/-1"><label>Description</label>
                <input id="pi-desc" type="text" value="${gCustom.description || ""}" /></div>
            </div>
          </div>

          <div class="field" style="grid-column:1/-1">
            <label>Item Details (from MRN)</label>
            <table class="data"><thead><tr>
              <th>Item</th><th>Qty</th><th>Rate</th><th>GST%</th><th>Disc%</th><th>Unit</th><th>Amt</th>
            </tr></thead><tbody>${lineRows || `<tr><td colspan="7">No lines</td></tr>`}</tbody></table>
          </div>

          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Other / Tax</strong>
            <div class="row" style="gap:8px;flex-wrap:wrap;margin-bottom:8px">
              <select id="pi-ch-nature"><option>Add</option><option>Less</option></select>
              <select id="pi-ch-type">${otherTypes.map((t) => `<option value="${t}">${t}</option>`).join("")}</select>
              <input id="pi-ch-pct" type="number" min="0" step="any" style="width:88px" placeholder="Tax %" />
              <input id="pi-ch-amt" type="number" min="0" step="any" style="width:100px" placeholder="Amount" />
              <button type="button" class="btn btn-accent btn-sm" id="pi-add-charge">AddTax</button>
            </div>
            <div id="pi-charges"></div>
            <div class="row" style="gap:12px;margin-top:8px">
              <div class="field" style="max-width:140px"><label>Other Tax</label>
                <input id="pi-other-tax" type="number" min="0" step="any" value="0" /></div>
              <div class="field" style="max-width:140px"><label>Round Off</label>
                <input id="pi-round" type="number" step="any" value="0" /></div>
            </div>
          </div>

          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Payment Method (optional)</strong>
            <div class="master-form-grid" style="margin-top:8px">
              <div class="field"><label>Mode</label><input id="pi-paymode" type="text" placeholder="Bank / Cash" /></div>
              <div class="field"><label>Amount</label><input id="pi-payamt" type="number" min="0" step="any" value="0" /></div>
              <div class="field"><label>Transaction No</label><input id="pi-paytxn" type="text" /></div>
              <div class="field"><label>Transaction Date</label><input id="pi-paydate" type="date" /></div>
              <div class="field" style="grid-column:1/-1"><label>Narration</label><input id="pi-paynarr" type="text" /></div>
              <div class="field"><label>Advance Adjust</label><input id="pi-adv" type="number" min="0" step="any" value="0" /></div>
            </div>
          </div>

          <div class="field" style="grid-column:1/-1;margin-top:8px;padding-top:10px;border-top:1px solid rgba(255,255,255,.08)">
            <strong style="font-size:13px">Journal Voucher (optional)</strong>
            <div class="master-form-grid" style="margin-top:8px">
              <div class="field"><label>Account</label><input id="pi-jv-acc" type="text" /></div>
              <div class="field"><label>Debit / Credit</label>
                <select id="pi-jv-type"><option value="">—</option><option>Debit</option><option>Credit</option></select></div>
              <div class="field"><label>Amount</label><input id="pi-jv-amt" type="number" min="0" step="any" value="0" /></div>
              <div class="field"><label>Txn No</label><input id="pi-jv-txn" type="text" /></div>
              <div class="field"><label>Txn Date</label><input id="pi-jv-date" type="date" /></div>
              <div class="field" style="grid-column:1/-1"><label>Narration</label><input id="pi-jv-narr" type="text" /></div>
            </div>
          </div>

          <div class="row" style="gap:8px;margin-top:12px;grid-column:1/-1;flex-wrap:wrap">
            <button type="submit" class="btn btn-primary">Save Purchase Invoice</button>
            <button type="button" class="btn btn-ghost" id="pi-cancel">Reset / Cancel</button>
          </div>
        </form>
      </div>`;
    overlay.hidden = false;
    const charges = [];
    const close = () => {
      overlay.hidden = true;
    };
    const renderCharges = () => {
      const box = $("#pi-charges");
      if (!box) return;
      if (!charges.length) {
        box.innerHTML = `<p class="hint">No other tax rows</p>`;
        return;
      }
      box.innerHTML = `<table class="data"><thead><tr><th>Nature</th><th>Type</th><th>Tax%</th><th>Amount</th><th></th></tr></thead><tbody>
        ${charges
          .map(
            (ch, i) => `<tr>
            <td>${ch.nature}</td><td>${ch.other_type}</td><td>${ch.tax_percent}</td><td>${money(ch.amount)}</td>
            <td><button type="button" class="btn btn-ghost btn-sm" data-pi-ch-rm="${i}">✕</button></td>
          </tr>`
          )
          .join("")}
      </tbody></table>`;
      box.querySelectorAll("[data-pi-ch-rm]").forEach((btn) => {
        btn.addEventListener("click", () => {
          charges.splice(Number(btn.dataset.piChRm), 1);
          renderCharges();
        });
      });
    };
    renderCharges();
    $("#pi-add-charge")?.addEventListener("click", () => {
      const amount = Number($("#pi-ch-amt")?.value || 0);
      if (!amount) return toast("Charge amount required");
      charges.push({
        nature: $("#pi-ch-nature")?.value || "Add",
        other_type: $("#pi-ch-type")?.value || "",
        tax_percent: Number($("#pi-ch-pct")?.value || 0),
        amount,
      });
      if ($("#pi-ch-amt")) $("#pi-ch-amt").value = "";
      if ($("#pi-ch-pct")) $("#pi-ch-pct").value = "";
      renderCharges();
    });
    $("#pi-x")?.addEventListener("click", close);
    $("#pi-cancel")?.addEventListener("click", close);
    overlay.onclick = (e) => {
      if (e.target === overlay) close();
    };
    $("#pi-form-el")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const body = {
        rcm: $("#pi-rcm")?.value === "true",
        series_type: $("#pi-series")?.value || "Main",
        invoice_date: $("#pi-date")?.value || "",
        bill_no: $("#pi-bill")?.value || "",
        bill_date: $("#pi-bill-date")?.value || "",
        freight_mode: $("#pi-freight")?.value || "",
        qc_status: $("#pi-qc")?.value || "No",
        received_by: $("#pi-recv")?.value || "",
        invoice_remarks: $("#pi-remarks")?.value || "",
        remarks: $("#pi-remarks")?.value || "",
        lot_no: $("#pi-lot")?.value || "",
        gr_no: $("#pi-gr")?.value || "",
        gr_date: $("#pi-gr-date")?.value || "",
        total_wt: $("#pi-wt")?.value || "",
        transport: $("#pi-transport")?.value || "",
        description: $("#pi-desc")?.value || "",
        other_tax: Number($("#pi-other-tax")?.value || 0),
        round_off: Number($("#pi-round")?.value || 0),
        charges: charges.map((c) => ({ ...c })),
        payment_mode: $("#pi-paymode")?.value || "",
        payment_amount: Number($("#pi-payamt")?.value || 0),
        transaction_no: $("#pi-paytxn")?.value || "",
        transaction_date: $("#pi-paydate")?.value || "",
        payment_narration: $("#pi-paynarr")?.value || "",
        advance_adjust: Number($("#pi-adv")?.value || 0),
        jv_account: $("#pi-jv-acc")?.value || "",
        jv_type: $("#pi-jv-type")?.value || "",
        jv_amount: Number($("#pi-jv-amt")?.value || 0),
        jv_txn_no: $("#pi-jv-txn")?.value || "",
        jv_txn_date: $("#pi-jv-date")?.value || "",
        jv_narration: $("#pi-jv-narr")?.value || "",
      };
      try {
        await onSubmit(body);
        close();
      } catch (err) {
        toast(err.message || "PI failed");
      }
    });
  }

  function _normalizeClientLines(lines) {
    return (lines || []).map((ln) => {
      const ordered = Number(ln.ordered_qty != null ? ln.ordered_qty : ln.qty || 0);
      const delivered = Number(ln.delivered_qty || 0);
      const bal = ln.bal_qty != null ? Number(ln.bal_qty) : Math.max(0, ordered - delivered);
      return { ...ln, ordered_qty: ordered, delivered_qty: delivered, bal_qty: bal };
    });
  }

  /** Store voucher: Issue / Receive / Transfer / Physical — SBAC exact fields. */
  function openStoreDocForm(title, { products, warehouses }, onSubmit, opts = {}) {
    let overlay = document.getElementById("store-doc-form");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "store-doc-form";
      overlay.className = "saved-detail detail-drawer master-form-drawer";
      overlay.hidden = true;
      document.body.appendChild(overlay);
    }
    const kind = opts.docKind || (opts.countMode ? "physical" : opts.showToWarehouse ? "transfer" : "issue");
    const isIssue = kind === "issue";
    const isRecv = kind === "receive";
    const isPhys = kind === "physical" || !!opts.countMode;
    const isXfer = kind === "transfer" || !!opts.showToWarehouse;
    const whOpts = (warehouses || [])
      .map((w) => `<option value="${w.id}">${w.code} · ${w.name}</option>`)
      .join("");
    const prodOpts = (products || [])
      .map((p) => {
        const rate = p.cost_price || p.sale_price || 0;
        return `<option value="${p.id}" data-sku="${p.sku}" data-name="${p.name}" data-uom="${p.uom || "NOS"}" data-rate="${rate}">${p.sku} · ${p.name}</option>`;
      })
      .join("");
    const units = ["BAG", "NOS", "BOX", "MTR", "PCS", "MT", "BUNDLE", "KGS", "COIL", "QTL", "PACKET", "LTR"];
    const today = new Date().toISOString().slice(0, 10);
    const deepHeader = isIssue
      ? `
          <div class="field"><label>Issue No</label><input type="text" value="Auto" disabled /></div>
          <div class="field"><label>Issue Date</label><input id="stf-date" type="date" value="${today}" /></div>
          <div class="field"><label>Issue Type</label><input id="stf-itype" type="text" placeholder="Issue Type" value="${opts.issueType || ""}" /></div>
          <div class="field"><label>Bill No</label><input id="stf-bill" type="text" placeholder="Bill No" /></div>
          <div class="field"><label>Party</label><input id="stf-party" type="text" placeholder="Party / Dept party" /></div>
          <div class="field"><label>Issued By</label><input id="stf-issuedby" type="text" placeholder="Issued By" /></div>
          <div class="field"><label>Item Issue Type</label>
            <select id="stf-iitype"><option value="">—</option><option>Consumable</option><option>Returnable</option></select></div>
          <div class="field"><label>Department</label><input id="stf-dept" type="text" placeholder="Production / Store / …" value="${opts.department || ""}" /></div>
          <div class="field"><label>Purpose</label><input id="stf-purpose" type="text" placeholder="${opts.purposePlaceholder || "Purpose"}" value="${opts.purpose || ""}" /></div>
        `
      : isRecv
        ? `
          <div class="field"><label>Receive No</label><input type="text" value="Auto" disabled /></div>
          <div class="field"><label>Received Date</label><input id="stf-date" type="date" value="${today}" /></div>
          <div class="field"><label>Receive Type</label><input id="stf-rtype" type="text" placeholder="Receive Type" /></div>
          <div class="field"><label>Bill No</label><input id="stf-bill" type="text" placeholder="Bill No" /></div>
          <div class="field"><label>Party</label><input id="stf-party" type="text" placeholder="Party" /></div>
          <div class="field"><label>Source</label>
            <select id="stf-purpose"><option value="return">return</option><option value="production">production</option><option value="other">other</option></select></div>
        `
      : isPhys
        ? `
          <div class="field"><label>Physical Stock No *</label><input type="text" value="Auto" disabled /></div>
          <div class="field"><label>Date</label><input id="stf-date" type="date" value="${today}" /></div>
          <div class="field"><label>Branch</label><input id="stf-branch" type="text" placeholder="Branch" /></div>
          <div class="field"><label>Store Keeper</label><input id="stf-keeper" type="text" placeholder="Store Keeper" /></div>
          <div class="field"><label>Project Manager</label><input id="stf-pm" type="text" placeholder="Project Manager" /></div>
        `
      : `
          <div class="field"><label>Department</label><input id="stf-dept" type="text" placeholder="Production / Store / …" /></div>
          <div class="field"><label>Purpose / Source</label><input id="stf-purpose" type="text" placeholder="${opts.purposePlaceholder || "Purpose"}" /></div>
        `;
    const lineExtras = isIssue || isRecv
      ? `
              <input id="stf-rate" type="number" min="0" step="any" style="width:90px" placeholder="Rate" />
              ${isRecv ? `<input id="stf-thaan" type="text" style="width:72px" placeholder="Thaan" />
              <input id="stf-disc" type="number" min="0" step="any" style="width:72px" placeholder="Disc%" />
              <input id="stf-elong" type="text" style="width:88px" placeholder="Elongation" />` : ""}
              <select id="stf-unit" style="width:80px">${units.map((u) => `<option value="${u}">${u}</option>`).join("")}</select>
        `
      : isPhys
        ? `
              <select id="stf-unit" style="width:80px">${units.map((u) => `<option value="${u}">${u}</option>`).join("")}</select>
              <input id="stf-desc" type="text" style="flex:1;min-width:100px" placeholder="Item desc" />
        `
      : "";
    overlay.innerHTML = `
      <div class="saved-detail__card glass detail-drawer__card master-form-card" style="width:min(${isIssue || isRecv || isPhys ? 860 : 680}px,100vw)">
        <div class="saved-detail__hd">
          <div>
            <div class="saved-detail__eyebrow">${opts.eyebrow || "Store · fresh entry"}</div>
            <h3>${title}</h3>
            <p class="hint" style="margin:.35rem 0 0">SBAC exact fields · Kanha design · no client data</p>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" id="stf-x">Close</button>
        </div>
        <form id="stf-form" class="master-form-grid">
          ${deepHeader}
          <div class="field"><label>${isXfer ? "From Godown" : isPhys ? "Store Name" : "Godown"} *</label>
            <select id="stf-wh" required>${whOpts || "<option value=''>No godown</option>"}</select></div>
          ${isXfer ? `<div class="field"><label>To Godown *</label><select id="stf-wh-to" required>${whOpts}</select></div>` : ""}
          <div class="field" style="grid-column:1/-1"><label>Remarks / Notes</label>
            <textarea id="stf-remarks" rows="2" placeholder="Notes"></textarea></div>
          ${isIssue || isRecv ? `<div class="field"><label>Advance</label><input id="stf-adv" type="number" min="0" step="any" value="0" /></div>` : ""}
          ${isRecv ? `<div class="field"><label>GST Amount</label><input id="stf-gstamt" type="number" min="0" step="any" value="0" /></div>` : ""}
          <div class="field" style="grid-column:1/-1">
            <label>Item Details</label>
            <div class="row" style="gap:8px;flex-wrap:wrap;margin-bottom:8px">
              <select id="stf-prod" style="flex:1;min-width:160px">${prodOpts || "<option value=''>No items</option>"}</select>
              <input id="stf-qty" type="number" min="0" step="any" value="1" style="width:100px" placeholder="${isPhys ? "Physical qty" : "Qty"}" />
              ${lineExtras}
              <button type="button" class="btn btn-accent btn-sm" id="stf-add">Add</button>
            </div>
            <div id="stf-lines" class="sdf-lines"></div>
            <p class="hint" id="stf-total" style="margin-top:6px">Total: —</p>
          </div>
          <div class="row" style="gap:8px;margin-top:12px;grid-column:1/-1">
            <button type="submit" class="btn btn-primary">${opts.saveLabel || "Save"}</button>
            <button type="button" class="btn btn-ghost" id="stf-cancel">Reset / Cancel</button>
          </div>
        </form>
      </div>`;
    overlay.hidden = false;
    const lines = [];
    const close = () => {
      overlay.hidden = true;
    };
    const renderLines = () => {
      const box = $("#stf-lines");
      if (!lines.length) {
        box.innerHTML = `<p class="hint">No lines — pick item + Add</p>`;
        $("#stf-total").textContent = "Total: —";
        return;
      }
      let tQty = 0;
      let tAmt = 0;
      const cols = isPhys
        ? "<th>Item</th><th>Unit</th><th>Physical Qty</th><th>Desc</th><th></th>"
        : isIssue || isRecv
          ? `<th>Item</th><th>Qty</th><th>Rate</th><th>Unit</th>${isRecv ? "<th>Disc%</th><th>Thaan</th>" : ""}<th>Amt</th><th></th>`
          : "<th>Item</th><th>Qty</th><th></th>";
      box.innerHTML = `<table class="data"><thead><tr>${cols}</tr></thead><tbody>
        ${lines
          .map((ln, i) => {
            const qty = isPhys ? ln.counted_qty : ln.qty;
            tQty += Number(qty || 0);
            const amt = Number(qty || 0) * Number(ln.rate || 0) * (1 - Number(ln.discount_pct || 0) / 100);
            tAmt += amt;
            if (isPhys) {
              return `<tr><td>${ln.sku} · ${ln.name}</td><td>${ln.uom || ""}</td><td>${ln.counted_qty}</td><td>${ln.item_description || ""}</td>
                <td><button type="button" class="btn btn-ghost btn-sm" data-rm="${i}">✕</button></td></tr>`;
            }
            if (isIssue || isRecv) {
              return `<tr><td>${ln.sku} · ${ln.name}</td><td>${ln.qty}</td><td>${money(ln.rate || 0)}</td><td>${ln.uom || ""}</td>
                ${isRecv ? `<td>${ln.discount_pct || 0}</td><td>${ln.thaan || ""}</td>` : ""}
                <td>${money(amt)}</td>
                <td><button type="button" class="btn btn-ghost btn-sm" data-rm="${i}">✕</button></td></tr>`;
            }
            return `<tr><td>${ln.sku} · ${ln.name}</td><td>${ln.qty}</td>
              <td><button type="button" class="btn btn-ghost btn-sm" data-rm="${i}">✕</button></td></tr>`;
          })
          .join("")}
      </tbody></table>`;
      $("#stf-total").textContent = `Total Qty: ${tQty} · Total Amt: ${money(tAmt)}`;
      box.querySelectorAll("[data-rm]").forEach((btn) => {
        btn.addEventListener("click", () => {
          lines.splice(Number(btn.dataset.rm), 1);
          renderLines();
        });
      });
    };
    renderLines();
    $("#stf-prod")?.addEventListener("change", () => {
      const opt = $("#stf-prod")?.selectedOptions?.[0];
      if (!opt) return;
      if ($("#stf-rate")) $("#stf-rate").value = opt.dataset.rate || "";
      if ($("#stf-unit") && opt.dataset.uom) $("#stf-unit").value = opt.dataset.uom;
    });
    $("#stf-add")?.addEventListener("click", () => {
      const opt = $("#stf-prod")?.selectedOptions?.[0];
      if (!opt?.value) return toast("Select item");
      const qty = Number($("#stf-qty").value || 0);
      if (qty < 0 || (!isPhys && qty <= 0)) return toast("Invalid qty");
      const row = {
        product_id: Number(opt.value),
        sku: opt.dataset.sku || "",
        name: opt.dataset.name || "",
        uom: ($("#stf-unit") && $("#stf-unit").value) || opt.dataset.uom || "NOS",
        rate: Number($("#stf-rate")?.value || opt.dataset.rate || 0),
        discount_pct: Number($("#stf-disc")?.value || 0),
        thaan: $("#stf-thaan")?.value || "",
        elongation: $("#stf-elong")?.value || "",
        item_description: $("#stf-desc")?.value || "",
      };
      if (isPhys) row.counted_qty = qty;
      else row.qty = qty;
      lines.push(row);
      if ($("#stf-desc")) $("#stf-desc").value = "";
      if ($("#stf-disc")) $("#stf-disc").value = "";
      if ($("#stf-thaan")) $("#stf-thaan").value = "";
      if ($("#stf-elong")) $("#stf-elong").value = "";
      renderLines();
    });
    $("#stf-x")?.addEventListener("click", close);
    $("#stf-cancel")?.addEventListener("click", close);
    overlay.onclick = (e) => {
      if (e.target === overlay) close();
    };
    $("#stf-form")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      if (!lines.length) return toast("Add at least one line");
      const payload = {
        warehouse_id: Number($("#stf-wh").value || 0) || null,
        from_warehouse_id: Number($("#stf-wh").value || 0) || null,
        to_warehouse_id: isXfer ? Number($("#stf-wh-to").value || 0) || null : null,
        department: $("#stf-dept")?.value || "",
        purpose: $("#stf-purpose")?.value || "",
        source: $("#stf-purpose")?.value || opts.defaultSource || "return",
        remarks: $("#stf-remarks")?.value || "",
        notes: $("#stf-remarks")?.value || "",
        indent_id: opts.indentId || null,
        issue_date: $("#stf-date")?.value || "",
        receive_date: $("#stf-date")?.value || "",
        count_date: $("#stf-date")?.value || "",
        issue_type: $("#stf-itype")?.value || "",
        receive_type: $("#stf-rtype")?.value || "",
        bill_no: $("#stf-bill")?.value || "",
        party_name: $("#stf-party")?.value || "",
        issued_by: $("#stf-issuedby")?.value || "",
        item_issue_type: $("#stf-iitype")?.value || "",
        advance: Number($("#stf-adv")?.value || 0),
        gst_amount: Number($("#stf-gstamt")?.value || 0),
        branch: $("#stf-branch")?.value || "",
        store_keeper: $("#stf-keeper")?.value || "",
        project_manager: $("#stf-pm")?.value || "",
        lines: lines.map((l) => ({ ...l })),
      };
      try {
        await onSubmit(payload);
        close();
      } catch (err) {
        toast(err.message || "Save failed");
      }
    });
  }

  /** Accounts voucher drawer — Payment / Receipt / Contra / Journal / CN / DN. */
  function openVoucherForm(voucherType, { accounts, centres }, onSubmit, opts = {}) {
    let overlay = document.getElementById("voucher-form");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "voucher-form";
      overlay.className = "saved-detail detail-drawer master-form-drawer";
      overlay.hidden = true;
      document.body.appendChild(overlay);
    }
    const leaf = (accounts || []).filter((a) => !a.is_group);
    const accOpts = leaf
      .map((a) => `<option value="${a.code}">${a.code} · ${a.name}</option>`)
      .join("");
    const ccOpts = (centres || [])
      .map((c) => `<option value="${c.code}">${c.code} · ${c.name}</option>`)
      .join("");
    const labels = {
      payment: { title: "Payment Voucher", from: "Paid from (Bank/Cash)", to: "Paid to (AP/Expense)", amt: true },
      receipt: { title: "Receipt Voucher", from: "Received from (AR/Party)", to: "Deposit to (Bank/Cash)", amt: true },
      contra: { title: "Contra Voucher", from: "From (Bank/Cash)", to: "To (Cash/Bank)", amt: true },
      journal: { title: "Journal Voucher", from: "Credit account", to: "Debit account", amt: true },
      credit_note: { title: "Credit Note", from: "From", to: "To", amt: true },
      debit_note: { title: "Debit Note", from: "From", to: "To", amt: true },
      sales: { title: "Sales Voucher", from: "From", to: "To", amt: true },
      purchase: { title: "Purchase Voucher", from: "From", to: "To", amt: true },
    };
    const meta = labels[voucherType] || labels.journal;
    const showAccounts = ["payment", "receipt", "contra", "journal", "credit_note", "debit_note"].includes(voucherType);
    const defFrom = opts.from_account || (voucherType === "receipt" ? "1300" : voucherType === "payment" ? "1200" : voucherType === "contra" ? "1200" : "4100");
    const defTo = opts.to_account || (voucherType === "receipt" ? "1200" : voucherType === "payment" ? "2100" : voucherType === "contra" ? "1100" : "1300");
    const today = new Date().toISOString().slice(0, 10);
    overlay.innerHTML = `
      <div class="saved-detail__card glass detail-drawer__card master-form-card" style="width:min(720px,100vw)">
        <div class="saved-detail__hd">
          <div>
            <div class="saved-detail__eyebrow">${opts.eyebrow || "Accounts · fresh voucher"}</div>
            <h3>${meta.title}</h3>
            <p class="hint" style="margin:.35rem 0 0">SBAC Voucherdenominations fields · Kanha Books · no client data</p>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" id="vf-x">Close</button>
        </div>
        <form id="vf-form" class="master-form-grid">
          <div class="field"><label>Voucher Type</label>
            <input type="text" value="${meta.title}" disabled /></div>
          <div class="field"><label>Voucher No</label>
            <input type="text" value="Auto" disabled /></div>
          <div class="field"><label>Voucher Date</label>
            <input id="vf-date" type="date" value="${today}" /></div>
          <div class="field"><label>Bill / On Account</label>
            <select id="vf-rtype"><option>Bill</option><option>On Account</option></select></div>
          <div class="field"><label>Party Name</label>
            <input id="vf-party" type="text" placeholder="Customer / Vendor" value="${opts.party || ""}" /></div>
          ${showAccounts ? `
          <div class="field"><label>${meta.from}</label>
            <select id="vf-from">${accOpts}</select></div>
          <div class="field"><label>${meta.to}</label>
            <select id="vf-to">${accOpts}</select></div>` : ""}
          <div class="field"><label>Amount *</label>
            <input id="vf-amt" type="number" min="0.01" step="any" required placeholder="0.00" /></div>
          <div class="field"><label>Cost Centre</label>
            <select id="vf-cc"><option value="">—</option>${ccOpts}</select></div>
          <div class="field"><label>Currency</label>
            <select id="vf-cur"><option>Indian Rupee (INR)</option><option>USD</option><option>Euro (EURO)</option></select></div>
          <div class="field"><label>Exchange Rate</label>
            <input id="vf-rate" type="number" min="0" step="any" value="1" /></div>
          <div class="field"><label>Convert Amount</label>
            <input id="vf-conamt" type="number" min="0" step="any" value="0" /></div>
          <div class="field"><label>Cheque / Ref No</label>
            <input id="vf-chq" type="text" placeholder="Cheque No" /></div>
          <div class="field"><label>Cheque Date</label>
            <input id="vf-chq-date" type="date" /></div>
          <div class="field"><label>Adjust Amount</label>
            <input id="vf-adj" type="number" min="0" step="any" value="0" /></div>
          <div class="field" style="grid-column:1/-1"><label>Sub Narration</label>
            <textarea id="vf-subnar" rows="2" placeholder="Line narration"></textarea></div>
          <div class="field" style="grid-column:1/-1"><label>Narration</label>
            <textarea id="vf-nar" rows="2" placeholder="Narration">${opts.narration || ""}</textarea></div>
          <div class="field" style="grid-column:1/-1"><label>Remarks</label>
            <textarea id="vf-remarks" rows="2" placeholder="Remarks"></textarea></div>
          <div class="row" style="gap:8px;margin-top:12px;grid-column:1/-1;flex-wrap:wrap">
            <button type="submit" class="btn btn-primary">Submit</button>
            <button type="button" class="btn btn-ghost" id="vf-cancel">Reset / Cancel</button>
          </div>
        </form>
      </div>`;
    overlay.hidden = false;
    if (showAccounts) {
      $("#vf-from").value = defFrom;
      $("#vf-to").value = defTo;
      if (![...$("#vf-from").options].some((o) => o.value === defFrom) && $("#vf-from").options[0]) {
        $("#vf-from").selectedIndex = 0;
      }
      if (![...$("#vf-to").options].some((o) => o.value === defTo) && $("#vf-to").options[0]) {
        $("#vf-to").selectedIndex = Math.min(1, $("#vf-to").options.length - 1);
      }
    }
    const close = () => {
      overlay.hidden = true;
    };
    $("#vf-x")?.addEventListener("click", close);
    $("#vf-cancel")?.addEventListener("click", close);
    overlay.onclick = (e) => {
      if (e.target === overlay) close();
    };
    $("#vf-form")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const amount = Number($("#vf-amt").value || 0);
      if (amount <= 0) return toast("Amount required");
      const payload = {
        voucher_type: voucherType,
        party_name: $("#vf-party").value || "",
        amount,
        narration: $("#vf-nar").value || "",
        entry_date: $("#vf-date").value || null,
        cost_centre: $("#vf-cc")?.value || "",
        from_account: showAccounts ? ($("#vf-from")?.value || "") : "",
        to_account: showAccounts ? ($("#vf-to")?.value || "") : "",
        receipt_type: $("#vf-rtype")?.value || "Bill",
        cheque_no: $("#vf-chq")?.value || "",
        cheque_date: $("#vf-chq-date")?.value || "",
        currency: $("#vf-cur")?.value || "Indian Rupee (INR)",
        exchange_rate: Number($("#vf-rate")?.value || 1),
        convert_amount: Number($("#vf-conamt")?.value || 0),
        sub_narration: $("#vf-subnar")?.value || "",
        adjust_amount: Number($("#vf-adj")?.value || 0),
        remarks: $("#vf-remarks")?.value || "",
      };
      try {
        await onSubmit(payload);
        close();
      } catch (err) {
        toast(err.message || "Post failed");
      }
    });
  }

  function openDetail(title, data, opts = {}) {
    let overlay = document.getElementById("saved-detail");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "saved-detail";
      overlay.className = "saved-detail detail-drawer";
      overlay.hidden = true;
      document.body.appendChild(overlay);
    }
    const eyebrow = opts.eyebrow || "Details";
    let rows = "";
    if (Array.isArray(data)) {
      rows = data.map(([k, v]) => `<div class="saved-detail__row"><span>${k}</span><strong>${v}</strong></div>`).join("");
    } else if (data && typeof data === "object") {
      rows = Object.entries(data)
        .filter(([, v]) => v !== undefined && v !== null && typeof v !== "object")
        .slice(0, 24)
        .map(([k, v]) => `<div class="saved-detail__row"><span>${k}</span><strong>${v}</strong></div>`)
        .join("");
    } else if (typeof data === "string") {
      rows = `<div class="hint">${data}</div>`;
    }
    overlay.innerHTML = `
      <div class="saved-detail__card glass detail-drawer__card">
        <div class="saved-detail__hd">
          <div>
            <div class="saved-detail__eyebrow">${eyebrow}</div>
            <h3>${title}</h3>
          </div>
          <button type="button" class="btn btn-ghost btn-sm" id="saved-detail-x">Close</button>
        </div>
        <div class="saved-detail__grid">${rows || `<div class="hint">No fields</div>`}</div>
        ${opts.html || ""}
        ${opts.showJson !== false && data && typeof data === "object" && !Array.isArray(data)
          ? `<pre class="report-pre saved-detail__json">${JSON.stringify(data, null, 2)}</pre>`
          : ""}
      </div>`;
    overlay.hidden = false;
    $("#saved-detail-x")?.addEventListener("click", () => { overlay.hidden = true; });
    overlay.onclick = (e) => { if (e.target === overlay) overlay.hidden = true; };
  }

  /** Pure SVG charts — no CDN dependency */
  function chartBars(items, opts = {}) {
    const key = opts.key || "amount";
    const labelKey = opts.label || "name";
    const w = opts.width || 420;
    const h = opts.height || 160;
    const pad = 28;
    const data = (items || []).slice(0, 12);
    if (!data.length) return `<p class="hint">No chart data</p>`;
    const vals = data.map((i) => Number(i[key]) || 0);
    const max = Math.max(...vals, 1);
    const gap = 8;
    const barW = (w - pad * 2 - gap * (data.length - 1)) / data.length;
    const bars = data.map((i, idx) => {
      const v = Number(i[key]) || 0;
      const bh = Math.max(2, (v / max) * (h - pad - 20));
      const x = pad + idx * (barW + gap);
      const y = h - pad - bh;
      const lab = String(i[labelKey] || i.month || i.name || idx).slice(0, 8);
      return `<rect class="ch-bar" x="${x}" y="${y}" width="${barW}" height="${bh}" rx="4" data-i="${idx}"/>
        <text x="${x + barW / 2}" y="${h - 8}" text-anchor="middle" class="ch-lab">${lab}</text>`;
    }).join("");
    return `<div class="chart-card"><svg class="chart-svg" viewBox="0 0 ${w} ${h}" role="img">${bars}</svg></div>`;
  }

  function chartDonut(segments, opts = {}) {
    const size = opts.size || 160;
    const data = (segments || []).filter((s) => Number(s.value) > 0);
    if (!data.length) return `<p class="hint">No chart data</p>`;
    const total = data.reduce((a, s) => a + Number(s.value), 0) || 1;
    const cx = size / 2;
    const cy = size / 2;
    const r = size * 0.36;
    const stroke = size * 0.14;
    let ang = -Math.PI / 2;
    const colors = ["#2563eb", "#0d9488", "#d97706", "#db2777", "#7c3aed", "#059669"];
    const arcs = data.map((s, i) => {
      const frac = Number(s.value) / total;
      const sweep = frac * Math.PI * 2;
      const x1 = cx + r * Math.cos(ang);
      const y1 = cy + r * Math.sin(ang);
      ang += sweep;
      const x2 = cx + r * Math.cos(ang);
      const y2 = cy + r * Math.sin(ang);
      const large = sweep > Math.PI ? 1 : 0;
      return `<path d="M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}" fill="none" stroke="${colors[i % colors.length]}" stroke-width="${stroke}" stroke-linecap="butt"/>`;
    }).join("");
    const legend = data.map((s, i) =>
      `<span class="ch-leg"><i style="background:${colors[i % colors.length]}"></i>${s.label} · ${moneyFit(s.value)}</span>`
    ).join("");
    return `<div class="chart-card chart-card--donut">
      <svg class="chart-svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">${arcs}
        <text x="${cx}" y="${cy + 4}" text-anchor="middle" class="ch-center">${moneyFit(total)}</text>
      </svg>
      <div class="ch-legend">${legend}</div>
    </div>`;
  }

  function chartLine(points, opts = {}) {
    const w = opts.width || 420;
    const h = opts.height || 140;
    const pad = 24;
    const data = (points || []).slice(-12);
    if (data.length < 2) return chartBars(data, opts);
    const vals = data.map((p) => Number(p.amount ?? p.value ?? 0));
    const max = Math.max(...vals, 1);
    const min = Math.min(...vals, 0);
    const span = Math.max(max - min, 1);
    const step = (w - pad * 2) / (data.length - 1);
    const coords = data.map((p, i) => {
      const v = Number(p.amount ?? p.value ?? 0);
      const x = pad + i * step;
      const y = h - pad - ((v - min) / span) * (h - pad * 2);
      return [x, y];
    });
    const poly = coords.map(([x, y]) => `${x},${y}`).join(" ");
    const area = `${pad},${h - pad} ${poly} ${coords[coords.length - 1][0]},${h - pad}`;
    return `<div class="chart-card"><svg class="chart-svg" viewBox="0 0 ${w} ${h}">
      <polygon points="${area}" class="ch-area"/>
      <polyline points="${poly}" class="ch-line" fill="none"/>
      ${coords.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3.5" class="ch-dot"/>`).join("")}
    </svg></div>`;
  }

  function viewToggle(id, active = "chart") {
    return `<div class="view-toggle" data-view-for="${id}">
      <button type="button" class="view-toggle__btn ${active === "chart" ? "on" : ""}" data-view="chart">Chart</button>
      <button type="button" class="view-toggle__btn ${active === "table" ? "on" : ""}" data-view="table">Details</button>
    </div>`;
  }

  function bindViewToggle(root, id) {
    const wrap = root.querySelector(`[data-view-for="${id}"]`);
    if (!wrap) return;
    wrap.querySelectorAll("[data-view]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.getAttribute("data-view");
        wrap.querySelectorAll(".view-toggle__btn").forEach((b) => b.classList.toggle("on", b === btn));
        root.querySelectorAll(`[data-view-panel="${id}"]`).forEach((p) => {
          p.hidden = p.getAttribute("data-mode") !== mode;
        });
      });
    });
  }

  function flowSave(title, data, tip) {
    openDetail(title, data, {
      eyebrow: "Saved · working flow",
      showJson: false,
      html: tip ? `<p class="hint" style="margin-top:12px">${tip}</p>` : `<p class="hint" style="margin-top:12px">Data database me save ho gaya. Related tabs me ab dikhega.</p>`,
    });
  }

  function bindThemeStudio() {
    const btn = $("#btn-theme");
    const panel = $("#theme-panel");
    if (!btn || !panel) return;
    const current = document.documentElement.dataset.theme || "light";
    const prefs = getUiPrefs();
    panel.innerHTML = `
      <div class="theme-panel__title">My workspace look</div>
      <div class="theme-panel__hint">Har employee apna theme save kare — sirf aapke account pe apply hoga.</div>
      <div class="theme-grid">
        ${THEME_PRESETS.map((t) => `
          <button type="button" class="theme-swatch ${t.id === current ? "on" : ""}" data-theme-id="${t.id}" title="${t.name}">
            <span class="theme-swatch__chip" style="background:${t.swatch}"></span>
            <span class="theme-swatch__name">${t.name}</span>
          </button>`).join("")}
      </div>
      <div class="theme-opts">
        <label>Density
          <select id="theme-density">
            <option value="comfortable" ${prefs.density === "comfortable" ? "selected" : ""}>Comfortable</option>
            <option value="compact" ${prefs.density === "compact" ? "selected" : ""}>Compact</option>
          </select>
        </label>
        <label>Corners
          <select id="theme-radius">
            <option value="soft" ${prefs.radius === "soft" ? "selected" : ""}>Soft</option>
            <option value="sharp" ${prefs.radius === "sharp" ? "selected" : ""}>Sharp</option>
          </select>
        </label>
      </div>
      <button type="button" class="btn btn-primary btn-sm" id="theme-save" style="width:100%;margin-top:10px">Save to my profile</button>
    `;

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      panel.hidden = !panel.hidden;
    });
    panel.addEventListener("click", (e) => e.stopPropagation());
    document.addEventListener("click", () => { panel.hidden = true; });

    panel.querySelectorAll("[data-theme-id]").forEach((el) => {
      el.addEventListener("click", () => {
        const id = el.getAttribute("data-theme-id");
        document.documentElement.dataset.theme = id;
        panel.querySelectorAll(".theme-swatch").forEach((s) => s.classList.toggle("on", s === el));
      });
    });
    $("#theme-density")?.addEventListener("change", (e) => {
      document.documentElement.dataset.density = e.target.value;
    });
    $("#theme-radius")?.addEventListener("change", (e) => {
      document.documentElement.dataset.radius = e.target.value;
    });
    $("#theme-save")?.addEventListener("click", async () => {
      const theme = document.documentElement.dataset.theme || "light";
      const density = $("#theme-density")?.value || "comfortable";
      const radius = $("#theme-radius")?.value || "soft";
      document.documentElement.dataset.density = density;
      document.documentElement.dataset.radius = radius;
      localStorage.setItem("kanha_theme", theme);
      localStorage.setItem("kanha_ui_prefs", JSON.stringify({ density, radius }));
      try {
        const res = await API.put("/api/auth/theme", { theme, density, radius });
        if (API.user) {
          API.user.theme = res.theme || theme;
          API.user.ui_prefs = res.ui_prefs || { density, radius };
          localStorage.setItem("kanha_user", JSON.stringify(API.user));
        }
        toast("Theme saved to your profile");
      } catch (err) {
        toast("Saved locally · " + (err.message || ""));
      }
      panel.hidden = true;
    });
  }

  function bindMobileNav() {
    const burger = $("#nav-burger");
    const backdrop = $("#nav-backdrop");
    const side = $("#sidebar");
    if (!burger || !side) return;
    const open = () => {
      document.body.classList.add("nav-open");
      if (backdrop) backdrop.hidden = false;
    };
    const close = () => {
      document.body.classList.remove("nav-open");
      if (backdrop) backdrop.hidden = true;
    };
    burger.addEventListener("click", () => {
      if (document.body.classList.contains("nav-open")) close();
      else open();
    });
    backdrop?.addEventListener("click", close);
    side.querySelectorAll("a.nav-item").forEach((a) => a.addEventListener("click", close));
  }

  function bindAiCore() {
    const orb = $("#ai-orb");
    const dock = $("#ai-dock");
    const chat = $("#ai-dock-chat");
    const input = $("#ai-dock-input");
    const chips = $("#ai-dock-chips");
    const actions = $("#ai-dock-actions");
    if (!orb || !dock || !chat) return;

    let lastDraft = null;

    const persist = () => {
      try {
        localStorage.setItem("kanha_ai_dock_chat", chat.innerHTML.slice(0, 12000));
      } catch (_) {}
    };

    const renderChips = (list) => {
      if (!chips) return;
      const items = list || [
        "ERP modules guide",
        "Outstanding receivables",
        "Chase overdue invoices",
        "Pending SO → challan → invoice",
        "Low stock reorder",
        "GST register summary",
        "Draft WhatsApp chase",
        "HR leave + payroll status",
        "MIS sales vs last month",
      ];
      chips.innerHTML = items.map((s) => `<button type="button" class="ai-dock__chip" data-chip="${s}">${s}</button>`).join("");
      chips.querySelectorAll("[data-chip]").forEach((btn) => {
        btn.addEventListener("click", () => {
          if (input) input.value = btn.dataset.chip || "";
          send();
        });
      });
    };

    const push = (who, text, html) => {
      const b = document.createElement("div");
      b.className = `bubble ${who}`;
      if (html) b.innerHTML = html;
      else b.textContent = text;
      chat.appendChild(b);
      chat.scrollTop = chat.scrollHeight;
      persist();
    };

    if (!chat.dataset.ready) {
      const saved = localStorage.getItem("kanha_ai_dock_chat");
      if (saved) {
        chat.innerHTML = saved;
      } else {
        push(
          "bot",
          null,
          "Kanha Core online — poori ERP ki operational jaankari. Personal details (naam, phone, email) share nahi hote. Modules, sales, stock, GST, agents poochho."
        );
      }
      chat.dataset.ready = "1";
    }
    renderChips();

    const showActions = (r) => {
      if (!actions) return;
      actions.hidden = true;
      actions.innerHTML = "";
      const parts = [];
      if (r.action && r.action.href) {
        parts.push(`<a class="btn btn-ghost btn-sm" href="${r.action.href}">Open module →</a>`);
      }
      if (r.whatsapp_draft) {
        lastDraft = r.whatsapp_draft;
        parts.push(`<button type="button" class="btn btn-accent btn-sm" id="ai-dock-wa-send">Send WhatsApp draft</button>`);
      }
      if (!parts.length) return;
      actions.innerHTML = parts.join(" ");
      actions.hidden = false;
      $("#ai-dock-wa-send")?.addEventListener("click", async () => {
        if (!lastDraft) return;
        try {
          const phone = lastDraft.to_phone || prompt("Customer phone (E.164)", "+919876543210");
          if (!phone) return;
          const res = await API.post("/api/comms/whatsapp/send", {
            to_phone: phone,
            body: lastDraft.body,
            template: lastDraft.template || "invoice_overdue",
          });
          toast(res.message || "WhatsApp sent");
          push("bot", `WA sent · status ${res.status || "sent"}`);
        } catch (e) {
          toast(e.message || "Send failed");
        }
      });
    };

    const open = () => {
      dock.hidden = false;
      orb.classList.add("is-open");
      document.body.classList.add("ai-dock-open");
      setTimeout(() => input?.focus(), 120);
    };
    const close = () => {
      dock.hidden = true;
      orb.classList.remove("is-open");
      document.body.classList.remove("ai-dock-open");
    };

    orb.addEventListener("click", () => {
      if (dock.hidden) open();
      else close();
    });
    $("#ai-dock-close")?.addEventListener("click", close);

    orb.addEventListener("pointermove", (e) => {
      const r = orb.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      orb.style.setProperty("--tilt-x", `${(-y * 24).toFixed(2)}deg`);
      orb.style.setProperty("--tilt-y", `${(x * 28).toFixed(2)}deg`);
    }, { passive: true });
    orb.addEventListener("pointerleave", () => {
      orb.style.setProperty("--tilt-x", "0deg");
      orb.style.setProperty("--tilt-y", "0deg");
    });

    const send = async () => {
      const msg = (input?.value || "").trim();
      if (!msg) return;
      push("me", msg);
      input.value = "";
      if (actions) actions.hidden = true;
      try {
        const r = await API.post("/api/ai/chat", { message: msg });
        const modeEl = $("#ai-dock-mode");
        if (modeEl) modeEl.textContent = r.live ? `LLM · ${r.provider || "live"}` : "Kanha Core · full ERP";
        const replyHtml = (r.reply || "…").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
        push("bot", null, replyHtml);
        if (r.suggestions && r.suggestions.length) renderChips(r.suggestions);
        showActions(r);
      } catch (err) {
        push("bot", String(err.message || err));
      }
    };
    $("#ai-dock-send")?.addEventListener("click", send);
    input?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") send();
    });
  }

  function bindCoreControl(opts = {}) {
    const forceShow = !!opts.forceShow;
    const fromLogin = !!opts.fromLogin;
    const btn = $("#core-ctrl-btn") || (fromLogin ? $("#login-core-btn") : null);
    const dock = $("#core-ctrl-dock");
    const chat = $("#core-ctrl-chat");
    const score = $("#core-ctrl-score");
    const input = $("#core-ctrl-input");
    if (!dock || !chat) return;

    // Prevent double-binding on the same dock instance
    if (dock.dataset.bound === "1") {
      if (fromLogin || forceShow) {
        const enter = $("#core-ctrl-enter");
        if (enter) enter.hidden = false;
        dock.hidden = false;
      }
      return;
    }
    dock.dataset.bound = "1";

    // Owner-only: superadmin or access probe (shell button)
    if (btn && btn.id === "core-ctrl-btn") {
      (async () => {
        try {
          const a = await API.get("/api/core-control/access");
          if (a.owner) btn.hidden = false;
        } catch (_) {
          if (API.user?.is_superadmin) btn.hidden = false;
        }
      })();
    }

    const push = (who, text) => {
      const b = document.createElement("div");
      b.className = `bubble ${who}`;
      b.innerHTML = String(text || "").replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
      chat.appendChild(b);
      chat.scrollTop = chat.scrollHeight;
    };

    const paintScore = (n, confidence) => {
      if (!score) return;
      const v = Number(n);
      const conf = confidence || score.dataset.confidence || "";
      if (Number.isFinite(v)) {
        score.textContent = conf ? `Health ${v}/100 · ${conf}` : `Health ${v}/100`;
        score.style.setProperty("--score-pct", `${Math.max(0, Math.min(100, v))}%`);
      } else {
        score.textContent = "—";
        score.style.setProperty("--score-pct", "0%");
      }
      if (conf) score.dataset.confidence = conf;
      score.dataset.tone = v >= 85 ? "ok" : v >= 60 ? "warn" : "bad";
    };

    const open = () => {
      dock.hidden = false;
      const ai = $("#ai-dock");
      if (ai) ai.hidden = true;
      if (!chat.dataset.ready) {
        push("bot", "Core Control — NEVER delete / NEVER purge. Sirf sudhaar. Pehle Preview → Safe fix. Risky unlock alag Confirm. Full scan = deep diagnose. Password bhoola: Reset PW.");
        chat.dataset.ready = "1";
      }
    };
    const close = () => { dock.hidden = true; };

    if (btn && btn.id === "core-ctrl-btn" && !btn.dataset.coreBound) {
      btn.dataset.coreBound = "1";
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (dock.hidden) open();
        else close();
      });
    }
    const closeBtn = $("#core-ctrl-close");
    if (closeBtn && !closeBtn.dataset.coreBound) {
      closeBtn.dataset.coreBound = "1";
      closeBtn.addEventListener("click", close);
    }

    const scan = async () => {
      push("me", "Scan ERP health");
      try {
        const r = await API.get("/api/core-control/diagnose");
        paintScore(r.health_score, r.confidence);
        const lines = (r.issues || []).slice(0, 8).map((i) => `• [${i.severity}/${i.safety || ""}/${i.category || ""}] ${i.where}: ${i.why}`).join("\n") || "• No blocking issues";
        const pol = r.policy?.message || "Never deletes data.";
        push("bot", `${r.summary}\n${lines}\n\n${pol}`);
      } catch (e) {
        push("bot", e.message || "Scan failed — owner only");
      }
    };

    const fullScan = async () => {
      push("me", "Full strength scan");
      try {
        const r = await API.get("/api/core-control/full");
        paintScore(r.health_score, r.confidence);
        const pulse = r.module_pulse || {};
        const pulseTxt = Object.entries(pulse).map(([k, v]) => `${k}=${v}`).join(", ");
        const integ = r.integrity || {};
        const hist = (r.history || []).slice(-3).map((h) => `• ${h.action} ${h.score_before}→${h.score_after}`).join("\n") || "• No history yet";
        const issues = ((r.diagnose && r.diagnose.issues) || []).slice(0, 6)
          .map((i) => `• [${i.severity}/${i.category || ""}] ${i.why}`).join("\n") || "• Clean";
        push("bot", `${r.summary || ""}\nPulse: ${pulseTxt}\nIntegrity: paid>total=${integ.invoices_paid_gt_total || 0} · SO>7d=${integ.sales_orders_pending_over_7d || 0} · failed aging=${integ.failed_entries_aging_3d || 0}\n\nFindings:\n${issues}\n\nRecent:\n${hist}\n\nNever delete · preview first.`);
      } catch (e) {
        push("bot", e.message || "Full scan failed");
      }
    };

    const history = async () => {
      push("me", "Action history");
      try {
        const r = await API.get("/api/core-control/history");
        const lines = (r.history || []).slice(-15).reverse().map((h) =>
          `• ${h.timestamp || ""} · ${h.action} · ${h.score_before}→${h.score_after} · ${h.user_email || ""}`
        ).join("\n") || "• Empty history";
        push("bot", `Last ${Math.min(15, (r.history || []).length)} of ${r.count || 0} actions:\n${lines}`);
      } catch (e) {
        push("bot", e.message || "History failed");
      }
    };

    const preview = async () => {
      push("me", "Preview drawbacks (no change)");
      try {
        const r = await API.get("/api/core-control/preview");
        paintScore(r.health_score, r.confidence);
        const lines = (r.plan || []).map((p) => `• ${p.fix} · auto=${p.would_run_in_default_autofix} · ${(p.drawbacks || [])[0] || ""}`).join("\n") || "• Empty plan";
        push("bot", `${r.message}\n${lines}`);
      } catch (e) {
        push("bot", e.message || "Preview failed");
      }
    };

    const autofix = async () => {
      push("me", "Safe autofix (no delete)");
      try {
        const r = await API.post("/api/core-control/autofix", { confirm_risky: false });
        paintScore(r.after_score, r.confidence);
        const applied = (r.applied || []).map((a) => `• ${a.message || a.fix}`).join("\n") || "• Nothing safe pending";
        const skip = (r.skipped_needs_confirm || []).map((s) => `• SKIP ${s.fix}: ${(s.drawbacks || [])[0] || s.reason}`).join("\n");
        push("bot", `${r.message}\n${applied}${skip ? `\n\nNeeds confirm:\n${skip}` : ""}`);
      } catch (e) {
        push("bot", e.message || "Autofix failed");
      }
    };

    const confirmRisky = async () => {
      if (!confirm("Risky fixes (blackout unlock / period unlock / approve pending SO / demo density).\nSQLite backup pehle hoga.\nData DELETE nahi hoga — lekin books freeze / approvals bypass ho sakte hain.\nContinue?")) return;
      push("me", "Confirm risky fixes");
      try {
        const r = await API.post("/api/core-control/autofix", { confirm_risky: true, run_agents: false });
        paintScore(r.after_score, r.confidence);
        if (r.refused) {
          push("bot", `${r.message}\nBackup: ${JSON.stringify(r.backup || {})}`);
          return;
        }
        const bak = r.backup?.ok ? `Backup OK · ${r.backup.path || ""}` : (r.backup_warning || (r.backup ? `Backup note: ${r.backup.note || r.backup.error || ""}` : ""));
        const applied = (r.applied || []).map((a) => `• ${a.message || a.fix}${a.rolled_back ? " (ROLLED BACK)" : ""}`).join("\n") || "• None";
        push("bot", `${r.message}\n${bak ? bak + "\n" : ""}${applied}`);
      } catch (e) {
        push("bot", e.message || "Confirm failed");
      }
    };

    const resetPw = async () => {
      const email = prompt("User email jiska password reset karna hai:", "admin@kanhaerp.com");
      if (!email) return;
      const newPassword = prompt("Naya password (min 8, prod me letters+numbers):", "Welcome9x");
      if (!newPassword) return;
      if (!confirm(`Reset password for ${email}?\nUser delete nahi hoga.`)) return;
      push("me", `Reset password ${email}`);
      try {
        const r = await API.post("/api/core-control/reset-password", {
          email: email.trim(),
          new_password: newPassword,
        });
        push("bot", r.message || "Password updated");
      } catch (e) {
        push("bot", e.message || "Reset failed");
      }
    };

    const send = async () => {
      const msg = (input?.value || "").trim();
      if (!msg) return;
      push("me", msg);
      input.value = "";
      try {
        const r = await API.post("/api/core-control/chat", { message: msg });
        if (r.result?.after_score != null) paintScore(r.result.after_score, r.result.confidence);
        if (r.diagnose?.health_score != null) paintScore(r.diagnose.health_score, r.diagnose.confidence);
        if (r.preview?.health_score != null) paintScore(r.preview.health_score, r.preview.confidence);
        if (r.full?.health_score != null) paintScore(r.full.health_score, r.full.confidence);
        push("bot", r.reply || "…");
      } catch (e) {
        push("bot", e.message || "Denied");
      }
    };

    const wire = (id, fn) => {
      const el = document.getElementById(id);
      if (el && !el.dataset.coreBound) {
        el.dataset.coreBound = "1";
        el.addEventListener("click", fn);
      }
    };
    wire("core-ctrl-scan", scan);
    wire("core-ctrl-full", fullScan);
    wire("core-ctrl-history", history);
    wire("core-ctrl-preview", preview);
    wire("core-ctrl-fix", autofix);
    wire("core-ctrl-confirm", confirmRisky);
    wire("core-ctrl-reset-pw", resetPw);
    wire("core-ctrl-send", send);
    wire("core-ctrl-enter", () => { location.hash = "#/dashboard"; });

    if (input && !input.dataset.coreBound) {
      input.dataset.coreBound = "1";
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
    }

    if (fromLogin) {
      const enter = $("#core-ctrl-enter");
      if (enter) enter.hidden = false;
      open();
    }
  }

  async function loadDemoBanner() {
    const el = $("#demo-banner");
    const ha = $("#ha-banner");
    if (el) {
      try {
        const h = await API.get("/api/health");
        if (h.demo_mode !== false) el.hidden = false;
        state.cluster = h.cluster || state.cluster;
        if (h.cluster && h.cluster.primary_url) API.setPrimaryUrl(h.cluster.primary_url);
        if (ha && h.cluster && h.cluster.enabled) {
          if (h.cluster.role === "replica") {
            ha.hidden = false;
            ha.innerHTML = `HOT REPLICA — reads/sync only · writes → <a href="${h.cluster.primary_url}">${h.cluster.primary_url}</a> · <a href="#/ha">Resilience</a>`;
          } else {
            ha.hidden = false;
            ha.innerHTML = `PRIMARY writer · node <b>${h.cluster.node_id || ""}</b> · mirrors ${h.cluster.mirrors || 0} · <a href="#/ha">Risks & failover</a>`;
          }
        }
        if (h.blackout && h.blackout.active) {
          if (ha) {
            ha.hidden = false;
            ha.style.background = "rgba(185,28,28,.18)";
            ha.innerHTML = `⛔ <b>EMERGENCY BLACKOUT</b> — entries locked · data frozen in portable packs · <a href="#/ha">Unlock / Download ERP</a>`;
          }
          if (el) {
            el.hidden = false;
            el.textContent = "BLACKOUT MODE — no new entries until Resilience → Unlock";
          }
        }
      } catch {
        el.hidden = false;
      }
    }
  }

  async function loadNotifications() {
    const countEl = $("#notif-count");
    const panel = $("#notif-panel");
    const btn = $("#btn-notif");
    if (!btn || !panel) return;
    try {
      const rows = await API.get("/api/notifications");
      const unread = (rows || []).filter((n) => !n.read).length;
      if (countEl) countEl.textContent = String(unread || 0);
      panel.innerHTML = (rows || []).length
        ? rows.slice(0, 8).map((n) => `<button type="button" class="notif-item ${n.read ? "" : "unread"}" data-notif-id="${n.id}">
            <strong>${n.title}</strong><span>${n.body || ""}</span>
          </button>`).join("")
        : `<div class="notif-item"><strong>No alerts</strong><span>You're all caught up.</span></div>`;
      panel.querySelectorAll("[data-notif-id]").forEach((item) => {
        item.addEventListener("click", async () => {
          const id = item.getAttribute("data-notif-id");
          if (!id) return;
          try {
            await API.post(`/api/notifications/${id}/read`);
            item.classList.remove("unread");
            loadNotifications();
          } catch {}
        });
      });
    } catch {
      if (countEl) countEl.textContent = "0";
    }
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      panel.hidden = !panel.hidden;
    });
    panel.addEventListener("click", (e) => e.stopPropagation());
    document.addEventListener("click", () => { if (panel) panel.hidden = true; });
  }

  function table(headers, rows, emptyHint) {
    const empty = emptyHint || "No data — use + buttons above to create, or keep DEMO_MODE for seeded samples.";
    return `<div class="data-frame"><table><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
      <tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="${headers.length}">${empty}</td></tr>`}</tbody></table></div>`;
  }

  async function pageDashboard(el) {
    const [d, board, actions, alerts, cmp, guide] = await Promise.all([
      API.get("/api/dashboard"),
      API.get("/api/ops-board/pending").catch(() => ({ tiles: [], total_pending: 0, kanha_value: [] })),
      API.get("/api/ops-board/actions").catch(() => ({ order: [], sales: [], purchase: [] })),
      API.get("/api/advanced/smart-alerts").catch(() => ({ alerts: [], health_score: 100, alert_count: 0 })),
      API.get("/api/advanced/mis/compare").catch(() => null),
      API.get("/api/advanced/flow-guide").catch(() => ({ flows: [] })),
    ]);
    const k = d.kpis;
    const tiles = board.tiles || [];
    const alertTone = (lv) => (lv === "critical" ? "rose" : lv === "warn" ? "amber" : "blue");
    el.innerHTML = `
      <div class="kpi-grid">
        ${kpiCard("Revenue", "", { icon: "₹", tone: "blue", raw: k.revenue })}
        ${kpiCard("Outstanding", "", { icon: "◉", tone: "amber", raw: k.outstanding })}
        ${kpiCard("Inventory Value", "", { icon: "▣", tone: "violet", raw: k.inventory_value })}
        ${kpiCard("Health score", String(alerts.health_score ?? "—"), { icon: "★", tone: "emerald", meta: `${alerts.alert_count || 0} alerts` })}
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Data flow map (demo training)</h2></div>
        <div class="panel-bd">
          <p class="hint">${guide.tip || "Click each flow to open the working desk."}</p>
          <div class="action-hub" style="margin-top:8px">
            ${(guide.flows || []).map((f) => `
              <a class="action-chip" href="${f.href}" title="${(f.steps || []).join(' → ')}">${f.name}</a>
            `).join("")}
          </div>
          <div class="grid-2" style="margin-top:12px">
            ${(guide.flows || []).slice(0, 4).map((f) => `
              <div class="hint"><b>${f.name}:</b> ${(f.steps || []).join(" → ")}</div>
            `).join("")}
          </div>
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Smart alerts</h2>
        ${viewToggle("dash-alerts", "chart")}
        <a class="btn btn-ghost btn-sm" href="#/payments-ops">Ageing</a>
        <a class="btn btn-accent btn-sm" href="#/whatsapp">WhatsApp chase</a></div>
        <div class="panel-bd">
          <div data-view-panel="dash-alerts" data-mode="chart">
            ${chartDonut([
              { label: "Critical", value: (alerts.alerts || []).filter((a) => a.level === "critical").length || 0.01 },
              { label: "Warn", value: (alerts.alerts || []).filter((a) => a.level === "warn").length || 0.01 },
              { label: "Info", value: (alerts.alerts || []).filter((a) => a.level === "info").length || 0.01 },
            ], { size: 150 })}
            ${cmp ? chartLine([
              { name: cmp.last_month, amount: cmp.sales?.last },
              { name: cmp.this_month, amount: cmp.sales?.this },
            ], { width: 360, height: 120 }) : ""}
          </div>
          <div data-view-panel="dash-alerts" data-mode="table" hidden>
          ${(alerts.alerts || []).length
            ? `<div class="pending-grid">${(alerts.alerts || []).map((a) => `
                <a class="pending-tile pending-tile--${alertTone(a.level)}" href="${a.href || "#/"}">
                  <span class="pending-tile__label">${a.title}</span>
                  <strong class="pending-tile__count" style="font-size:13px;font-weight:600">${a.detail || a.action || ""}</strong>
                </a>`).join("")}</div>`
            : `<p class="hint">All clear — no critical ops alerts.</p>`}
          </div>
          ${cmp ? `<p class="hint" style="margin-top:10px">MIS ${cmp.this_month}: sales ${money(cmp.sales?.this)} (${cmp.sales?.change_pct}% vs last) · purchase ${money(cmp.purchase?.this)} (${cmp.purchase?.change_pct}%)</p>` : ""}
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Ops Pending Board</h2>
        <a class="btn btn-ghost btn-sm" href="#/ops-board">Full board</a></div>
        <div class="panel-bd">
          <div class="pending-grid">
            ${tiles.map((t) => `
              <a class="pending-tile pending-tile--${t.tone || "blue"}" href="${t.href || "#/ops-board"}">
                <span class="pending-tile__label">${t.label}</span>
                <strong class="pending-tile__count">${t.count}</strong>
              </a>`).join("") || "<p class='hint'>No pending tiles</p>"}
          </div>
          <p class="hint" style="margin-top:10px">Total pending signals: <b>${board.total_pending || 0}</b></p>
        </div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Recent Invoices</h2>
          ${viewToggle("dash-inv", "table")}</div>
          <div class="panel-bd">
            <div data-view-panel="dash-inv" data-mode="chart">
              ${chartBars((d.recent_invoices || []).map((i) => ({ name: i.number, amount: i.total })), { label: "name", key: "amount", width: 380 })}
            </div>
            <div data-view-panel="dash-inv" data-mode="table">
              ${table(["Number", "Total", "Paid", "Status", ""], d.recent_invoices.map((i) => [
                i.number, money(i.total), money(i.paid), `<span class="pill">${i.status}</span>`,
                `<button class="btn btn-ghost btn-sm" data-inv-d="${i.number}" data-tot="${i.total}" data-paid="${i.paid}" data-st="${i.status}">Details</button>`,
              ]))}
            </div>
          </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Action hubs</h2></div><div class="panel-bd action-hub">
          <div><h3>Order</h3>${(actions.order || []).map((a) => `<a class="action-chip" href="${a.href}">${a.label}</a>`).join("")}</div>
          <div><h3>Sales</h3>${(actions.sales || []).map((a) => `<a class="action-chip" href="${a.href}">${a.label}</a>`).join("")}</div>
          <div><h3>Purchase</h3>${(actions.purchase || []).map((a) => `<a class="action-chip" href="${a.href}">${a.label}</a>`).join("")}</div>
        </div></div>
      </div>
      <div class="panel glass"><div class="panel-bd">Pending approvals: <b>${d.approvals_pending}</b> · Open orders: <b>${k.open_orders}</b>
        · <a href="#/books">Kanha Books</a> · <a href="#/mis">MIS</a> · <a href="#/followup">Followups</a>
      </div></div>`;
    bindViewToggle(el, "dash-alerts");
    bindViewToggle(el, "dash-inv");
    el.querySelectorAll("[data-inv-d]").forEach((btn) => {
      btn.addEventListener("click", () => openDetail(`Invoice ${btn.dataset.invD}`, {
        number: btn.dataset.invD,
        total: btn.dataset.tot,
        paid: btn.dataset.paid,
        status: btn.dataset.st,
      }, { eyebrow: "Invoice detail", showJson: false }));
    });
  }

  async function pageOpsBoard(el) {
    const board = await API.get("/api/ops-board/pending");
    const actions = await API.get("/api/ops-board/actions");
    el.innerHTML = `
      ${moduleIntro("Ops Pending Board", "Command-center pending cards — live counts, WhatsApp/Agents linked. Never deletes data.")}
      <div class="pending-grid pending-grid--lg">
        ${(board.tiles || []).map((t) => `
          <a class="pending-tile pending-tile--${t.tone || "blue"}" href="${t.href}">
            <span class="pending-tile__label">${t.label}</span>
            <strong class="pending-tile__count">${t.count}</strong>
          </a>`).join("")}
      </div>
      <div class="grid-3" style="margin-top:16px">
        <div class="panel glass"><div class="panel-hd"><h2>Order Module</h2></div><div class="panel-bd action-hub">
          ${(actions.order || []).map((a) => `<a class="action-chip" href="${a.href}">${a.label}</a>`).join("")}
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Sales</h2></div><div class="panel-bd action-hub">
          ${(actions.sales || []).map((a) => `<a class="action-chip" href="${a.href}">${a.label}</a>`).join("")}
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Purchase</h2></div><div class="panel-bd action-hub">
          ${(actions.purchase || []).map((a) => `<a class="action-chip" href="${a.href}">${a.label}</a>`).join("")}
        </div></div>
      </div>
      <div class="panel glass" style="margin-top:12px"><div class="panel-bd">
        <b>Kanha value stack:</b> ${(board.kanha_value || []).join(" · ")}
      </div></div>`;
  }

  async function pageVisit(el) {
    const rows = await API.get("/api/visits");
    el.innerHTML = `
      ${moduleIntro("Visit Planner & Management", "Field visits — plan, search, mark done. Better UX than classic ASP forms.")}
      <div class="panel glass"><div class="panel-hd"><h2>Plan visit</h2></div><div class="panel-bd grid-2">
        <div class="field"><label>Executive</label><input id="vis-exec" placeholder="Name" /></div>
        <div class="field"><label>Client</label><input id="vis-client" placeholder="Party name" /></div>
        <div class="field"><label>Contact</label><input id="vis-contact" /></div>
        <div class="field"><label>Purpose</label><input id="vis-purpose" /></div>
        <div class="field"><label>Date</label><input id="vis-date" type="date" /></div>
        <div class="field"><label>Time</label><input id="vis-time" placeholder="11:00" /></div>
        <button class="btn btn-primary" id="vis-save" type="button">Submit plan</button>
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Visit list</h2></div><div class="panel-bd">
        ${table(
          ["Plan", "Executive", "Client", "Purpose", "Date", "Status", ""],
          rows.map((r) => [
            r.plan_no, r.executive_name, r.client_name, r.purpose || "—", r.visit_date || "—",
            `<span class="pill">${r.status}</span>`,
            `${r.status === "planned" ? `<button class="btn btn-ghost btn-sm" data-vis-done="${r.id}">Done</button>` : ""}
             <button class="btn btn-ghost btn-sm" data-vis-d="${r.id}">Details</button>`,
          ])
        )}
      </div></div>`;
    $("#vis-save")?.addEventListener("click", async () => {
      try {
        const payload = {
          executive_name: $("#vis-exec")?.value,
          client_name: $("#vis-client")?.value,
          contact_person: $("#vis-contact")?.value,
          purpose: $("#vis-purpose")?.value,
          visit_date: $("#vis-date")?.value || null,
          visit_time: $("#vis-time")?.value,
        };
        const r = await API.post("/api/visits", payload);
        toast("Visit planned");
        flowSave(`Visit ${r.plan_no || r.id}`, { ...payload, id: r.id, plan_no: r.plan_no }, "Field Visit list me dikhega · Done se close karo · Followup tab se chase.");
        pageVisit(el);
      } catch (e) { toast(e.message); }
    });
    document.querySelectorAll("[data-vis-done]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await API.post(`/api/visits/${btn.getAttribute("data-vis-done")}/status?status=done`, {});
        pageVisit(el);
      });
    });
    document.querySelectorAll("[data-vis-d]").forEach((btn) => {
      const row = rows.find((x) => String(x.id) === btn.getAttribute("data-vis-d"));
      btn.addEventListener("click", () => openDetail(row?.plan_no || "Visit", row || {}, { eyebrow: "Visit detail", showJson: false }));
    });
  }

  async function pageFieldTasks(el) {
    const rows = await API.get("/api/field-tasks");
    el.innerHTML = `
      ${moduleIntro("Task Desk", "Assign · track · close — priority, due date, remarks.")}
      <div class="panel glass"><div class="panel-hd"><h2>Add task</h2></div><div class="panel-bd grid-2">
        <div class="field"><label>Task*</label><input id="ft-title" /></div>
        <div class="field"><label>To (assignee)</label><input id="ft-to" /></div>
        <div class="field"><label>Client</label><input id="ft-client" /></div>
        <div class="field"><label>Priority</label>
          <select id="ft-pri"><option>High</option><option selected>Medium</option><option>Low</option></select></div>
        <div class="field"><label>Due</label><input id="ft-due" type="date" /></div>
        <button class="btn btn-primary" id="ft-save" type="button">Submit</button>
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Open tasks</h2></div><div class="panel-bd">
        ${table(
          ["ID", "Task", "To", "Client", "Priority", "Due", "Status", ""],
          rows.map((r) => [
            r.id, r.title, r.assignee_name, r.client_name || "—", r.priority, r.due_date || "—",
            `<span class="pill">${r.status}</span>`,
            r.status !== "done"
              ? `<button class="btn btn-ghost btn-sm" data-ft-done="${r.id}">Done</button> <button class="btn btn-ghost btn-sm" data-ft-d="${r.id}">Details</button>`
              : `<button class="btn btn-ghost btn-sm" data-ft-d="${r.id}">Details</button>`,
          ])
        )}
      </div></div>`;
    $("#ft-save")?.addEventListener("click", async () => {
      try {
        const payload = {
          title: $("#ft-title")?.value,
          assignee_name: $("#ft-to")?.value,
          client_name: $("#ft-client")?.value,
          priority: $("#ft-pri")?.value,
          due_date: $("#ft-due")?.value || null,
        };
        const r = await API.post("/api/field-tasks", payload);
        toast("Task created");
        flowSave(`Task #${r.id}`, payload, "Task Desk list me open status dikhega · Done se close.");
        pageFieldTasks(el);
      } catch (e) { toast(e.message); }
    });
    document.querySelectorAll("[data-ft-done]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await API.post(`/api/field-tasks/${btn.getAttribute("data-ft-done")}/update`, { status: "done", last_remark: "Closed from desk" });
        pageFieldTasks(el);
      });
    });
    document.querySelectorAll("[data-ft-d]").forEach((btn) => {
      const row = rows.find((x) => String(x.id) === btn.getAttribute("data-ft-d"));
      btn.addEventListener("click", () => openDetail(row?.title || "Task", row || {}, { eyebrow: "Task detail", showJson: false }));
    });
  }

  async function pageFollowup(el) {
    const rows = await API.get("/api/followups");
    el.innerHTML = `
      ${moduleIntro("Followups", "Order / payment / lead followups with next date — export-ready list.")}
      <div class="panel glass"><div class="panel-hd"><h2>Log followup</h2></div><div class="panel-bd grid-2">
        <div class="field"><label>Type</label>
          <select id="fu-type"><option value="order">Order</option><option value="payment">Payment</option><option value="lead">Lead</option><option value="visit">Visit</option></select></div>
        <div class="field"><label>Party*</label><input id="fu-party" /></div>
        <div class="field"><label>Contact</label><input id="fu-contact" /></div>
        <div class="field"><label>Phone</label><input id="fu-phone" /></div>
        <div class="field"><label>Next followup</label><input id="fu-next" type="date" /></div>
        <div class="field"><label>Remarks</label><input id="fu-remarks" /></div>
        <button class="btn btn-primary" id="fu-save" type="button">Save</button>
        <a class="btn btn-accent" href="#/whatsapp">Chase on WhatsApp</a>
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Followup report</h2><span class="hint">${rows.length} records</span></div><div class="panel-bd">
        ${table(
          ["Party", "Contact", "Type", "Remarks", "Next", "Executive", "Status", ""],
          rows.map((r) => [
            r.party_name, r.contact_person || "—", r.followup_type, r.remarks || "—",
            r.next_followup_date || "—", r.executive_name || "—", `<span class="pill">${r.status}</span>`,
            r.status === "open"
              ? `<button class="btn btn-ghost btn-sm" data-fu-close="${r.id}">Close</button> <button class="btn btn-ghost btn-sm" data-fu-d="${r.id}">Details</button>`
              : `<button class="btn btn-ghost btn-sm" data-fu-d="${r.id}">Details</button>`,
          ])
        )}
      </div></div>`;
    $("#fu-save")?.addEventListener("click", async () => {
      try {
        const payload = {
          followup_type: $("#fu-type")?.value,
          party_name: $("#fu-party")?.value,
          contact_person: $("#fu-contact")?.value,
          contact_no: $("#fu-phone")?.value,
          next_followup_date: $("#fu-next")?.value || null,
          remarks: $("#fu-remarks")?.value,
        };
        const r = await API.post("/api/followups", payload);
        toast("Followup saved");
        flowSave(`Followup ${r.id || ""}`, payload, "Followup report me dikhega · WhatsApp chase link use karo · Close se band.");
        pageFollowup(el);
      } catch (e) { toast(e.message); }
    });
    document.querySelectorAll("[data-fu-close]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await API.post(`/api/followups/${btn.getAttribute("data-fu-close")}/close`, {});
        pageFollowup(el);
      });
    });
    document.querySelectorAll("[data-fu-d]").forEach((btn) => {
      const row = rows.find((x) => String(x.id) === btn.getAttribute("data-fu-d"));
      btn.addEventListener("click", () => openDetail(row?.party_name || "Followup", row || {}, { eyebrow: "Followup detail", showJson: false }));
    });
  }

  async function pagePaymentsOps(el) {
    const [reqs, out, ar, ap, chase] = await Promise.all([
      API.get("/api/payment-requests"),
      API.get("/api/outstanding/summary"),
      API.get("/api/advanced/ageing/receivables").catch(() => ({ parties: [], buckets: {}, total: 0 })),
      API.get("/api/advanced/ageing/payables").catch(() => ({ parties: [], buckets: {}, total: 0 })),
      API.get("/api/advanced/chase/overdue").catch(() => ({ drafts: [], count: 0 })),
    ]);
    el.innerHTML = `
      ${moduleIntro("Payment Requests & Outstanding", "Request → approve → paid + AR/AP ageing + WhatsApp chase drafts.")}
      <div class="kpi-grid">
        ${kpiCard("Buyer outstanding", "", { icon: "₹", tone: "amber", raw: out.buyer_total })}
        ${kpiCard("Vendor outstanding", "", { icon: "₹", tone: "violet", raw: out.vendor_total })}
        ${kpiCard("AR ageing", "", { icon: "₹", tone: "rose", raw: ar.total })}
        ${kpiCard("Chase drafts", String(chase.count || 0), { icon: "#", tone: "blue" })}
      </div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>AR ageing</h2>
          ${viewToggle("ar-age", "chart")}</div><div class="panel-bd">
          <div data-view-panel="ar-age" data-mode="chart">
            ${chartDonut([
              { label: "0-30", value: ar.buckets?.["0-30"] || 0 },
              { label: "31-60", value: ar.buckets?.["31-60"] || 0 },
              { label: "61-90", value: ar.buckets?.["61-90"] || 0 },
              { label: "90+", value: ar.buckets?.["90+"] || 0 },
            ])}
          </div>
          <div data-view-panel="ar-age" data-mode="table" hidden>
          <p class="hint">0-30 ${money(ar.buckets?.["0-30"])} · 31-60 ${money(ar.buckets?.["31-60"])} · 61-90 ${money(ar.buckets?.["61-90"])} · 90+ ${money(ar.buckets?.["90+"])}</p>
          ${table(["Party", "Bal", "0-30", "31-60", "61-90", "90+", ""], (ar.parties || []).slice(0, 12).map((p) => [
            p.party, money(p.balance), money(p["0-30"]), money(p["31-60"]), money(p["61-90"]), money(p["90+"]),
            `<button class="btn btn-ghost btn-sm" data-ar="${p.party}">Details</button>`,
          ]))}
          </div>
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>AP ageing</h2>
          ${viewToggle("ap-age", "chart")}</div><div class="panel-bd">
          <div data-view-panel="ap-age" data-mode="chart">
            ${chartDonut([
              { label: "0-30", value: ap.buckets?.["0-30"] || 0 },
              { label: "31-60", value: ap.buckets?.["31-60"] || 0 },
              { label: "61-90", value: ap.buckets?.["61-90"] || 0 },
              { label: "90+", value: ap.buckets?.["90+"] || 0 },
            ])}
          </div>
          <div data-view-panel="ap-age" data-mode="table" hidden>
          <p class="hint">Total ${money(ap.total)}</p>
          ${table(["Party", "Bal", "0-30", "31-60", "61-90", "90+"], (ap.parties || []).slice(0, 12).map((p) => [
            p.party, money(p.balance), money(p["0-30"]), money(p["31-60"]), money(p["61-90"]), money(p["90+"])
          ]))}
          </div>
        </div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>WhatsApp chase drafts (overdue)</h2>
        <div class="row" style="gap:6px;flex-wrap:wrap">
          <button type="button" class="btn btn-primary btn-sm" id="chase-send-all">Send all chases</button>
          <a class="btn btn-accent btn-sm" href="#/whatsapp">Open WhatsApp OS</a>
          <a class="btn btn-ghost btn-sm" href="#/extras">Extras hub</a>
        </div></div>
        <div class="panel-bd">${table(["Invoice", "Party", "Days", "Balance", "Draft", ""], (chase.drafts || []).slice(0, 10).map((d, idx) => [
          d.invoice, d.party, d.days_overdue, money(d.balance),
          `<span class="hint">${(d.whatsapp_draft || "").slice(0, 60)}…</span>`,
          `<button class="btn btn-accent btn-sm" data-chase-send="${idx}">Send WA</button>`,
        ]))}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>New payment request</h2></div><div class="panel-bd grid-2">
        <div class="field"><label>Party</label><input id="prq-party" /></div>
        <div class="field"><label>Amount</label><input id="prq-amt" type="number" /></div>
        <div class="field"><label>Purpose</label><input id="prq-purpose" /></div>
        <button class="btn btn-primary" id="prq-save" type="button">Submit request</button>
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Requests</h2></div><div class="panel-bd">
        ${table(
          ["No", "Party", "Amount", "Purpose", "Status", ""],
          reqs.map((r) => [
            r.number, r.party_name, money(r.amount), r.purpose || "—", `<span class="pill">${r.status}</span>`,
            `${r.status === "pending"
              ? `<button class="btn btn-ghost btn-sm" data-prq-ok="${r.id}">Approve</button>
                 <button class="btn btn-accent btn-sm" data-prq-paid="${r.id}">Paid</button>`
              : (r.status === "approved"
                ? `<button class="btn btn-accent btn-sm" data-prq-paid="${r.id}">Mark paid</button>`
                : "")}
             <button class="btn btn-ghost btn-sm" data-prq-d="${r.id}">Details</button>`,
          ])
        )}
      </div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Buyer outstanding</h2></div><div class="panel-bd">
          ${table(["Party", "Ref", "Balance"], (out.buyer_outstanding || []).map((x) => [x.party, x.ref, money(x.balance)]))}
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Vendor outstanding</h2></div><div class="panel-bd">
          ${table(["Party", "Ref", "Balance"], (out.vendor_outstanding || []).map((x) => [x.party, x.ref, money(x.balance)]))}
        </div></div>
      </div>`;
    $("#prq-save")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/payment-requests", {
          party_name: $("#prq-party")?.value,
          amount: Number($("#prq-amt")?.value || 0),
          purpose: $("#prq-purpose")?.value,
        });
        toast("Payment request created");
        flowSave(r.number || "Payment request", r, "Requests list me pending · Approve → Mark paid · Outstanding update.");
        pagePaymentsOps(el);
      } catch (e) { toast(e.message); }
    });
    $("#chase-send-all")?.addEventListener("click", async () => {
      if (!(chase.drafts || []).length) return toast("No overdue drafts");
      try {
        const r = await API.post("/api/advanced/chase/send-all", { limit: 10 });
        toast(r.message || `Sent ${r.sent}`);
        flowSave("Chase batch", r, "WhatsApp OS outbox + notification bell me dikhega.");
        pagePaymentsOps(el);
      } catch (e) { toast(e.message || "Chase batch failed"); }
    });
    el.querySelectorAll("[data-chase-send]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const d = (chase.drafts || [])[Number(btn.dataset.chaseSend)];
        if (!d) return;
        try {
          const r = await API.post("/api/advanced/chase/send", {
            invoice: d.invoice,
            phone: d.phone || "",
          });
          toast(r.message || "Chase sent");
          flowSave(`Chase ${d.invoice}`, r, "WhatsApp OS · bell notification.");
        } catch (e) { toast(e.message || "Send failed"); }
      });
    });
    bindViewToggle(el, "ar-age");
    bindViewToggle(el, "ap-age");
    el.querySelectorAll("[data-ar]").forEach((btn) => {
      const p = (ar.parties || []).find((x) => x.party === btn.dataset.ar);
      btn.addEventListener("click", () => openDetail(btn.dataset.ar, p || {}, { eyebrow: "AR party", showJson: false }));
    });
    el.querySelectorAll("[data-prq-d]").forEach((btn) => {
      const row = reqs.find((x) => String(x.id) === btn.dataset.prqD);
      btn.addEventListener("click", () => openDetail(row?.number || "Request", row || {}, { eyebrow: "Payment request", showJson: false }));
    });
    document.querySelectorAll("[data-prq-ok]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const r = await API.post(`/api/payment-requests/${btn.getAttribute("data-prq-ok")}/process?status=approved`, {});
        flowSave("Request approved", r || {}, "Ab Mark paid dabao · Vendor/buyer outstanding clear hoga.");
        pagePaymentsOps(el);
      });
    });
    document.querySelectorAll("[data-prq-paid]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const r = await API.post(`/api/payment-requests/${btn.getAttribute("data-prq-paid")}/process?status=paid`, {});
        flowSave("Marked paid", r || {}, "Outstanding summary + ageing refresh · Books payment voucher linked ho sakta hai.");
        pagePaymentsOps(el);
      });
    });
  }

  async function pageIndents(el) {
    const [inds, prs] = await Promise.all([
      API.get("/api/indents"),
      API.get("/api/purchase/requisitions"),
    ]);
    el.innerHTML = `
      ${moduleIntro("Indents & Purchase Requisitions", "Store indent → PR → PO chain — full live path.")}
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Create indent</h2>
          <button class="btn btn-primary btn-sm" id="ind-save">+ Indent</button></div>
          <div class="panel-bd">
            ${table(["No", "Purpose", "Status", ""], inds.map((r) => [
              r.number, r.purpose, `<span class="pill">${r.status}</span>`,
              r.status === "pending"
                ? `<button class="btn btn-ghost btn-sm" data-ind-ok="${r.id}">Approve</button>`
                : (r.status === "approved"
                  ? `<button class="btn btn-accent btn-sm" data-ind-pr="${r.id}">→ PR</button>`
                  : "—"),
            ]))}
          </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Purchase requisitions</h2>
          <button class="btn btn-accent btn-sm" id="pr-save">+ PR</button></div>
          <div class="panel-bd">
            ${table(["No", "By", "Dept", "Status", ""], prs.map((r) => [
              r.number, r.requested_by, r.department || "—", `<span class="pill">${r.status}</span>`,
              r.status === "pending"
                ? `<button class="btn btn-ghost btn-sm" data-pr-ok="${r.id}">Approve</button>`
                : (r.status === "approved"
                  ? `<button class="btn btn-primary btn-sm" data-pr-po="${r.id}">→ PO</button>`
                  : "—"),
            ]))}
          </div></div>
      </div>
      <p class="hint"><a href="#/purchase">Open Purchase</a> · <a href="#/rfq">RFQ rates</a> · <a href="#/manufacturing">Production challan</a> · <a href="#/books">Kanha Books</a></p>`;
    $("#ind-save")?.addEventListener("click", async () => {
      const r = await API.post("/api/indents", { purpose: "production" });
      toast("Indent created");
      flowSave(`Indent ${r.number || r.id}`, r, "Approve → phir → PR → Approve → → PO (purchase path).");
      pageIndents(el);
    });
    $("#pr-save")?.addEventListener("click", async () => {
      const r = await API.post("/api/purchase/requisitions", { department: "Store" });
      toast("PR created");
      flowSave(`PR ${r.number || r.id}`, r, "Approve ke baad → PO button se Purchase Order.");
      pageIndents(el);
    });
    document.querySelectorAll("[data-ind-ok]").forEach((b) => b.addEventListener("click", async () => {
      await API.post(`/api/indents/${b.getAttribute("data-ind-ok")}/approve`, {});
      toast("Indent approved");
      pageIndents(el);
    }));
    document.querySelectorAll("[data-ind-pr]").forEach((b) => b.addEventListener("click", async () => {
      const r = await API.post(`/api/indents/${b.getAttribute("data-ind-pr")}/to-pr`, {});
      toast(`PR ${r.pr_number} created`);
      flowSave(`PR ${r.pr_number}`, r, "Indents tab → PR list · Approve → PO.");
      pageIndents(el);
    }));
    document.querySelectorAll("[data-pr-ok]").forEach((b) => b.addEventListener("click", async () => {
      await API.post(`/api/purchase/requisitions/${b.getAttribute("data-pr-ok")}/approve`, {});
      toast("PR approved");
      pageIndents(el);
    }));
    document.querySelectorAll("[data-pr-po]").forEach((b) => b.addEventListener("click", async () => {
      try {
        const r = await API.post(`/api/purchase/requisitions/${b.getAttribute("data-pr-po")}/convert-po`, {});
        toast(`PO ${r.po_number} from PR`);
        flowSave(`PO ${r.po_number}`, r, "Purchase module me PO open karo · Receive = GRN.");
        pageIndents(el);
      } catch (e) { toast(e.message); }
    }));
  }

  async function pageMIS(el) {
    const [m, cmp, stockAge, outstanding, attReport, bridges] = await Promise.all([
      API.get("/api/mis/sales-summary"),
      API.get("/api/advanced/mis/compare").catch(() => null),
      API.get("/api/advanced/stock-ageing").catch(() => ({ lines: [], slow_movers: 0 })),
      API.get("/api/outstanding/summary").catch(() => ({ buyer_outstanding: [], vendor_outstanding: [] })),
      API.get("/api/reports/run/attendance_summary").catch(() => ({ rows: [] })),
      API.get("/api/bridges").catch(() => ({ erp_targets: [], summary: {} })),
    ]);
    const bar = (items, key = "amount") => {
      const max = Math.max(...items.map((i) => Number(i[key]) || 0), 1);
      return `<div class="mis-bars">${items.map((i) => {
        const v = Number(i[key]) || 0;
        const pct = Math.round((v / max) * 100);
        return `<div class="mis-bar"><span>${i.month || i.name}</span><i style="width:${pct}%"></i><em>${moneyFit(v)}</em></div>`;
      }).join("")}</div>`;
    };
    const buyers = outstanding.buyer_outstanding || outstanding.buyers || [];
    const vendors = outstanding.vendor_outstanding || outstanding.vendors || [];
    const attPayload = attReport.data || attReport.rows || attReport.lines || [];
    const attRows = Array.isArray(attPayload) ? attPayload : [];
    const erpTargets = bridges.erp_targets || [];
    const attIsStatusBag = attRows.length && attRows[0] && ("count" in attRows[0]) && ("status" in attRows[0]);
    el.innerHTML = `
      ${moduleIntro("MIS Analytics", "SBAC-style desk · Sales analysis · Party outstanding · Attendance · Stock · ERP bridges (Tally+Marg+Other).", {
        clients: (m.by_client || []).length,
        slow: stockAge.slow_movers || 0,
        ar: buyers.length,
        bridges: erpTargets.length || 5,
      }, `<a class="btn btn-ghost btn-sm" href="#/bridges">ERP Bridges</a>
          <a class="btn btn-ghost btn-sm" href="#/books">Books / Outstanding</a>
          <a class="btn btn-ghost btn-sm" href="#/bi">BI Panel</a>
          <button class="btn btn-ghost btn-sm" id="mis-csv">Export CSV</button>`)}
      ${cmp ? `<div class="kpi-grid">
        ${kpiCard(`Sales ${cmp.this_month}`, "", { icon: "↗", tone: "blue", raw: cmp.sales?.this, meta: `${cmp.sales?.change_pct}% vs ${cmp.last_month}` })}
        ${kpiCard(`Purchase ${cmp.this_month}`, "", { icon: "↙", tone: "violet", raw: cmp.purchase?.this, meta: `${cmp.purchase?.change_pct}% vs last` })}
        ${kpiCard("Spread this mo", "", { icon: "★", tone: "emerald", raw: cmp.gross_spread?.this })}
        ${kpiCard("Slow movers", String(stockAge.slow_movers || 0), { icon: "#", tone: "amber" })}
      </div>` : ""}
      <div class="panel glass"><div class="panel-hd"><h2>Sales analysis</h2>
        ${viewToggle("mis-sales", "chart")}</div>
        <div class="panel-bd">
          <div data-view-panel="mis-sales" data-mode="chart">
            ${chartLine(m.monthly_sales || [], { width: 520, height: 160 })}
            <div class="grid-2" style="margin-top:12px">
              ${chartBars(m.by_client || [], { label: "name", key: "amount", width: 400 })}
              ${chartDonut((m.by_category || []).slice(0, 6).map((c) => ({ label: c.name, value: c.amount })), { size: 150 })}
            </div>
          </div>
          <div data-view-panel="mis-sales" data-mode="table" hidden>
            <div class="grid-2">
              <div>${bar(m.monthly_sales || [])}</div>
              <div>${bar(m.monthly_purchase || [])}</div>
              <div>${bar(m.by_client || [])}</div>
              <div>${bar(m.by_category || [])}</div>
            </div>
          </div>
        </div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Party outstanding (Buyer AR)</h2>
          <a class="btn btn-ghost btn-sm" href="#/books">Open books</a></div>
          <div class="panel-bd">${table(
            ["Party", "Outstanding", "Bills"],
            buyers.slice(0, 12).map((b) => [
              b.name || b.party || b.customer_name || "—",
              money(b.outstanding ?? b.balance ?? b.amount ?? 0),
              b.bills ?? b.count ?? "—",
            ])
          )}</div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Vendor outstanding (AP)</h2></div>
          <div class="panel-bd">${table(
            ["Vendor", "Outstanding", "Bills"],
            vendors.slice(0, 12).map((v) => [
              v.name || v.party || v.vendor_name || "—",
              money(v.outstanding ?? v.balance ?? v.amount ?? 0),
              v.bills ?? v.count ?? "—",
            ])
          )}</div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Attendance (MIS)</h2>
        <a class="btn btn-ghost btn-sm" href="#/hrms">HRMS</a></div>
        <div class="panel-bd">${attIsStatusBag
          ? table(["Status", "Count"], attRows.map((r) => [r.status, r.count]))
          : table(
            ["Employee", "Present", "Absent", "Leave", "Period"],
            attRows.slice(0, 12).map((r) => [
              r.name || r.employee_name || r.code || "—",
              r.present ?? r.present_days ?? "—",
              r.absent ?? r.absent_days ?? "—",
              r.leave ?? r.leave_days ?? "—",
              r.period || r.month || "—",
            ])
          )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Stock ageing (slow movers)</h2></div><div class="panel-bd">
        ${table(["SKU", "Name", "WH", "Qty", "Days idle", "Bucket", "Value", ""], (stockAge.lines || []).filter((l) => l.slow).slice(0, 15).map((l) => [
          l.sku, l.name, l.warehouse, l.qty, l.days_idle, l.bucket, money(l.value),
          `<button class="btn btn-ghost btn-sm" data-st-d="${l.sku}">Details</button>`,
        ]))}
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>MIS Report (SBAC filters)</h2>
        <button class="btn btn-primary btn-sm" id="mis-run" type="button">Run / Refresh</button></div>
        <div class="panel-bd">
          <p class="hint" style="margin-top:0">FrmmisReport · Summary/Detail + document type · From/To · Executive · Item · Status · Sale type</p>
          <div class="grid-2" style="gap:8px;margin-bottom:10px">
            <div class="field"><label>View</label>
              <select id="mis-view"><option value="summary">Summary</option><option value="detail">Detail</option></select></div>
            <div class="field"><label>Document</label>
              <select id="mis-doc">
                <option value="invoice">Invoice</option>
                <option value="order">Sales Order</option>
                <option value="challan">Challan</option>
                <option value="lead">Lead</option>
                <option value="quotation">Quotation</option>
                <option value="dispatch">Dispatch</option>
                <option value="po">PO</option>
                <option value="mrn">Material Receipt</option>
                <option value="pinvoice">Purchase Invoice</option>
                <option value="follow">Follow-up</option>
                <option value="issue">Item Issue</option>
                <option value="receive">Item Receive</option>
              </select></div>
            <div class="field"><label>From</label><input id="mis-from" type="date" /></div>
            <div class="field"><label>To</label><input id="mis-to" type="date" /></div>
            <div class="field"><label>Buyer</label><input id="mis-buyer" placeholder="txtbuyer" /></div>
            <div class="field"><label>Vendor</label><input id="mis-vendor" placeholder="txtvendor" /></div>
            <div class="field"><label>Item / Code</label><input id="mis-item" placeholder="txtitem / txtitemcode" /></div>
            <div class="field"><label>Status</label>
              <select id="mis-status">
                <option value="">—</option>
                <option>Pending</option><option>Running</option><option>Confirmed</option>
                <option>Closed Won</option><option>Closed Lost</option>
              </select></div>
            <div class="field"><label>Sale type</label>
              <select id="mis-saletype"><option value="">—</option><option>Cash</option><option>Tax</option></select></div>
          </div>
          <div id="mis-filter-box" class="hint">Filters local to this desk · charts below refresh on Run · deep export on CSV</div>
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>ERP bridge desk</h2>
        <a class="btn btn-accent btn-sm" href="#/bridges">Open Connected Apps</a>
        <a class="btn btn-ghost btn-sm" href="#/bridges">Tally Parent / Errors</a></div>
        <div class="panel-bd">
          <p class="hint" style="margin-top:0">Tally path kept · Parent mapping · Inactive ledger/item · Error queue · Marg / Busy / Vyapar packs</p>
          ${table(
            ["Target", "Format", ""],
            (erpTargets.length ? erpTargets : [
              { id: "tally", label: "Tally", format: "kanha_tally_pack_v1" },
              { id: "marg", label: "Marg ERP", format: "kanha_marg_pack_v1" },
              { id: "other", label: "Other ERP / CSV", format: "kanha_erp_generic_pack_v1" },
            ]).map((t) => [
              t.label || t.id,
              t.format || "—",
              `<a class="btn btn-ghost btn-sm" href="#/bridges">Export</a>`,
            ])
          )}
        </div></div>
      <div class="panel glass"><div class="panel-bd">
        <b>Kanha extras:</b> ${(m.kanha_extras || []).join(" · ") || "Charts · CSV · AR/AP · bridges"}
        · <a href="#/payments-ops">AR/AP ageing</a> · <a href="#/bi">BI</a>
      </div></div>`;
    bindViewToggle(el, "mis-sales");
    const todayMis = new Date().toISOString().slice(0, 10);
    if ($("#mis-from") && !$("#mis-from").value) $("#mis-from").value = todayMis.slice(0, 8) + "01";
    if ($("#mis-to") && !$("#mis-to").value) $("#mis-to").value = todayMis;
    $("#mis-run")?.addEventListener("click", () => {
      const f = {
        view: $("#mis-view")?.value,
        doc: $("#mis-doc")?.value,
        from: $("#mis-from")?.value,
        to: $("#mis-to")?.value,
        buyer: $("#mis-buyer")?.value,
        vendor: $("#mis-vendor")?.value,
        item: $("#mis-item")?.value,
        status: $("#mis-status")?.value,
        sale_type: $("#mis-saletype")?.value,
      };
      const box = $("#mis-filter-box");
      if (box) {
        box.innerHTML = `<span class="pill ok">${f.view} · ${f.doc}</span> `
          + `${f.from || "—"} → ${f.to || "—"} · buyer ${f.buyer || "—"} · vendor ${f.vendor || "—"} · item ${f.item || "—"} · ${f.status || "any"} · ${f.sale_type || "any"}`
          + `<div style="margin-top:8px">${table(
            ["Metric", "Value"],
            [
              ["Clients in chart", (m.by_client || []).length],
              ["Buyer OS rows", buyers.length],
              ["Vendor OS rows", vendors.length],
              ["Attendance rows", attRows.length],
              ["Slow movers", stockAge.slow_movers || 0],
            ]
          )}</div>`;
      }
      toast(`MIS ${f.doc} · ${f.view} refreshed`);
      state.misFilters = f;
    });
    $("#mis-csv")?.addEventListener("click", () => {
      exportCsv("kanha-mis-clients.csv", ["Client", "Amount"], (m.by_client || []).map((c) => [c.name, c.amount]));
      toast("CSV exported");
    });
    el.querySelectorAll("[data-st-d]").forEach((btn) => {
      const row = (stockAge.lines || []).find((l) => l.sku === btn.dataset.stD);
      btn.addEventListener("click", () => openDetail(`SKU ${btn.dataset.stD}`, row || {}, { eyebrow: "Stock detail", showJson: false }));
    });
  }

  async function pageRfq(el) {
    const rows = await API.get("/api/rfq");
    el.innerHTML = `
      ${moduleIntro("RFQ / Vendor Rates", "Supplier-wise item rates — convert best quote to PO.")}
      <div class="panel glass"><div class="panel-hd"><h2>Add rate</h2></div><div class="panel-bd grid-2">
        <div class="field"><label>Vendor</label><input id="rfq-vendor" /></div>
        <div class="field"><label>Item</label><input id="rfq-item" /></div>
        <div class="field"><label>Rate</label><input id="rfq-rate" type="number" step="0.01" /></div>
        <div class="field"><label>Qty</label><input id="rfq-qty" type="number" value="1" /></div>
        <button class="btn btn-primary" id="rfq-save" type="button">Save quote</button>
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Quotes</h2></div><div class="panel-bd">
        ${table(["Vendor", "Item", "Rate", "Qty", "UOM", "Status", ""], rows.map((r) => [
          r.vendor_name, r.item_name, money(r.rate), r.qty, r.uom, `<span class="pill">${r.status}</span>`,
          `${r.status === "active" ? `<button class="btn btn-ghost btn-sm" data-rfq-po="${r.id}">→ PO</button> ` : ""}<button class="btn btn-ghost btn-sm" data-rfq-d="${r.id}">Details</button>`,
        ]))}
      </div></div>`;
    $("#rfq-save")?.addEventListener("click", async () => {
      try {
        const payload = {
          vendor_name: $("#rfq-vendor")?.value,
          item_name: $("#rfq-item")?.value,
          rate: Number($("#rfq-rate")?.value || 0),
          qty: Number($("#rfq-qty")?.value || 1),
        };
        const r = await API.post("/api/rfq", payload);
        toast("RFQ saved");
        flowSave(`RFQ #${r.id}`, { ...payload, id: r.id }, "Quotes list me → PO dabao = Purchase Order banega.");
        pageRfq(el);
      } catch (e) { toast(e.message); }
    });
    document.querySelectorAll("[data-rfq-d]").forEach((btn) => {
      const row = rows.find((x) => String(x.id) === btn.getAttribute("data-rfq-d"));
      btn.addEventListener("click", () => openDetail(`${row?.vendor_name || "RFQ"} · ${row?.item_name || ""}`, row || {}, { eyebrow: "Vendor rate", showJson: false }));
    });
    document.querySelectorAll("[data-rfq-po]").forEach((b) => b.addEventListener("click", async () => {
      try {
        const r = await API.post(`/api/rfq/${b.getAttribute("data-rfq-po")}/to-po`, {});
        toast(`PO ${r.po_number} created`);
        flowSave(`PO ${r.po_number}`, r, "Purchase tab me PO dikhega · GRN / invoice wahan se.");
        pageRfq(el);
      } catch (e) { toast(e.message); }
    }));
  }

  async function pageBooks(el) {
    const [sum, vouchers, day, tb, coa, cash, bank, gstr, recon, centres, pnl, bs, outstanding] = await Promise.all([
      API.get("/api/books/summary"),
      API.get("/api/books/vouchers"),
      API.get("/api/books/daybook"),
      API.get("/api/books/reports/trial-balance"),
      API.get("/api/books/coa"),
      API.get("/api/books/cash-book"),
      API.get("/api/books/bank-book"),
      API.get("/api/books/reports/gstr3b"),
      API.get("/api/books/bank-recon"),
      API.get("/api/books/cost-centres"),
      API.get("/api/books/reports/pnl"),
      API.get("/api/books/reports/balance-sheet").catch(() => ({ assets: [], liabilities: [], equity: [] })),
      API.get("/api/outstanding/summary").catch(() => ({ buyer_outstanding: [], vendor_outstanding: [], buyer_total: 0, vendor_total: 0 })),
    ]);
    const ledgerCode = state.booksLedger || "1100";
    let ledger = null;
    try { ledger = await API.get(`/api/books/ledger/${ledgerCode}`); } catch { ledger = { entries: [], closing: 0, account: {} }; }
    const leafCoa = (coa || []).filter((a) => !a.is_group);
    const voucherCtx = { accounts: coa || [], centres: centres || [] };
    const postVoucher = async (payload) => {
      const r = await API.post("/api/books/vouchers", payload);
      toast(`${r.voucher_type} ${r.number} posted`);
      flowSave(`${r.voucher_type} ${r.number}`, r, "Day book + Cash/Bank · Trial balance · Reverse se undo.");
      pageBooks(el);
    };
    el.innerHTML = `
      ${moduleIntro("Kanha Books · Accounts", "Ledger Master + Payment/Receipt/Journal/Contra/CN/DN · Day Book · Outstanding. SBAC process · Kanha design.", {
        vouchers: sum.voucher_count, coa: sum.coa_count, day: day.count,
        buyer_os: outstanding.buyer_total || 0, vendor_os: outstanding.vendor_total || 0,
      }, `<a class="btn btn-accent btn-sm" href="#/bridges">Tally / Bridges</a>
          <button class="btn btn-ghost btn-sm" id="bk-bridge-export" type="button">Tally export</button>
          <a class="btn btn-ghost btn-sm" href="#/accounting">Reports / Period lock</a>`)}
      <div class="kpi-grid">
        ${kpiCard("Cash", "", { icon: "₹", tone: "emerald", raw: sum.cash_balance })}
        ${kpiCard("Bank", "", { icon: "₹", tone: "blue", raw: sum.bank_balance })}
        ${kpiCard("Net profit", "", { icon: "★", tone: "violet", raw: pnl.net_profit })}
        ${kpiCard("Buyer OS", "", { icon: "↗", tone: "amber", raw: outstanding.buyer_total || 0 })}
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Ledger Master</h2>
        <button class="btn btn-primary btn-sm" id="bk-ledger-new">+ Create Ledger</button></div>
        <div class="panel-bd">${table(
          ["Code", "Name", "Type", "Group?", "Balance"],
          (coa || []).slice(0, 40).map((a) => [
            a.code, a.name, a.type || a.account_type || "—",
            a.is_group ? "Yes" : "—",
            a.is_group ? "—" : money(a.balance),
          ]),
          "No COA — open Accounting once to seed."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Vouchers (SBAC types)</h2>
        <div class="row" style="gap:6px;flex-wrap:wrap">
          <button class="btn btn-primary btn-sm" data-vtype="receipt">+ Receipt</button>
          <button class="btn btn-accent btn-sm" data-vtype="payment">+ Payment</button>
          <button class="btn btn-ghost btn-sm" data-vtype="contra">+ Contra</button>
          <button class="btn btn-ghost btn-sm" data-vtype="journal">+ Journal</button>
          <button class="btn btn-ghost btn-sm" data-vtype="credit_note">+ Credit Note</button>
          <button class="btn btn-ghost btn-sm" data-vtype="debit_note">+ Debit Note</button>
          <button class="btn btn-ghost btn-sm" id="bk-export" type="button">Export pack</button>
        </div></div>
        <div class="panel-bd"><p class="hint">Pick voucher type → account + party + amount drawer (fresh entry).</p></div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Day book · ${day.date || ""}</h2></div><div class="panel-bd">
          ${table(["No", "Type", "Party", "Narration", "Amount"], (day.entries || []).map((v) => [
            v.number, v.voucher_type, v.party_name || "—", v.narration || "—", money(v.debit)
          ]))}
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Recent vouchers</h2></div><div class="panel-bd">
          ${table(["No", "Type", "Date", "Party", "Dr", ""], (vouchers || []).slice(0, 20).map((v) => [
            v.number, v.voucher_type, v.entry_date || "—", v.party_name || "—", money(v.debit),
            v.status !== "reversed"
              ? `<button class="btn btn-ghost btn-sm" data-rev="${v.id}">Reverse</button>`
              : `<span class="pill">reversed</span>`,
          ]))}
        </div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Party Outstanding (Buyer / Vendor)</h2></div>
        <div class="panel-bd grid-2">
          <div>
            <h3 style="margin:0 0 8px;font-size:13px">Buyer · AR ${money(outstanding.buyer_total || 0)}</h3>
            ${table(
              ["Party", "Bill", "Balance"],
              (outstanding.buyer_outstanding || []).slice(0, 15).map((r) => [r.party, r.ref, money(r.balance)]),
              "No buyer outstanding."
            )}
          </div>
          <div>
            <h3 style="margin:0 0 8px;font-size:13px">Vendor · AP ${money(outstanding.vendor_total || 0)}</h3>
            ${table(
              ["Party", "Bill", "Balance"],
              (outstanding.vendor_outstanding || []).slice(0, 15).map((r) => [r.party, r.ref || r.number || "—", money(r.balance)]),
              "No vendor outstanding."
            )}
          </div>
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Party ledger</h2></div><div class="panel-bd grid-2">
        <div class="field"><label>Party name</label><input id="pl-name" placeholder="Customer / vendor" value="${state.partyLedger || ""}" /></div>
        <div class="field"><label>Type</label>
          <select id="pl-type"><option value="customer">Customer</option><option value="vendor">Vendor</option></select></div>
        <button class="btn btn-primary btn-sm" id="pl-go" type="button">Open ledger</button>
        <button class="btn btn-ghost btn-sm" id="pl-csv" type="button">Download CSV</button>
        <div id="pl-box" class="hint">Search a party to see running ledger</div>
      </div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Cash book · closing ${money(cash.closing)}</h2></div><div class="panel-bd">
          ${table(["Date", "Voucher", "Narration", "Dr", "Cr", "Bal"], (cash.entries || []).slice(-15).map((e) => [
            e.date || "—", e.voucher, e.narration || "—", money(e.debit), money(e.credit), money(e.balance)
          ]))}
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Bank book · closing ${money(bank.closing)}</h2></div><div class="panel-bd">
          ${table(["Date", "Voucher", "Narration", "Dr", "Cr", "Bal"], (bank.entries || []).slice(-15).map((e) => [
            e.date || "—", e.voucher, e.narration || "—", money(e.debit), money(e.credit), money(e.balance)
          ]))}
        </div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Ledger drill</h2>
        <select id="bk-ledger">${leafCoa.map((a) => `<option value="${a.code}" ${a.code === ledgerCode ? "selected" : ""}>${a.code} · ${a.name} · ${money(a.balance)}</option>`).join("")}</select>
      </div><div class="panel-bd">
        <p class="hint">${ledger.account?.name || ""} · closing ${money(ledger.closing)}</p>
        ${table(["Date", "Voucher", "Type", "Narration", "Dr", "Cr", "Bal"], (ledger.entries || []).slice(-20).map((e) => [
          e.date || "—", e.voucher, e.voucher_type || e.type || "—", e.narration || "—", money(e.debit), money(e.credit), money(e.balance)
        ]))}
      </div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>P&amp;L</h2></div><div class="panel-bd">
          ${table(["Metric", "Amount"], [
            ["Income", money(pnl.income || pnl.total_income || 0)],
            ["Expense", money(pnl.expense || pnl.total_expense || 0)],
            ["Gross profit", money(pnl.gross_profit || 0)],
            ["Net profit", money(pnl.net_profit || 0)],
          ])}
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Balance Sheet</h2></div><div class="panel-bd">
          ${table(["Side", "Account", "Amount"], [
            ...((bs.assets || []).slice(0, 12).map((a) => ["Asset", `${a.code} · ${a.name}`, money(a.balance || 0)])),
            ...((bs.liabilities || []).slice(0, 12).map((a) => ["Liab/Eq", `${a.code} · ${a.name}`, money(Math.abs(a.balance || 0))])),
          ], "Balance sheet empty — post vouchers first.")}
          <p class="hint">Totals · Assets ${money(bs.assets_total || 0)} · Liab+Eq ${money(bs.liabilities_total || 0)}</p>
        </div></div>
      </div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Bank reconciliation</h2>
          <span class="hint">open ${recon.open_count || 0} · matched ${recon.matched_count || 0}</span></div>
          <div class="panel-bd grid-2">
            <div class="field"><label>Description</label><input id="br-desc" /></div>
            <div class="field"><label>Amount (+credit / −debit)</label><input id="br-amt" type="number" step="0.01" /></div>
            <button class="btn btn-primary btn-sm" id="br-add" type="button">Add statement line</button>
            <div class="field" style="grid-column:1/-1"><label>Import bank CSV (date,description,amount)</label>
              <textarea id="br-csv" rows="3" placeholder="2026-07-28,UPI IN Jaipur Auto,48000&#10;2026-07-27,NEFT OUT Steel Mart,-15000"></textarea></div>
            <button class="btn btn-accent btn-sm" id="br-import" type="button">Import CSV</button>
          </div>
          <div class="panel-bd">${table(["Date", "Desc", "Amount", "Status", ""], (recon.items || []).map((r) => [
            r.statement_date || "—", r.description, money(r.amount), `<span class="pill">${r.status}</span>`,
            r.status === "open" ? `<button class="btn btn-ghost btn-sm" data-br-match="${r.id}">Auto-match</button>` : "—",
          ]))}</div></div>
        <div class="panel glass"><div class="panel-hd"><h2>GSTR-3B style</h2>
          <button class="btn btn-ghost btn-sm" id="bk-gstr1">Download GSTR-1 JSON</button>
          <span class="pill warn">${gstr.watermark || ""}</span></div>
          <div class="panel-bd">
            <div class="kpi-grid">
              ${kpiCard("Output tax", "", { icon: "↗", tone: "blue", raw: (gstr.outward || {}).total_tax })}
              ${kpiCard("ITC", "", { icon: "↙", tone: "teal", raw: (gstr.inward_itc || {}).total_tax })}
              ${kpiCard("Net payable", "", { icon: "₹", tone: "amber", raw: gstr.net_payable })}
              ${kpiCard("IGST out", "", { icon: "₹", tone: "violet", raw: (gstr.outward || {}).igst })}
            </div>
            <p class="hint">Period ${gstr.period} · <a href="#/compliance">Compliance desk</a></p>
          </div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Bill-by-bill outstanding</h2>
        <select id="bk-bills-type"><option value="customer">AR · Customer</option><option value="vendor">AP · Vendor</option></select>
        <button class="btn btn-primary btn-sm" id="bk-bills" type="button">Load open bills</button></div>
        <div class="panel-bd"><div id="bk-bills-box" class="hint">CA-style open invoices — receipt/payment allocate per bill</div></div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Trial balance</h2>
        <a class="btn btn-ghost btn-sm" href="#/accounting">Full Accounting</a></div>
        <div class="panel-bd">${table(["Code", "Account", "Debit", "Credit"], (tb || []).map((t) => [t.code, t.name, money(t.debit), money(t.credit)]))}</div></div>`;

    $("#bk-ledger-new")?.addEventListener("click", () => {
      openMasterForm(
        "Create Ledger / Group",
        [
          { name: "code", label: "Ledger Code", required: true, placeholder: "e.g. 5210" },
          { name: "name", label: "Ledger Name", required: true, placeholder: "e.g. Freight Inward" },
          {
            name: "account_type",
            label: "Type",
            type: "select",
            options: [
              { value: "asset", label: "Asset" },
              { value: "liability", label: "Liability" },
              { value: "equity", label: "Equity" },
              { value: "income", label: "Income" },
              { value: "expense", label: "Expense" },
            ],
            value: "expense",
          },
          {
            name: "is_group",
            label: "Is Group?",
            type: "select",
            options: [
              { value: "0", label: "No — ledger (postable)" },
              { value: "1", label: "Yes — group only" },
            ],
            value: "0",
          },
          { name: "parent_code", label: "Under Group (Parent Code)", placeholder: "e.g. 5000 or leave blank" },
          { name: "opening_balance", label: "Opening Balance", type: "number", value: "0" },
          {
            name: "bal_type",
            label: "Opening Dr/Cr",
            type: "select",
            options: [
              { value: "Debit", label: "Debit" },
              { value: "Credit", label: "Credit" },
            ],
            value: "Debit",
          },
          { name: "opening_date", label: "Opening Date", type: "date" },
          {
            name: "currency",
            label: "Currency",
            type: "select",
            options: [
              { value: "Indian Rupee (INR)", label: "Indian Rupee (INR)" },
              { value: "USD", label: "USD" },
              { value: "Euro (EURO)", label: "Euro (EURO)" },
            ],
            value: "Indian Rupee (INR)",
          },
          { name: "other_value_pct", label: "Value %", type: "number", value: "0" },
          {
            name: "other_value_status",
            label: "Other Value Status",
            type: "select",
            options: [
              { value: "No", label: "No" },
              { value: "Yes", label: "Yes" },
            ],
            value: "No",
          },
        ],
        async (data) => {
          const r = await API.post("/api/books/ledgers", {
            code: data.code,
            name: data.name,
            account_type: data.account_type,
            is_group: data.is_group === "1",
            parent_code: data.parent_code || "",
            opening_balance: Number(data.opening_balance || 0),
            bal_type: data.bal_type || "Debit",
            opening_date: data.opening_date || "",
            currency: data.currency || "Indian Rupee (INR)",
            other_value_pct: Number(data.other_value_pct || 0),
            other_value_status: data.other_value_status || "No",
          });
          toast(r.message || `Ledger ${r.code}`);
          showSavedDetail("Ledger created", r);
          pageBooks(el);
        },
        { eyebrow: "Master · Ledger (SBAC Create Ledger)" }
      );
    });
    el.querySelectorAll("[data-vtype]").forEach((btn) => {
      btn.addEventListener("click", () => {
        openVoucherForm(btn.dataset.vtype, voucherCtx, postVoucher, { eyebrow: `Accounts · ${btn.dataset.vtype}` });
      });
    });
    $("#bk-export")?.addEventListener("click", async () => {
      const pack = await API.get("/api/books/export-pack");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([JSON.stringify(pack, null, 2)], { type: "application/json" }));
      a.download = `kanha-books-${Date.now()}.json`;
      a.click();
      toast("Kanha Books pack downloaded");
    });
    $("#bk-bridge-export")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/bridges/tally/export", {});
        toast(r.message || "Tally pack via bridge");
        const pack = r.pack || r;
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([JSON.stringify(pack, null, 2)], { type: "application/json" }));
        a.download = `kanha-tally-bridge-${Date.now()}.json`;
        a.click();
      } catch (e) { toast(e.message || "Bridge export failed — open Connected Apps"); }
    });
    $("#bk-ledger")?.addEventListener("change", () => {
      state.booksLedger = $("#bk-ledger").value;
      pageBooks(el);
    });
    $("#br-add")?.addEventListener("click", async () => {
      try {
        await API.post("/api/books/bank-recon", {
          description: $("#br-desc")?.value,
          amount: Number($("#br-amt")?.value || 0),
        });
        toast("Statement line added");
        pageBooks(el);
      } catch (e) { toast(e.message); }
    });
    $("#br-import")?.addEventListener("click", async () => {
      const csv_text = $("#br-csv")?.value || "";
      if (!csv_text.trim()) return toast("Paste CSV first");
      try {
        const r = await API.post("/api/books/bank-recon/import", { csv_text, auto_match: true });
        toast(r.message || `Imported ${r.created}`);
        flowSave("Bank CSV imported", r, "Open lines → Auto-match · Books bank book se match.");
        pageBooks(el);
      } catch (e) { toast(e.message); }
    });
    $("#bk-gstr1")?.addEventListener("click", async () => {
      try {
        const pack = await API.get("/api/books/reports/gstr1");
        const a = document.createElement("a");
        a.href = URL.createObjectURL(new Blob([JSON.stringify(pack, null, 2)], { type: "application/json" }));
        a.download = `kanha-gstr1-${pack.period || "desk"}.json`;
        a.click();
        toast(`GSTR-1 desk · ${pack.count} B2B rows`);
        flowSave("GSTR-1 JSON", pack, "CA ko do · GSTN upload GSP keys ke baad.");
      } catch (e) { toast(e.message); }
    });
    $("#bk-bills")?.addEventListener("click", async () => {
      try {
        const pt = $("#bk-bills-type")?.value || "customer";
        const r = await API.get(`/api/advanced/bill-wise?party_type=${pt}`);
        const box = $("#bk-bills-box");
        if (box) {
          box.innerHTML = table(
            ["Bill", "Date", "Party", "Total", "Paid", "Balance"],
            (r.bills || []).map((b) => [b.number, b.date || "—", b.party, money(b.total), money(b.paid), money(b.balance)])
          ) + `<p class="hint">${pt === "vendor" ? "AP" : "AR"} open ₹${money(r.total_balance)} · ${r.count} bills</p>`;
        }
        flowSave(`Bill-by-bill ${pt}`, r, "Sales/Purchase payment allocates bill-wise.");
      } catch (e) { toast(e.message); }
    });
    document.querySelectorAll("[data-br-match]").forEach((b) => b.addEventListener("click", async () => {
      const r = await API.post(`/api/books/bank-recon/${b.getAttribute("data-br-match")}/match`, {});
      toast(`Match → ${r.status}`);
      pageBooks(el);
    }));
    document.querySelectorAll("[data-rev]").forEach((b) => b.addEventListener("click", async () => {
      try {
        const r = await API.post(`/api/books/vouchers/${b.getAttribute("data-rev")}/reverse`, {});
        toast(`Reversed ${r.reversed} → ${r.reversal}`);
        pageBooks(el);
      } catch (e) { toast(e.message); }
    }));
    $("#pl-go")?.addEventListener("click", async () => {
      const name = $("#pl-name")?.value?.trim();
      if (!name) return toast("Enter party name");
      state.partyLedger = name;
      try {
        const r = await API.get(`/api/advanced/party-ledger?party=${encodeURIComponent(name)}&party_type=${$("#pl-type")?.value || "customer"}`);
        const box = $("#pl-box");
        if (box) {
          box.innerHTML = `<p class="hint">Closing ${money(r.closing)} · ${r.count} lines</p>` +
            table(["Date", "Doc", "Type", "Narration", "Dr", "Cr", "Bal"], (r.entries || []).slice(-25).map((e) => [
              e.date || "—", e.doc, e.type, e.narration || "—", money(e.debit), money(e.credit), e.balance != null ? money(e.balance) : "—"
            ]));
        }
      } catch (e) { toast(e.message); }
    });
    $("#pl-csv")?.addEventListener("click", async () => {
      const name = $("#pl-name")?.value?.trim() || state.partyLedger;
      if (!name) return toast("Enter party name");
      try {
        const pt = $("#pl-type")?.value || "customer";
        const url = `/api/advanced/party-ledger.csv?party=${encodeURIComponent(name)}&party_type=${pt}`;
        const res = await fetch(url, {
          headers: API.token ? { Authorization: `Bearer ${API.token}` } : {},
        });
        if (!res.ok) throw new Error((await res.text()) || "CSV failed");
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `kanha-party-${name.replace(/\s+/g, "_")}.csv`;
        a.click();
        toast("Party statement CSV downloaded");
      } catch (e) { toast(e.message || "CSV failed"); }
    });
  }

  async function pageDealers(el) {
    const [dealers, lists, orders] = await Promise.all([
      API.get("/api/dealers"),
      API.get("/api/pricing/lists"),
      API.get("/api/portal/dealer-orders"),
    ]);
    const d0 = dealers[0];
    let portal = null;
    if (d0) {
      try { portal = await API.get(`/api/portal/dealer/${d0.id}`); } catch {}
    }
    el.innerHTML = `
      <div class="panel glass"><div class="panel-hd"><h2>Dealers / Distributors</h2>
        <button class="btn btn-primary btn-sm" id="add-dealer">+ Dealer</button></div>
        <div class="panel-bd">
          ${stubNote("Credit limit + price slab + portal orders — channel management ready.")}
          ${table(
            ["Code", "Name", "Region", "Price list", "Credit", "Outstanding", "Available", ""],
            dealers.map((d) => [
              d.code, d.name, d.region || "—", d.price_list_code,
              money(d.credit_limit), money(d.outstanding), money(d.credit_available),
              `<button class="btn btn-ghost btn-sm" data-dl-d="${d.id}">Details</button>`,
            ])
          )}
        </div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Price lists / schemes</h2></div><div class="panel-bd">
          ${table(["Code", "Name", "For", "SKUs"], lists.map((p) => [p.code, p.name, p.party_type, (p.lines || []).length]))}
          ${lists[0] ? `<div class="hint" style="margin-top:10px">Sample: ${(lists[0].lines || []).slice(0, 3).map((l) => `${l.sku} @ ${money(l.price)}`).join(" · ")}</div>` : ""}
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Dealer portal orders</h2>
          <button class="btn btn-accent btn-sm" id="place-do" ${d0 ? "" : "disabled"}>Place demo order</button></div>
          <div class="panel-bd">${table(
            ["Number", "Dealer", "Total", "Status", "Action"],
            orders.map((o) => [
              o.number, o.dealer_name || o.dealer_id, money(o.total), `<span class="pill">${o.status}</span>`,
              `${o.status === "submitted" ? `<button class="btn btn-ghost btn-sm" data-do-ok="${o.id}">Approve</button> ` : ""}<button class="btn btn-ghost btn-sm" data-do-d="${o.id}">Details</button>`,
            ])
          )}</div></div>
      </div>
      ${portal ? `<div class="panel glass"><div class="panel-hd"><h2>Portal preview · ${portal.dealer.name}</h2></div><div class="panel-bd">
        <div class="kpi-grid" style="margin-bottom:12px">
          ${kpiCard("Outstanding", "", { icon: "₹", tone: "amber", raw: portal.outstanding })}
          ${kpiCard("Credit left", "", { icon: "◎", tone: "emerald", raw: portal.credit_available })}
          ${kpiCard("Invoices", String((portal.invoices || []).length), { icon: "#", tone: "blue" })}
          ${kpiCard("Orders", String((portal.orders || []).length), { icon: "▣", tone: "violet" })}
        </div>
        ${table(["Invoice", "Total", "Balance", "Status"], (portal.invoices || []).map((i) => [i.number, money(i.total), money(i.balance), i.status]))}
      </div></div>` : ""}`;
    $("#add-dealer")?.addEventListener("click", async () => {
      const name = prompt("Dealer / distributor name");
      if (!name) return;
      const r = await API.post("/api/dealers", { name, region: "India", credit_limit: 1000000, party_type: "dealer" });
      toast("Dealer created");
      flowSave(r.code || name, r, "Dealers list · Place demo order · Approve → Sales path.");
      pageDealers(el);
    });
    $("#place-do")?.addEventListener("click", async () => {
      if (!d0 || !portal) return;
      const line = (portal.price_list.lines || [])[0] || { sku: "DEMO", product_id: 1, price: 1000 };
      const r = await API.post("/api/portal/dealer-orders", {
        dealer_id: d0.id,
        lines: [{ sku: line.sku, product_id: line.product_id, qty: 10, rate: line.price || 1000 }],
        notes: "Portal demo order",
      });
      toast("Dealer order submitted");
      flowSave(r.number || "Dealer order", r, "Portal orders list me submitted · Approve se SO/fulfillment path.");
      pageDealers(el);
    });
    el.querySelectorAll("[data-do-ok]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const r = await API.post(`/api/portal/dealer-orders/${btn.dataset.doOk}/decide`, { status: "approved" });
        toast("Order approved");
        flowSave("Dealer order approved", r || {}, "Status approved · credit / outstanding portal me reflect.");
        pageDealers(el);
      });
    });
    el.querySelectorAll("[data-dl-d]").forEach((btn) => {
      const row = dealers.find((d) => String(d.id) === btn.dataset.dlD);
      btn.addEventListener("click", () => openDetail(row?.name || "Dealer", row || {}, { eyebrow: "Dealer", showJson: false }));
    });
    el.querySelectorAll("[data-do-d]").forEach((btn) => {
      const row = orders.find((o) => String(o.id) === btn.dataset.doD);
      btn.addEventListener("click", () => openDetail(row?.number || "Order", row || {}, { eyebrow: "Dealer order", showJson: false }));
    });
  }

  async function pageLogistics(el) {
    const [packing, dispatch, einv] = await Promise.all([
      API.get("/api/logistics/packing"),
      API.get("/api/logistics/dispatch"),
      API.get("/api/logistics/einvoice"),
    ]);
    el.innerHTML = `
      <div class="panel glass"><div class="panel-hd"><h2>Packing lists</h2>
        <button class="btn btn-primary btn-sm" id="mk-pack">Create packing</button></div>
        <div class="panel-bd">${table(
          ["Number", "Invoice", "Customer", "Packages", "Weight kg", "Status"],
          packing.map((p) => [p.number, p.invoice_number || p.invoice_id || "—", p.customer_name || "—", p.packages, p.weight_kg, `<span class="pill ok">${p.status}</span>`])
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Dispatch challan / LR</h2>
        <button class="btn btn-accent btn-sm" id="mk-dc">Create dispatch</button></div>
        <div class="panel-bd">${table(
          ["Challan", "Invoice", "Customer", "Transporter", "LR No", "Vehicle", "Date", "Status", ""],
          dispatch.map((d) => [d.number, d.invoice_number || "—", d.customer_name || "—", d.transporter, d.lr_number, d.vehicle_no, d.dispatch_date || "—", `<span class="pill">${d.status}</span>`,
            `<button class="btn btn-ghost btn-sm" data-dc-print="${d.id}">Print</button>`])
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>E-Invoice (IRN)</h2>
        <button class="btn btn-primary btn-sm" id="mk-irn">Generate IRN</button></div>
        <div class="panel-bd">
          ${stubNote("DEMO-LIVE IRN — local generate + books/audit save. Live NIC/GSP push when keys + Legal gate.")}
          ${table(
            ["Invoice", "IRN", "Ack", "Status"],
            einv.map((e) => [e.invoice_number, `<span class="mono">${(e.irn || "").slice(0, 28)}…</span>`, e.ack_no, `<span class="pill ok">${e.status}</span>`])
          )}
        </div></div>`;
    $("#mk-pack")?.addEventListener("click", async () => {
      const r = await API.post("/api/logistics/packing");
      toast(`Packing ${r.number}`);
      flowSave(`Packing ${r.number}`, r, "Packing list ready · Dispatch se LR banega.");
      pageLogistics(el);
    });
    $("#mk-dc")?.addEventListener("click", async () => {
      const r = await API.post("/api/logistics/dispatch");
      toast(`Dispatch ${r.number} · LR ${r.lr_number}`);
      flowSave(`Dispatch ${r.number}`, r, "LR + vehicle · E-invoice generate se IRN (GSP keys = live, warna DEMO-IRN).");
      pageLogistics(el);
    });
    $("#mk-irn")?.addEventListener("click", async () => {
      const r = await API.post("/api/logistics/einvoice/generate");
      toast(r.live ? `Live IRN ${r.irn}` : `IRN ${r.status}`);
      flowSave("E-Invoice IRN", r, r.live ? "Live GSP IRN saved on invoice." : "Local DEMO-IRN — Settings me GSP keys paste karo for live.");
      pageLogistics(el);
    });
    el.querySelectorAll("[data-dc-print]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const row = dispatch.find((d) => String(d.id) === btn.dataset.dcPrint);
        if (!row) return toast("Dispatch not found");
        printSheet(buildDispatchHtml(row), `Dispatch ${row.number}`);
      });
    });
  }

  async function pageCRM(el) {
    const [leads, customers, opps, quotes] = await Promise.all([
      API.get("/api/crm/leads"),
      API.get("/api/crm/customers"),
      API.get("/api/crm/opportunities"),
      API.get("/api/crm/quotations"),
    ]);
    el.innerHTML = `
      ${moduleIntro("CRM", "Leads → Opportunities → Customers → Quotations. Har company type (manufacture/service/retail/solo) ke liye pehla sales funnel.", {
        leads: leads.length, customers: customers.length, opportunities: opps.length, quotations: quotes.length,
      })}
      <div class="panel glass"><div class="panel-hd"><h2>Leads</h2>
        <div class="row" style="gap:6px">
          <button class="btn btn-primary btn-sm" id="add-lead">+ Lead</button>
          <button class="btn btn-accent btn-sm" id="lead-quote" ${leads[0] ? "" : "disabled"}>Lead → Quote</button>
        </div></div>
      <div class="panel-bd">${table(["Name", "Company", "Stage", "Value", "Source", ""], leads.map((l) => [
        l.name, l.company_name || "—", `<span class="pill">${l.stage}</span>`, money(l.value), l.source,
        `<button class="btn btn-ghost btn-sm" data-crm-d="lead" data-id="${l.id}">Details</button>`,
      ]))}</div></div>
      <div class="grid-2">
      <div class="panel glass"><div class="panel-hd"><h2>Customers / Party Master</h2><button class="btn btn-primary btn-sm" id="add-cust">+ Party</button></div>
        <div class="panel-bd">${table(["Code", "Name", "Type", "Nature", "GSTIN", "WhatsApp", "Under A/c", ""], customers.map((c) => [
          c.code, c.name, `<span class="pill">${c.party_type || "customer"}</span>`,
          (c.custom && c.custom.party_nature) || "—",
          c.gstin || "—",
          (c.custom && c.custom.whatsapp) || c.phone || "—",
          (c.custom && c.custom.under_account) || "—",
          `<button class="btn btn-ghost btn-sm" data-crm-d="cust" data-id="${c.id}">Details</button>`,
        ]))}</div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Pipeline</h2><button class="btn btn-primary btn-sm" id="add-opp">+ Opportunity</button></div>
          <div class="panel-bd">${table(["Opportunity", "Customer", "Stage", "Amount", "Prob", ""], opps.map((o) => [
            o.title, o.customer_name || o.lead_name || "—", o.stage, money(o.amount), o.probability + "%",
            `<button class="btn btn-ghost btn-sm" data-crm-d="opp" data-id="${o.id}">Details</button>`,
          ]))}</div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Quotations</h2><button class="btn btn-primary btn-sm" id="add-quote">+ Quotation</button></div>
        <div class="panel-bd">${table(["Number", "Customer", "Status", "Total", ""], quotes.map((q) => [
          q.number, q.customer_name || q.lead_name || "—", q.status, money(q.total),
          `<button class="btn btn-ghost btn-sm" data-crm-d="quote" data-id="${q.id}">Details</button>`,
        ]))}</div></div>`;
    $("#add-lead")?.addEventListener("click", async () => {
      const name = prompt("Lead name");
      if (!name) return;
      const r = await API.post("/api/crm/leads", { name, company_name: name + " Co", stage: "new", value: 50000, source: "web" });
      toast("Lead saved");
      showSavedDetail("Lead saved", r);
      pageCRM(el);
    });
    $("#add-cust")?.addEventListener("click", () => {
      const underOpts = [
        "Agent/Salesman A/C",
        "Bank Accounts",
        "Bank OD A/c",
        "Branch / Divisions",
        "EMPLOYEE",
        "Employee A/c",
        "INTEREST PAYABLE",
        "Other Expence",
        "Other Income",
        "Production party",
        "Sundry Debtors",
        "Sundry Creditors",
        "Sundry Creditors (Transportation)",
        "Sundry Creditors (Commission)",
        "Sundry Creditors (Employee)",
        "Secured Loans",
        "Transport A/c",
      ];
      const branchOpts = [
        "SHRI BALAJI ALLOYS CORPORATION RPR",
        "SBAC FARM",
        "SHREE BALAJI ALLOYS CORPORATION HYD",
        "SHRI BALAJI ALLOYS CORPORATION",
        "SHRI BALAJI ALLOYS CORPORATION DGP",
        "SHRI BALAJI ALLOYS CORPORATION IND",
        "SHRI BALAJI ALLOYS CORPORATION MANDAWA",
      ];
      const empDepts = [
        "Telli Marketing", "HR", "Security", "Admin", "Worksshop", "Lab", "Purchase", "Sales",
        "Production", "Accounts", "Machnical", "Store", "Telecaller", "Driver", "Dispatch", "It Networking",
      ];
      const designations = [
        "Purchase Manager", "Hod", "Area Manager", "General Manager", "Store HOD", "Senior Accountant",
        "Managing Director", "Formen", "Workshop Incharge", "Marketing Executive", "Account HOD", "Welder",
        "Accountant", "Store Incharg", "Account", "Executive", "Consultant", "Purchase executive", "Agent",
        "Store executive", "It Executive",
      ];
      const addrTypes = [
        "Billing Address", "Shiping Address", "Permanent Address", "Official", "Work",
        "Registered Office", "Factory", "Permanent address", "Billing address", "Shipping address",
      ];
      const companyTypes = ["User", "Industries", "Traders", "Exporter", "Retailer"];
      const customerTypes = [
        "Industries", "Trader", "User", "Distributor", "Dealer", "Fabricator", "Contractor", "Mation", "Tractor",
      ];
      const areas = ["Raipur", "Raigarh", "Ambikapur", "Durgapur", "Indore", "Bhiwadi", "Goa", "Jalna", "Giridih"];
      const currencies = [
        "Indian Rupee (INR)", "US Dollar (USD)", "Euro (EURO)", "Pound Sterling (GBP)", "Yen (JPY)",
        "STERLINGS", "AUSTRALIAN DOLLAR", "China(RMB)", "Singapore Dollar (SGD)", "Nepalese Rupee (NPR)",
      ];
      openMasterForm(
        "Party Master",
        [
          { type: "section", label: "Primary", hint: "SBAC Add Party — live field parity (2026-08-02)" },
          { name: "gstin", label: "GST Number", placeholder: "GST Number" },
          { name: "name", label: "Party Name", required: true, placeholder: "Party Name" },
          {
            name: "party_nature",
            label: "Domestic / Export",
            type: "select",
            options: ["Domestic", "Export"],
            value: "Domestic",
          },
          {
            name: "under_account",
            label: "Under Account",
            type: "select",
            required: true,
            options: underOpts,
            value: "Sundry Debtors",
          },
          { name: "file_as", label: "File As", placeholder: "File As" },
          { name: "whatsapp", label: "Whatsapp Number", required: true, placeholder: "Whatsapp Number" },
          { name: "joining_date", label: "Joinning Date", type: "date" },
          { name: "work_area", label: "W. Area", placeholder: "W. Area" },
          { name: "repeat_order_days", label: "Repeat Order Days", type: "number", placeholder: "Repeat Order Days" },
          {
            name: "branch_list",
            label: "Branch List",
            type: "checkboxes",
            options: branchOpts,
            value: [branchOpts[0]],
            defaultFirst: true,
          },
          {
            name: "show_order_followup",
            label: "Show in Order followup",
            type: "select",
            options: ["Yes", "No"],
            value: "Yes",
          },
          { name: "transport", label: "Transport", placeholder: "Transport name" },
          { name: "agent", label: "Agent Name", placeholder: "Agent / executive" },
          {
            name: "party_type",
            label: "Kanha Role (extra)",
            type: "select",
            options: [
              { value: "customer", label: "Customer / Debtor" },
              { value: "vendor", label: "Vendor / Creditor" },
              { value: "dealer", label: "Dealer" },
              { value: "transport", label: "Transport" },
              { value: "agent", label: "Agent / Executive" },
              { value: "employee", label: "Employee" },
            ],
            value: "customer",
          },

          { type: "section", label: "Employee Details", hint: "SBAC CheckBox1 · Department / Designation / Reporting" },
          { name: "emp_department", label: "Department", type: "select", options: ["", ...empDepts] },
          { name: "emp_designation", label: "Designation", type: "select", options: ["", ...designations] },
          { name: "emp_email", label: "Email", placeholder: "Email" },
          { name: "emp_mobile", label: "Mobile No.", placeholder: "Mobile Number" },
          { name: "emp_reporting_person", label: "Reporting Person", placeholder: "Reporting person" },

          { type: "section", label: "Address Details", hint: "SBAC CheckBox3 · multi-line via Add Address" },
          {
            name: "addr_type",
            label: "Address Type",
            type: "select",
            options: ["", ...addrTypes],
            value: "Billing Address",
          },
          { name: "addr_country", label: "Country", value: "India", placeholder: "Country" },
          { name: "addr_state", label: "State", placeholder: "State" },
          { name: "addr_city", label: "City", placeholder: "City" },
          { name: "addr_area", label: "Area", placeholder: "Area" },
          { name: "addr_address", label: "Address", type: "textarea", placeholder: "Address" },
          { name: "addr_pincode", label: "Pin Code", placeholder: "Pin Code" },
          { name: "addr_telephone", label: "Telephone", placeholder: "Telephone" },
          { name: "addr_email", label: "Email", placeholder: "Email" },
          { name: "addr_mobile", label: "Mobile", placeholder: "Mobile" },
          { name: "addr_website", label: "Website", placeholder: "Website" },
          { name: "addr_fax", label: "Fax No.", placeholder: "Fax Number" },
          { type: "list_preview", name: "addresses", label: "Saved addresses" },

          { type: "section", label: "Account Details", hint: "SBAC CheckBox2" },
          { name: "opening_balance", label: "Opening Balance", type: "number", value: "0" },
          {
            name: "opening_drcr",
            label: "Dr / Cr",
            type: "select",
            options: ["", "Cr", "Dr"],
            value: "Dr",
          },
          {
            name: "currency",
            label: "Currency",
            type: "select",
            options: ["", ...currencies],
            value: "Indian Rupee (INR)",
          },
          { name: "credit_limit", label: "Credit Limit", type: "number", value: "0" },
          { name: "credit_days", label: "Credit Limit(Days)", type: "number", value: "0" },
          {
            name: "grade",
            label: "Grade",
            type: "select",
            options: ["", "A", "B", "C", "D"],
          },
          { name: "pan", label: "Pan No.", placeholder: "Pan Number" },
          { name: "cts_no", label: "CTS No.", placeholder: "CTS Number" },
          { name: "pvt_marka", label: "Pvt Marka", placeholder: "Pvt Marka" },
          { name: "sales_target", label: "Sales Target", placeholder: "Sales Target" },
          { name: "ecc_no", label: "Ecc No.", placeholder: "Ecc No." },
          {
            name: "status_active",
            label: "Status",
            type: "radio",
            options: [
              { value: "Active", label: "Active" },
              { value: "NonActive", label: "NonActive" },
            ],
            value: "Active",
          },
          {
            name: "tcs_allow",
            label: "Tcs Allow",
            type: "radio",
            options: [
              { value: "Yes", label: "Yes" },
              { value: "No", label: "No" },
            ],
            value: "No",
          },
          {
            name: "tds_allow",
            label: "Tds Allow",
            type: "radio",
            options: [
              { value: "Yes", label: "Yes" },
              { value: "No", label: "No" },
            ],
            value: "No",
          },

          { type: "section", label: "Company Details", hint: "SBAC chkAcd" },
          {
            name: "company_type",
            label: "Company type",
            type: "select",
            options: ["", ...companyTypes],
          },
          {
            name: "customer_type",
            label: "Customer Type",
            type: "select",
            options: ["", ...customerTypes],
          },
          { name: "head_quarter", label: "Head Quarter", placeholder: "Head Quarter" },
          {
            name: "company_area",
            label: "Area",
            type: "select",
            options: ["", ...areas],
          },
          { name: "discount_pct", label: "Discount Percente", type: "number", placeholder: "Discount %" },
          { name: "discount_name", label: "Discount Name", placeholder: "Discount Name" },
          { name: "alias", label: "Alias", placeholder: "Alias" },
          { name: "remarks", label: "Remarks", type: "textarea", placeholder: "Remarks" },
          { name: "show_remarks", label: "Show Remarks", type: "checkbox", value: false },

          { type: "section", label: "Bank Details", hint: "SBAC CheckBox4 · multi via Add Bank" },
          { name: "bank_name", label: "Bank Name", placeholder: "Bank Name" },
          { name: "bank_holder", label: "Account Holder", placeholder: "Account Holder" },
          { name: "bank_account", label: "Account No.", placeholder: "Account No" },
          { name: "bank_swift", label: "Swift Code", placeholder: "Swift Code" },
          { name: "bank_ifsc", label: "IFSC Code", placeholder: "IFSC Code" },
          { name: "bank_country", label: "Region/Country", value: "India", placeholder: "Country" },
          { name: "bank_state", label: "State", placeholder: "State" },
          { name: "bank_city", label: "City", placeholder: "City" },
          { name: "bank_address", label: "Address", type: "textarea", placeholder: "Address" },
          { name: "bank_pincode", label: "Pin Code", placeholder: "Pin Code" },
          { name: "bank_telephone", label: "Telephone", placeholder: "Telephone" },
          { name: "bank_email", label: "Email", placeholder: "Email" },
          { name: "bank_mobile", label: "Mobile", placeholder: "Mobile" },
          { name: "bank_website", label: "Website", placeholder: "Website" },
          { name: "bank_fax", label: "Fax No.", placeholder: "Fax Number" },
          { type: "list_preview", name: "banks", label: "Saved bank accounts" },

          { type: "section", label: "Contact Details", hint: "SBAC CheckBox5 · multi via Add Contact" },
          { name: "contact_person", label: "Contact Person", placeholder: "Contact Person" },
          { name: "contact_job_title", label: "Job Title", placeholder: "Job Title" },
          {
            name: "contact_designation",
            label: "Designation",
            type: "select",
            options: ["", ...designations],
          },
          { name: "contact_mobile", label: "Mobile", placeholder: "Mobile" },
          { name: "contact_whatsapp", label: "Whatsapp Number", placeholder: "Whatsapp Number" },
          { name: "contact_telephone", label: "Telephone", placeholder: "Telephone" },
          { name: "contact_dob", label: "DOB", type: "date" },
          { name: "contact_associate_date", label: "Associate Date", type: "date" },
          { name: "contact_email", label: "Email", placeholder: "Email" },
          { name: "contact_commission", label: "Commission %", type: "number", placeholder: "Commission %" },
          { type: "list_preview", name: "contacts", label: "Saved contacts" },

          { type: "section", label: "Export Details", hint: "SBAC chkexport" },
          { name: "export_packing_charge", label: "Packing Charge", placeholder: "Packing Charge" },
          { name: "export_carriage_by", label: "Pre-Carriage by", placeholder: "Pre-Carriage by" },
          { name: "export_receipt_by", label: "Place of Receipt by Pre-Carrier", placeholder: "Place of Receipt" },
          { name: "export_port_discharge", label: "Port of Discharge", placeholder: "Port of Discharge" },
          { name: "export_port_loading", label: "Port of Loading", placeholder: "Port of Loading" },
          { name: "export_lut_bond", label: "LUT/Bond No", placeholder: "LUT/Bond No" },
          { name: "export_final_dest", label: "Final Destination", placeholder: "Final Destination" },
        ],
        async (data) => {
          const addresses = Array.isArray(data.addresses) ? data.addresses : [];
          const banks = Array.isArray(data.banks) ? data.banks : [];
          const contacts = Array.isArray(data.contacts) ? data.contacts : [];
          // If user filled address fields but didn't click Add, keep as primary + include once
          const draftAddr = {
            address_type: data.addr_type || "",
            country: data.addr_country || "India",
            state: data.addr_state || "",
            city: data.addr_city || "",
            area: data.addr_area || "",
            address: data.addr_address || "",
            pincode: data.addr_pincode || "",
            telephone: data.addr_telephone || "",
            email: data.addr_email || "",
            mobile: data.addr_mobile || "",
            website: data.addr_website || "",
            fax: data.addr_fax || "",
          };
          if (draftAddr.address || draftAddr.city || draftAddr.pincode) {
            const dup = addresses.some((a) => a.address === draftAddr.address && a.address_type === draftAddr.address_type);
            if (!dup) addresses.push(draftAddr);
          }
          const draftBank = {
            bank_name: data.bank_name || "",
            account_holder: data.bank_holder || "",
            account_no: data.bank_account || "",
            swift: data.bank_swift || "",
            ifsc: data.bank_ifsc || "",
            country: data.bank_country || "",
            state: data.bank_state || "",
            city: data.bank_city || "",
            address: data.bank_address || "",
            pincode: data.bank_pincode || "",
            telephone: data.bank_telephone || "",
            email: data.bank_email || "",
            mobile: data.bank_mobile || "",
            website: data.bank_website || "",
            fax: data.bank_fax || "",
          };
          if (draftBank.bank_name || draftBank.account_no) {
            const dup = banks.some((b) => b.account_no === draftBank.account_no && b.bank_name === draftBank.bank_name);
            if (!dup) banks.push(draftBank);
          }
          const draftContact = {
            person: data.contact_person || "",
            job_title: data.contact_job_title || "",
            designation: data.contact_designation || "",
            mobile: data.contact_mobile || "",
            whatsapp: data.contact_whatsapp || "",
            telephone: data.contact_telephone || "",
            dob: data.contact_dob || "",
            associate_date: data.contact_associate_date || "",
            email: data.contact_email || "",
            commission: data.contact_commission || "",
          };
          if (draftContact.person || draftContact.mobile) {
            const dup = contacts.some((c) => c.person === draftContact.person && c.mobile === draftContact.mobile);
            if (!dup) contacts.push(draftContact);
          }
          const primary = addresses.find((a) => /billing/i.test(a.address_type || "")) || addresses[0] || draftAddr;
          const branchList = Array.isArray(data.branch_list) ? data.branch_list.join(", ") : (data.branch_list || "");
          const r = await API.post("/api/crm/customers", {
            name: data.name,
            email: primary.email || data.contact_email || data.emp_email || "",
            gstin: data.gstin || "",
            phone: data.whatsapp || primary.mobile || data.contact_mobile || "",
            billing_address: primary.address || "",
            party_type: data.party_type || "customer",
            region: primary.city || data.work_area || "",
            credit_limit: Number(data.credit_limit || 0),
            custom: {
              party_nature: data.party_nature || "Domestic",
              under_account: data.under_account || "",
              file_as: data.file_as || "",
              whatsapp: data.whatsapp || "",
              joining_date: data.joining_date || "",
              work_area: data.work_area || "",
              repeat_order_days: data.repeat_order_days || "",
              branch_list: branchList,
              show_order_followup: data.show_order_followup || "Yes",
              transport: data.transport || "",
              agent: data.agent || "",
              employee: {
                department: data.emp_department || "",
                designation: data.emp_designation || "",
                email: data.emp_email || "",
                mobile: data.emp_mobile || "",
                reporting_person: data.emp_reporting_person || "",
              },
              addresses,
              address_type: primary.address_type || "",
              city: primary.city || "",
              state: primary.state || "",
              country: primary.country || "India",
              pincode: primary.pincode || "",
              area: primary.area || "",
              telephone: primary.telephone || "",
              website: primary.website || "",
              fax: primary.fax || "",
              opening_balance: data.opening_balance || "",
              opening_drcr: data.opening_drcr || "Dr",
              currency: data.currency || "",
              credit_days: data.credit_days || "",
              grade: data.grade || "",
              pan: data.pan || "",
              cts_no: data.cts_no || "",
              pvt_marka: data.pvt_marka || "",
              sales_target: data.sales_target || "",
              ecc_no: data.ecc_no || "",
              status_active: data.status_active || "Active",
              tcs_allow: data.tcs_allow || "No",
              tds_allow: data.tds_allow || "No",
              company: {
                company_type: data.company_type || "",
                customer_type: data.customer_type || "",
                head_quarter: data.head_quarter || "",
                area: data.company_area || "",
                discount_pct: data.discount_pct || "",
                discount_name: data.discount_name || "",
                alias: data.alias || "",
                remarks: data.remarks || "",
                show_remarks: data.show_remarks || "No",
              },
              banks,
              contacts,
              export: {
                packing_charge: data.export_packing_charge || "",
                carriage_by: data.export_carriage_by || "",
                receipt_by: data.export_receipt_by || "",
                port_discharge: data.export_port_discharge || "",
                port_loading: data.export_port_loading || "",
                lut_bond: data.export_lut_bond || "",
                final_dest: data.export_final_dest || "",
              },
              source: "kanha_party_master",
              sbac_parity: "2026-08-02-live",
            },
          });
          toast(r.message || `Party ${r.code || r.name} saved`);
          showSavedDetail("Party Master saved", r);
          pageCRM(el);
        },
        {
          eyebrow: "Master · Party (SBAC exact fields · live scan)",
          saveLabel: "Submit",
          extraButtons: [
            {
              id: "mf-gst-search",
              label: "GST Search",
              onClick: async (overlay) => {
                const gstin = mfRead(overlay, "gstin");
                if (!gstin) return toast("GST Number enter karo");
                try {
                  const r = await API.post("/api/crm/gst-lookup", { gstin });
                  const set = (name, val) => {
                    const el = overlay.querySelector(`[data-mf="${name}"]`);
                    if (el && val != null && val !== "") el.value = val;
                  };
                  set("name", r.trade_name || r.legal_name);
                  set("party_nature", r.party_nature || "Domestic");
                  set("addr_type", "Billing Address");
                  set("addr_address", r.billing_address || "");
                  set("addr_state", r.state || "");
                  set("addr_city", r.city || "");
                  set("addr_pincode", r.pincode || "");
                  set("addr_country", r.country || "India");
                  toast(r.message || "GST filled");
                } catch (e) {
                  toast(e.message || "GST Search failed");
                }
              },
            },
            {
              id: "mf-add-address",
              label: "Add Address",
              onClick: (overlay) => {
                const item = {
                  address_type: mfRead(overlay, "addr_type"),
                  country: mfRead(overlay, "addr_country") || "India",
                  state: mfRead(overlay, "addr_state"),
                  city: mfRead(overlay, "addr_city"),
                  area: mfRead(overlay, "addr_area"),
                  address: mfRead(overlay, "addr_address"),
                  pincode: mfRead(overlay, "addr_pincode"),
                  telephone: mfRead(overlay, "addr_telephone"),
                  email: mfRead(overlay, "addr_email"),
                  mobile: mfRead(overlay, "addr_mobile"),
                  website: mfRead(overlay, "addr_website"),
                  fax: mfRead(overlay, "addr_fax"),
                };
                if (!item.address && !item.city) return toast("Address ya City bharo");
                mfListPush(overlay, "addresses", item, `${item.address_type || "Address"} · ${item.city || item.address || item.pincode}`);
                mfClear(overlay, [
                  "addr_address", "addr_area", "addr_pincode", "addr_telephone", "addr_email",
                  "addr_mobile", "addr_website", "addr_fax",
                ]);
                toast("Address added");
              },
            },
            {
              id: "mf-add-bank",
              label: "Add Bank",
              onClick: (overlay) => {
                const item = {
                  bank_name: mfRead(overlay, "bank_name"),
                  account_holder: mfRead(overlay, "bank_holder"),
                  account_no: mfRead(overlay, "bank_account"),
                  swift: mfRead(overlay, "bank_swift"),
                  ifsc: mfRead(overlay, "bank_ifsc"),
                  country: mfRead(overlay, "bank_country"),
                  state: mfRead(overlay, "bank_state"),
                  city: mfRead(overlay, "bank_city"),
                  address: mfRead(overlay, "bank_address"),
                  pincode: mfRead(overlay, "bank_pincode"),
                  telephone: mfRead(overlay, "bank_telephone"),
                  email: mfRead(overlay, "bank_email"),
                  mobile: mfRead(overlay, "bank_mobile"),
                  website: mfRead(overlay, "bank_website"),
                  fax: mfRead(overlay, "bank_fax"),
                };
                if (!item.bank_name || !item.account_no) return toast("Bank Name aur Account No. required");
                mfListPush(overlay, "banks", item, `${item.bank_name} · ${item.account_no}`);
                mfClear(overlay, [
                  "bank_name", "bank_holder", "bank_account", "bank_swift", "bank_ifsc",
                  "bank_state", "bank_city", "bank_address", "bank_pincode", "bank_telephone",
                  "bank_email", "bank_mobile", "bank_website", "bank_fax",
                ]);
                toast("Bank added");
              },
            },
            {
              id: "mf-add-contact",
              label: "Add Contact",
              onClick: (overlay) => {
                const item = {
                  person: mfRead(overlay, "contact_person"),
                  job_title: mfRead(overlay, "contact_job_title"),
                  designation: mfRead(overlay, "contact_designation"),
                  mobile: mfRead(overlay, "contact_mobile"),
                  whatsapp: mfRead(overlay, "contact_whatsapp"),
                  telephone: mfRead(overlay, "contact_telephone"),
                  dob: mfRead(overlay, "contact_dob"),
                  associate_date: mfRead(overlay, "contact_associate_date"),
                  email: mfRead(overlay, "contact_email"),
                  commission: mfRead(overlay, "contact_commission"),
                };
                if (!item.person) return toast("Contact Person required");
                mfListPush(overlay, "contacts", item, `${item.person} · ${item.designation || item.mobile || ""}`);
                mfClear(overlay, [
                  "contact_person", "contact_job_title", "contact_designation", "contact_mobile",
                  "contact_whatsapp", "contact_telephone", "contact_dob", "contact_associate_date",
                  "contact_email", "contact_commission",
                ]);
                toast("Contact added");
              },
            },
          ],
        }
      );
    });
    $("#add-opp")?.addEventListener("click", async () => {
      const title = prompt("Opportunity title", "New deal");
      if (!title) return;
      const amount = Number(prompt("Amount", "250000") || 0);
      const r = await API.post("/api/crm/opportunities", {
        title,
        amount,
        stage: "prospect",
        probability: 40,
        lead_id: leads[0]?.id || null,
        customer_id: customers[0]?.id || null,
      });
      toast("Opportunity created");
      showSavedDetail("Opportunity saved", r);
      pageCRM(el);
    });
    $("#add-quote")?.addEventListener("click", async () => {
      const cust = customers[0];
      if (!cust) return toast("Create a customer first");
      const products = await API.get("/api/inventory/products");
      const p = products[0];
      if (!p) return toast("No products");
      const r = await API.post("/api/crm/quotations", {
        customer_id: cust.id,
        status: "sent",
        lines: [{ product_id: p.id, sku: p.sku, name: p.name, qty: 10, rate: p.sale_price, gst_rate: p.gst_rate || 18 }],
      });
      toast(`Quote ${r.number} · ${money(r.total)}`);
      pageCRM(el);
    });
    $("#lead-quote")?.addEventListener("click", async () => {
      if (!leads[0]) return;
      const r = await API.post(`/api/crm/flow/lead-to-quote/${leads[0].id}`);
      toast(r.message || `Quote ${r.quotation || r.number}`);
      flowSave("Lead → Quote", r, "Quotations list + Sales Quote→SO path.");
      pageCRM(el);
    });
    el.querySelectorAll("[data-crm-d]").forEach((btn) => {
      const kind = btn.getAttribute("data-crm-d");
      const id = Number(btn.getAttribute("data-id"));
      const map = { lead: leads, cust: customers, opp: opps, quote: quotes };
      const row = (map[kind] || []).find((x) => x.id === id);
      btn.addEventListener("click", () => openDetail(`${kind} #${id}`, row || {}, { eyebrow: "CRM detail", showJson: false }));
    });
  }

  function barcodeSvg(code, opts = {}) {
    const raw = String(code || "");
    const h = opts.height || 48;
    let bits = "101";
    for (let i = 0; i < raw.length; i++) {
      const n = raw.charCodeAt(i) % 10;
      const patterns = ["110110", "100100", "110010", "101100", "100110", "110001", "101001", "100011", "111000", "100101"];
      bits += patterns[n] + "0";
    }
    bits += "101";
    const unit = 1.6;
    const bars = [];
    let x = 0;
    for (let i = 0; i < bits.length; i++) {
      if (bits[i] === "1") bars.push(`<rect x="${x}" y="0" width="${unit}" height="${h}" fill="#0f172a"/>`);
      x += unit;
    }
    const w = Math.ceil(x + 4);
    return `<svg class="bc-svg" viewBox="0 0 ${w} ${h + 16}" width="${Math.min(220, w)}" height="${h + 16}" aria-hidden="true">${bars.join("")}<text x="${w / 2}" y="${h + 12}" text-anchor="middle" font-size="10" font-family="IBM Plex Mono, monospace" fill="#334155">${raw}</text></svg>`;
  }

  async function pagePOS(el) {
    const [products, customers, wh] = await Promise.all([
      API.get("/api/inventory/products"),
      API.get("/api/crm/customers"),
      API.get("/api/inventory/warehouses"),
    ]);
    const cart = [];
    const walkin = customers.find((c) => c.code === "WALKIN") || customers[0];
    const sellable = products.filter((p) => Number(p.sale_price) > 0);

    function cartTotals() {
      let sub = 0;
      let tax = 0;
      cart.forEach((ln) => {
        const amt = ln.qty * ln.rate;
        sub += amt;
        tax += amt * (ln.gst_rate || 18) / 100;
      });
      return { sub: Math.round(sub * 100) / 100, tax: Math.round(tax * 100) / 100, total: Math.round((sub + tax) * 100) / 100 };
    }

    function renderCart() {
      const box = $("#pos-cart");
      const tot = $("#pos-totals");
      if (!box) return;
      if (!cart.length) {
        box.innerHTML = `<div class="pos-empty">Scan barcode / SKU — USB scanner ya type + Enter</div>`;
      } else {
        box.innerHTML = table(
          ["Item", "Barcode", "Qty", "Rate", "Amount", ""],
          cart.map((ln, idx) => [
            `<strong>${ln.name}</strong><br><small>${ln.sku}</small>`,
            `<code>${ln.barcode || "—"}</code>`,
            `<input type="number" min="1" step="1" value="${ln.qty}" data-qty="${idx}" class="pos-qty" />`,
            money(ln.rate),
            money(ln.qty * ln.rate),
            `<button type="button" class="btn btn-ghost btn-sm" data-rm="${idx}">✕</button>`,
          ])
        );
      }
      const t = cartTotals();
      if (tot) {
        tot.innerHTML = `
          <div><span>Subtotal</span><strong>${money(t.sub)}</strong></div>
          <div><span>GST</span><strong>${money(t.tax)}</strong></div>
          <div class="pos-totals__grand"><span>Total</span><strong>${money(t.total)}</strong></div>`;
      }
      box.querySelectorAll("[data-qty]").forEach((inp) => {
        inp.addEventListener("change", () => {
          const i = Number(inp.getAttribute("data-qty"));
          cart[i].qty = Math.max(1, Number(inp.value) || 1);
          renderCart();
        });
      });
      box.querySelectorAll("[data-rm]").forEach((btn) => {
        btn.addEventListener("click", () => {
          cart.splice(Number(btn.getAttribute("data-rm")), 1);
          renderCart();
        });
      });
    }

    async function addByCode(code) {
      const raw = String(code || "").trim();
      if (!raw) return;
      const err = $("#pos-scan-err");
      if (err) err.textContent = "";
      try {
        const p = await API.get(`/api/inventory/products/lookup?code=${encodeURIComponent(raw)}`);
        if (!Number(p.sale_price)) {
          if (err) err.textContent = "This SKU has no sale price (raw material)";
          return;
        }
        const hit = cart.find((c) => c.product_id === p.id);
        if (hit) hit.qty += 1;
        else {
          cart.push({
            product_id: p.id,
            sku: p.sku,
            name: p.name,
            barcode: p.barcode,
            qty: 1,
            rate: p.sale_price,
            gst_rate: p.gst_rate || 18,
          });
        }
        toast(`+ ${p.name}`);
        renderCart();
      } catch (e) {
        if (err) err.textContent = e.message || "Not found";
        toast(e.message || "Barcode not found");
      }
    }

    el.innerHTML = `
      <div class="pos-layout">
        <div class="panel glass pos-main">
          <div class="panel-hd"><h2>Scan Billing</h2>
            <span class="pill ok">Barcode-first · fast counter</span></div>
          <div class="panel-bd">
            <label class="pos-scan-label">Scan / type barcode</label>
            <div class="pos-scan-row">
              <input id="pos-scan" class="pos-scan" type="text" inputmode="numeric" autocomplete="off" placeholder="Scan here — e.g. 8901001000001" autofocus />
              <button type="button" class="btn btn-primary" id="pos-add">Add</button>
              <button type="button" class="btn btn-accent" id="pos-cam" title="Camera barcode">📷 Cam</button>
            </div>
            <div class="pos-cam-box" id="pos-cam-box" hidden>
              <video id="pos-video" playsinline muted></video>
              <div class="pos-cam-actions">
                <button type="button" class="btn btn-ghost btn-sm" id="pos-cam-stop">Stop camera</button>
                <span class="hint">Phone/laptop camera se barcode padhega (Chrome/Edge)</span>
              </div>
            </div>
            <div class="error" id="pos-scan-err"></div>
            <div class="pos-chips">
              ${sellable.slice(0, 5).map((p) => `
                <button type="button" class="pos-chip" data-code="${p.barcode || p.sku}" title="${p.name}">
                  <strong>${p.sku}</strong>
                  <span>${barcodeSvg(p.barcode || p.sku, { height: 28 })}</span>
                  <em>${money(p.sale_price)}</em>
                </button>`).join("")}
            </div>
            <div id="pos-cart" class="pos-cart"></div>
          </div>
        </div>
        <div class="panel glass pos-side">
          <div class="panel-hd"><h2>Checkout</h2></div>
          <div class="panel-bd">
            <div class="field"><label>Customer</label>
              <select id="pos-customer">
                ${customers.map((c) => `<option value="${c.id}" ${walkin && c.id === walkin.id ? "selected" : ""}>${c.code} · ${c.name}</option>`).join("")}
              </select>
            </div>
            <div class="field"><label>Warehouse</label>
              <select id="pos-wh">${wh.map((w) => `<option value="${w.id}">${w.code} · ${w.name}</option>`).join("")}</select>
            </div>
            <div class="field"><label>Pay method</label>
              <select id="pos-method">
                <option value="cash">Cash</option>
                <option value="upi">UPI</option>
                <option value="card">Card</option>
                <option value="bank">Bank</option>
              </select>
            </div>
            <label class="pos-paynow"><input type="checkbox" id="pos-pay" checked /> Pay now (mark paid)</label>
            <div id="pos-totals" class="pos-totals"></div>
            <button type="button" class="btn btn-ghost" style="width:100%;margin-top:8px" id="pos-demo">Load demo cart</button>
            <button type="button" class="btn btn-accent" style="width:100%;margin-top:8px" id="pos-checkout">Post invoice</button>
            <div class="hint" style="margin-top:10px">Demo barcodes: <b>8901001000001</b> … <b>0004</b>. USB scanner = type + Enter.</div>
            <div id="pos-last" class="pos-last" hidden></div>
          </div>
        </div>
      </div>`;

    renderCart();
    const scan = $("#pos-scan");
    const doAdd = () => {
      addByCode(scan?.value);
      if (scan) { scan.value = ""; scan.focus(); }
    };
    $("#pos-add")?.addEventListener("click", doAdd);
    scan?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); doAdd(); }
    });
    el.querySelectorAll("[data-code]").forEach((b) => {
      b.addEventListener("click", () => addByCode(b.getAttribute("data-code")));
    });

    let camStream = null;
    let camTimer = null;
    async function stopCam() {
      if (camTimer) { clearInterval(camTimer); camTimer = null; }
      if (camStream) { camStream.getTracks().forEach((t) => t.stop()); camStream = null; }
      const box = $("#pos-cam-box");
      if (box) box.hidden = true;
    }
    async function startCam() {
      const box = $("#pos-cam-box");
      const video = $("#pos-video");
      if (!box || !video) return;
      if (!navigator.mediaDevices?.getUserMedia) {
        toast("Camera not available on this device");
        return;
      }
      try {
        camStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false,
        });
        video.srcObject = camStream;
        await video.play();
        box.hidden = false;
        const Detector = window.BarcodeDetector;
        if (!Detector) {
          toast("BarcodeDetector missing — type code or use USB scanner");
          return;
        }
        const formats = ["ean_13", "ean_8", "code_128", "qr_code", "upc_a", "upc_e"];
        let detector;
        try { detector = new Detector({ formats }); }
        catch { detector = new Detector(); }
        let last = "";
        camTimer = setInterval(async () => {
          try {
            if (video.readyState < 2) return;
            const codes = await detector.detect(video);
            const val = codes?.[0]?.rawValue;
            if (val && val !== last) {
              last = val;
              await addByCode(val);
              setTimeout(() => { last = ""; }, 1500);
            }
          } catch {}
        }, 450);
      } catch (e) {
        toast(e.message || "Camera permission denied");
      }
    }
    $("#pos-cam")?.addEventListener("click", () => {
      if (camStream) stopCam();
      else startCam();
    });
    $("#pos-cam-stop")?.addEventListener("click", stopCam);

    $("#pos-demo")?.addEventListener("click", () => {
      const picks = sellable.slice(0, 3);
      if (!picks.length) return toast("No sellable products");
      cart.length = 0;
      picks.forEach((p) => {
        cart.push({
          product_id: p.id,
          sku: p.sku,
          name: p.name,
          barcode: p.barcode,
          qty: 1,
          rate: p.sale_price,
          gst_rate: p.gst_rate || 18,
        });
      });
      renderCart();
      flowSave("Demo cart loaded", { lines: cart.length, skus: cart.map((c) => c.sku) }, "Ab Post invoice dabao → Sales invoice + stock − + Books receipt.");
    });

    $("#pos-checkout")?.addEventListener("click", async () => {
      if (!cart.length) return toast("Cart empty — scan products first");
      try {
        const r = await API.post("/api/sales/pos/checkout", {
          customer_id: Number($("#pos-customer")?.value),
          warehouse_id: Number($("#pos-wh")?.value),
          pay_now: !!$("#pos-pay")?.checked,
          method: $("#pos-method")?.value || "cash",
          lines: cart.map((ln) => ({ product_id: ln.product_id, qty: ln.qty })),
        });
        cart.length = 0;
        renderCart();
        const last = $("#pos-last");
        if (last) {
          last.hidden = false;
          last.innerHTML = `<strong>${r.invoice.number}</strong> · ${money(r.invoice.total)} · ${r.invoice.status}<br><small>${r.warehouse} · ${r.invoice.customer}</small>`;
        }
        toast(`Billed ${r.invoice.number} · ${money(r.invoice.total)}`);
        flowSave(`POS ${r.invoice.number}`, r, "Sales → Invoices me dikhega · Inventory down · Kanha Books sales/receipt · Dashboard KPIs.");
        scan?.focus();
      } catch (e) {
        toast(e.message || "Checkout failed");
      }
    });
  }

  async function pageRFID(el) {
    const [tags, scans, products, wh] = await Promise.all([
      API.get("/api/rfid/tags"),
      API.get("/api/rfid/scans"),
      API.get("/api/inventory/products"),
      API.get("/api/inventory/warehouses"),
    ]);
    el.innerHTML = `
      <div class="pos-layout">
        <div class="panel glass">
          <div class="panel-hd"><h2>RFID Gate</h2><span class="pill ok">UHF demo · no hardware needed</span></div>
          <div class="panel-bd">
            <p class="hint">Tag pe “scan” = warehouse reader beep. Inbound/Outbound stock bhi update hota hai.</p>
            <div class="field"><label>EPC / Tag ID</label>
              <input id="rfid-epc" list="rfid-epc-list" placeholder="E28011601000ABCD" />
              <datalist id="rfid-epc-list">${tags.map((t) => `<option value="${t.epc}">${t.sku} · ${t.location_code}</option>`).join("")}</datalist>
            </div>
            <div class="field"><label>Action</label>
              <select id="rfid-action">
                <option value="locate">Locate</option>
                <option value="inbound">Inbound (+1 stock)</option>
                <option value="outbound">Outbound (−1 stock)</option>
                <option value="cycle">Cycle count</option>
              </select>
            </div>
            <div class="field"><label>Bin / Location</label>
              <input id="rfid-loc" placeholder="A-01" />
            </div>
            <div class="auto-actions">
              <button type="button" class="btn btn-primary" id="rfid-scan">Scan tag</button>
              ${tags.slice(0, 3).map((t) => `<button type="button" class="btn btn-ghost btn-sm" data-epc="${t.epc}">${t.epc.slice(-8)}</button>`).join("")}
            </div>
            <div id="rfid-out" class="auto-out"></div>
            <div class="rfid-wave" aria-hidden="true"><i></i><i></i><i></i></div>
          </div>
        </div>
        <div class="panel glass">
          <div class="panel-hd"><h2>Bind new tag</h2></div>
          <div class="panel-bd">
            <div class="field"><label>EPC</label><input id="rfid-new-epc" placeholder="E28011609999ABCD" /></div>
            <div class="field"><label>Product</label>
              <select id="rfid-prod">${products.map((p) => `<option value="${p.id}">${p.sku} · ${p.name}</option>`).join("")}</select>
            </div>
            <div class="field"><label>Warehouse</label>
              <select id="rfid-wh">${wh.map((w) => `<option value="${w.id}">${w.code}</option>`).join("")}</select>
            </div>
            <button type="button" class="btn btn-accent" style="width:100%" id="rfid-bind">Bind RFID</button>
          </div>
        </div>
      </div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Active tags</h2></div><div class="panel-bd">
          ${table(["EPC", "SKU", "Product", "Bin", "Last scan", "Status"], tags.map((t) => [
            `<code>${t.epc}</code>`, t.sku, t.product, t.location_code, (t.last_scan_at || "—").slice(0, 19), `<span class="pill">${t.status}</span>`
          ]))}
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Scan log</h2></div><div class="panel-bd">
          ${table(["When", "EPC", "Action", "SKU", "Note"], scans.map((s) => [
            (s.created_at || "").slice(0, 19), s.epc, s.action, s.sku || "—", s.notes || "—"
          ]))}
        </div></div>
      </div>`;
    const doScan = async (epc) => {
      try {
        const r = await API.post("/api/rfid/scan", {
          epc: epc || $("#rfid-epc")?.value,
          action: $("#rfid-action")?.value || "locate",
          location_code: $("#rfid-loc")?.value || undefined,
          warehouse_id: wh[0]?.id,
        });
        $("#rfid-out").innerHTML = `<pre class="report-pre">${JSON.stringify(r, null, 2)}</pre>`;
        toast(r.message || "Scanned");
        setTimeout(() => pageRFID(el), 600);
      } catch (e) {
        toast(e.message || "RFID scan failed");
      }
    };
    $("#rfid-scan")?.addEventListener("click", () => doScan());
    el.querySelectorAll("[data-epc]").forEach((b) => {
      b.addEventListener("click", () => {
        if ($("#rfid-epc")) $("#rfid-epc").value = b.getAttribute("data-epc");
        doScan(b.getAttribute("data-epc"));
      });
    });
    $("#rfid-bind")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/rfid/tags", {
          epc: $("#rfid-new-epc")?.value,
          product_id: Number($("#rfid-prod")?.value),
          warehouse_id: Number($("#rfid-wh")?.value),
          location_code: $("#rfid-loc")?.value || "A-01",
        });
        toast(`Tag ${r.tag.epc} bound`);
        pageRFID(el);
      } catch (e) {
        toast(e.message || "Bind failed");
      }
    });
  }

  async function pageSales(el) {
    const [orders, invoices, eway, quotes, payments, deliveries, pendingSO, pendingDC, customers, products, warehouses] =
      await Promise.all([
        API.get("/api/sales/orders"),
        API.get("/api/sales/invoices"),
        API.get("/api/logistics/eway"),
        API.get("/api/crm/quotations"),
        API.get("/api/sales/payments"),
        API.get("/api/sales/deliveries"),
        API.get("/api/sales/orders/pending-challan").catch(() => []),
        API.get("/api/sales/challans/pending-invoice").catch(() => []),
        API.get("/api/crm/customers").catch(() => []),
        API.get("/api/inventory/products").catch(() => []),
        API.get("/api/inventory/warehouses").catch(() => []),
      ]);
    const unpaid = (invoices || []).find((i) => (i.invoice_type || "sales") !== "credit" && (i.balance || 0) > 0) || invoices.find((i) => (i.invoice_type || "sales") !== "credit");
    const openQuote = (quotes || []).find((q) => ["draft", "sent", "accepted"].includes(String(q.status || "").toLowerCase())) || quotes[0];
    const openSO = (orders || []).find((o) => String(o.status || "").toLowerCase() !== "invoiced") || orders[0];
    const salesInvs = (invoices || []).filter((i) => (i.invoice_type || "sales") !== "credit");
    const credits = (invoices || []).filter((i) => (i.invoice_type || "") === "credit");
    const docCtx = { customers, products, warehouses };
    el.innerHTML = `
      ${moduleIntro("Sales", "SO → Delivery Challan (bal qty) → Invoice · ya Direct Invoice. Class-level money loop.", {
        orders: orders.length, pending_challan: (pendingSO || []).length, pending_invoice: (pendingDC || []).length,
        invoices: salesInvs.length, credit_notes: credits.length,
        deliveries: (deliveries || []).length, payments: (payments || []).length,
        unpaid: salesInvs.filter((i) => (i.balance || 0) > 0).length,
      })}
      <div class="panel glass"><div class="panel-hd"><h2>Sales Orders</h2>
        <div class="row" style="gap:6px;flex-wrap:wrap">
          <button class="btn btn-primary btn-sm" id="add-so">+ Sales Order</button>
          <button class="btn btn-accent btn-sm" id="quote-to-so" ${openQuote ? "" : "disabled"}>Quote → SO</button>
          <button class="btn btn-ghost btn-sm" id="so-to-inv" ${openSO ? "" : "disabled"} title="Atomic: DN + Invoice (old path)">SO → Invoice (one-shot)</button>
        </div></div><div class="panel-bd">
        ${table(
          ["Number", "Customer", "Status", "Bal Qty", "Total", "Approval", ""],
          orders.map((o) => [
            o.number,
            o.customer_name || "—",
            o.status,
            o.bal_qty ?? "—",
            money(o.total),
            `<span class="pill ${o.approval_status === "approved" ? "ok" : o.approval_status === "pending" ? "warn" : "danger"}">${o.approval_status}</span>`,
            `${o.approval_status === "pending"
              ? `<button class="btn btn-accent btn-sm" data-so-approve="${o.id}">Approve</button> <button class="btn btn-ghost btn-sm" data-so-reject="${o.id}">Reject</button>`
              : ""} <button class="btn btn-ghost btn-sm" data-so-d="${o.id}">Details</button>`,
          ]),
          "No sales orders — + Sales Order ya Quote → SO."
        )}
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Pending SO → Delivery Challan</h2></div>
        <div class="panel-bd">
          <div class="row" style="gap:8px;flex-wrap:wrap;margin-bottom:10px">
            <input id="dc-filter-party" type="text" placeholder="Party Name" style="max-width:180px" />
            <input id="dc-filter-order" type="text" placeholder="Order No" style="max-width:120px" />
            <button type="button" class="btn btn-ghost btn-sm" id="dc-filter-go">Search</button>
          </div>
          <div id="dc-pending-box">${table(
          ["Order No", "Date", "Party", "Total Qty", "Bal Qty", "Total Amt", ""],
          (pendingSO || []).map((o) => [
            o.number,
            o.order_date || "—",
            o.customer_name || "—",
            o.total_qty,
            o.bal_qty,
            money(o.total),
            `<button class="btn btn-primary btn-sm" data-mk-challan="${o.id}">Create Challan</button>`,
          ]),
          "Koi pending SO nahi — bal qty wale orders yahan aate hain."
        )}</div></div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Delivery Challans</h2></div>
        <div class="panel-bd">${table(
          ["Challan", "SO", "Customer", "Status", "Qty", "Amt", ""],
          (deliveries || []).map((d) => [
            d.number, d.sales_order || "—", d.customer_name || "—",
            `<span class="pill">${d.status}</span>`,
            d.total_qty ?? d.line_count ?? (Array.isArray(d.lines) ? d.lines.length : d.lines),
            money(d.total || 0),
            `<button class="btn btn-ghost btn-sm" data-dn-d="${d.id}">Details</button>`,
          ]),
          "No challans yet — Pending SO se Create Challan."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Pending Challan → Sales Invoice</h2>
        <button class="btn btn-accent btn-sm" id="add-dir-inv">+ Direct Invoice</button></div>
        <div class="panel-bd">${table(
          ["Challan No", "Date", "Party", "Total Qty", "Total Amt", ""],
          (pendingDC || []).map((d) => [
            d.number,
            d.challan_date || "—",
            d.customer_name || "—",
            d.total_qty,
            money(d.total),
            `<button class="btn btn-primary btn-sm" data-mk-inv="${d.id}">Create Invoice</button>`,
          ]),
          "Koi pending challan nahi — Direct Invoice bhi ban sakta hai."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Invoices</h2>
        <div class="row">
        <button class="btn btn-ghost btn-sm" id="print-inv" ${salesInvs[0] ? "" : "disabled"}>Print invoice</button>
        <button class="btn btn-accent btn-sm" id="rzp-pay" ${salesInvs.some((i) => (i.balance || 0) > 0) ? "" : "disabled"}>Razorpay settle</button>
        <button class="btn btn-primary btn-sm" id="pay-inv" ${unpaid ? "" : "disabled"}>Record payment</button>
        <button class="btn btn-accent btn-sm" id="credit-note" ${unpaid ? "" : "disabled"}>Credit note / return</button></div></div>
        <div class="panel-bd">${table(
          ["Number", "Type", "Customer", "Date", "Total", "Paid", "Balance", "Status", ""],
          salesInvs.map((i) => [
            i.number,
            i.invoice_type || "sales",
            i.customer_name || "—",
            i.invoice_date || "—",
            money(i.total),
            money(i.paid),
            money(i.balance),
            `<span class="pill">${i.status}</span>`,
            `<button class="btn btn-ghost btn-sm" data-inv-row="${i.id}">Details</button>
             <button class="btn btn-ghost btn-sm" data-inv-print="${i.id}">Print</button>`,
          ])
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Credit notes</h2></div>
        <div class="panel-bd">${table(
          ["CN", "Against", "Customer", "Amount", "Status"],
          credits.map((c) => [c.number, c.against_invoice || "—", c.customer_name || "—", money(c.total), `<span class="pill ok">${c.status}</span>`]),
          "No credit notes — issue return/credit from an invoice."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Payments received</h2></div>
        <div class="panel-bd">${table(
          ["Date", "Invoice", "Customer", "Amount", "Method", "Ref"],
          (payments || []).map((p) => [p.payment_date || "—", p.invoice_number || "—", p.customer_name || "—", money(p.amount), p.method, p.reference || "—"])
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>E-Way Bill</h2>
        <button class="btn btn-accent btn-sm" id="gen-eway">Generate e-way</button></div>
        <div class="panel-bd">
          ${stubNote("DEMO-LIVE e-Way — register linked to invoice with DEMO-EWB. Live NIC/GSP needs credentials + Legal approve.")}
          ${table(
            ["Doc", "Invoice", "Route", "Vehicle", "EWB No", "Valid", "Status"],
            eway.map((e) => [
              e.number,
              e.invoice_number || "—",
              `${e.from_place} → ${e.to_place}`,
              e.vehicle_no,
              e.ewb_no || "—",
              e.valid_upto || "—",
              `<span class="pill ok">${e.status}</span>`,
            ])
          )}
        </div></div>`;
    $("#add-so")?.addEventListener("click", () => {
      if (!(customers || []).length) return toast("Pehle Party Master me party banao");
      if (!(products || []).length) return toast("Pehle Item Master me item banao");
      openSalesDocForm(
        "Create Sales Order",
        docCtx,
        async (payload) => {
          const r = await API.post("/api/sales/orders", payload);
          toast(`SO ${r.number} saved`);
          flowSave(`Sales Order ${r.number}`, r, "Pending SO → Challan list me dikhega · Create Challan.");
          pageSales(el);
        },
        {
          eyebrow: "Sales · SO (SBAC exact fields · live scan)",
          saveLabel: "Submit",
          docKind: "sales_order",
        }
      );
    });
    $("#add-dir-inv")?.addEventListener("click", () => {
      if (!(customers || []).length) return toast("Pehle Party Master me party banao");
      if (!(products || []).length) return toast("Pehle Item Master me item banao");
      openSalesDocForm(
        "Direct Sales Invoice",
        docCtx,
        async (payload) => {
          const r = await API.post("/api/sales/invoices/direct", payload);
          toast(r.message || `Invoice ${r.number}`);
          flowSave(`Direct Invoice ${r.number}`, r, "Stock issue + Books sales voucher · Payment se settle.");
          pageSales(el);
        },
        {
          eyebrow: "Sales · Direct Invoice (SBAC exact fields · live scan)",
          saveLabel: "Save",
          docKind: "sales_invoice",
          refLabel: "Customer Order / Ref",
        }
      );
    });
    const renderPendingSO = (list) => {
      const box = $("#dc-pending-box");
      if (!box) return;
      box.innerHTML = table(
        ["Order No", "Date", "Party", "Total Qty", "Bal Qty", "Total Amt", ""],
        (list || []).map((o) => [
          o.number,
          o.order_date || "—",
          o.customer_name || "—",
          o.total_qty,
          o.bal_qty,
          money(o.total),
          `<button class="btn btn-primary btn-sm" data-mk-challan="${o.id}">Create Challan</button>`,
        ]),
        "Koi pending SO nahi — bal qty wale orders yahan aate hain."
      );
      box.querySelectorAll("[data-mk-challan]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const so = (pendingSO || []).find((o) => String(o.id) === String(btn.dataset.mkChallan))
            || (orders || []).find((o) => String(o.id) === String(btn.dataset.mkChallan));
          if (!so) return toast("SO not found");
          openChallanFromSOForm(so, warehouses || [], async (body) => {
            const r = await API.post(`/api/sales/flow/order-to-challan/${so.id}`, body);
            toast(r.message || `Challan ${r.number}`);
            flowSave(`Delivery Challan ${r.number}`, r, "Stock out · Pending Challan → Invoice se bill banao.");
            pageSales(el);
          });
        });
      });
    };
    renderPendingSO(pendingSO || []);
    $("#dc-filter-go")?.addEventListener("click", () => {
      const party = ($("#dc-filter-party")?.value || "").trim().toLowerCase();
      const order = ($("#dc-filter-order")?.value || "").trim().toLowerCase();
      const filtered = (pendingSO || []).filter((o) => {
        if (party && !(o.customer_name || "").toLowerCase().includes(party)) return false;
        if (order && !(o.number || "").toLowerCase().includes(order)) return false;
        return true;
      });
      renderPendingSO(filtered);
    });
    el.querySelectorAll("[data-mk-inv]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const dc = (pendingDC || []).find((d) => String(d.id) === String(btn.dataset.mkInv))
          || (deliveries || []).find((d) => String(d.id) === String(btn.dataset.mkInv));
        if (!dc) return toast("Challan not found");
        openMasterForm(
          "Create Invoice from Challan",
          [
            { type: "section", label: `Challan ${dc.number}`, hint: `${dc.customer_name || ""} · qty ${dc.total_qty ?? "—"} · ${money(dc.total || 0)}` },
            { name: "series_type", label: "Series Type", type: "select", options: ["Main", "Export"], value: "Main" },
            { name: "invoice_date", label: "Invoice Date", type: "date", value: new Date().toISOString().slice(0, 10) },
            { name: "transport", label: "Transport", value: (dc.custom && dc.custom.transport) || "" },
            { name: "delivery_type", label: "Delivery Type", type: "select", options: ["", "CIF", "PAID", "TO PAY", "TO PAY WITH CC", "TO PAY WITHOUT CC"] },
            { name: "freight_mode", label: "Freight Mode", type: "select", options: ["", "FOR", "PAID", "TO PAY"] },
            { name: "eway_bill_no", label: "E-way Bill No", placeholder: "E-way Bill No" },
            { name: "truck_no", label: "Truck No", placeholder: "Truck No" },
            { name: "pay_mode", label: "Pay Mode", type: "select", options: ["", "ADVANCE", "AFTER DELIVERY", "AGAINST PROFORMA", "CASH", "NEFT / RTGS", "UPI PAY"] },
            { name: "remarks", label: "Remarks", type: "textarea" },
            { name: "terms", label: "Term And Condition", type: "textarea", value: "100% Payment Against Proforma Invoice." },
            { type: "section", label: "Payment (optional)" },
            { name: "payment_mode", label: "Mode", placeholder: "Bank / Cash" },
            { name: "payment_amount", label: "Amount", type: "number", value: "0" },
            { name: "transaction_no", label: "Transaction No" },
            { name: "transaction_date", label: "Transaction Date", type: "date" },
            { name: "payment_narration", label: "Narration" },
          ],
          async (data) => {
            const r = await API.post(`/api/sales/flow/delivery-to-invoice/${dc.id}`, {
              series_type: data.series_type || "Main",
              invoice_date: data.invoice_date || "",
              transport: data.transport || "",
              delivery_type: data.delivery_type || "",
              freight_mode: data.freight_mode || "",
              eway_bill_no: data.eway_bill_no || "",
              truck_no: data.truck_no || "",
              pay_mode: data.pay_mode || "",
              remarks: data.remarks || "",
              terms: data.terms || "",
              payment_mode: data.payment_mode || "",
              payment_amount: Number(data.payment_amount || 0),
              transaction_no: data.transaction_no || "",
              transaction_date: data.transaction_date || "",
              payment_narration: data.payment_narration || "",
            });
            toast(r.message || "Invoice created");
            flowSave("Challan → Invoice", r, "Invoice list · Books · Payment.");
            pageSales(el);
          },
          { eyebrow: "Sales · Challan → Invoice (SBAC exact)", saveLabel: "Save" }
        );
      });
    });
    $("#quote-to-so")?.addEventListener("click", async () => {
      if (!openQuote) return;
      try {
        const r = await API.post(`/api/sales/flow/quote-to-order/${openQuote.id}`);
        toast(r.message || `SO ${r.order || r.number}${r.approval_status === "pending" ? " · pending approval" : ""}`);
        flowSave("Quote → Sales Order", r, "Pending SO → Challan list me · Create Challan.");
        pageSales(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
    el.querySelectorAll("[data-so-approve]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const r = await API.post(`/api/sales/orders/${btn.dataset.soApprove}/approve`, { note: "Approved from Sales UI" });
          toast(r.message || "Approved");
          flowSave("SO approved", r, "Ab Create Challan ya SO → Invoice.");
          pageSales(el);
        } catch (e) { toast(e.message || "Approve failed"); }
      });
    });
    el.querySelectorAll("[data-so-reject]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Reject this sales order?")) return;
        try {
          const r = await API.post(`/api/sales/orders/${btn.dataset.soReject}/reject`, { note: "Rejected from Sales UI" });
          toast(r.message || "Rejected");
          pageSales(el);
        } catch (e) { toast(e.message || "Reject failed"); }
      });
    });
    $("#so-to-inv")?.addEventListener("click", async () => {
      if (!openSO) return;
      try {
        const r = await API.post(`/api/sales/flow/order-to-invoice/${openSO.id}`);
        toast(r.message || `Invoice ${r.invoice || r.number}`);
        flowSave("SO → Invoice + Delivery", r, "Invoice + Delivery lists · Inventory down · Kanha Books sales voucher · Pay se receipt.");
        pageSales(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
    el.querySelectorAll("[data-so-d]").forEach((btn) => {
      const row = orders.find((o) => String(o.id) === btn.dataset.soD);
      btn.addEventListener("click", () => openDetail(row?.number || "SO", row || {}, { eyebrow: "Sales order", showJson: false }));
    });
    el.querySelectorAll("[data-dn-d]").forEach((btn) => {
      const row = (deliveries || []).find((d) => String(d.id) === btn.dataset.dnD);
      btn.addEventListener("click", () => openDetail(row?.number || "DN", row || {}, { eyebrow: "Delivery Challan", showJson: false }));
    });
    el.querySelectorAll("[data-inv-row]").forEach((btn) => {
      const row = salesInvs.find((i) => String(i.id) === btn.dataset.invRow);
      btn.addEventListener("click", () => openDetail(row?.number || "Invoice", row || {}, { eyebrow: "Invoice detail", showJson: false }));
    });
    $("#pay-inv")?.addEventListener("click", async () => {
      if (!unpaid) return toast("No invoice");
      const raw = prompt(
        `Payment for ${unpaid.number} (balance ${money(unpaid.balance)}). Amount > this bill → FIFO across open customer invoices.`,
        String(unpaid.balance || unpaid.total || 0)
      );
      if (raw == null) return;
      const amount = Number(raw);
      if (!amount || amount <= 0) return toast("Invalid amount");
      try {
        const r = await API.post("/api/sales/payments", { invoice_id: unpaid.id, amount, method: "bank", reference: "DEMO-PAY" });
        toast(r.message || `Paid · ${ (r.allocations || []).length } bill(s)`);
        flowSave(`Receipt ${r.journal || unpaid.number}`, r, "Bill-wise FIFO allocate · Books receipt · Cash/Bank book.");
        pageSales(el);
      } catch (e) { toast(e.message || "Payment failed"); }
    });
    $("#credit-note")?.addEventListener("click", async () => {
      if (!unpaid) return toast("No invoice");
      const reason = prompt(`Credit note / return reason for ${unpaid.number}`, "Sales return — damaged goods") || "Sales return";
      const raw = prompt(`Credit amount (blank = full balance ${money(unpaid.balance || unpaid.total)})`, String(unpaid.balance || unpaid.total || 0));
      if (raw == null) return;
      const amount = Number(raw);
      if (!amount || amount <= 0) return toast("Invalid amount");
      try {
        const r = await API.post("/api/sales/credit-notes", {
          invoice_id: unpaid.id,
          reason,
          amount,
          return_stock: true,
        });
        toast(r.message || "Credit note created");
        showSavedDetail("Credit note saved", r);
        pageSales(el);
      } catch (e) { toast(e.message || "Credit note failed"); }
    });
    $("#print-inv")?.addEventListener("click", () => {
      const inv = unpaid || salesInvs[0];
      if (!inv) return toast("No invoice to print");
      printSheet(buildTaxInvoiceHtml(inv), `Invoice ${inv.number}`);
    });
    $("#rzp-pay")?.addEventListener("click", async () => {
      const inv = unpaid || salesInvs.find((i) => (i.balance || 0) > 0) || salesInvs[0];
      if (!inv) return toast("No unpaid invoice");
      try {
        const intent = await API.post(`/api/payments/razorpay/intent?invoice_id=${inv.id}&amount=${inv.balance || inv.total}`);
        const cap = await API.post("/api/payments/razorpay/capture", {
          order_id: intent.order_id,
          invoice_id: inv.id,
          amount: intent.settle_amount || inv.balance || inv.total,
        });
        toast(cap.message || "Razorpay settled");
        flowSave(`Razorpay ${inv.number}`, cap, "Intent → capture → receipt voucher · invoice paid/partial.");
        pageSales(el);
      } catch (e) { toast(e.message || "Razorpay failed"); }
    });
    el.querySelectorAll("[data-inv-print]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const inv = salesInvs.find((i) => String(i.id) === btn.dataset.invPrint);
        if (!inv) return toast("Invoice not found");
        printSheet(buildTaxInvoiceHtml(inv), `Invoice ${inv.number}`);
      });
    });
    $("#gen-eway")?.addEventListener("click", async () => {
      const inv = invoices[0];
      const r = await API.post("/api/logistics/eway/generate", {
        invoice_id: inv?.id,
        from_place: "Jaipur, RJ",
        to_place: "Delhi, DL",
        distance_km: 280,
        vehicle_no: "RJ14AB1234",
        transporter: "Kanha Logistics",
      });
      toast(`E-Way ${r.ewb_no} · ${r.status}`);
      pageSales(el);
    });
  }

  async function pagePurchase(el) {
    const [vendors, orders, invoices, products, grns, vpay, pendingPO, pendingMRN, warehouses] = await Promise.all([
      API.get("/api/purchase/vendors"),
      API.get("/api/purchase/orders"),
      API.get("/api/purchase/invoices"),
      API.get("/api/inventory/products"),
      API.get("/api/purchase/grn"),
      API.get("/api/purchase/payments"),
      API.get("/api/purchase/orders/pending-grn").catch(() => []),
      API.get("/api/purchase/grn/pending-invoice").catch(() => []),
      API.get("/api/inventory/warehouses").catch(() => []),
    ]);
    const open = orders.filter((o) => !["received", "closed", "cancelled", "invoiced"].includes(String(o.status || "").toLowerCase()) || (o.bal_qty || 0) > 0);
    const unpaidPi = (invoices || []).find((i) => (i.balance || 0) > 0) || invoices[0];
    const docCtx = { parties: vendors, products, warehouses };
    el.innerHTML = `
      ${moduleIntro("Purchase", "Vendor → PO → MRN/GRN (bal qty) → Purchase Invoice · ya Direct PI. Stock + books loop.", {
        vendors: vendors.length, orders: orders.length, pending_mrn: (pendingPO || []).length,
        pending_pi: (pendingMRN || []).length, invoices: invoices.length, grn: (grns || []).length,
      })}
      <div class="panel glass"><div class="panel-hd"><h2>Vendors / Supplier Master</h2>
        <button class="btn btn-primary btn-sm" id="add-vendor">+ Vendor</button></div>
        <div class="panel-bd">${table(["Code", "Name", "GSTIN", "WhatsApp", "Under A/c", ""], vendors.map((v) => [
          v.code, v.name, v.gstin || "—",
          (v.custom && v.custom.whatsapp) || v.phone || "—",
          (v.custom && v.custom.under_account) || "Sundry Creditors",
          `<button class="btn btn-ghost btn-sm" data-ven-d="${v.id}">Details</button>`,
        ]))}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Purchase Orders</h2>
        <div class="row" style="gap:6px;flex-wrap:wrap">
          <button class="btn btn-sm btn-primary" id="add-po">+ Purchase Order</button>
          <button class="btn btn-sm btn-ghost" id="recv-po" title="Atomic MRN+PI">Receive one-shot</button>
          <button class="btn btn-sm btn-ghost" id="recv-po-rcm">Receive one-shot RCM</button>
        </div></div>
        <div class="panel-bd">${table(
          ["Number", "Vendor", "Status", "Bal Qty", "Total", ""],
          orders.map((o) => [o.number, o.vendor_name || o.vendor_id, `<span class="pill">${o.status}</span>`, o.bal_qty ?? "—", money(o.total),
            `<button class="btn btn-ghost btn-sm" data-po-d="${o.id}">Details</button>
             <button class="btn btn-ghost btn-sm" data-po-print="${o.id}">Print</button>`]),
          "No POs — + Purchase Order se banao."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Pending PO → MRN (Goods Receipt)</h2></div>
        <div class="panel-bd">${table(
          ["PO No", "Date", "Vendor", "Total Qty", "Bal Qty", "Total Amt", ""],
          (pendingPO || []).map((o) => [
            o.number, o.order_date || "—", o.vendor_name || "—", o.total_qty, o.bal_qty, money(o.total),
            `<button class="btn btn-primary btn-sm" data-mk-mrn="${o.id}">Create MRN</button>`,
          ]),
          "Koi pending PO nahi — bal qty wale PO yahan aate hain."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>MRN / Goods Receipt</h2></div>
        <div class="panel-bd">${table(
          ["MRN", "PO", "Vendor", "Status", "Qty", "Amt", ""],
          (grns || []).map((g) => [
            g.number, g.po_number || "—", g.vendor_name || "—", `<span class="pill">${g.status}</span>`,
            g.total_qty ?? g.line_count ?? (Array.isArray(g.lines) ? g.lines.length : g.lines),
            money(g.total || 0),
            `<button class="btn btn-ghost btn-sm" data-grn-d="${g.id}">Details</button>`,
          ]),
          "No MRN yet — Pending PO se Create MRN."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Pending MRN → Purchase Invoice</h2>
        <button class="btn btn-accent btn-sm" id="add-dir-pi">+ Direct PI</button></div>
        <div class="panel-bd">${table(
          ["MRN No", "Date", "Vendor", "Total Qty", "Total Amt", ""],
          (pendingMRN || []).map((g) => [
            g.number, g.grn_date || "—", g.vendor_name || "—", g.total_qty, money(g.total),
            `<button class="btn btn-primary btn-sm" data-mk-pi="${g.id}">Create PI</button>
             <button class="btn btn-ghost btn-sm" data-mk-pi-rcm="${g.id}">PI (RCM)</button>`,
          ]),
          "Koi pending MRN nahi — Direct PI bhi ban sakta hai."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Purchase Invoices</h2>
        <div class="row" style="gap:6px">
          <button class="btn btn-accent btn-sm" id="pay-vendor" ${unpaidPi ? "" : "disabled"}>Pay vendor</button>
          <button class="btn btn-ghost btn-sm" id="print-pi" ${invoices[0] ? "" : "disabled"}>Print bill</button>
        </div></div>
        <div class="panel-bd">${table(
          ["Number", "Vendor", "Total", "Paid", "Balance", "Status", ""],
          invoices.map((i) => [i.number, i.vendor_name || "—", money(i.total), money(i.paid), money(i.balance),
            `${i.status}${i.rcm ? " · RCM" : ""}`,
            `<button class="btn btn-ghost btn-sm" data-pi-d="${i.id}">Details</button>
             <button class="btn btn-ghost btn-sm" data-pi-print="${i.id}">Print</button>`])
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Vendor payments</h2></div>
        <div class="panel-bd">${table(
          ["Date", "Vendor", "Amount", "Method", "Ref", ""],
          (vpay || []).map((p) => [p.payment_date || "—", p.vendor_name || "—", money(p.amount), p.method, p.reference || "—",
            `<button class="btn btn-ghost btn-sm" data-vp-d="${p.id}">Details</button>`]),
          "No vendor payments yet — Pay vendor on a PI."
        )}</div></div>`;
    $("#add-vendor")?.addEventListener("click", () => {
      openMasterForm(
        "Vendor / Supplier Master",
        [
          { name: "name", label: "Vendor Name", required: true, placeholder: "Supplier name" },
          { name: "gstin", label: "GST Number", placeholder: "GSTIN" },
          {
            name: "under_account",
            label: "Under Account",
            type: "select",
            options: ["Sundry Creditors", "Sundry Creditors (Transportation)", "Sundry Creditors (Commission)", "Other Expence"],
            value: "Sundry Creditors",
          },
          { name: "whatsapp", label: "WhatsApp Number", required: true, placeholder: "91…" },
          { name: "phone", label: "Phone", placeholder: "Phone" },
          { name: "email", label: "Email", placeholder: "email@" },
          { name: "transport", label: "Transport", placeholder: "Default transport" },
          { name: "billing_address", label: "Billing Address", type: "textarea", placeholder: "Address" },
        ],
        async (data) => {
          const r = await API.post("/api/purchase/vendors", {
            name: data.name,
            gstin: data.gstin || "",
            phone: data.phone || data.whatsapp || "",
            email: data.email || "",
            whatsapp: data.whatsapp || "",
            under_account: data.under_account || "Sundry Creditors",
            transport: data.transport || "",
            billing_address: data.billing_address || "",
          });
          toast(`Vendor ${r.code} saved`);
          showSavedDetail("Vendor saved", r);
          pagePurchase(el);
        },
        { eyebrow: "Master · Vendor (SBAC parity)" }
      );
    });
    $("#add-po")?.addEventListener("click", () => {
      if (!(vendors || []).length) return toast("Pehle Vendor Master me vendor banao");
      if (!(products || []).length) return toast("Pehle Item Master me item banao");
      openSalesDocForm(
        "Create Purchase Order",
        docCtx,
        async (payload) => {
          const r = await API.post("/api/purchase/orders", {
            vendor_id: payload.vendor_id,
            warehouse_id: payload.warehouse_id,
            lines: payload.lines,
            remarks: payload.remarks,
            vendor_po_ref: payload.vendor_po_ref || payload.ref_no || payload.customer_order_no,
            transport: payload.transport,
            bill_to: payload.bill_to,
            order_date: payload.order_date,
            delivery_date: payload.delivery_date,
            series_type: payload.series_type,
            party_type: payload.party_type,
            freight_mode: payload.freight_mode,
            narration: payload.narration,
            delivery_branch: payload.delivery_branch,
            booked_station: payload.booked_station,
            ship_branch: payload.ship_branch,
            ship_to: payload.ship_to,
            state: payload.state,
            agent: payload.agent,
            payment_mode: payload.payment_mode,
            currency: payload.currency,
            transporter_mode: payload.transporter_mode,
            godown: payload.godown,
            supplier_contact: payload.supplier_contact,
            delivery_person: payload.delivery_person,
            delivery_contact: payload.delivery_contact,
            ref_no: payload.ref_no,
            behalf_of: payload.behalf_of,
            order_duration: payload.order_duration,
            declaration: payload.declaration,
            round_off: payload.round_off,
            terms: payload.terms,
            other_tax: payload.other_tax,
            charges: payload.charges || [],
          });
          toast(`PO ${r.number} saved`);
          flowSave(`PO ${r.number}`, r, "Pending PO → MRN list me · Create MRN.");
          pagePurchase(el);
        },
        {
          eyebrow: "Purchase · PO (SBAC parity)",
          saveLabel: "Save Purchase Order",
          partyLabel: "Vendor / Supplier",
          partyKey: "vendor_id",
          rateField: "cost_price",
          refLabel: "Vendor Ref / Quotation No",
          refPlaceholder: "Vendor quote / ref",
          docKind: "purchase_order",
        }
      );
    });
    $("#add-dir-pi")?.addEventListener("click", () => {
      if (!(vendors || []).length) return toast("Pehle Vendor banao");
      if (!(products || []).length) return toast("Pehle Item banao");
      openSalesDocForm(
        "Direct Purchase Invoice",
        docCtx,
        async (payload) => {
          const r = await API.post("/api/purchase/invoices/direct", {
            vendor_id: payload.vendor_id,
            warehouse_id: payload.warehouse_id,
            lines: payload.lines,
            remarks: payload.remarks || payload.invoice_remarks,
            rcm: !!payload.rcm,
            series_type: payload.series_type,
            invoice_date: payload.invoice_date || payload.order_date,
            bill_no: payload.bill_no || payload.vendor_po_ref,
            bill_date: payload.bill_date,
            freight_mode: payload.freight_mode,
            qc_status: payload.qc_status,
            received_by: payload.received_by,
            invoice_remarks: payload.invoice_remarks || payload.remarks,
            lot_no: payload.lot_no,
            gr_no: payload.gr_no,
            gr_date: payload.gr_date,
            total_wt: payload.total_wt,
            transport: payload.transport,
            other_tax: payload.other_tax,
            charges: payload.charges || [],
            payment_mode: payload.payment_mode,
            payment_amount: payload.payment_amount,
            transaction_no: payload.transaction_no,
            transaction_date: payload.transaction_date,
            payment_narration: payload.payment_narration,
            advance_adjust: payload.advance_adjust,
            jv_account: payload.jv_account,
            jv_type: payload.jv_type,
            jv_amount: payload.jv_amount,
            pi_type: payload.pi_type || "Direct",
          });
          toast(r.message || `PI ${r.number}`);
          flowSave(`Direct PI ${r.number}`, r, "Stock in + Books purchase voucher · Pay vendor.");
          pagePurchase(el);
        },
        {
          eyebrow: "Purchase · Direct PI (SBAC Cash/Direct)",
          saveLabel: "Save Purchase Invoice",
          partyLabel: "Vendor / Supplier",
          partyKey: "vendor_id",
          rateField: "cost_price",
          refLabel: "Vendor Bill Ref",
          docKind: "purchase_invoice",
        }
      );
    });
    el.querySelectorAll("[data-mk-mrn]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const po = (pendingPO || []).find((o) => String(o.id) === btn.dataset.mkMrn)
          || (orders || []).find((o) => String(o.id) === btn.dataset.mkMrn);
        if (!po) return toast("PO not found");
        openMrnFromPOForm(po, warehouses || [], async (body) => {
          const r = await API.post(`/api/purchase/flow/po-to-grn/${po.id}`, body);
          toast(r.message || `MRN ${r.number}`);
          flowSave(`MRN ${r.number}`, r, "Stock in · Pending MRN → Invoice se PI banao.");
          pagePurchase(el);
        });
      });
    });
    el.querySelectorAll("[data-mk-pi]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const grn = (pendingMRN || []).find((g) => String(g.id) === btn.dataset.mkPi)
          || (grns || []).find((g) => String(g.id) === btn.dataset.mkPi);
        if (!grn) return toast("MRN not found");
        openPiFromMrnForm(grn, async (body) => {
          const r = await API.post(`/api/purchase/flow/grn-to-invoice/${grn.id}`, body);
          toast(r.message || "PI created");
          flowSave("MRN → Purchase Invoice", r, "Books purchase voucher · Pay vendor.");
          pagePurchase(el);
        }, { rcm: false });
      });
    });
    el.querySelectorAll("[data-mk-pi-rcm]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const grn = (pendingMRN || []).find((g) => String(g.id) === btn.dataset.mkPiRcm)
          || (grns || []).find((g) => String(g.id) === btn.dataset.mkPiRcm);
        if (!grn) return toast("MRN not found");
        openPiFromMrnForm(grn, async (body) => {
          const r = await API.post(`/api/purchase/flow/grn-to-invoice/${grn.id}`, { ...body, rcm: true });
          toast(r.message || "RCM PI created");
          flowSave("MRN → RCM PI", r, "AP = taxable · ITC + GST Payable.");
          pagePurchase(el);
        }, { rcm: true });
      });
    });
    $("#recv-po")?.addEventListener("click", async () => {
      const po = (pendingPO || [])[0] || open[0] || orders[0];
      if (!po) return toast("No PO");
      try {
        const r = await API.post(`/api/purchase/orders/${po.id}/receive`);
        toast(`MRN ${r.grn} · ${r.purchase_invoice}`);
        flowSave("One-shot MRN + PI", r, "Stock + Books ek saath.");
        pagePurchase(el);
      } catch (e) {
        toast(e.message || "Receive failed");
      }
    });
    $("#recv-po-rcm")?.addEventListener("click", async () => {
      const po = (pendingPO || [])[0] || open[0] || orders[0];
      if (!po) return toast("No PO");
      try {
        const r = await API.post(`/api/purchase/orders/${po.id}/receive?rcm=true`);
        toast(`RCM · MRN ${r.grn} · ${r.purchase_invoice}`);
        flowSave("RCM receive", r, "AP = taxable only · ITC Dr + GST Payable Cr.");
        pagePurchase(el);
      } catch (e) {
        toast(e.message || "RCM receive failed");
      }
    });
    $("#pay-vendor")?.addEventListener("click", async () => {
      if (!unpaidPi) return toast("No purchase invoice");
      const raw = prompt(
        `Pay ${unpaidPi.number} (balance ${money(unpaidPi.balance)}). Amount > this bill → FIFO across open vendor bills.`,
        String(unpaidPi.balance || unpaidPi.total || 0)
      );
      if (raw == null) return;
      const amount = Number(raw);
      if (!amount || amount <= 0) return toast("Invalid amount");
      try {
        const r = await API.post("/api/purchase/payments", {
          purchase_invoice_id: unpaidPi.id,
          amount,
          method: "bank",
          reference: "VENDOR-PAY",
        });
        toast(r.message || "Vendor paid");
        flowSave("Vendor payment", r, "Bill-wise allocations · Books payment voucher · AP ageing.");
        pagePurchase(el);
      } catch (e) { toast(e.message || "Pay failed"); }
    });
    el.querySelectorAll("[data-ven-d]").forEach((btn) => {
      const row = vendors.find((v) => String(v.id) === btn.dataset.venD);
      btn.addEventListener("click", () => openDetail(row?.name || "Vendor", row || {}, { eyebrow: "Vendor", showJson: false }));
    });
    el.querySelectorAll("[data-po-d]").forEach((btn) => {
      const row = orders.find((o) => String(o.id) === btn.dataset.poD);
      btn.addEventListener("click", () => openDetail(row?.number || "PO", row || {}, { eyebrow: "Purchase order", showJson: false }));
    });
    el.querySelectorAll("[data-po-print]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const row = orders.find((o) => String(o.id) === btn.dataset.poPrint);
        if (!row) return;
        printSheet(buildPoHtml(row), `PO ${row.number}`);
      });
    });
    el.querySelectorAll("[data-pi-d]").forEach((btn) => {
      const row = invoices.find((i) => String(i.id) === btn.dataset.piD);
      btn.addEventListener("click", () => openDetail(row?.number || "PI", row || {}, { eyebrow: "Purchase invoice", showJson: false }));
    });
    el.querySelectorAll("[data-pi-print]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const row = invoices.find((i) => String(i.id) === btn.dataset.piPrint);
        if (!row) return;
        printSheet(buildPurchaseBillHtml(row), `Bill ${row.number}`);
      });
    });
    $("#print-pi")?.addEventListener("click", () => {
      const row = unpaidPi || invoices[0];
      if (!row) return toast("No purchase invoice");
      printSheet(buildPurchaseBillHtml(row), `Bill ${row.number}`);
    });
    el.querySelectorAll("[data-grn-d]").forEach((btn) => {
      const row = (grns || []).find((g) => String(g.id) === btn.dataset.grnD);
      btn.addEventListener("click", () => openDetail(row?.number || "MRN", row || {}, { eyebrow: "MRN / Goods receipt", showJson: false }));
    });
    el.querySelectorAll("[data-vp-d]").forEach((btn) => {
      const row = (vpay || []).find((p) => String(p.id) === btn.dataset.vpD);
      btn.addEventListener("click", () => openDetail("Vendor payment", row || {}, { eyebrow: "Payment", showJson: false }));
    });
  }

  async function pageStore(el) {
    const [issues, receives, physical, pendingPS, pendingInd, transfers, products, warehouses, stock, moves] =
      await Promise.all([
        API.get("/api/store/issues").catch(() => []),
        API.get("/api/store/receives").catch(() => []),
        API.get("/api/store/physical").catch(() => []),
        API.get("/api/store/physical/pending-approval").catch(() => []),
        API.get("/api/store/indents/pending-issue").catch(() => []),
        API.get("/api/store/transfers").catch(() => []),
        API.get("/api/inventory/products").catch(() => []),
        API.get("/api/inventory/warehouses").catch(() => []),
        API.get("/api/inventory/stock").catch(() => []),
        API.get("/api/inventory/moves?limit=40").catch(() => []),
      ]);
    const ctx = { products, warehouses };
    el.innerHTML = `
      ${moduleIntro("Store", "Material Issue / Receive · Physical Stock · Godown Transfer. SBAC Store process · Kanha design.", {
        issues: (issues || []).length, receives: (receives || []).length,
        pending_indent: (pendingInd || []).length, pending_physical: (pendingPS || []).length,
        transfers: (transfers || []).length, skus: (stock || []).length,
      })}
      <div class="panel glass"><div class="panel-hd"><h2>Pending Indent → Material Issue</h2>
        <a class="btn btn-ghost btn-sm" href="#/indents">Indents</a></div>
        <div class="panel-bd">${table(
          ["Indent", "Purpose", "Lines", "Qty", ""],
          (pendingInd || []).map((r) => [
            r.number, r.purpose || "—", (r.lines || []).length, r.total_qty,
            `<button class="btn btn-primary btn-sm" data-ind-issue="${r.id}">Create Issue</button>`,
          ]),
          "Koi approved indent nahi — Indents me approve karo, ya Direct Issue."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Material Issue</h2>
        <button class="btn btn-primary btn-sm" id="st-issue">+ Issue</button></div>
        <div class="panel-bd">${table(
          ["MI No", "Godown", "Dept", "Purpose", "Lines", ""],
          (issues || []).map((r) => [
            r.number, r.warehouse || "—", r.department || "—", r.purpose || "—", (r.lines || []).length,
            `<button class="btn btn-ghost btn-sm" data-mi-d="${r.id}">Details</button>`,
          ]),
          "No issues yet."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Material Receive (internal / return)</h2>
        <button class="btn btn-accent btn-sm" id="st-recv">+ Receive</button></div>
        <div class="panel-bd">${table(
          ["MR No", "Godown", "Source", "Lines", ""],
          (receives || []).map((r) => [
            r.number, r.warehouse || "—", r.source || "—", (r.lines || []).length,
            `<button class="btn btn-ghost btn-sm" data-mr-d="${r.id}">Details</button>`,
          ]),
          "No internal receives yet."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Pending Physical Stock → Approve</h2>
        <button class="btn btn-primary btn-sm" id="st-phys">+ Physical Count</button></div>
        <div class="panel-bd">${table(
          ["PS No", "Lines", "Status", ""],
          (pendingPS || []).map((r) => [
            r.number, r.line_count || (r.lines || []).length, `<span class="pill warn">${r.status}</span>`,
            `<button class="btn btn-accent btn-sm" data-ps-ok="${r.id}">Approve</button>
             <button class="btn btn-ghost btn-sm" data-ps-d="${r.id}">Details</button>`,
          ]),
          "Koi draft physical count nahi."
        )}
        <p class="hint" style="margin-top:10px">All physical sheets:</p>
        ${table(
          ["PS No", "Godown", "Status", "Lines", ""],
          (physical || []).map((r) => [
            r.number, r.warehouse || "—", `<span class="pill">${r.status}</span>`, (r.lines || []).length,
            `<button class="btn btn-ghost btn-sm" data-ps-d="${r.id}">Details</button>`,
          ]),
          "—"
        )}
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Godown Transfer</h2>
        <button class="btn btn-accent btn-sm" id="st-xfer">+ Transfer</button></div>
        <div class="panel-bd">${table(
          ["GT No", "From", "To", "Lines", ""],
          (transfers || []).map((r) => [
            r.number, r.from_warehouse || "—", r.to_warehouse || "—", (r.lines || []).length,
            `<button class="btn btn-ghost btn-sm" data-gt-d="${r.id}">Details</button>`,
          ]),
          "No transfers yet — need 2 godowns."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Stock snapshot</h2>
        <a class="btn btn-ghost btn-sm" href="#/inventory">Item Master / Inventory</a></div>
        <div class="panel-bd">${table(
          ["SKU", "Warehouse", "Qty", "Value"],
          (stock || []).slice(0, 30).map((s) => [s.sku, s.warehouse, s.qty, money(s.value)]),
          "No stock balances."
        )}
        <p class="hint" style="margin-top:12px">Recent moves</p>
        ${table(
          ["When", "SKU", "WH", "Type", "Qty"],
          (moves || []).map((m) => [(m.created_at || "").slice(0, 19) || "—", m.sku, m.warehouse, m.move_type, m.qty]),
          "No moves."
        )}
        </div></div>`;

    const needItems = () => {
      if (!(products || []).length) {
        toast("Pehle Item Master me item banao");
        return false;
      }
      if (!(warehouses || []).length) {
        toast("No godown — Inventory/seed check karo");
        return false;
      }
      return true;
    };

        $("#st-issue")?.addEventListener("click", () => {
          if (!needItems()) return;
          openStoreDocForm(
            "Material Issue",
            ctx,
            async (payload) => {
              const r = await API.post("/api/store/issues", {
                warehouse_id: payload.warehouse_id,
                department: payload.department,
                purpose: payload.purpose,
                remarks: payload.remarks,
                lines: payload.lines,
                issue_date: payload.issue_date,
                issue_type: payload.issue_type,
                bill_no: payload.bill_no,
                party_name: payload.party_name,
                issued_by: payload.issued_by,
                item_issue_type: payload.item_issue_type,
                advance: payload.advance,
              });
              toast(r.message || `Issue ${r.number}`);
              flowSave(`Material Issue ${r.number}`, r, "Stock out · ledger me issue move.");
              pageStore(el);
            },
            { eyebrow: "Store · Issue (SBAC)", saveLabel: "Save and Print", purposePlaceholder: "Production / Job / …", docKind: "issue" }
          );
        });
        el.querySelectorAll("[data-ind-issue]").forEach((btn) => {
          btn.addEventListener("click", () => {
            if (!needItems()) return;
            const ind = (pendingInd || []).find((x) => String(x.id) === btn.dataset.indIssue);
            openStoreDocForm(
              `Issue from Indent ${ind?.number || ""}`,
              ctx,
              async (payload) => {
                const r = await API.post(`/api/store/flow/indent-to-issue/${btn.dataset.indIssue}`, {
                  warehouse_id: payload.warehouse_id,
                  department: payload.department || "Production",
                  purpose: payload.purpose || ind?.purpose || "",
                  remarks: payload.remarks,
                  lines: payload.lines,
                  issue_date: payload.issue_date,
                  issue_type: payload.issue_type,
                  bill_no: payload.bill_no,
                  party_name: payload.party_name,
                  issued_by: payload.issued_by,
                  item_issue_type: payload.item_issue_type,
                  advance: payload.advance,
                });
                toast(r.message || "Issued");
                flowSave(`Indent → Issue ${r.number}`, r, "Indent closed · stock out.");
                pageStore(el);
              },
              {
                eyebrow: "Store · Indent → Issue",
                saveLabel: "Post Issue",
                indentId: Number(btn.dataset.indIssue),
                purpose: ind?.purpose || "",
                department: "Production",
                docKind: "issue",
              }
            );
          });
        });
        $("#st-recv")?.addEventListener("click", () => {
          if (!needItems()) return;
          openStoreDocForm(
            "Material Receive (internal)",
            ctx,
            async (payload) => {
              const r = await API.post("/api/store/receives", {
                warehouse_id: payload.warehouse_id,
                source: payload.source || payload.purpose || "return",
                remarks: payload.remarks,
                lines: payload.lines,
                receive_date: payload.receive_date,
                receive_type: payload.receive_type,
                bill_no: payload.bill_no,
                party_name: payload.party_name,
                advance: payload.advance,
                gst_amount: payload.gst_amount,
              });
              toast(r.message || `Receive ${r.number}`);
              flowSave(`Store Receive ${r.number}`, r, "Stock in (internal) · purchase MRN alag hai.");
              pageStore(el);
            },
            { eyebrow: "Store · Receive (SBAC)", saveLabel: "Save", docKind: "receive", defaultSource: "return" }
          );
        });
        $("#st-phys")?.addEventListener("click", () => {
          if (!needItems()) return;
          openStoreDocForm(
            "Physical Stock Count",
            ctx,
            async (payload) => {
              const r = await API.post("/api/store/physical", {
                warehouse_id: payload.warehouse_id,
                notes: payload.notes || payload.remarks,
                lines: payload.lines,
                count_date: payload.count_date,
                branch: payload.branch,
                store_keeper: payload.store_keeper,
                project_manager: payload.project_manager,
              });
              toast(r.message || `PS ${r.number}`);
              flowSave(`Physical ${r.number}`, r, "Draft · Approve pe variance stock adjust.");
              pageStore(el);
            },
            { eyebrow: "Store · Physical (SBAC)", saveLabel: "Save", docKind: "physical", countMode: true }
          );
        });
        el.querySelectorAll("[data-ps-ok]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            if (!confirm("Approve physical count and post variance adjusts?")) return;
            try {
              const r = await API.post(`/api/store/physical/${btn.dataset.psOk}/approve`);
              toast(r.message || "Approved");
              flowSave("Physical approved", r, "Stock balances updated.");
              pageStore(el);
            } catch (e) {
              toast(e.message || "Approve failed");
            }
          });
        });
        $("#st-xfer")?.addEventListener("click", () => {
          if (!needItems()) return;
          if ((warehouses || []).length < 2) return toast("Need 2 godowns for transfer");
          openStoreDocForm(
            "Godown Transfer",
            ctx,
            async (payload) => {
              const r = await API.post("/api/store/godown-transfer", {
                from_warehouse_id: payload.from_warehouse_id,
                to_warehouse_id: payload.to_warehouse_id,
                notes: payload.notes || payload.remarks,
                lines: payload.lines,
              });
              toast(r.message || `Transfer ${r.number}`);
              flowSave(`Godown Transfer ${r.number}`, r, "Stock moved between godowns.");
              pageStore(el);
            },
            { eyebrow: "Store · Transfer", saveLabel: "Post Transfer", showToWarehouse: true, docKind: "transfer", fromLabel: "From Godown" }
          );
    });
    el.querySelectorAll("[data-mi-d]").forEach((btn) => {
      const row = (issues || []).find((r) => String(r.id) === btn.dataset.miD);
      btn.addEventListener("click", () => openDetail(row?.number || "MI", row || {}, { eyebrow: "Material Issue", showJson: false }));
    });
    el.querySelectorAll("[data-mr-d]").forEach((btn) => {
      const row = (receives || []).find((r) => String(r.id) === btn.dataset.mrD);
      btn.addEventListener("click", () => openDetail(row?.number || "MR", row || {}, { eyebrow: "Store Receive", showJson: false }));
    });
    el.querySelectorAll("[data-ps-d]").forEach((btn) => {
      const row = (physical || []).find((r) => String(r.id) === btn.dataset.psD)
        || (pendingPS || []).find((r) => String(r.id) === btn.dataset.psD);
      btn.addEventListener("click", () => openDetail(row?.number || "PS", row || {}, { eyebrow: "Physical Stock", showJson: false }));
    });
    el.querySelectorAll("[data-gt-d]").forEach((btn) => {
      const row = (transfers || []).find((r) => String(r.id) === btn.dataset.gtD);
      btn.addEventListener("click", () => openDetail(row?.number || "GT", row || {}, { eyebrow: "Godown Transfer", showJson: false }));
    });
  }

  async function pageInventory(el) {
    const [products, stock, wh, batches, moves, godown, valuation] = await Promise.all([
      API.get("/api/inventory/products"),
      API.get("/api/inventory/stock"),
      API.get("/api/inventory/warehouses"),
      API.get("/api/inventory/batches"),
      API.get("/api/inventory/moves?limit=30"),
      API.get("/api/inventory/godown-stock").catch(() => ({ godowns: [], godown_count: 0 })),
      API.get("/api/advanced/godown-valuation").catch(() => ({ godowns: [], total_value: 0 })),
    ]);
    const valRows = valuation.godowns || [];
    const godownBlocks = (valRows.length
      ? valRows.map((g) => `
            <div style="margin-top:12px"><strong>${g.code} · ${g.name}</strong> · value ${money(g.value)}
              ${table(["SKU", "Name", "Qty", "Avg cost", "Value"], (g.lines || []).map((l) => [l.sku, l.name, l.qty, money(l.avg_cost), money(l.value)]))}
            </div>`)
      : (godown.godowns || []).map((g) => `
            <div style="margin-top:12px"><strong>${g.code} · ${g.name}</strong> · ${g.skus} SKUs
              ${table(["SKU", "Name", "Qty", "Avg cost"], (g.lines || []).map((l) => [l.sku, l.name, l.qty, money(l.avg_cost)]))}
            </div>`)
    ).join("");
    el.innerHTML = `
      <div class="panel glass"><div class="panel-hd"><h2>Multi-godown / warehouses</h2>
        <a class="btn btn-accent btn-sm" href="#/pos">Open Scan Billing</a></div>
        <div class="panel-bd">
          <p class="hint">${godown.godown_count || wh.length} godowns · valuation <b>${money(valuation.total_value)}</b> (avg cost)</p>
          ${wh.map((w) => `<span class="pill" style="margin-right:6px">${w.code} · ${w.name}</span>`).join("")}
          ${godownBlocks}
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Item Master + Barcodes</h2>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-accent btn-sm" id="add-product">+ Item</button>
          <button class="btn btn-primary btn-sm" id="adj-stock">Adjust stock</button>
          <button class="btn btn-accent btn-sm" id="xfer-stock" ${wh.length > 1 ? "" : "disabled"}>WH Transfer</button>
          <button class="btn btn-ghost btn-sm" id="print-labels">Print barcode labels</button>
        </div></div>
        <div class="panel-bd">${table(
          ["Code", "Name", "HSN", "Group", "UOM", "Sale", "On Hand", ""],
          products.map((p) => [
            p.sku,
            p.name,
            (p.custom && p.custom.hsn) || "—",
            (p.custom && p.custom.main_group) || p.category || "—",
            p.uom || "NOS",
            money(p.sale_price),
            p.qty_on_hand,
            `<button class="btn btn-ghost btn-sm" data-prod-d="${p.id}">Details</button>`,
          ])
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Barcode shelf</h2></div>
        <div class="panel-bd"><div class="bc-shelf">
          ${products.filter((p) => p.barcode).map((p) => `
            <div class="bc-card">
              <strong>${p.name}</strong>
              <small>${p.sku} · ${money(p.sale_price)}</small>
              ${barcodeSvg(p.barcode)}
            </div>`).join("")}
        </div></div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Batch / Lot tracking</h2>
        <button class="btn btn-accent btn-sm" id="add-batch">+ Batch</button></div>
        <div class="panel-bd">${table(
          ["Batch", "SKU", "Product", "WH", "Qty", "Mfg", "Expiry"],
          batches.map((b) => [b.batch_no, b.sku, b.product, b.warehouse, b.qty, b.mfg_date || "—", b.expiry_date || "—"])
        )}
        <p class="hint">Sales/POS issue uses <b>FEFO</b> (earliest expiry first) when batches exist.</p>
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Stock Valuation</h2></div><div class="panel-bd">${table(["SKU", "Warehouse", "Qty", "Avg Cost", "Value"], stock.map((s) => [s.sku, s.warehouse, s.qty, money(s.avg_cost), money(s.value)]))}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Stock ledger (moves)</h2></div>
        <div class="panel-bd">${table(
          ["When", "SKU", "WH", "Type", "Qty", "Notes"],
          (moves || []).map((m) => [
            (m.created_at || "").slice(0, 19) || "—",
            m.sku,
            m.warehouse,
            m.move_type,
            m.qty,
            m.notes || "—",
          ]),
          "No moves yet — adjust / transfer / POS / GRN will appear here."
        )}</div></div>
      <div id="label-print" class="label-print" hidden></div>`;
    $("#adj-stock")?.addEventListener("click", async () => {
      const p = products[0];
      const w = wh[0];
      if (!p || !w) return toast("No product/warehouse");
      const raw = prompt(`Adjust qty for ${p.sku} (+/-)`, "5");
      if (raw == null) return;
      const qty = Number(raw);
      if (!qty) return toast("Enter non-zero qty");
      const r = await API.post("/api/inventory/adjust", { product_id: p.id, warehouse_id: w.id, qty, notes: "Manual adjust" });
      toast(`Stock updated · on hand ${r.qty}`);
      flowSave(`Stock adjust ${p.sku}`, r, "On Hand + Stock Valuation + Stock ledger moves me dikhega.");
      pageInventory(el);
    });
    $("#xfer-stock")?.addEventListener("click", async () => {
      if (wh.length < 2) return toast("Need 2 warehouses — demo seeds WH-FG");
      const p = products[0];
      if (!p) return toast("No product");
      const qty = Number(prompt(`Transfer qty of ${p.sku} from ${wh[0].code} → ${wh[1].code}`, "5") || 0);
      if (!qty) return;
      try {
        const r = await API.post("/api/inventory/transfer", {
          product_id: p.id,
          from_warehouse_id: wh[0].id,
          to_warehouse_id: wh[1].id,
          qty,
          notes: "UI warehouse transfer",
        });
        toast(r.message || "Transferred");
        showSavedDetail("Stock transfer saved", r);
        pageInventory(el);
      } catch (e) { toast(e.message || "Transfer failed"); }
    });
    $("#add-product")?.addEventListener("click", () => {
      const units = ["BAG", "NOS", "BOX", "MTR", "PCS", "MT", "BUNDLE", "KGS", "COIL", "QTL", "PACKET", "TIN", "SQF", "LTR"];
      const brands = [
        "MS PIPE", "ASTRAL", "POWERTECH", "JK LAXMI", "SST SALDU", "MAXIDURA", "JSW", "ASIAN PAINTS",
        "BOSCO", "JINDAL", "CHHANEL", "SBAC", "Generic", "OEM", "Other",
      ];
      const mainGroups = [
        "BAJRI", "BRICKS", "CAST IRON ELECTRODES", "CEMENT", "CONDUIT", "CONSUMABLE", "CPVC",
        "Finished Goods", "Raw Material", "Semi Finished", "Trading", "Scrap", "General",
      ];
      const subGroups = ["CEMENT", "POLL", "GITTI", "JK SUPER", "FABT", "RD BUSH", "PLUG THREADED", "Alloys", "Ingots", "Other"];
      const categories = [
        "HARD FACING", "Mild Steel", "CAST IRON", "WELDING ELECTRODES", "Stainless steel", "JOINING", "MaxiDura", "Other",
      ];
      const branchOpts = [
        "SHRI BALAJI ALLOYS CORPORATION RPR",
        "SBAC FARM",
        "SHREE BALAJI ALLOYS CORPORATION HYD",
        "SHRI BALAJI ALLOYS CORPORATION",
        "SHRI BALAJI ALLOYS CORPORATION DGP",
        "SHRI BALAJI ALLOYS CORPORATION IND",
        "SHRI BALAJI ALLOYS CORPORATION MANDAWA",
      ];
      const sizes = ["3.15x450MM", "5X450mm", "2.5X350mm", "4X350mm", "9'", "8.5'", "3.15x350mm"];
      const countries = [
        "India", "Oman", "TANZANIA", "United States of America", "IRAN", "AUSTRALIA", "SOUTH AFRICA",
        "UGANDA", "Singapore", "Kenya", "UKRAINE", "AMERICA", "Bangladesh", "Canada", "England",
        "FRANCE", "United Arab Emirates( Dubai)", "Nepal", "Germany", "China",
      ];
      openMasterForm(
        "Item Master",
        [
          { type: "section", label: "Primary", hint: "SBAC Add Item — live parity 2026-08-02" },
          {
            name: "branch_name",
            label: "Branch Name",
            type: "select",
            options: branchOpts,
            value: branchOpts[0],
          },
          { name: "sku", label: "Item Code", placeholder: "Leave blank to auto-generate" },
          { name: "name", label: "Item Name", required: true, placeholder: "Item Name" },
          { name: "part_image_url", label: "Part Image (URL)", placeholder: "Optional image URL — file upload later" },
          {
            name: "brand",
            label: "Select Brand",
            type: "select",
            options: ["", ...brands],
          },
          {
            name: "uom",
            label: "Base Unit",
            type: "select",
            required: true,
            options: units,
            value: "KGS",
          },
          {
            name: "main_group",
            label: "Main Group",
            type: "select",
            required: true,
            options: mainGroups,
            value: "Finished Goods",
          },
          {
            name: "sub_group",
            label: "Sub Group",
            type: "select",
            options: ["", ...subGroups],
          },
          {
            name: "category",
            label: "Category/Make",
            type: "select",
            options: ["", ...categories],
          },
          { name: "hsn", label: "HSN Code", placeholder: "HSN Code" },
          { name: "description", label: "Item Description", type: "textarea", placeholder: "Item Description" },
          {
            name: "purchase_uom",
            label: "Purchase Default Unit",
            type: "select",
            options: ["", ...units],
            value: "KGS",
          },
          {
            name: "sale_uom",
            label: "Sale Default Unit",
            type: "select",
            options: ["", ...units],
            value: "KGS",
          },
          { name: "color", label: "Color", placeholder: "Color" },
          {
            name: "size",
            label: "Size",
            type: "select",
            options: ["", ...sizes],
          },
          {
            name: "branch_list",
            label: "Branch list",
            type: "checkboxes",
            options: branchOpts,
            value: [branchOpts[0]],
            defaultFirst: true,
          },

          { type: "section", label: "Other Section", hint: "SBAC chkotherdiv" },
          { name: "same_as_item_name", label: "Same as Item Name", type: "checkbox", value: false },
          { name: "parent_item_name", label: "Parent / Alias Name", placeholder: "Same as Item Name target" },
          { name: "parent_item_code", label: "Parent Item Code", placeholder: "Parent Item Code" },
          { name: "gross_weight", label: "Gross Weight", type: "number", placeholder: "Gross Weight" },
          { name: "net_weight", label: "Net Weight", type: "number", placeholder: "Net Weight" },
          { name: "cartoon_weight", label: "Cartoon Weight", type: "number", placeholder: "Cartoon Weight" },
          { name: "std_pack_qty", label: "Standard Packaging Quantity", type: "number", placeholder: "Std pack qty" },
          { name: "sub_item", label: "Sub Item", type: "checkbox", value: false },
          {
            name: "subitem_required",
            label: "Subitem Required",
            type: "select",
            options: ["Yes", "No"],
            value: "No",
          },
          {
            name: "area_calc_required",
            label: "Area calculationrequired",
            type: "select",
            options: ["Yes", "No"],
            value: "No",
          },
          {
            name: "formula_required",
            label: "Formula Reqd",
            type: "select",
            options: ["No", "Yes"],
            value: "No",
          },
          { name: "formula", label: "Formula", placeholder: "Formula" },

          { type: "section", label: "Conversion Factor", hint: "SBAC chkConversion · Add Conversion" },
          {
            name: "conv_base_unit",
            label: "Base Unit",
            type: "select",
            options: ["", ...units],
          },
          {
            name: "conv_unit",
            label: "Conversion Unit",
            type: "select",
            options: ["", ...units],
          },
          { name: "conv_value", label: "Value", type: "number", placeholder: "Value" },
          { type: "list_preview", name: "conversions", label: "Saved conversions" },

          { type: "section", label: "Item Specification", hint: "SBAC chkbox" },
          { name: "specification", label: "Item Specification", type: "textarea", placeholder: "Specification" },

          { type: "section", label: "Item Classification", hint: "SBAC chkitemclass" },
          { name: "rack_no", label: "Rack No", placeholder: "Rack No" },
          { name: "bin_no", label: "Bin No", placeholder: "Bin No" },
          { name: "purchase_name", label: "Purchase Name", placeholder: "Purchase Name" },
          { name: "purchase_code", label: "Purchase Code", placeholder: "Purchase Code" },
          { name: "barcode", label: "Bar Code", placeholder: "Optional — auto if blank" },
          {
            name: "item_class",
            label: "Classification",
            type: "radio",
            options: [
              { value: "Finished Goods", label: "Finished Goods" },
              { value: "Raw Material", label: "Raw Material" },
              { value: "Semi finished", label: "Semi finished" },
              { value: "Powder coated", label: "Powder coated" },
            ],
            value: "Finished Goods",
          },

          { type: "section", label: "Tax Duty Details", hint: "SBAC chktaxduty" },
          { name: "tariff_classification", label: "Tarrif Classification", placeholder: "Tariff" },
          { name: "duty", label: "Duty", placeholder: "Duty" },
          { name: "commodity_code", label: "Commodity Code", placeholder: "Commodity Code" },

          { type: "section", label: "Dimension", hint: "SBAC chkdimension" },
          { name: "dim_length", label: "Length", type: "number", placeholder: "Length" },
          { name: "dim_width", label: "Width", type: "number", placeholder: "Width" },
          { name: "dim_height", label: "Height", type: "number", placeholder: "Height" },
          { name: "dim_weight", label: "Weight", type: "number", placeholder: "Weight" },
          {
            name: "dim_unit",
            label: "Dimension Unit",
            type: "select",
            options: ["", ...units],
          },
          { name: "volumetric_weight", label: "Volumetric Weight", type: "number", placeholder: "Volumetric Weight" },

          { type: "section", label: "Stock Value", hint: "SBAC chkstokevalue" },
          {
            name: "stock_unit",
            label: "Unit",
            type: "select",
            options: ["", ...units],
            value: "KGS",
          },
          { name: "closing_stock", label: "Closing Stock", type: "number", placeholder: "Closing Stock" },
          { name: "opening_stock", label: "Opening Stock", type: "number", placeholder: "Opening Stock" },
          { name: "monthly_consumption", label: "Monthly Consumption", type: "number", placeholder: "Monthly Consumption" },
          { name: "reorder_level", label: "Re order level", type: "number", placeholder: "Re order level" },
          { name: "min_stock", label: "Minimum Stock", type: "number", placeholder: "Minimum Stock" },
          { name: "max_stock", label: "Maximum Stock", type: "number", placeholder: "Maximum Stock" },
          { name: "min_order_qty", label: "Minimum Order Quantity", type: "number", placeholder: "MOQ" },

          { type: "section", label: "Rate List", hint: "SBAC chkratelist" },
          { name: "cost_price", label: "Purchase", type: "number", placeholder: "Purchase" },
          { name: "mrp", label: "MRP", type: "number", placeholder: "MRP" },
          { name: "sale_price", label: "Sale Price (Kanha)", type: "number", placeholder: "0 — defaults from MRP" },
          { name: "gst_rate", label: "GST(%)", type: "number", value: "18" },
          { name: "gst_include", label: "GST Include", type: "checkbox", value: false },
          { name: "rate_date", label: "Date", type: "date" },
          { name: "exporter_gst", label: "Exporter GST(%)", type: "number", placeholder: "Exporter GST(%)" },
          { name: "exporter_gst_include", label: "Exporter GST Include", type: "checkbox", value: false },
          { name: "bom_rate", label: "Bom Rate", type: "number", placeholder: "Bom Rate" },
          {
            name: "status_active",
            label: "Status",
            type: "radio",
            options: [
              { value: "Active", label: "Active" },
              { value: "NonActive", label: "NonActive" },
            ],
            value: "Active",
          },

          { type: "section", label: "Country List", hint: "SBAC chkcountrylist — common export set + Other" },
          {
            name: "country_list",
            label: "Country List",
            type: "checkboxes",
            options: countries,
            value: ["India"],
          },
          { name: "country_list_extra", label: "Other countries", placeholder: "Comma-separated extra countries" },

          { type: "section", label: "Vendor Details", hint: "SBAC chkvendorlist · Add Vendor" },
          { name: "vendor_name", label: "Vendor Name", placeholder: "Vendor Name" },
          { name: "vendor_contact", label: "Contact No.", placeholder: "Contact No." },
          { type: "list_preview", name: "vendors", label: "Saved vendors" },

          { type: "section", label: "Packing Instruction", hint: "SBAC PackingInstruction · Add Packing" },
          {
            name: "pack_unit",
            label: "Packing Unit",
            type: "select",
            options: ["", ...units],
          },
          { name: "pack_serial", label: "Serial No", placeholder: "Serial No" },
          { name: "pack_qty", label: "Qty", type: "number", placeholder: "Qty" },
          {
            name: "pack_qty_unit",
            label: "Qty Unit",
            type: "select",
            options: ["", ...units],
          },
          { name: "pack_weight", label: "Weight", type: "number", placeholder: "Weight" },
          {
            name: "pack_weight_unit",
            label: "Weight Unit",
            type: "select",
            options: ["", ...units],
          },
          { name: "pack_height", label: "Height", type: "number", placeholder: "Height" },
          {
            name: "pack_height_unit",
            label: "Height Unit",
            type: "select",
            options: ["", ...units],
          },
          { name: "pack_width", label: "Width", type: "number", placeholder: "Width" },
          {
            name: "pack_width_unit",
            label: "Width Unit",
            type: "select",
            options: ["", ...units],
          },
          { name: "pack_length", label: "Length", type: "number", placeholder: "Length" },
          {
            name: "pack_length_unit",
            label: "Length Unit",
            type: "select",
            options: ["", ...units],
          },
          {
            name: "pack_from_unit",
            label: "From Unit",
            type: "select",
            options: ["", ...units],
          },
          { type: "list_preview", name: "packings", label: "Saved packing lines" },
        ],
        async (data) => {
          const sku = (data.sku || "").trim() || "ITM-" + Date.now().toString().slice(-6);
          const mrp = Number(data.mrp || 0);
          const price = Number(data.sale_price || 0) || mrp;
          const cost = Number(data.cost_price || 0) || (price ? Math.round(price * 0.65) : 0);
          const branches = Array.isArray(data.branch_list) ? data.branch_list : [];
          const countryList = Array.isArray(data.country_list) ? [...data.country_list] : [];
          if (data.country_list_extra) {
            data.country_list_extra.split(",").map((s) => s.trim()).filter(Boolean).forEach((c) => {
              if (!countryList.includes(c)) countryList.push(c);
            });
          }
          const conversions = Array.isArray(data.conversions) ? data.conversions : [];
          if (data.conv_base_unit && data.conv_unit && data.conv_value) {
            conversions.push({
              base_unit: data.conv_base_unit,
              conversion_unit: data.conv_unit,
              value: data.conv_value,
            });
          }
          const vendors = Array.isArray(data.vendors) ? data.vendors : [];
          if (data.vendor_name) {
            vendors.push({ name: data.vendor_name, contact: data.vendor_contact || "" });
          }
          const packings = Array.isArray(data.packings) ? data.packings : [];
          if (data.pack_qty || data.pack_unit) {
            packings.push({
              packing_unit: data.pack_unit || "",
              serial_no: data.pack_serial || "",
              qty: data.pack_qty || "",
              qty_unit: data.pack_qty_unit || "",
              weight: data.pack_weight || "",
              weight_unit: data.pack_weight_unit || "",
              height: data.pack_height || "",
              height_unit: data.pack_height_unit || "",
              width: data.pack_width || "",
              width_unit: data.pack_width_unit || "",
              length: data.pack_length || "",
              length_unit: data.pack_length_unit || "",
              from_unit: data.pack_from_unit || "",
            });
          }
          const parentName = data.same_as_item_name === "Yes" ? data.name : (data.parent_item_name || "");
          const r = await API.post("/api/inventory/products", {
            sku,
            name: data.name,
            brand: data.brand || "",
            uom: data.uom || "NOS",
            category: data.category || data.main_group || "General",
            sale_price: price,
            cost_price: cost,
            gst_rate: Number(data.gst_rate || 18),
            barcode: (data.barcode || "").trim() || "890" + Date.now().toString().slice(-10),
            custom: {
              branch_name: data.branch_name || "",
              branch_list: branches.join(", "),
              hsn: data.hsn || "",
              main_group: data.main_group || "",
              sub_group: data.sub_group || "",
              description: data.description || "",
              purchase_uom: data.purchase_uom || data.uom || "",
              sale_uom: data.sale_uom || data.uom || "",
              color: data.color || "",
              size: data.size || "",
              part_image_url: data.part_image_url || "",
              other: {
                same_as_item_name: data.same_as_item_name || "No",
                parent_item_name: parentName,
                parent_item_code: data.parent_item_code || "",
                gross_weight: data.gross_weight || "",
                net_weight: data.net_weight || "",
                cartoon_weight: data.cartoon_weight || "",
                std_pack_qty: data.std_pack_qty || "",
                sub_item: data.sub_item || "No",
                subitem_required: data.subitem_required || "No",
                area_calc_required: data.area_calc_required || "No",
                formula_required: data.formula_required || "No",
                formula: data.formula || "",
              },
              conversions,
              specification: data.specification || "",
              classification: {
                rack_no: data.rack_no || "",
                bin_no: data.bin_no || "",
                purchase_name: data.purchase_name || "",
                purchase_code: data.purchase_code || "",
                item_class: data.item_class || "Finished Goods",
              },
              tax_duty: {
                tariff_classification: data.tariff_classification || "",
                duty: data.duty || "",
                commodity_code: data.commodity_code || "",
              },
              dimension: {
                length: data.dim_length || "",
                width: data.dim_width || "",
                height: data.dim_height || "",
                weight: data.dim_weight || "",
                unit: data.dim_unit || "",
                volumetric_weight: data.volumetric_weight || "",
              },
              stock: {
                unit: data.stock_unit || "",
                closing_stock: data.closing_stock || "",
                opening_stock: data.opening_stock || "",
                monthly_consumption: data.monthly_consumption || "",
                reorder_level: data.reorder_level || "",
                min_stock: data.min_stock || "",
                max_stock: data.max_stock || "",
                min_order_qty: data.min_order_qty || "",
              },
              rate_list: {
                purchase: data.cost_price || "",
                mrp: data.mrp || "",
                gst_pct: data.gst_rate || "",
                gst_include: data.gst_include || "No",
                date: data.rate_date || "",
                exporter_gst: data.exporter_gst || "",
                exporter_gst_include: data.exporter_gst_include || "No",
                bom_rate: data.bom_rate || "",
                status: data.status_active || "Active",
              },
              country_list: countryList,
              vendors,
              packings,
              source: "kanha_item_master",
              sbac_parity: "2026-08-02-live",
            },
          });
          toast(`Item ${r.sku || sku} saved`);
          showSavedDetail("Item Master saved", r);
          pageInventory(el);
        },
        {
          eyebrow: "Master · Item (SBAC exact fields · live scan)",
          saveLabel: "Submit",
          extraButtons: [
            {
              id: "mf-same-name",
              label: "Same as Item Name",
              onClick: (overlay) => {
                const name = mfRead(overlay, "name");
                if (!name) return toast("Item Name pehle bharo");
                const el = overlay.querySelector('[data-mf="parent_item_name"]');
                if (el) el.value = name;
                const cb = overlay.querySelector('[data-mf="same_as_item_name"]');
                if (cb) cb.checked = true;
                toast("Parent / Alias = Item Name");
              },
            },
            {
              id: "mf-add-conversion",
              label: "Add Conversion",
              onClick: (overlay) => {
                const base = mfRead(overlay, "conv_base_unit");
                const unit = mfRead(overlay, "conv_unit");
                const value = mfRead(overlay, "conv_value");
                if (!base || !unit || !value) return toast("Base Unit, Conversion Unit, Value bharo");
                mfListPush(overlay, "conversions", { base_unit: base, conversion_unit: unit, value }, `${base} → ${unit} = ${value}`);
                mfClear(overlay, ["conv_base_unit", "conv_unit", "conv_value"]);
                toast("Conversion added");
              },
            },
            {
              id: "mf-add-vendor",
              label: "Add Vendor",
              onClick: (overlay) => {
                const name = mfRead(overlay, "vendor_name");
                const contact = mfRead(overlay, "vendor_contact");
                if (!name) return toast("Vendor Name required");
                mfListPush(overlay, "vendors", { name, contact }, `${name} · ${contact || "—"}`);
                mfClear(overlay, ["vendor_name", "vendor_contact"]);
                toast("Vendor added");
              },
            },
            {
              id: "mf-add-packing",
              label: "Add Packing",
              onClick: (overlay) => {
                const item = {
                  packing_unit: mfRead(overlay, "pack_unit"),
                  serial_no: mfRead(overlay, "pack_serial"),
                  qty: mfRead(overlay, "pack_qty"),
                  qty_unit: mfRead(overlay, "pack_qty_unit"),
                  weight: mfRead(overlay, "pack_weight"),
                  weight_unit: mfRead(overlay, "pack_weight_unit"),
                  height: mfRead(overlay, "pack_height"),
                  height_unit: mfRead(overlay, "pack_height_unit"),
                  width: mfRead(overlay, "pack_width"),
                  width_unit: mfRead(overlay, "pack_width_unit"),
                  length: mfRead(overlay, "pack_length"),
                  length_unit: mfRead(overlay, "pack_length_unit"),
                  from_unit: mfRead(overlay, "pack_from_unit"),
                };
                if (!item.packing_unit && !item.qty) return toast("Packing Unit ya Qty bharo");
                mfListPush(
                  overlay,
                  "packings",
                  item,
                  `${item.packing_unit || "Pack"} · qty ${item.qty || "—"} ${item.qty_unit || ""}`.trim()
                );
                mfClear(overlay, [
                  "pack_unit", "pack_serial", "pack_qty", "pack_qty_unit", "pack_weight", "pack_weight_unit",
                  "pack_height", "pack_height_unit", "pack_width", "pack_width_unit", "pack_length",
                  "pack_length_unit", "pack_from_unit",
                ]);
                toast("Packing added");
              },
            },
          ],
        }
      );
    });
    $("#add-batch")?.addEventListener("click", async () => {
      const p = products[0];
      const w = wh[0];
      if (!p || !w) return toast("No product/warehouse");
      const qty = Number(prompt("Batch qty", "50") || 0);
      if (!qty) return;
      const r = await API.post("/api/inventory/batches", {
        product_id: p.id,
        warehouse_id: w.id,
        batch_no: "BCH-" + Date.now().toString().slice(-6),
        qty,
        mfg_date: new Date().toISOString().slice(0, 10),
      });
      toast(`Batch ${r.batch_no} created`);
      flowSave(`Batch ${r.batch_no}`, r, "Batch / Lot tracking table me · Expiry MIS se track.");
      pageInventory(el);
    });
    el.querySelectorAll("[data-prod-d]").forEach((btn) => {
      const row = products.find((p) => String(p.id) === btn.dataset.prodD);
      btn.addEventListener("click", () => openDetail(row?.sku || "Product", row || {}, { eyebrow: "Product · barcode ready", showJson: false }));
    });
    $("#print-labels")?.addEventListener("click", () => {
      const list = products.filter((p) => p.barcode);
      if (!list.length) return toast("No barcodes — add product barcodes first");
      const html = `
        <div class="print-doc">
          <div class="print-doc__hd">
            <div><div class="print-doc__brand">${BRAND.name}</div><div class="print-doc__sub">Barcode labels · ${list.length} SKUs</div></div>
            <div class="print-doc__badge">LABELS</div>
          </div>
          <div class="label-print-grid">
            ${list.map((p) => `
              <div class="label-print__item">
                <strong>${BRAND.name}</strong>
                <span>${p.name}</span>
                <span class="hint">${p.sku || ""} · ${p.barcode}</span>
                ${typeof barcodeSvg === "function" ? barcodeSvg(p.barcode, { height: 40 }) : `<code>${p.barcode}</code>`}
                <em>${money(p.sale_price)}</em>
              </div>`).join("")}
          </div>
        </div>`;
      printSheet(html, "Barcode labels");
    });
  }

  async function pageAccounting(el) {
    const [coa, journals, pnl, gst, tb, budgets, assets, period] = await Promise.all([
      API.get("/api/accounting/coa"),
      API.get("/api/accounting/journals"),
      API.get("/api/accounting/reports/pnl"),
      API.get("/api/accounting/reports/gst"),
      API.get("/api/accounting/reports/trial-balance"),
      API.get("/api/accounting/budgets"),
      API.get("/api/accounting/assets"),
      API.get("/api/accounting/period-lock"),
    ]);
    el.innerHTML = `
      ${moduleIntro("Accounting", "COA, journals, P&L, GST, trial balance, period lock — books hygiene that protects sales/WhatsApp trust.", {
        accounts: coa.length, journals: journals.length, budgets: (budgets || []).length, assets: (assets || []).length,
        closed_through: period.closed_through || "open",
      }, `<button class="btn btn-primary btn-sm" id="mk-journal">+ Journal voucher</button>
         <button class="btn btn-accent btn-sm" id="period-lock">Period lock</button>
         <a class="btn btn-ghost btn-sm" href="#/books">Kanha Books desk</a>`)}
      <div class="panel glass"><div class="panel-bd">
        <span class="pill ${period.closed_through ? "danger" : "ok"}">${period.closed_through ? `Closed through ${period.closed_through}` : "All periods open"}</span>
        <span class="hint" style="margin-left:8px">${period.message || ""}</span>
      </div></div>
      <div class="kpi-grid">
        ${kpiCard("Income", "", { icon: "↗", tone: "blue", raw: pnl.income })}
        ${kpiCard("Gross Profit", "", { icon: "◎", tone: "teal", raw: pnl.gross_profit })}
        ${kpiCard("Net Profit", "", { icon: "★", tone: "emerald", raw: pnl.net_profit })}
        ${kpiCard("Net GST Payable", "", { icon: "₹", tone: "amber", raw: gst.net_payable })}
      </div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Chart of Accounts</h2></div><div class="panel-bd">${table(["Code", "Name", "Type"], coa.map((a) => [a.code, a.name, a.account_type]))}</div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Journal Entries</h2></div><div class="panel-bd">${table(
          ["Number", "Date", "Narration", "Lines"],
          journals.map((j) => [j.number, j.entry_date || "—", j.narration || "—", (j.lines || []).length])
        )}</div></div>
      </div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Trial Balance</h2></div><div class="panel-bd">${table(["Code", "Account", "Debit", "Credit"], tb.map((t) => [t.code, t.name, money(t.debit), money(t.credit)]))}</div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Budgets</h2></div><div class="panel-bd">${table(
          ["Name", "FY", "Lines"],
          (budgets || []).map((b) => [b.name, b.fiscal_year, (b.lines || []).map((l) => `${l.account}: ${money(l.budget)}`).join(" · ") || (b.lines || []).length])
        ) || "<p class='hint'>No budgets</p>"}</div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>GST Register</h2></div><div class="panel-bd">
        <div class="kpi-grid" style="margin-bottom:12px">
          ${kpiCard("Output CGST", "", { icon: "◎", tone: "blue", raw: (gst.output_split || {}).cgst || 0 })}
          ${kpiCard("Output SGST", "", { icon: "◎", tone: "teal", raw: (gst.output_split || {}).sgst || 0 })}
          ${kpiCard("Input ITC", "", { icon: "↙", tone: "amber", raw: gst.input_gst })}
          ${kpiCard("Net payable", "", { icon: "₹", tone: "emerald", raw: gst.net_payable })}
        </div>
        <p class="hint">${gst.gstr_hint || "GSTR-3B net = output − input ITC"}</p>
        ${table(
          ["Type", "Doc", "Date", "Taxable", "CGST", "SGST", "IGST", "Tax"],
          (gst.register || []).map((r) => [
            r.doc_type,
            r.number,
            r.date || "—",
            money(r.taxable),
            money(r.cgst),
            money(r.sgst),
            money(r.igst),
            money(r.total_tax),
          ]),
          "No GST documents yet."
        )}
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Fixed assets</h2></div><div class="panel-bd">${table(
        ["Name", "Purchase", "Cost", "Method", "Life", "Salvage"],
        (assets || []).map((a) => [a.name, a.purchase_date || "—", money(a.cost), a.method, a.life_years + "y", money(a.salvage)])
      )}</div></div>`;
    $("#mk-journal")?.addEventListener("click", async () => {
      try {
        const coa = await API.get("/api/books/coa");
        openVoucherForm(
          "journal",
          { accounts: coa, centres: [] },
          async (payload) => {
            const r = await API.post("/api/books/vouchers", payload);
            toast(`Journal ${r.number} posted · Dr/Cr ${money(r.debit)}`);
            showSavedDetail("Journal posted", r);
            pageAccounting(el);
          },
          { eyebrow: "Accounting · Journal" }
        );
      } catch (e) {
        toast(e.message || "Failed");
      }
    });
    $("#period-lock")?.addEventListener("click", async () => {
      const cur = period.closed_through || "";
      const next = prompt(
        "Close books through YYYY-MM (blank = unlock all)",
        cur || new Date().toISOString().slice(0, 7)
      );
      if (next === null) return;
      try {
        const r = await API.post("/api/accounting/period-lock", {
          closed_through: next.trim() || null,
          note: next.trim() ? "Period closed from Accounting UI" : "Period unlocked",
        });
        toast(r.message || "Period updated");
        showSavedDetail("Period lock", r);
        pageAccounting(el);
      } catch (e) { toast(e.message || "Lock failed"); }
    });
  }

  async function pageManufacturing(el) {
    const [boms, wos, machines, mrp, products, challans] = await Promise.all([
      API.get("/api/manufacturing/boms"),
      API.get("/api/manufacturing/work-orders"),
      API.get("/api/manufacturing/machines"),
      API.get("/api/manufacturing/mrp"),
      API.get("/api/inventory/products"),
      API.get("/api/production/challans").catch(() => []),
    ]);
    const running = wos.filter((w) => ["released", "in_progress", "running"].includes(String(w.status || "").toLowerCase()));
    el.innerHTML = `
      ${moduleIntro("Manufacturing / Production", "BOM → Work Order → Production challan → MRP. Trading/service companies can turn this module off.", {
        machines: machines.length, boms: boms.length, work_orders: wos.length, running: running.length, challans: (challans || []).length,
      })}
      <div class="grid-3">
        <div class="panel glass"><div class="panel-hd"><h2>Machines</h2><button class="btn btn-sm btn-primary" id="add-mch">+ Machine</button></div>
          <div class="panel-bd">${table(["Code", "Name", "Status"], machines.map((m) => [m.code, m.name, `<span class="pill">${m.status}</span>`]))}</div></div>
        <div class="panel glass"><div class="panel-hd"><h2>BOMs</h2><button class="btn btn-sm btn-primary" id="add-bom">+ BOM</button></div>
          <div class="panel-bd">${table(
          ["ID", "Product", "SKU", "Ver", "Components"],
          boms.map((b) => [b.id, b.product_name || b.product_id, b.product_sku || "—", b.version, (b.components || []).length])
        )}</div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Work Orders</h2><button class="btn btn-sm btn-primary" id="add-wo">+ WO</button></div>
          <div class="panel-bd">${table(
          ["Number", "Product", "Qty", "Status", ""],
          wos.map((w) => [
            w.number,
            w.product_name || w.product_id,
            w.qty,
            `<span class="pill">${w.status}</span>`,
            `<button class="btn btn-ghost btn-sm" data-adv="${w.id}">Advance</button>
             <button class="btn btn-accent btn-sm" data-ch="${w.id}">Challan</button>`,
          ])
        )}</div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Production challans</h2></div>
        <div class="panel-bd">${table(
          ["No", "Product", "Qty", "WO", "Status", ""],
          (challans || []).map((c) => [
            c.number, c.product_name, c.qty, c.work_order_id || "—", `<span class="pill">${c.status}</span>`,
            c.status === "issued"
              ? `<button class="btn btn-primary btn-sm" data-recv="${c.id}">Receive stock</button>`
              : "—",
          ])
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>MRP / Production planning</h2>
        <button class="btn btn-primary btn-sm" id="run-mrp">Run MRP</button></div>
        <div class="panel-bd">
          ${table(
            ["Plan", "Period", "Status", "Lines", "Notes"],
            mrp.map((r) => [r.number, r.period, r.status, (r.lines || []).length, r.notes || "—"])
          )}
          ${mrp[0] ? `<h3 style="margin:14px 0 8px;font-size:14px">Latest plan lines · ${mrp[0].number}</h3>${table(
            ["SKU", "On hand", "Demand", "Shortage", "Suggest", "Qty"],
            (mrp[0].lines || []).map((l) => [l.sku, l.on_hand, l.demand, l.shortage, l.suggest, l.suggest_qty])
          )}` : `<p class="hint">No MRP yet — click Run MRP.</p>`}
        </div></div>`;
    $("#run-mrp")?.addEventListener("click", async () => {
      const r = await API.post("/api/manufacturing/mrp/run");
      toast(`MRP ${r.number} · ${r.count} lines`);
      pageManufacturing(el);
    });
    $("#add-mch")?.addEventListener("click", async () => {
      const name = prompt("Machine name", "CNC-Line");
      if (!name) return;
      await API.post("/api/manufacturing/machines", { name, status: "idle" });
      toast("Machine added");
      pageManufacturing(el);
    });
    $("#add-bom")?.addEventListener("click", async () => {
      const p = products[0];
      if (!p) return toast("No product");
      await API.post("/api/manufacturing/boms", {
        product_id: p.id,
        version: "1.0",
        components: [{ sku: "RM-01", name: "Raw material", qty: 2 }],
      });
      toast("BOM created");
      pageManufacturing(el);
    });
    $("#add-wo")?.addEventListener("click", async () => {
      const p = products.find((x) => boms.some((b) => b.product_id === x.id)) || products[0];
      if (!p) return toast("No product");
      const qty = Number(prompt(`Qty to produce (${p.sku})`, "10") || 0);
      if (!qty) return;
      const bom = boms.find((b) => b.product_id === p.id);
      const r = await API.post("/api/manufacturing/work-orders", { product_id: p.id, bom_id: bom?.id || null, qty });
      toast(`WO ${r.number} planned`);
      pageManufacturing(el);
    });
    el.querySelectorAll("[data-adv]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const r = await API.post(`/api/manufacturing/work-orders/${btn.dataset.adv}/advance`);
        toast(`${r.number} → ${r.status}`);
        pageManufacturing(el);
      });
    });
    el.querySelectorAll("[data-ch]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const r = await API.post(`/api/production/challans/from-wo/${btn.dataset.ch}`, {});
          toast(`Challan ${r.number}`);
          flowSave(`Challan ${r.number}`, r, "Production challans list · Receive stock = godown qty badhega.");
          pageManufacturing(el);
        } catch (e) { toast(e.message); }
      });
    });
    el.querySelectorAll("[data-recv]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const r = await API.post(`/api/production/challans/${btn.dataset.recv}/receive-stock`, {});
          toast(`Stock +${r.qty} → ${r.warehouse}`);
          flowSave("Stock received", r, "Inventory / godown stock me qty dikhega · Stock moves ledger me entry.");
          pageManufacturing(el);
        } catch (e) { toast(e.message); }
      });
    });
  }

  async function pageQuality(el) {
    const rows = await API.get("/api/quality/inspections");
    const pass = rows.filter((q) => String(q.result).toLowerCase() === "pass").length;
    const fail = rows.filter((q) => String(q.result).toLowerCase() === "fail").length;
    el.innerHTML = `
      ${moduleIntro("Quality / CAPA", "Incoming, process & outgoing inspections. Fail → CAPA notes. Manufacturing profile pe yeh critical hai; retail pe optional.", {
        inspections: rows.length, pass, fail, pending: rows.length - pass - fail,
      }, `<button class="btn btn-primary btn-sm" id="qi-new">+ Inspection</button>`)}
      <div class="panel glass"><div class="panel-hd"><h2>Inspections</h2></div>
        <div class="panel-bd">${table(
          ["Number", "Type", "Ref", "Checklist", "Result", "CAPA", ""],
          rows.map((q) => [
            q.number,
            q.inspection_type,
            q.ref || "—",
            (q.checklist || []).length ? (q.checklist || []).map((c) => c.item || c.name || JSON.stringify(c)).slice(0, 3).join("; ") : "—",
            `<span class="pill ${String(q.result).toLowerCase() === "pass" ? "ok" : String(q.result).toLowerCase() === "fail" ? "danger" : ""}">${q.result}</span>`,
            q.capa || "—",
            q.result === "pending"
              ? `<button class="btn btn-ghost btn-sm" data-pass="${q.id}">Pass</button> <button class="btn btn-ghost btn-sm" data-fail="${q.id}">Fail+CAPA</button>`
              : "—",
          ])
        )}
        ${!rows.length ? `<p class="hint">No inspections yet — seed demo or add one.</p>` : ""}
      </div></div>`;
    $("#qi-new")?.addEventListener("click", async () => {
      const ref = prompt("Reference (WO / PO / Batch)", "WO-DEMO");
      if (ref == null) return;
      await API.post("/api/quality/inspections", {
        inspection_type: "incoming",
        ref,
        checklist: [{ item: "Visual", ok: true }, { item: "Dimension", ok: true }],
        result: "pending",
        capa: "",
      });
      toast("Inspection created");
      showSavedDetail("Quality inspection saved", { ref, result: "pending", type: "incoming" });
      pageQuality(el);
    });
    el.querySelectorAll("[data-pass]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await API.post(`/api/quality/inspections/${btn.dataset.pass}/decide`, { result: "pass" });
        toast("Passed");
        pageQuality(el);
      });
    });
    el.querySelectorAll("[data-fail]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const capa = prompt("CAPA note", "Rework + supplier alert") || "CAPA opened";
        await API.post(`/api/quality/inspections/${btn.dataset.fail}/decide`, { result: "fail", capa });
        toast("Failed + CAPA");
        pageQuality(el);
      });
    });
  }

  async function pageHRMS(el) {
    const [emps, att, payroll, leaves, disbursements, expenses, tracking, salPol, perf, loans] = await Promise.all([
      API.get("/api/hrms/employees"),
      API.get("/api/hrms/attendance"),
      API.get("/api/hrms/payroll"),
      API.get("/api/hrms/leaves"),
      API.get("/api/hrms/disbursements"),
      API.get("/api/hrms/expenses"),
      API.get("/api/hrms/tracking/live"),
      API.get("/api/hrms/salary-policy").catch(() => ({ mode: "labour_safe", labour_note: "" })),
      API.get("/api/hrms/performance").catch(() => ({ employees: [] })),
      API.get("/api/hrms/loans").catch(() => []),
    ]);
    const active = emps.filter((e) => e.active !== false);
    const empOpts = active.map((e) => ({ value: e.id, label: `${e.code} · ${e.full_name}` }));
    const empName = (id) => (emps.find((e) => e.id === id) || {}).full_name || id;
    const lastPay = payroll[payroll.length - 1];
    const perfRows = perf.employees || [];
    const periodDefault = new Date().toISOString().slice(0, 7);
    el.innerHTML = `
      <div class="panel glass"><div class="panel-bd">
        <div class="row" style="flex-wrap:wrap;gap:8px">
          <a class="btn btn-accent btn-sm" href="#/hr-flow">▶ Start HR Live Flow</a>
          <a class="btn btn-ghost btn-sm" href="#/compliance">Legal & Risk board</a>
          <span class="hint" style="margin:0">SBAC HR parity · Employee → Leave/Attendance → Salary Confirm→Approve→Disburse · Loans EMI</span>
        </div>
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Salary policy (labour-aware)</h2>
        <button class="btn btn-primary btn-sm" id="save-sal-pol">Save policy</button></div>
        <div class="panel-bd">
          <p class="hint">${salPol.labour_note || "Code on Wages: arbitrary deductions restricted. Cut is optional — approve on Legal board first."}</p>
          <div class="grid-3" style="gap:10px;margin-top:8px">
            <div class="field"><label>Mode</label>
              <select id="sal-mode">
                <option value="labour_safe"${salPol.mode === "labour_safe" ? " selected" : ""}>labour_safe</option>
                <option value="target_first"${salPol.mode === "target_first" ? " selected" : ""}>target_first</option>
                <option value="hybrid"${salPol.mode === "hybrid" ? " selected" : ""}>hybrid</option>
              </select></div>
            <div class="field"><label>Sales pay basis</label>
              <select id="sal-sales-basis">
                <option value="target"${salPol.sales_pay_basis === "target" ? " selected" : ""}>target</option>
                <option value="hybrid"${salPol.sales_pay_basis === "hybrid" ? " selected" : ""}>hybrid</option>
                <option value="attendance"${salPol.sales_pay_basis === "attendance" ? " selected" : ""}>attendance</option>
              </select></div>
            <div class="field"><label>Attendance salary cut</label>
              <select id="sal-cut">
                <option value="0"${!salPol.attendance_cut_enabled ? " selected" : ""}>OFF</option>
                <option value="1"${salPol.attendance_cut_enabled ? " selected" : ""}>ON (needs Legal approve)</option>
              </select>
              <span class="hint">Gate: ${salPol.cut_gate_approved ? "approved" : "blocked — Compliance → Approve salary cut"}</span>
            </div>
            <div class="field"><label>Max cut % (0–50)</label>
              <input id="sal-cut-pct" type="number" min="0" max="50" value="${Number(salPol.max_attendance_cut_pct || 0)}" /></div>
            <div class="field"><label>Target full-pay %</label>
              <input id="sal-thr" type="number" min="50" max="150" value="${Number(salPol.target_full_pay_threshold_pct || 100)}" /></div>
            <div class="field"><label>Incentive overachieve</label>
              <select id="sal-inc">
                <option value="1"${salPol.incentive_on_overachieve !== false ? " selected" : ""}>Yes</option>
                <option value="0"${salPol.incentive_on_overachieve === false ? " selected" : ""}>No</option>
              </select></div>
          </div>
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Sales / marketing performance</h2>
        <button class="btn btn-accent btn-sm" id="set-perf">Update target</button></div>
        <div class="panel-bd">
          <p class="hint">${perf.note || ""}</p>
          ${table(
            ["Code", "Name", "Dept", "Target", "Achieved", "%", "Updated"],
            perfRows.map((p) => [
              p.code, p.name, p.department || "—",
              p.monthly_target != null ? money(p.monthly_target) : "—",
              p.achieved != null ? money(p.achieved) : "—",
              p.target_achieved_pct != null ? `${p.target_achieved_pct}%` : "—",
              (p.updated_at || "—").toString().slice(0, 10),
            ])
          )}
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Employee Master</h2>
        <div class="row">
          <button class="btn btn-primary btn-sm" id="hire-emp">+ Hire / Employee</button>
          <button class="btn btn-ghost btn-sm" id="run-pay">Run Payroll (draft)</button>
        </div></div>
        <div class="panel-bd">${table(
          ["Code", "Name", "Dept", "Grade", "Type", "GPS consent", "Status", "Bank", "Basic", ""],
          emps.map((e) => [
            e.code,
            e.full_name,
            e.department,
            (e.custom || {}).grade || "—",
            `<span class="pill">${e.work_type || "office"}</span>`,
            e.gps_consent ? `<span class="pill ok">offer+app</span>` : `<span class="pill warn">pending</span>`,
            e.active === false ? `<span class="pill danger">relieved</span>` : `<span class="pill ok">active</span>`,
            e.bank_account ? `****${String(e.bank_account).slice(-4)}` : "—",
            money(e.basic_salary),
            e.active === false
              ? `<button class="btn btn-ghost btn-sm" data-emp-d="${e.id}">Details</button>`
              : `${e.gps_consent ? "" : `<button class="btn btn-accent btn-sm" data-consent="${e.id}">Record consent</button> `}<button class="btn btn-ghost btn-sm" data-exit="${e.id}">Exit</button> <button class="btn btn-ghost btn-sm" data-emp-d="${e.id}">Details</button>`,
          ])
        )}</div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Attendance</h2>
          <button class="btn btn-primary btn-sm" id="mark-att">Mark attendance</button>
          <button class="btn btn-accent btn-sm" id="proc-att">Process month</button>
          <button class="btn btn-ghost btn-sm" id="mark-face">Device face → Present</button></div>
          <div class="panel-bd">${table(["Day", "Employee", "Status", "In", "Out", "Source"], att.map((a) => [a.day, a.employee_name || empName(a.employee_id), a.status, a.check_in || "—", a.check_out || "—", a.source || "—"]))}</div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Payroll · Confirm → Approve → Disburse</h2>
          <button class="btn btn-ghost btn-sm" id="confirm-pay" ${lastPay && ["draft","processed"].includes(lastPay.status) ? "" : "disabled"}>Confirm</button>
          <button class="btn btn-ghost btn-sm" id="approve-pay" ${lastPay && ["confirmed","draft","processed"].includes(lastPay.status) ? "" : "disabled"}>Approve</button>
          <button class="btn btn-ghost btn-sm" id="view-payslip" ${lastPay ? "" : "disabled"}>View payslips</button></div>
          <div class="panel-bd">${table(["Period", "Status", "Employees"], payroll.map((p) => [p.period, `<span class="pill ${p.status === "approved" || p.status === "disbursed" ? "ok" : p.status === "draft" ? "warn" : ""}">${p.status}</span>`, (p.lines || []).length]))}
          <div id="payslip-box"></div></div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Salary Bank Disbursement</h2>
        <button class="btn btn-accent btn-sm" id="disburse-pay">Disburse to bank</button></div>
        <div class="panel-bd">
          ${stubNote("Flow: Run payroll (draft) → Confirm → Approve → Disburse. DEMO-LIVE NEFT + salary voucher. EMI deducted from active loans.")}
          ${table(
            ["Period", "Mode", "Total", "Status", "UTRs"],
            disbursements.map((d) => [
              d.period, d.mode, money(d.total_amount),
              `<span class="pill ok">${d.status}</span>`,
              (d.lines || []).filter((l) => l.utr).length,
            ])
          )}
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Leave Requests</h2>
        <button class="btn btn-primary btn-sm" id="apply-leave">+ Apply leave</button></div>
        <div class="panel-bd">${table(
          ["Employee", "Type", "From", "To", "Status", "Reason", "Action"],
          leaves.map((l) => [
            l.employee_name || empName(l.employee_id),
            l.leave_type,
            l.from_date,
            l.to_date,
            `<span class="pill ${l.status === "approved" ? "ok" : l.status === "rejected" ? "danger" : "warn"}">${l.status}</span>`,
            l.reason || "—",
            l.status === "pending"
              ? `<button class="btn btn-ghost btn-sm" data-leave-ok="${l.id}">Approve</button> <button class="btn btn-ghost btn-sm" data-leave-no="${l.id}">Reject</button>`
              : "—",
          ])
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Employee Loans</h2>
        <button class="btn btn-primary btn-sm" id="add-loan">+ Loan entry</button></div>
        <div class="panel-bd">${table(
          ["Emp", "Amount", "EMI", "Tenure", "Purpose", "Status", ""],
          (loans || []).map((ln) => [
            ln.employee_name || empName(ln.employee_id),
            money(ln.amount),
            money(ln.emi),
            `${ln.tenure_months || "—"} mo`,
            ln.purpose || "—",
            `<span class="pill ${ln.status === "active" || ln.status === "approved" ? "ok" : ln.status === "rejected" ? "danger" : "warn"}">${ln.status}</span>`,
            ln.status === "pending"
              ? `<button class="btn btn-ghost btn-sm" data-loan-ok="${ln.id}">Approve</button> <button class="btn btn-ghost btn-sm" data-loan-no="${ln.id}">Reject</button>`
              : "—",
          ])
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Marketing / Field Expenses</h2>
        <button class="btn btn-primary btn-sm" id="add-exp">+ Claim</button></div>
        <div class="panel-bd">
          ${stubNote("Field claims → Approve / Reject / Mark paid. Paid posts payment voucher to books (DEMO-LIVE).")}
          ${table(
            ["Emp", "Date", "Category", "Amount", "Status", "Action"],
            expenses.map((x) => [
              x.employee_name || x.employee_id,
              x.claim_date,
              x.category,
              money(x.amount),
              `<span class="pill ${x.status === "approved" || x.status === "paid" ? "ok" : x.status === "rejected" ? "danger" : "warn"}">${x.status}</span>`,
              x.status === "pending"
                ? `<button class="btn btn-ghost btn-sm" data-approve="${x.id}">Approve</button> <button class="btn btn-ghost btn-sm" data-reject="${x.id}">Reject</button>`
                : x.status === "approved"
                ? `<button class="btn btn-ghost btn-sm" data-paid="${x.id}">Mark paid</button>`
                : (x.decision_note || "—"),
            ])
          )}
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Live Field Tracking</h2>
        <button class="btn btn-accent btn-sm" id="sim-track">Simulate live ping</button>
        <button class="btn btn-primary btn-sm" id="phone-gps">Phone GPS ping</button></div>
        <div class="panel-bd">
          ${stubNote("GPS = phone lat/lng → /hrms/tracking/ping (realtime). No Maps key needed. Legal gps_always_on + employee consent gate live pings.")}
          <div class="track-map" aria-hidden="true">
            ${(tracking || []).filter((t) => t.lat != null).map((t, i) => {
              const x = 12 + ((Number(t.lng) % 1) * 76);
              const y = 14 + ((Number(t.lat) % 1) * 68);
              return `<div class="track-pin" style="left:${x}%;top:${y}%" title="${t.name}">
                <i></i><span>${t.name.split(" ")[0]}</span>
              </div>`;
            }).join("") || `<div class="track-map__empty">Simulate ping to plot field staff</div>`}
          </div>
          <div class="track-grid">
            ${(tracking || []).map((t) => `
              <div class="track-card glass">
                <div class="track-card__top">
                  <strong>${t.name}</strong>
                  <span class="track-dot ${t.online ? "on" : ""}"></span>
                </div>
                <div class="track-card__meta">${t.code} · ${t.work_type || "field"} · ${t.phone || ""}</div>
                <div class="track-card__place">${t.place_label || "Waiting for ping…"}</div>
                <div class="track-card__coords">${t.lat != null ? `${t.lat}, ${t.lng}` : "—"} · ±${t.accuracy_m ?? "—"}m · 🔋 ${t.battery_pct ?? "—"}%</div>
                <div class="track-card__time">${t.recorded_at || ""}</div>
              </div>`).join("") || "<p>No field staff tracking yet — click Simulate.</p>"}
          </div>
        </div></div>`;
    $("#save-sal-pol")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/hrms/salary-policy", {
          mode: $("#sal-mode")?.value || "labour_safe",
          sales_pay_basis: $("#sal-sales-basis")?.value || "target",
          attendance_cut_enabled: $("#sal-cut")?.value === "1",
          max_attendance_cut_pct: Number($("#sal-cut-pct")?.value || 0),
          target_full_pay_threshold_pct: Number($("#sal-thr")?.value || 100),
          incentive_on_overachieve: $("#sal-inc")?.value === "1",
          attendance_cut_requires_reason: true,
        });
        toast(`Salary policy saved · mode ${r.mode}`);
        pageHRMS(el);
      } catch (e) { toast(e.message || "Policy save failed — approve cut on Legal board if enabling cut"); }
    });
    $("#set-perf")?.addEventListener("click", async () => {
      const emp = active.find((e) => /sales|marketing|field/i.test(`${e.department} ${e.work_type}`)) || active[0] || emps[0];
      if (!emp) return toast("No employee");
      const t = prompt(`Monthly target ₹ for ${emp.full_name}`, "200000");
      if (t == null) return;
      const a = prompt("Achieved ₹ this month", "200000");
      if (a == null) return;
      try {
        const r = await API.post("/api/hrms/performance", {
          employee_id: emp.id,
          monthly_target: Number(t),
          achieved: Number(a),
          note: "Updated from HRMS",
        });
        toast(`${emp.code} · ${r.performance?.target_achieved_pct}% of target`);
        pageHRMS(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
    $("#run-pay")?.addEventListener("click", async () => {
      const r = await API.post("/api/hrms/payroll/run");
      toast(r.message || `Payroll ${r.period} draft · ${r.employees} employees`);
      flowSave(`Payroll ${r.period}`, r, "Confirm → Approve → Disburse.");
      pageHRMS(el);
    });
    $("#confirm-pay")?.addEventListener("click", async () => {
      if (!lastPay) return;
      try {
        const r = await API.post(`/api/hrms/payroll/${lastPay.id}/confirm`);
        toast(r.message || "Confirmed");
        pageHRMS(el);
      } catch (e) { toast(e.message || "Confirm failed"); }
    });
    $("#approve-pay")?.addEventListener("click", async () => {
      if (!lastPay) return;
      try {
        const r = await API.post(`/api/hrms/payroll/${lastPay.id}/approve`);
        toast(r.message || "Approved");
        pageHRMS(el);
      } catch (e) { toast(e.message || "Approve failed"); }
    });
    $("#hire-emp")?.addEventListener("click", () => {
      const today = new Date().toISOString().slice(0, 10);
      openMasterForm(
        "Employee Master",
        [
          { name: "full_name", label: "First / Full Name *", required: true, placeholder: "txtfirstname" },
          {
            name: "gender",
            label: "Gender",
            type: "select",
            options: [
              { value: "Male", label: "Male" },
              { value: "Female", label: "Female" },
            ],
            value: "Male",
          },
          { name: "department", label: "Department", value: "Sales", placeholder: "ddldept" },
          { name: "designation", label: "Designation", value: "Executive", placeholder: "ddldesig" },
          {
            name: "grade",
            label: "Grade",
            type: "select",
            options: ["A", "B", "C", "D", "E"].map((g) => ({ value: g, label: g })),
            value: "C",
          },
          { name: "phone", label: "Phone", placeholder: "txtphone" },
          { name: "email", label: "Personal Email", placeholder: "txtemail" },
          { name: "company_email", label: "Company Email", placeholder: "txtcompemail" },
          { name: "biometric_id", label: "Biometric ID", placeholder: "txtBiometricID" },
          { name: "pf_no", label: "PF No", placeholder: "txtpfno" },
          { name: "esi_no", label: "ESI No", placeholder: "txtesino" },
          { name: "dob", label: "Date of Birth", type: "date" },
          { name: "join_date", label: "Joining Date", type: "date", value: today },
          { name: "username", label: "User Name", placeholder: "txtuser" },
          {
            name: "smtp_type",
            label: "SMTP Type",
            type: "select",
            options: [
              { value: "Self", label: "Self" },
              { value: "Department", label: "Department" },
            ],
            value: "Self",
          },
          { name: "father_name", label: "Father Name", placeholder: "txtffirstname" },
          { name: "father_phone", label: "Father Phone", placeholder: "txtfphone" },
          { name: "father_profession", label: "Father Profession", placeholder: "txtfprof" },
          { name: "mother_name", label: "Mother Name", placeholder: "txtmfirstname" },
          { name: "mother_phone", label: "Mother Phone", placeholder: "txtmphone" },
          { name: "mother_profession", label: "Mother Profession", placeholder: "txtmprof" },
          {
            name: "emp_status",
            label: "Status",
            type: "select",
            options: [
              { value: "Active", label: "Active" },
              { value: "Inactive", label: "Inactive" },
            ],
            value: "Active",
          },
          { name: "status_date", label: "Status Date", type: "date", value: today },
          {
            name: "experience_type",
            label: "Experience",
            type: "select",
            options: [
              { value: "Experience", label: "Experience" },
              { value: "Fresher", label: "Fresher" },
            ],
            value: "Experience",
          },
          {
            name: "pay_mode",
            label: "Pay Mode",
            type: "select",
            options: [
              { value: "Salary", label: "Salary" },
              { value: "Imprest", label: "Imprest" },
            ],
            value: "Salary",
          },
          { name: "basic_salary", label: "Salary ₹", type: "number", value: "25000", required: true },
          {
            name: "salary_month",
            label: "Salary Month",
            type: "select",
            options: ["January","February","March","April","May","June","July","August","September","October","November","December"].map((m) => ({ value: m, label: m })),
            value: "April",
          },
          { name: "increment_amount", label: "Increment ₹", type: "number", value: "0" },
          {
            name: "increment_month",
            label: "Increment Month",
            type: "select",
            options: ["", "January","February","March","April","May","June","July","August","September","October","November","December"].map((m) => ({ value: m, label: m || "—" })),
            value: "",
          },
          {
            name: "work_type",
            label: "Work type",
            type: "select",
            options: [
              { value: "office", label: "Office" },
              { value: "field", label: "Field" },
              { value: "marketing", label: "Marketing / Sales" },
            ],
            value: "office",
          },
          { name: "shift", label: "Shift", value: "general" },
          { name: "latitude", label: "Latitude", placeholder: "txtLatitude" },
          { name: "longitude", label: "Longitude", placeholder: "txtLongitude" },
          { name: "distance", label: "Distance (m)", placeholder: "txtDistance" },
          { name: "aadhaar", label: "Aadhaar No", placeholder: "txtadharno" },
          { name: "pan", label: "PAN", placeholder: "txtpancardno" },
          { name: "licence_no", label: "Licence No", placeholder: "txtlicenceno" },
          { name: "voter_no", label: "Voter No", placeholder: "txtvoterno" },
          { name: "blood_group", label: "Blood group", placeholder: "B+" },
          { name: "bank_name", label: "Bank Name", value: "SBI", placeholder: "txtbank" },
          { name: "ifsc", label: "IFSC", value: "SBIN0001122", placeholder: "txtifsc" },
          { name: "bank_account", label: "Account No", placeholder: "txtaccount (blank=auto)" },
          { name: "bank_holder", label: "Account Holder", placeholder: "txtholder" },
          { name: "bank_branch", label: "Branch", placeholder: "txtbranch" },
          {
            name: "account_type",
            label: "Account Type",
            type: "select",
            options: [
              { value: "Salary Acount", label: "Salary Account" },
              { value: "Personal Account", label: "Personal Account" },
            ],
            value: "Salary Acount",
          },
          { name: "address", label: "Address 1", type: "textarea", placeholder: "txtaddress" },
          { name: "state", label: "State", placeholder: "ddlstate" },
          { name: "city", label: "City", placeholder: "ddlcity" },
          { name: "pincode", label: "Pincode", placeholder: "txtpincode" },
          { name: "address_contact", label: "Address Contact", placeholder: "txtaddresscontact" },
          { name: "address2", label: "Address 2", type: "textarea", placeholder: "txtaddress2" },
          { name: "state2", label: "State 2", placeholder: "ddlstate2" },
          { name: "city2", label: "City 2", placeholder: "ddlcity2" },
          { name: "pincode2", label: "Pincode 2", placeholder: "txtpincode2" },
          { name: "owner_name", label: "Owner Name", placeholder: "txtowner" },
          { name: "owner_phone", label: "Owner Phone", placeholder: "txtownerphone" },
          { name: "emergency_contact", label: "Emergency contact", placeholder: "Name · phone" },
          {
            name: "gps_consent",
            label: "GPS consent (offer + app)",
            type: "select",
            options: [
              { value: "0", label: "No (office / later)" },
              { value: "1", label: "Yes — record at hire" },
            ],
            value: "0",
          },
        ],
        async (data) => {
          const field = data.work_type === "field" || data.work_type === "marketing";
          const gps = data.gps_consent === "1" || field;
          const r = await API.post("/api/hrms/employees", {
            full_name: data.full_name,
            father_name: data.father_name || "",
            phone: data.phone || "",
            email: data.email || "",
            department: data.department || (field ? "Sales" : "Operations"),
            designation: data.designation || "Staff",
            grade: data.grade || "",
            work_type: data.work_type || "office",
            shift: data.shift || "general",
            basic_salary: Number(data.basic_salary || 25000),
            join_date: data.join_date || null,
            aadhaar: data.aadhaar || "",
            pan: data.pan || "",
            blood_group: data.blood_group || "",
            emergency_contact: data.emergency_contact || "",
            address: data.address || "",
            bank_name: data.bank_name || "SBI",
            bank_account: data.bank_account || "",
            ifsc: data.ifsc || "",
            offer_letter_gps_ack: gps,
            app_install_gps_ack: gps,
            gender: data.gender || "",
            company_email: data.company_email || "",
            biometric_id: data.biometric_id || "",
            dob: data.dob || "",
            username: data.username || "",
            smtp_type: data.smtp_type || "",
            father_phone: data.father_phone || "",
            father_profession: data.father_profession || "",
            mother_name: data.mother_name || "",
            mother_phone: data.mother_phone || "",
            mother_profession: data.mother_profession || "",
            emp_status: data.emp_status || "Active",
            status_date: data.status_date || "",
            experience_type: data.experience_type || "",
            pay_mode: data.pay_mode || "Salary",
            salary_month: data.salary_month || "",
            increment_amount: Number(data.increment_amount || 0),
            increment_month: data.increment_month || "",
            latitude: data.latitude || "",
            longitude: data.longitude || "",
            distance: data.distance || "",
            licence_no: data.licence_no || "",
            voter_no: data.voter_no || "",
            pf_no: data.pf_no || "",
            esi_no: data.esi_no || "",
            bank_holder: data.bank_holder || "",
            bank_branch: data.bank_branch || "",
            account_type: data.account_type || "Salary Acount",
            state: data.state || "",
            city: data.city || "",
            pincode: data.pincode || "",
            address_contact: data.address_contact || "",
            address2: data.address2 || "",
            state2: data.state2 || "",
            city2: data.city2 || "",
            pincode2: data.pincode2 || "",
            owner_name: data.owner_name || "",
            owner_phone: data.owner_phone || "",
          });
          toast(r.message || `Hired ${r.code}`);
          flowSave(`Hired ${r.code}`, r, "Attendance · Leave · Payroll · Loans.");
          pageHRMS(el);
        },
        { eyebrow: "HR · Employee Master (SBAC live 2026-08-02)" }
      );
    });
    el.querySelectorAll("[data-emp-d]").forEach((btn) => {
      const row = emps.find((e) => String(e.id) === btn.dataset.empD);
      btn.addEventListener("click", () => openDetail(row?.full_name || "Employee", row || {}, { eyebrow: "Employee master", showJson: false }));
    });
    el.querySelectorAll("[data-consent]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Record GPS consent?\nEmployee signed offer letter clause + accepted on app install.\nApproval aapke paas on file rahega.")) return;
        try {
          const r = await API.post("/api/hrms/consent", {
            employee_id: Number(btn.dataset.consent),
            offer_letter_ack: true,
            app_install_ack: true,
            gps_consent: true,
            note: "Offer letter + app install Accept",
          });
          toast(r.message || "Consent saved");
          pageHRMS(el);
        } catch (e) { toast(e.message || "Consent failed"); }
      });
    });
    $("#mark-att")?.addEventListener("click", () => {
      if (!empOpts.length) return toast("Pehle employee hire karo");
      openMasterForm(
        "Mark Attendance",
        [
          { name: "employee_id", label: "Employee", type: "select", options: empOpts, value: empOpts[0]?.value, required: true },
          {
            name: "status",
            label: "Status",
            type: "select",
            options: ["present", "absent", "half_day", "leave", "holiday"],
            value: "present",
          },
          { name: "day", label: "Date", type: "date", value: new Date().toISOString().slice(0, 10) },
          { name: "check_in", label: "Check in", value: "09:30" },
          { name: "check_out", label: "Check out", value: "18:00" },
          {
            name: "source",
            label: "Source",
            type: "select",
            options: ["manual", "biometric", "device_face"],
            value: "manual",
          },
        ],
        async (data) => {
          const r = await API.post("/api/hrms/attendance", {
            employee_id: Number(data.employee_id),
            day: data.day || null,
            status: data.status || "present",
            check_in: data.check_in || "09:30",
            check_out: data.check_out || "18:00",
            source: data.source || "manual",
          });
          toast(`Attendance ${r.status}`);
          pageHRMS(el);
        },
        { eyebrow: "HR · Attendance" }
      );
    });
    $("#proc-att")?.addEventListener("click", () => {
      const [yy, mm] = periodDefault.split("-");
      const lastDay = new Date(Number(yy), Number(mm), 0).toISOString().slice(0, 10);
      openMasterForm(
        "Process Salary Attendance",
        [
          { name: "period", label: "Month (YYYY-MM)", value: periodDefault, required: true },
          { name: "from_date", label: "From Date", type: "date", value: `${periodDefault}-01` },
          { name: "to_date", label: "To Date", type: "date", value: lastDay },
          { name: "employee_id", label: "Employee (blank = all)", type: "select", options: [{ value: "", label: "— All —" }, ...empOpts], value: "" },
          {
            name: "status",
            label: "Fill missing as",
            type: "select",
            options: ["present", "absent"],
            value: "present",
          },
          {
            name: "process_status",
            label: "Process Status",
            type: "select",
            options: [
              { value: "Processed", label: "Processed" },
              { value: "Pending", label: "Pending" },
            ],
            value: "Processed",
          },
        ],
        async (data) => {
          const r = await API.post("/api/hrms/attendance/process-month", {
            period: data.period,
            status: data.status || "present",
            fill_missing: true,
            from_date: data.from_date || null,
            to_date: data.to_date || null,
            employee_id: data.employee_id ? Number(data.employee_id) : null,
            process_status: data.process_status || "Processed",
          });
          toast(r.message || `Created ${r.created}`);
          pageHRMS(el);
        },
        { eyebrow: "HR · ProcessSalaryAttendance (SBAC)" }
      );
    });
    $("#mark-face")?.addEventListener("click", async () => {
      const emp = active[0] || emps[0];
      if (!emp) return toast("No employee");
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, "0");
      const mm = String(now.getMinutes()).padStart(2, "0");
      try {
        const r = await API.post("/api/hrms/attendance", {
          employee_id: emp.id,
          status: "present",
          check_in: `${hh}:${mm}`,
          check_out: "18:00",
          source: "device_face",
        });
        toast(`Face unlock → Present · ${emp.full_name}`);
        flowSave(`Attendance face ${emp.code}`, r, "On-device face unlock → Present (no biometrics stored in ERP).");
        pageHRMS(el);
      } catch (e) { toast(e.message || "Face mark failed"); }
    });
    $("#apply-leave")?.addEventListener("click", () => {
      if (!empOpts.length) return toast("Pehle employee hire karo");
      const today = new Date().toISOString().slice(0, 10);
      openMasterForm(
        "Leave Application",
        [
          { name: "employee_id", label: "Employee", type: "select", options: empOpts, value: empOpts[0]?.value, required: true },
          {
            name: "leave_type",
            label: "Leave type",
            type: "select",
            options: ["casual", "sick", "earned", "unpaid", "comp_off"],
            value: "casual",
          },
          { name: "from_date", label: "From", type: "date", value: today, required: true },
          { name: "to_date", label: "To", type: "date", value: today, required: true },
          { name: "reason", label: "Reason", type: "textarea", placeholder: "Reason", required: true },
        ],
        async (data) => {
          const r = await API.post("/api/hrms/leaves", {
            employee_id: Number(data.employee_id),
            leave_type: data.leave_type || "casual",
            from_date: data.from_date,
            to_date: data.to_date,
            reason: data.reason || "",
          });
          toast(`Leave #${r.id} pending`);
          pageHRMS(el);
        },
        { eyebrow: "HR · Leave (SBAC parity)" }
      );
    });
    $("#add-loan")?.addEventListener("click", () => {
      if (!empOpts.length) return toast("Pehle employee hire karo");
      const today = new Date().toISOString().slice(0, 10);
      openMasterForm(
        "Employee Loan Entry",
        [
          { name: "employee_id", label: "Employee", type: "select", options: empOpts, value: empOpts[0]?.value, required: true },
          { name: "loan_date", label: "Loan Date", type: "date", value: today },
          { name: "amount", label: "Loan Amount ₹", type: "number", required: true, placeholder: "txtloanamount" },
          { name: "emi", label: "EMI Amount ₹", type: "number", placeholder: "txtemiamount (blank=auto)" },
          { name: "start_date", label: "EMI Start Date", type: "date", value: today },
          { name: "tenure_months", label: "Tenure (months)", type: "number", value: "12" },
          { name: "purpose", label: "Purpose", placeholder: "Personal / medical / …" },
          { name: "notes", label: "Remarks", type: "textarea", placeholder: "txtremarks" },
        ],
        async (data) => {
          const r = await API.post("/api/hrms/loans", {
            employee_id: Number(data.employee_id),
            amount: Number(data.amount),
            tenure_months: Number(data.tenure_months || 12),
            emi: Number(data.emi || 0),
            loan_date: data.loan_date || null,
            start_date: data.start_date || null,
            purpose: data.purpose || "",
            notes: data.notes || "",
          });
          toast(r.message || "Loan pending");
          pageHRMS(el);
        },
        { eyebrow: "HR · Employee Loan Entry (SBAC live)" }
      );
    });
    el.querySelectorAll("[data-loan-ok]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await API.post(`/api/hrms/loans/${btn.dataset.loanOk}/decide`, { status: "approved", note: "Approved" });
        toast("Loan approved · EMI on next payroll");
        pageHRMS(el);
      });
    });
    el.querySelectorAll("[data-loan-no]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await API.post(`/api/hrms/loans/${btn.dataset.loanNo}/decide`, { status: "rejected", note: "Rejected" });
        toast("Loan rejected");
        pageHRMS(el);
      });
    });
    $("#view-payslip")?.addEventListener("click", async () => {
      if (!lastPay) return;
      const r = await API.get(`/api/hrms/payroll/${lastPay.id}/payslips`);
      const box = $("#payslip-box");
      if (!box) return;
      box.innerHTML = `<div class="hint" style="margin:10px 0 6px">Payslips · ${r.period} · Net total ${money(r.totals.net)}</div>` +
        table(["Employee", "Basic", "PF", "ESIC", "Net", "Bank", ""],
          (r.payslips || []).map((p, idx) => [p.name, money(p.basic), money(p.pf), money(p.esic), money(p.net), p.bank_account ? `****${String(p.bank_account).slice(-4)}` : "—",
            `<button class="btn btn-ghost btn-sm" data-slip-print="${idx}">Print</button>`]));
      box.querySelectorAll("[data-slip-print]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const p = (r.payslips || [])[Number(btn.dataset.slipPrint)];
          if (!p) return;
          printSheet(buildPayslipHtml(p, r.period), `Payslip ${p.name}`);
        });
      });
    });
    el.querySelectorAll("[data-exit]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Mark employee as relieved / exit?")) return;
        const r = await API.post(`/api/hrms/employees/${btn.dataset.exit}/exit`);
        toast(r.message || "Exited");
        pageHRMS(el);
      });
    });
    $("#disburse-pay")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/hrms/disbursements/from-payroll");
        toast(r.message || `Disbursed ${money(r.total_amount)} · ${r.status}`);
        flowSave(`Salary ${r.period}`, r, "DEMO-LIVE NEFT batch + salary voucher in books.");
        pageHRMS(el);
      } catch (e) { toast(e.message || "Disburse failed — Confirm + Approve first"); }
    });
    $("#sim-track")?.addEventListener("click", async () => {
      const r = await API.post("/api/hrms/tracking/simulate");
      toast(`Live ping · ${r.updated?.length || 0} field staff`);
      pageHRMS(el);
    });
    $("#phone-gps")?.addEventListener("click", async () => {
      const emp = (emps || []).find((e) => e.track_live || /field|marketing/i.test(e.work_type || "")) || active[0] || emps[0];
      if (!emp) return toast("No employee");
      if (!navigator.geolocation) return toast("Browser GPS not available — use Simulate");
      toast("Reading phone GPS…");
      navigator.geolocation.getCurrentPosition(async (pos) => {
        try {
          const r = await API.post("/api/hrms/tracking/ping", {
            employee_id: emp.id,
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
            accuracy_m: pos.coords.accuracy || 12,
            place_label: "Phone GPS",
            battery_pct: 80,
          });
          toast(`GPS saved · ${emp.full_name}`);
          flowSave(`GPS ${emp.code}`, r, "Realtime phone lat/lng → EmployeeLocation.");
          pageHRMS(el);
        } catch (e) { toast(e.message || "GPS ping blocked — Legal board / consent?"); }
      }, () => toast("GPS permission denied — Allow location or use Simulate"), { enableHighAccuracy: true, timeout: 12000 });
    });
    $("#add-exp")?.addEventListener("click", () => {
      if (!empOpts.length) return toast("Pehle employee hire karo");
      openMasterForm(
        "Expense Claim",
        [
          { name: "employee_id", label: "Employee", type: "select", options: empOpts, value: empOpts[0]?.value, required: true },
          {
            name: "category",
            label: "Category",
            type: "select",
            options: ["travel", "food", "lodging", "fuel", "misc"],
            value: "travel",
          },
          { name: "amount", label: "Amount ₹", type: "number", required: true, placeholder: "1200" },
          { name: "description", label: "Description", type: "textarea", placeholder: "Field expense note" },
        ],
        async (data) => {
          await API.post("/api/hrms/expenses", {
            employee_id: Number(data.employee_id),
            category: data.category || "travel",
            amount: Number(data.amount),
            description: data.description || "",
          });
          toast("Expense claim filed");
          pageHRMS(el);
        },
        { eyebrow: "HR · Field expense" }
      );
    });
    el.querySelectorAll("[data-approve]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await API.post(`/api/hrms/expenses/${btn.dataset.approve}/decide`, { status: "approved", decision_note: "Approved in demo" });
        toast("Expense approved");
        pageHRMS(el);
      });
    });
    el.querySelectorAll("[data-reject]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await API.post(`/api/hrms/expenses/${btn.dataset.reject}/decide`, { status: "rejected", decision_note: "Over limit" });
        toast("Expense rejected");
        pageHRMS(el);
      });
    });
    el.querySelectorAll("[data-paid]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await API.post(`/api/hrms/expenses/${btn.dataset.paid}/decide`, { status: "paid", decision_note: "Paid" });
        toast("Expense marked paid");
        pageHRMS(el);
      });
    });
    el.querySelectorAll("[data-leave-ok]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await API.post(`/api/hrms/leaves/${btn.dataset.leaveOk}/decide`, { status: "approved", decision_note: "Approved" });
        toast("Leave approved");
        pageHRMS(el);
      });
    });
    el.querySelectorAll("[data-leave-no]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await API.post(`/api/hrms/leaves/${btn.dataset.leaveNo}/decide`, { status: "rejected", decision_note: "Not available" });
        toast("Leave rejected");
        pageHRMS(el);
      });
    });
  }

  async function pageProjects(el) {
    const projects = await API.get("/api/projects");
    const q = new URLSearchParams((location.hash.split("?")[1] || ""));
    const selectedId = Number(q.get("id") || (projects[0] && projects[0].id) || 0);
    const cur = projects.find((p) => p.id === selectedId) || projects[0];
    let tasks = [];
    if (cur) tasks = await API.get(`/api/projects/${cur.id}/tasks`);
    const cols = { todo: [], doing: [], done: [] };
    tasks.forEach((t) => (cols[t.status] || cols.todo).push(t));
    const active = projects.filter((p) => String(p.status || "").toLowerCase() !== "closed");
    el.innerHTML = `
      ${moduleIntro("Projects / Delivery", "Customer delivery projects with task kanban. Select any project — move tasks todo → doing → done.", {
        projects: projects.length, active: active.length, tasks: tasks.length,
        todo: cols.todo.length, doing: cols.doing.length, done: cols.done.length,
      }, `<button class="btn btn-primary btn-sm" id="add-proj">+ Project</button>
         <button class="btn btn-accent btn-sm" id="add-task" ${cur ? "" : "disabled"}>+ Task</button>`)}
      <div class="panel glass"><div class="panel-hd"><h2>Projects</h2></div><div class="panel-bd">${table(
        ["Code", "Name", "Progress", "Status", ""],
        projects.map((p) => [
          p.code,
          p.name,
          p.progress + "%",
          `<span class="pill">${p.status}</span>`,
          `<button class="btn btn-ghost btn-sm" data-open-proj="${p.id}">${p.id === cur?.id ? "Selected" : "Open kanban"}</button>`,
        ]),
        "No projects — create one."
      )}
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Kanban · ${cur?.name || "Tasks"}</h2>
        <button class="btn btn-sm btn-ghost" id="proj-refresh" ${cur ? "" : "disabled"}>Refresh</button></div><div class="panel-bd">
        <div class="kanban">
          ${["todo", "doing", "done"].map((s) => `<div class="kanban-col"><h3>${s} (${(cols[s] || []).length})</h3>${(cols[s] || []).map((t) => `
            <div class="card-item">
              <strong>${t.title}</strong>
              <small style="display:block;opacity:.7;margin:4px 0">${t.milestone || t.status}</small>
              <div class="row" style="gap:4px;flex-wrap:wrap">
                ${s !== "todo" ? `<button class="btn btn-ghost btn-sm" data-task="${t.id}" data-to="todo">← Todo</button>` : ""}
                ${s !== "doing" ? `<button class="btn btn-ghost btn-sm" data-task="${t.id}" data-to="doing">Doing</button>` : ""}
                ${s !== "done" ? `<button class="btn btn-ghost btn-sm" data-task="${t.id}" data-to="done">Done →</button>` : ""}
              </div>
            </div>`).join("") || "<div class='card-item' style='opacity:.5'>—</div>"}</div>`).join("")}
        </div>
      </div></div>`;
    $("#proj-refresh")?.addEventListener("click", () => pageProjects(el));
    el.querySelectorAll("[data-open-proj]").forEach((btn) => {
      btn.addEventListener("click", () => {
        location.hash = `#/projects?id=${btn.dataset.openProj}`;
        pageProjects(el);
      });
    });
    $("#add-proj")?.addEventListener("click", async () => {
      const name = prompt("Project name", "Customer delivery");
      if (!name) return;
      const r = await API.post("/api/projects", { name });
      toast(`Project ${r.code} created`);
      showSavedDetail("Project saved", r);
      location.hash = `#/projects?id=${r.id}`;
      pageProjects(el);
    });
    $("#add-task")?.addEventListener("click", async () => {
      if (!cur) return;
      const title = prompt("Task title");
      if (!title) return;
      await API.post(`/api/projects/${cur.id}/tasks`, { title, status: "todo", milestone: "work" });
      toast("Task added");
      pageProjects(el);
    });
    el.querySelectorAll("[data-task]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const r = await API.patch(`/api/projects/tasks/${btn.dataset.task}`, { status: btn.dataset.to });
        toast(`Task → ${r.status} · progress ${r.project_progress}%`);
        pageProjects(el);
      });
    });
  }

  async function pageService(el) {
    const tickets = await API.get("/api/service/tickets");
    const open = tickets.filter((t) => !["closed", "resolved"].includes(String(t.status || "").toLowerCase()));
    el.innerHTML = `
      ${moduleIntro("Service / AMC / Warranty", "Complaints, AMC visits, warranty claims. Open → In progress → Resolved / Closed.", {
        tickets: tickets.length, open: open.length,
        amc: tickets.filter((t) => String(t.ticket_type).toLowerCase().includes("amc")).length,
      }, `<button class="btn btn-sm btn-primary" id="new-tkt">+ Ticket</button>`)}
      <div class="panel glass"><div class="panel-hd"><h2>Service tickets</h2></div>
      <div class="panel-bd">${table(
        ["Number", "Type", "Subject", "Customer", "Status", "Visit", ""],
        tickets.map((t) => [
          t.number,
          t.ticket_type,
          t.subject,
          t.customer_name || t.customer_id || "—",
          `<span class="pill">${t.status}</span>`,
          t.visit_date || "—",
          ["resolved", "closed"].includes(String(t.status).toLowerCase())
            ? "—"
            : `<button class="btn btn-ghost btn-sm" data-tstart="${t.id}">Start</button>
               <button class="btn btn-ghost btn-sm" data-tresolve="${t.id}">Resolve</button>
               <button class="btn btn-ghost btn-sm" data-tclose="${t.id}">Close</button>`,
        ])
      )}
      ${!tickets.length ? `<p class="hint">No tickets — create one to demo field service.</p>` : ""}
      </div></div>`;
    $("#new-tkt")?.addEventListener("click", async () => {
      const subject = prompt("Ticket subject");
      if (!subject) return;
      const r = await API.post("/api/service/tickets", { subject, ticket_type: "complaint" });
      toast("Ticket created");
      showSavedDetail("Service ticket saved", r);
      pageService(el);
    });
    const decide = async (id, status) => {
      await API.post(`/api/service/tickets/${id}/decide`, { status, notes: `Marked ${status} from UI` });
      toast(`Ticket ${status}`);
      pageService(el);
    };
    el.querySelectorAll("[data-tstart]").forEach((b) => b.addEventListener("click", () => decide(b.dataset.tstart, "in_progress")));
    el.querySelectorAll("[data-tresolve]").forEach((b) => b.addEventListener("click", () => decide(b.dataset.tresolve, "resolved")));
    el.querySelectorAll("[data-tclose]").forEach((b) => b.addEventListener("click", () => decide(b.dataset.tclose, "closed")));
  }

  async function pageDocuments(el) {
    const docs = await API.get("/api/documents");
    el.innerHTML = `
      ${moduleIntro("Documents", "Company file registry — invoices PDFs, contracts, QC photos metadata. Binary store local now; S3/Azure at go-live.", {
        documents: docs.length,
      }, `<label class="btn btn-primary btn-sm" style="cursor:pointer">Upload<input type="file" id="doc-file" hidden /></label>`)}
      <div class="panel glass"><div class="panel-hd"><h2>Registry</h2></div>
      <div class="panel-bd">
        ${stubNote("Local upload live (max 10MB). Object storage path go-live pe switch.")}
        ${docs.length ? table(["Name", "Entity", "MIME", "Ver", "Path"], docs.map((d) => [d.name, d.entity, d.mime, d.version, d.path ? `<a href="${d.path}" target="_blank" rel="noopener">open</a>` : "—"])) : "<p class='hint'>No documents yet — upload to test.</p>"}
      </div></div>`;
    $("#doc-file")?.addEventListener("change", async (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      try {
        await API.upload("/api/documents/upload", file, { entity: "general" });
        toast("Document uploaded");
        pageDocuments(el);
      } catch (err) {
        toast(String(err.message || err));
      }
    });
  }

  async function pageReports(el) {
    const reports = await API.get("/api/reports");
    el.innerHTML = `
      ${moduleIntro("Reports", "Library of operational reports — sales, stock, GST, payroll. Run returns live sample/query data.", {
        reports: reports.length,
      })}
      <div class="panel glass"><div class="panel-hd"><h2>Report library</h2></div>
      <div class="panel-bd">
        ${stubNote("Saare system reports Run kar sakte ho — output neeche dikhega.")}
        ${table(["Code", "Name", "Module", ""], reports.map((r) => [r.code, r.name, r.module, `<button class="btn btn-primary btn-sm" data-run="${r.code}">Run</button>`]))}
      </div>
      <div id="report-out" class="panel-bd"></div></div>`;
    el.querySelectorAll("[data-run]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const data = await API.get(`/api/reports/run/${btn.dataset.run}`);
        const note = data.status === "stub" ? `<div class="stub-note">${data.note || "Not wired yet"}</div>` : "";
        const rows = Array.isArray(data.data) ? data.data : null;
        const pretty = rows && rows.length && typeof rows[0] === "object"
          ? table(Object.keys(rows[0]), rows.map((r) => Object.values(r)))
          : `<pre class="report-pre">${JSON.stringify(data, null, 2)}</pre>`;
        $("#report-out").innerHTML = `${note}${pretty}`;
      });
    });
  }

  async function pageBI(el) {
    const bi = await API.get("/api/bi/overview");
    const trend = bi.revenue_trend || [];
    const abc = bi.abc_analysis || [];
    el.innerHTML = `
      ${moduleIntro("Business Intelligence", "KPIs, revenue trend, forecast & ABC stock bands — same numbers dashboard pe bhi dikhte hain.", {
        trend_months: trend.length, abc_skus: abc.length,
        revenue: bi.kpis?.revenue != null ? money(bi.kpis.revenue) : "—",
      })}
      <div class="kpi-grid">
        ${kpiCard("Revenue", "", { icon: "₹", tone: "blue", raw: bi.kpis.revenue })}
        ${kpiCard("Forecast Next Mo", "", { icon: "◇", tone: "violet", raw: bi.forecast.next_month_sales })}
        ${kpiCard("Inventory", "", { icon: "▣", tone: "teal", raw: bi.kpis.inventory_value })}
        ${kpiCard("Outstanding", "", { icon: "◉", tone: "rose", raw: bi.kpis.outstanding })}
      </div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Revenue Trend</h2></div><div class="panel-bd">${table(["Month", "Revenue"], trend.map((r) => [r.month, money(r.revenue)]))}</div></div>
        <div class="panel glass"><div class="panel-hd"><h2>ABC Analysis</h2></div><div class="panel-bd">${table(["Band", "SKU", "Name", "Price"], abc.map((a) => [a.band, a.sku, a.name, money(a.sale_price)]))}</div></div>
      </div>`;
  }

  async function pageAI(el) {
    el.innerHTML = `
      ${moduleIntro("Kanha Intelligence", "Demo AI + permanent company memory. File/folder ya note se sikhao — baad me poochho to yaad se bataayega.", {
        mode: "demo_ai / llm / memory",
      })}
      <div class="panel glass"><div class="panel-hd"><h2>Kanha Intelligence Layer</h2>
        <span class="pill ok" id="ai-mode-pill">Demo AI ON</span></div><div class="panel-bd">
        <p class="hint" style="margin:0 0 12px">Fully working without API key. Extra seekhana ho to neeche <b>Teach AI</b> — file, folder, ya note. Chat me bhi: <code>Yaad rakh: payment Net 30</code>.</p>
        <div class="auto-actions">
          <a class="btn btn-primary" href="#/agents">Open Kanha Agents</a>
          <a class="btn btn-accent" href="#/whatsapp">WhatsApp OS</a>
          <a class="btn btn-ghost" href="#/compliance">India Compliance</a>
          <a class="btn btn-ghost" href="#/automation">WA Templates</a>
        </div>
      </div></div>

      <div class="panel glass"><div class="panel-hd"><h2>Teach AI · permanent memory</h2>
        <span class="pill ok" id="ai-mem-count">0 memories</span></div>
        <div class="panel-bd">
          <p class="hint" style="margin-top:0">Browser se file/folder choose karo (txt, md, csv, json, code…). Binary/PDF skip. Memory company-scoped — logout ke baad bhi rehti hai.</p>
          <div class="field"><label>Note / policy (text)</label>
            <textarea id="ai-teach-text" rows="3" placeholder="Example: Hamari credit policy Net 30 hai. Overdue pe WhatsApp chase pehle, phir call."></textarea></div>
          <div class="field"><label>Title (optional)</label><input id="ai-teach-title" placeholder="Credit policy" /></div>
          <div class="row" style="flex-wrap:wrap;gap:8px;margin:10px 0">
            <button type="button" class="btn btn-primary btn-sm" id="ai-teach-save">Save to memory</button>
            <label class="btn btn-accent btn-sm" style="cursor:pointer">Upload file
              <input type="file" id="ai-teach-file" hidden accept=".txt,.md,.csv,.json,.log,.py,.js,.ts,.html,.css,.xml,.yml,.yaml,.sql,.toml,.ini" />
            </label>
            <label class="btn btn-ghost btn-sm" style="cursor:pointer">Upload folder
              <input type="file" id="ai-teach-folder" hidden webkitdirectory multiple />
            </label>
            <button type="button" class="btn btn-ghost btn-sm" id="ai-mem-refresh">Refresh list</button>
            <button type="button" class="btn btn-ghost btn-sm" id="ai-mem-clear">Clear all</button>
          </div>
          <div id="ai-mem-list"><div class="hint">Loading memory…</div></div>
        </div>
      </div>

      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>AI Chat Assistant</h2></div><div class="panel-bd">
          <div class="chat-box" id="chat"></div>
          <div class="row" style="flex-wrap:wrap;gap:6px;margin:8px 0" id="ai-chips"></div>
          <div class="row"><input id="ai-msg" style="flex:1;border:1px solid var(--line);border-radius:999px;padding:10px 14px;background:transparent;color:var(--ink)" placeholder="Ask ERP… or Yaad rakh: … / Kya seekha?" /><button class="btn btn-primary" id="ai-send">Send</button></div>
          <div id="ai-wa-draft" class="hint" style="margin-top:10px"></div>
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>AI Purchase Suggestions</h2><button class="btn btn-sm btn-ghost" id="ai-buy">Refresh</button></div>
          <div class="panel-bd" id="ai-buy-out"><div class="hint">Loading…</div></div></div>
      </div>`;
    const chat = $("#chat");
    const push = (who, text) => {
      const b = document.createElement("div");
      b.className = `bubble ${who}`;
      b.textContent = text;
      chat.appendChild(b);
      chat.scrollTop = chat.scrollHeight;
    };
    const setChips = (list) => {
      const box = $("#ai-chips");
      if (!box) return;
      box.innerHTML = (list || []).map((s) => `<button type="button" class="btn btn-ghost btn-sm ai-chip">${s}</button>`).join("");
      box.querySelectorAll(".ai-chip").forEach((btn) => {
        btn.addEventListener("click", () => {
          if ($("#ai-msg")) $("#ai-msg").value = btn.textContent;
          send();
        });
      });
    };
    const renderMem = async () => {
      try {
        const st = await API.get("/api/ai/memory");
        if ($("#ai-mem-count")) $("#ai-mem-count").textContent = `${st.count || 0} memories`;
        const items = st.items || [];
        $("#ai-mem-list").innerHTML = items.length
          ? table(["Title", "Source", "Chars", "When", ""], items.slice(0, 20).map((i) => [
            i.title,
            `${i.source}${i.filename ? " · " + i.filename : ""}`,
            i.chars,
            (i.created_at || "").slice(0, 19).replace("T", " "),
            `<button type="button" class="btn btn-ghost btn-sm" data-mem-del="${i.id}">Delete</button>`,
          ]))
          : `<p class="hint">${st.pitch || "No memory yet — teach a note or upload files."}</p>`;
        $("#ai-mem-list")?.querySelectorAll("[data-mem-del]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            try {
              await API.del(`/api/ai/memory/${btn.getAttribute("data-mem-del")}`);
              toast("Memory deleted");
              renderMem();
            } catch (e) { toast(e.message || "Delete failed"); }
          });
        });
      } catch (e) {
        $("#ai-mem-list").innerHTML = `<div class="hint">${e.message || "Memory load failed"}</div>`;
      }
    };
    setChips(["Show outstanding receivables", "Kya seekha hai memory me?", "Low stock reorder", "Yaad rakh: payment terms Net 30", "GST summary", "Draft WhatsApp overdue chase"]);
    push("bot", "Namaste — Demo AI ON. Extra seekhana ho to Teach panel me file/folder/note do, ya chat me “Yaad rakh: …”. Phir “Kya seekha?” poochho.");
    const send = async () => {
      const msg = $("#ai-msg").value.trim();
      if (!msg) return;
      push("me", msg);
      $("#ai-msg").value = "";
      try {
        const r = await API.post("/api/ai/chat", { message: msg });
        if ($("#ai-mode-pill")) {
          $("#ai-mode-pill").textContent = r.learned ? "MEMORY LEARNED" : r.from_memory ? "FROM MEMORY" : r.live ? "LLM LIVE" : "Demo AI ON";
        }
        push("bot", r.reply);
        if (r.suggestions) setChips(r.suggestions);
        if (r.learned || r.from_memory) renderMem();
        const draftBox = $("#ai-wa-draft");
        if (draftBox && r.whatsapp_draft) {
          const d = r.whatsapp_draft;
          draftBox.innerHTML = `<div class="stub-note" style="margin:0">WhatsApp draft → <b>${d.to_name}</b> (${d.to_phone})
            <button type="button" class="btn btn-accent btn-sm" id="ai-wa-send" style="margin-left:8px">Send via demo WA</button></div>
            <pre class="report-pre" style="margin-top:8px">${d.body}</pre>`;
          $("#ai-wa-send")?.addEventListener("click", async () => {
            try {
              const sent = await API.post("/api/comms/whatsapp/send", {
                to_phone: d.to_phone,
                to_name: d.to_name,
                body: d.body,
                template: d.template || "invoice_overdue",
              });
              toast(sent.message || "WhatsApp sent");
            } catch (e) { toast(e.message || "Send failed"); }
          });
        } else if (draftBox) draftBox.innerHTML = "";
      } catch (e) {
        push("bot", e.message || "AI error");
      }
    };
    $("#ai-send").addEventListener("click", send);
    $("#ai-msg").addEventListener("keydown", (e) => e.key === "Enter" && send());
    $("#ai-teach-save")?.addEventListener("click", async () => {
      const text = $("#ai-teach-text")?.value?.trim() || "";
      if (!text) { toast("Note likho pehle"); return; }
      try {
        const r = await API.post("/api/ai/memory/teach", {
          text,
          title: $("#ai-teach-title")?.value || "",
        });
        toast(r.message || "Learned");
        push("bot", r.message || "Yaad rakh liya");
        if ($("#ai-teach-text")) $("#ai-teach-text").value = "";
        renderMem();
      } catch (e) { toast(e.message || "Teach failed"); }
    });
    $("#ai-teach-file")?.addEventListener("change", async (ev) => {
      const f = ev.target.files?.[0];
      if (!f) return;
      try {
        const r = await API.upload("/api/ai/memory/upload", f);
        toast(r.message || "File learned");
        push("bot", r.message || `Seekh liya: ${f.name}`);
        renderMem();
      } catch (e) { toast(e.message || "Upload failed"); }
      ev.target.value = "";
    });
    $("#ai-teach-folder")?.addEventListener("change", async (ev) => {
      const files = ev.target.files;
      if (!files?.length) return;
      if (!confirm(`${files.length} files folder se seekhega (max 40 text files). Continue?`)) {
        ev.target.value = "";
        return;
      }
      try {
        const r = await API.uploadMany("/api/ai/memory/upload-many", files);
        toast(r.message || "Folder learned");
        push("bot", r.message || "Folder seekh liya");
        if ((r.skipped || []).length) {
          push("bot", `Skipped: ${(r.skipped || []).slice(0, 5).map((s) => s.file + " (" + s.reason + ")").join("; ")}`);
        }
        renderMem();
      } catch (e) { toast(e.message || "Folder upload failed"); }
      ev.target.value = "";
    });
    $("#ai-mem-refresh")?.addEventListener("click", renderMem);
    $("#ai-mem-clear")?.addEventListener("click", async () => {
      if (!confirm("Saari AI memory clear? Yeh undo nahi hoga.")) return;
      try {
        await API.post("/api/ai/memory/clear", {});
        toast("Memory cleared");
        renderMem();
      } catch (e) { toast(e.message || "Clear failed"); }
    });
    const loadBuy = async () => {
      try {
        const r = await API.post("/api/ai/purchase-suggest");
        $("#ai-buy-out").innerHTML = (r.suggestions || []).length
          ? table(["SKU", "Name", "On hand", "Point", "Suggest"], (r.suggestions || []).map((s) => [s.sku, s.name, s.qty, s.reorder_point, s.suggest_order_qty]))
          : `<div class="hint">${r.note || "Stock healthy — no reorder needed."}</div>`;
      } catch (e) {
        $("#ai-buy-out").innerHTML = `<div class="hint">${e.message || "Failed"}</div>`;
      }
    };
    $("#ai-buy").addEventListener("click", loadBuy);
    loadBuy();
    renderMem();
  }

  async function pageAgents(el) {
    const cat = await API.get("/api/agents");
    el.innerHTML = `
      <div class="panel glass agents-hero"><div class="panel-hd"><h2>KanhaERP = Agents × WhatsApp × Compliance</h2>
        <button type="button" class="btn btn-primary" id="agents-run-all">Run all agents</button></div>
        <div class="panel-bd">
          <div class="pillar-row">
            ${(cat.pillars || []).map((p) => `
              <div class="pillar-card pillar-card--${p.id}">
                <strong>${p.title}</strong>
                <span>${p.blurb}</span>
              </div>`).join("")}
          </div>
          <p class="hint" style="margin:14px 0 0">Niche 3 action agents — ye ERP ko “sochne + kaam karne” wali pehchan dete hain.</p>
        </div></div>
      <div class="agent-grid">
        ${(cat.agents || []).map((a) => `
          <div class="panel glass agent-card agent-card--${a.id}">
            <div class="panel-hd"><h2>${a.name}</h2><span class="pill">${a.queue} in queue</span></div>
            <div class="panel-bd">
              <p class="agent-mission">${a.mission}</p>
              <button type="button" class="btn btn-accent" style="width:100%" data-agent="${a.id}">Run ${a.name}</button>
            </div>
          </div>`).join("")}
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Agent output</h2></div><div class="panel-bd"><div id="agent-out" class="auto-out"><div class="hint">Run karke yahan result dikhega</div></div></div></div>`;
    const show = (r) => {
      $("#agent-out").innerHTML = `<pre class="report-pre">${JSON.stringify(r, null, 2)}</pre>`;
    };
    el.querySelectorAll("[data-agent]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-agent");
        try {
          const r = await API.post(`/api/agents/${id}/run`);
          show(r);
          toast(r.message || `${id} done`);
          setTimeout(() => pageAgents(el), 700);
        } catch (e) {
          toast(e.message || "Agent failed");
        }
      });
    });
    $("#agents-run-all")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/agents/run-all");
        show(r);
        toast(r.message || "All agents done");
        setTimeout(() => pageAgents(el), 800);
      } catch (e) {
        toast(e.message || "Failed");
      }
    });
  }

  async function pageWhatsAppOS(el) {
    const [os, waHub] = await Promise.all([
      API.get("/api/whatsapp/os"),
      API.get("/api/automation/whatsapp/hub").catch(() => ({ templates: [], live: false, demo_adapter: true })),
    ]);
    const templates = waHub.templates || [];
    const modeLabel = waHub.live ? "Meta LIVE" : "Demo adapter SENT";
    el.innerHTML = `
      ${moduleIntro("WhatsApp Business OS", "Templates + send fully working. Demo adapter pe status=sent + wamid.DEMO… — sirf Meta keys paste for live Cloud API.", {
        mode: waHub.mode || (waHub.live ? "meta_live" : "demo_sent"),
        templates: templates.length,
      })}
      <div class="panel glass"><div class="panel-hd"><h2>WhatsApp Business OS</h2>
        <span class="pill ok">${modeLabel}</span></div>
        <div class="panel-bd">
          <p class="hint" style="margin:0 0 12px">Desktop forms secondary — WhatsApp pe ORDER / YES / NO / PAY / STOCK. Outbound demo pe bhi real send path (not queue stub).</p>
          <div class="kpi-grid">
            ${kpiCard("Messages", String(os.stats?.messages || 0), { icon: "💬", tone: "teal" })}
            ${kpiCard("Sent", String(os.stats?.sent || 0), { icon: "↗", tone: "blue" })}
            ${kpiCard("Approvals pending", String(os.stats?.approvals_pending || 0), { icon: "✓", tone: "amber" })}
            ${kpiCard("Templates", String(templates.length), { icon: "▣", tone: "blue" })}
          </div>
        </div></div>
      <div class="grid-2">
        <div class="panel glass">
          <div class="panel-hd"><h2>Simulate inbound reply</h2></div>
          <div class="panel-bd">
            <div class="field"><label>From name</label><input id="wa-name" value="Aarav Traders" /></div>
            <div class="field"><label>Phone</label><input id="wa-phone" value="+919876543210" /></div>
            <div class="field"><label>Message</label>
              <select id="wa-text">
                ${(os.quick_replies || []).map((q) => `<option value="${q}">${q}</option>`).join("")}
                <option value="ORDER 10 controllers">ORDER 10 controllers</option>
              </select>
            </div>
            <button type="button" class="btn btn-primary" style="width:100%" id="wa-inbound">Process on WhatsApp OS</button>
            <div id="wa-os-out" class="auto-out" style="margin-top:10px"></div>
          </div>
        </div>
        <div class="panel glass">
          <div class="panel-hd"><h2>Send template (demo → sent)</h2></div>
          <div class="panel-bd">
            <div class="field"><label>Template</label>
              <select id="wa-tpl-code">${templates.map((t) => `<option value="${t.code}">${t.code} — ${t.name}</option>`).join("") || `<option value="invoice_overdue">invoice_overdue</option>`}</select>
            </div>
            <div class="field"><label>To name</label><input id="wa-send-name" value="Aarav Traders" /></div>
            <div class="field"><label>Phone</label><input id="wa-send-phone" value="919876543210" /></div>
            <div class="auto-actions">
              <button type="button" class="btn btn-ghost" id="wa-tpl-preview">Preview</button>
              <button type="button" class="btn btn-accent" id="wa-tpl-send">Send template</button>
              <button type="button" class="btn btn-ghost" id="wa-chase">Cash chase</button>
              <a class="btn btn-ghost" href="#/automation">Edit templates</a>
              <a class="btn btn-ghost" href="#/ai">AI draft</a>
            </div>
            <div id="wa-preview" class="hint" style="margin-top:10px"></div>
          </div>
        </div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Inbox / Outbox</h2>
        <button type="button" class="btn btn-sm btn-ghost" id="wa-refresh-os">Refresh</button></div><div class="panel-bd">
        ${table(
          ["When", "Who", "Phone", "Template", "Status", "Preview"],
          (os.inbox || []).map((m) => [
            (m.created_at || "").slice(0, 19),
            m.to_name || "—",
            m.to_phone,
            m.template,
            `<span class="pill ${m.status === "sent" ? "ok" : ""}">${m.status}</span>`,
            (m.body || "").slice(0, 70) + (m.body && m.body.length > 70 ? "…" : ""),
          ])
        ) || `<div class="hint">Empty — Send template / Cash chase / inbound simulate</div>`}
      </div></div>`;
    $("#wa-inbound")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/whatsapp/os/inbound", {
          from_name: $("#wa-name")?.value,
          from_phone: $("#wa-phone")?.value,
          text: $("#wa-text")?.value,
        });
        $("#wa-os-out").innerHTML = `<pre class="report-pre">${JSON.stringify(r, null, 2)}</pre>`;
        toast(r.reply || r.message);
        setTimeout(() => pageWhatsAppOS(el), 600);
      } catch (e) {
        toast(e.message || "Failed");
      }
    });
    $("#wa-tpl-preview")?.addEventListener("click", async () => {
      try {
        const code = $("#wa-tpl-code")?.value;
        const r = await API.get(`/api/automation/whatsapp/templates/${encodeURIComponent(code)}/preview?name=${encodeURIComponent($("#wa-send-name")?.value || "Aarav")}`);
        $("#wa-preview").innerHTML = `<pre class="report-pre">${r.preview || r.body || JSON.stringify(r, null, 2)}</pre>`;
      } catch (e) { toast(e.message || "Preview failed"); }
    });
    $("#wa-tpl-send")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/comms/whatsapp/send-template", {
          template_code: $("#wa-tpl-code")?.value,
          to_phone: $("#wa-send-phone")?.value,
          to_name: $("#wa-send-name")?.value,
          variables: { name: $("#wa-send-name")?.value || "Aarav", amount: "48,500", number: "INV-DEMO-001" },
        });
        $("#wa-preview").innerHTML = `<pre class="report-pre">${JSON.stringify(r, null, 2)}</pre>`;
        toast(r.message || "Template sent");
        setTimeout(() => pageWhatsAppOS(el), 500);
      } catch (e) { toast(e.message || "Send failed"); }
    });
    $("#wa-chase")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/agents/cash/run");
        toast(r.message);
        pageWhatsAppOS(el);
      } catch (e) {
        toast(e.message || "Failed");
      }
    });
    $("#wa-refresh-os")?.addEventListener("click", () => pageWhatsAppOS(el));
  }

  async function pageApprovals(el) {
    const [hier, inbox, all] = await Promise.all([
      API.get("/api/approvals/hierarchy"),
      API.get("/api/approvals?inbox=true"),
      API.get("/api/approvals"),
    ]);
    const ctrls = hier.module_controls || {};
    const items = inbox.items || [];
    const allItems = all.items || [];
    el.innerHTML = `
      ${moduleIntro("Approvals / Hierarchy", "Har department control — galat data niche se bina approval final nahi. Emergency → seedha Admin/L5 bypass.", {
        my_level: hier.my_level, pending_inbox: items.length, total: allItems.length,
      })}
      <div class="panel glass"><div class="panel-bd">
        <p class="hint">${hier.note || ""}</p>
        <div class="row" style="gap:8px;flex-wrap:wrap;margin-top:8px">
          <button class="btn btn-accent btn-sm" id="appr-emergency">🚨 Emergency approval</button>
          <button class="btn btn-primary btn-sm" id="appr-normal">Submit for approval</button>
          <button class="btn btn-ghost btn-sm" id="appr-refresh">Refresh</button>
        </div>
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>My inbox (level ≥ required)</h2>
        <span class="pill">You are L${hier.my_level}</span></div>
        <div class="panel-bd">${table(
          ["ID", "Module", "Title", "Amount", "Need", "Type", "By", "Action"],
          items.map((r) => [
            r.id,
            r.module,
            r.title,
            money(r.amount),
            `L${r.required_level}+`,
            r.emergency ? `<span class="pill danger">EMERGENCY</span>` : `<span class="pill warn">normal</span>`,
            r.requested_by_name || "—",
            `<button class="btn btn-ghost btn-sm" data-appr-d="${r.id}">Details</button>
             <button class="btn btn-accent btn-sm" data-appr-ok="${r.id}">Approve</button>
             <button class="btn btn-ghost btn-sm" data-appr-no="${r.id}">Reject</button>`,
          ]),
          "Inbox empty — no pending for your level."
        )}</div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Hierarchy (1→5)</h2></div>
          <div class="panel-bd">${table(
            ["Name", "Email", "Level", "Dept", "Title"],
            (hier.users || []).map((u) => [
              u.full_name,
              u.email,
              `L${u.level}`,
              u.dept || "—",
              u.title || (u.is_superadmin ? "Admin" : "—"),
            ])
          )}
          <div class="row" style="margin-top:10px;gap:8px">
            <button class="btn btn-sm btn-primary" id="set-level">Set user level</button>
          </div>
          </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Module controls</h2></div>
          <div class="panel-bd">${table(
            ["Module", "On", "Threshold", "Min level", "Dept"],
            Object.entries(ctrls).map(([k, v]) => [
              v.label || k,
              v.enabled ? `<span class="pill ok">ON</span>` : `<span class="pill">off</span>`,
              money(v.threshold || 0),
              `L${v.min_level || 2}`,
              v.dept || "—",
            ])
          )}
          <p class="hint" style="margin-top:8px">Toggle via API / Settings — ON modules need approver ≥ min level (or emergency L5).</p>
          </div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Recent requests</h2></div>
        <div class="panel-bd">${table(
          ["ID", "Status", "Module", "Title", "Emergency", "Decided", ""],
          allItems.slice(0, 40).map((r) => [
            r.id,
            `<span class="pill ${r.status.includes("approved") ? "ok" : r.status === "rejected" ? "danger" : "warn"}">${r.status}</span>`,
            r.module,
            r.title,
            r.emergency ? "yes" : "—",
            r.decided_by_name || "—",
            `<button class="btn btn-ghost btn-sm" data-appr-d="${r.id}">Details</button>`,
          ])
        )}</div></div>`;
    const decide = async (id, approve) => {
      try {
        const r = await API.post(`/api/approvals/${id}/decide`, { approve, note: approve ? "Approved" : "Rejected" });
        toast(r.message || "Done");
        flowSave(approve ? "Approved" : "Rejected", r, "Recent requests me status · linked Sales/Purchase entity unlock/block.");
        pageApprovals(el);
      } catch (e) { toast(e.message || "Failed"); }
    };
    el.querySelectorAll("[data-appr-ok]").forEach((b) => b.addEventListener("click", () => decide(b.dataset.apprOk, true)));
    el.querySelectorAll("[data-appr-no]").forEach((b) => b.addEventListener("click", () => decide(b.dataset.apprNo, false)));
    el.querySelectorAll("[data-appr-d]").forEach((btn) => {
      const row = [...items, ...allItems].find((x) => String(x.id) === btn.dataset.apprD);
      btn.addEventListener("click", () => openDetail(row?.title || `Approval #${btn.dataset.apprD}`, row || {}, { eyebrow: "Approval request", showJson: false }));
    });
    $("#appr-refresh")?.addEventListener("click", () => pageApprovals(el));
    $("#appr-emergency")?.addEventListener("click", async () => {
      const title = prompt("Emergency work title", "Urgent customer dispatch");
      if (!title) return;
      const reason = prompt("Why bypass hierarchy?", "Truck waiting — customer SLA") || "Urgent";
      try {
        const r = await API.post("/api/approvals/submit", {
          module: "logistics",
          entity_type: "emergency",
          entity_id: `EMG-${Date.now()}`,
          title,
          amount: 0,
          emergency: true,
          emergency_reason: reason,
        });
        toast(r.message || "Emergency sent to Admin");
        flowSave("Emergency approval", r, "Admin/L5 inbox me · Approve se bypass complete.");
        pageApprovals(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
    $("#appr-normal")?.addEventListener("click", async () => {
      const title = prompt("Approval title", "Dept request");
      if (!title) return;
      const mod = prompt("Module code (sales/purchase/inventory/hrms_expense/...)", "purchase") || "purchase";
      const amt = Number(prompt("Amount ₹", "150000") || 0);
      try {
        const r = await API.post("/api/approvals/submit", {
          module: mod,
          entity_type: "manual",
          entity_id: `MAN-${Date.now()}`,
          title,
          amount: amt,
        });
        toast(r.message || "Submitted");
        flowSave("Submitted for approval", r, "My inbox (approver level) me dikhega · Approve/Reject.");
        pageApprovals(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
    $("#set-level")?.addEventListener("click", async () => {
      const u = (hier.users || [])[0];
      if (!u) return;
      const uid = Number(prompt("User id", String(u.user_id)));
      const level = Number(prompt("Level 1–5 (5=admin)", "3"));
      const dept = prompt("Department", "sales") || "";
      try {
        const r = await API.post("/api/approvals/hierarchy/user", { user_id: uid, level, dept, title: `L${level}` });
        toast(`User ${uid} → L${level}`);
        flowSave(`User → L${level}`, r || { user_id: uid, level }, "Hierarchy table update · inbox visibility change.");
        pageApprovals(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
  }

  async function pageCompliance(el) {
    const [scan, legal, gstr] = await Promise.all([
      API.get("/api/compliance/scan"),
      API.get("/api/legal/board").catch(() => ({ items: [], counts: {}, policy: "" })),
      API.get("/api/books/reports/gstr3b").catch(() => ({})),
    ]);
    const s = scan.summary || {};
    const c = legal.counts || {};
    const levelPill = (lv) => {
      if (lv === "HIGHLIGHT_ILLEGAL_RISK") return `<span class="pill danger">HIGHLIGHT RISK</span>`;
      if (lv === "NEEDS_APPROVAL") return `<span class="pill warn">NEEDS APPROVAL</span>`;
      return `<span class="pill ok">SAFE</span>`;
    };
    el.innerHTML = `
      <div class="panel glass"><div class="panel-hd"><h2>GSTR-3B desk (Kanha)</h2>
        <a class="btn btn-ghost btn-sm" href="#/books">Open Kanha Books</a>
        <span class="pill warn">${gstr.watermark || "desk only"}</span></div>
        <div class="panel-bd">
          <div class="kpi-grid">
            ${kpiCard("Outward tax", "", { icon: "↗", tone: "blue", raw: (gstr.outward || {}).total_tax || 0 })}
            ${kpiCard("ITC", "", { icon: "↙", tone: "teal", raw: (gstr.inward_itc || {}).total_tax || 0 })}
            ${kpiCard("Net payable", "", { icon: "₹", tone: "amber", raw: gstr.net_payable || 0 })}
            ${kpiCard("Period", gstr.period || "—", { icon: "◉", tone: "violet" })}
          </div>
          <p class="hint">Live from sales/purchase docs — prepare numbers here; file on GST portal separately.</p>
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Legal & Risk board</h2>
        <span class="pill">${(c.blocked_gates || 0)} gates blocked</span></div>
        <div class="panel-bd">
          <p class="hint" style="margin:0 0 10px">${legal.policy || "Nothing deleted — conscious approvals only. Not formal legal advice."}</p>
          <div class="kpi-grid">
            ${kpiCard("Safe", String(c.SAFE || 0), { icon: "✓", tone: "teal" })}
            ${kpiCard("Needs approval", String(c.NEEDS_APPROVAL || 0), { icon: "!", tone: "amber" })}
            ${kpiCard("Highlight risk", String(c.HIGHLIGHT_ILLEGAL_RISK || 0), { icon: "⚠", tone: "rose" })}
            ${kpiCard("Gates open", String(c.approved_gates || 0), { icon: "◎", tone: "blue" })}
          </div>
          ${table(
            ["Level", "Feature", "Area", "Status", "Effective", "Action"],
            (legal.items || []).map((it) => [
              levelPill(it.level),
              `<strong>${it.title}</strong><div class="hint" style="margin:4px 0 0">${it.why}</div>`,
              it.area,
              it.status_in_product,
              it.effective === "blocked_until_approval"
                ? `<span class="pill warn">blocked</span>`
                : `<span class="pill ok">${it.effective || "open"}</span>`,
              it.gate
                ? (it.approved
                  ? `<button class="btn btn-ghost btn-sm" data-legal-revoke="${it.id}">Revoke</button>`
                  : `<button class="btn btn-accent btn-sm" data-legal-ok="${it.id}">Approve consciously</button>`)
                : (it.watermark ? `<span class="hint">${it.watermark}</span>` : "—"),
            ]),
            "Legal registry empty"
          )}
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>India Compliance Copilot</h2>
        <button type="button" class="btn btn-primary" id="comp-agent">Run Compliance Agent</button></div>
        <div class="panel-bd">
          <p class="hint" style="margin:0 0 12px">${scan.pillars_note || "GST · e-Invoice · e-Way"} — demo IRN/EWB always DEMO- watermarked (not GSTN filed).</p>
          <div class="kpi-grid">
            ${kpiCard("Avg score", `${s.avg_score ?? "—"}`, { icon: "◎", tone: "blue" })}
            ${kpiCard("Ready", String(s.ready || 0), { icon: "✓", tone: "teal" })}
            ${kpiCard("Warn", String(s.warn || 0), { icon: "!", tone: "amber" })}
            ${kpiCard("Blocked", String(s.blocked || 0), { icon: "✕", tone: "rose" })}
          </div>
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Invoice readiness</h2></div><div class="panel-bd">
        ${table(
          ["Invoice", "Customer", "GSTIN", "Total", "Score", "Status", "Issues"],
          (scan.reports || []).map((r) => [
            r.number,
            r.customer,
            r.gstin,
            money(r.total),
            r.score,
            `<span class="pill ${r.status === "ready" ? "ok" : ""}">${r.status}</span>`,
            (r.issues || []).map((i) => i.code).join(", ") || "—",
          ])
        )}
      </div></div>
      <div id="comp-out" class="auto-out"></div>`;
    el.querySelectorAll("[data-legal-ok]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-legal-ok");
        const note = prompt(
          `Conscious approval for ${id}.\nType reason (labour/GST/privacy decision). This does NOT delete anything — unlocks gated work when you choose.`,
          "Reviewed — enable for our company with SOP"
        );
        if (note == null) return;
        try {
          await API.post("/api/legal/approve", { feature_id: id, approved: true, note });
          toast("Approved — feature unlocked for this company");
          pageCompliance(el);
        } catch (e) { toast(e.message || "Approve failed"); }
      });
    });
    el.querySelectorAll("[data-legal-revoke]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-legal-revoke");
        if (!confirm(`Revoke approval for ${id}? Feature stays in product but blocked again.`)) return;
        try {
          await API.post("/api/legal/approve", { feature_id: id, approved: false, note: "Revoked" });
          toast("Revoked");
          pageCompliance(el);
        } catch (e) { toast(e.message || "Failed"); }
      });
    });
    $("#comp-agent")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/agents/compliance/run");
        $("#comp-out").innerHTML = `<pre class="report-pre">${JSON.stringify(r, null, 2)}</pre>`;
        toast(r.message);
        setTimeout(() => pageCompliance(el), 700);
      } catch (e) {
        toast(e.message || "Failed");
      }
    });
  }

  async function pageBridges(el) {
    let hub = { channels: [], outbox: [], summary: {}, pitch: "", hooks: { presets: [], items: [], inbox: [], log: [] }, intelligence: {} };
    try {
      hub = await API.get("/api/bridges");
    } catch (e) {
      try { hub = await API.post("/api/bridges/seed-defaults", {}); } catch (_) {}
    }
    const channels = hub.channels || [];
    const outbox = hub.outbox || [];
    const sum = hub.summary || {};
    const hooks = hub.hooks || {};
    const hookItems = hooks.items || [];
    const presets = hooks.presets || [];
    const modePill = (m) => {
      if (m === "bridge") return `<span class="pill ok">BRIDGE</span>`;
      if (m === "hybrid") return `<span class="pill warn">HYBRID</span>`;
      return `<span class="pill">NATIVE</span>`;
    };
    el.innerHTML = `
      ${moduleIntro("Connected Apps / Bridges", hub.pitch || "Native / Bridge / Hybrid · Tally (kept) + Marg / Busy / Other ERP data packs + hooks.", {
        native: sum.native || 0, hybrid: sum.hybrid || 0, bridge: sum.bridge || 0,
        hooks: sum.hooks_active || hookItems.filter((h) => h.status === "active").length,
        queued: sum.queued || 0,
      }, `<a class="btn btn-ghost btn-sm" href="#/books">Kanha Books</a>
          <a class="btn btn-ghost btn-sm" href="#/mis">MIS</a>
          <button type="button" class="btn btn-accent btn-sm" id="br-tally-export">Tally export</button>
          <button type="button" class="btn btn-primary btn-sm" id="bi-learn-full">Learn Full (9 phases)</button>
          <button type="button" class="btn btn-accent btn-sm" id="bi-learn">Learn cycle</button>
          <button type="button" class="btn btn-ghost btn-sm" id="bi-improve">Safe improve</button>`)}

      <div class="panel glass"><div class="panel-hd"><h2>ERP data bridges</h2>
        <span class="pill ok">Tally · Marg · Busy · Vyapar · Other</span></div>
        <div class="panel-bd">
          <p class="hint" style="margin-top:0">Jo pehle se hai (Tally export/import) woh <b>rahega</b>. Saath me Marg / Busy / Vyapar / Other ke liye alag data pack options — fresh Kanha data only, no client DB import.</p>
          <div class="grid-2" style="gap:10px">
            ${(hub.erp_targets || [
              { id: "tally", label: "Tally", hint: "Existing Tally path" },
              { id: "marg", label: "Marg ERP", hint: "Marg data pack" },
              { id: "busy", label: "Busy Accounting", hint: "Busy pack" },
              { id: "vyapar", label: "Vyapar / billing", hint: "Billing pack" },
              { id: "other", label: "Other ERP / CSV", hint: "Generic pack" },
            ]).map((t) => `
              <div class="readiness-item readiness-item--ready" style="flex-direction:column;align-items:stretch;margin:0">
                <strong>${t.label}</strong>
                <span class="hint">${t.hint || t.format || ""}</span>
                <div class="row" style="gap:6px;margin-top:8px;flex-wrap:wrap">
                  <button type="button" class="btn btn-primary btn-sm" data-erp-export="${t.id}">Export pack</button>
                  <button type="button" class="btn btn-ghost btn-sm" data-erp-hook="${t.id}">+ Hook</button>
                </div>
              </div>`).join("")}
          </div>
          <div style="margin-top:14px">
            <label class="hint">Import buffer · target</label>
            <div class="row" style="gap:8px;flex-wrap:wrap;margin-top:6px;align-items:center">
              <select id="br-erp-target">${(hub.erp_targets || [{ id: "marg", label: "Marg" }, { id: "tally", label: "Tally" }, { id: "other", label: "Other" }]).map((t) => `<option value="${t.id}">${t.label}</option>`).join("")}</select>
            </div>
            <textarea id="br-erp-import" rows="3" style="margin-top:8px;width:100%" placeholder='[{"date":"2026-08-01","amount":15000,"party":"…"}]'></textarea>
            <button type="button" class="btn btn-accent btn-sm" id="br-erp-imp" style="margin-top:8px">Import to selected bridge</button>
          </div>
        </div>
      </div>

      <div class="panel glass"><div class="panel-hd"><h2>Bridge Intelligence · internal learning curriculum</h2>
        <span class="pill ok">${hub.intelligence?.curriculum_pct ?? 0}% · ${hub.intelligence?.phases_complete || 0}/${hub.intelligence?.phases_total || 9} phases</span></div>
        <div class="panel-bd">
          <p class="hint" style="margin-top:0">Poori pipeline: ingest → normalize → compare → score → taxonomy → safe fix → rules → advance → retain. Money conflict kabhi auto-overwrite nahi.</p>
          <div class="kpi-grid" style="margin-bottom:10px">
            <div class="hint"><b>Trust</b> · ${hub.intelligence?.trust_score ?? sum.trust_score ?? "—"}</div>
            <div class="hint"><b>Last accuracy</b> · ${hub.intelligence?.last_accuracy ?? "—"}%</div>
            <div class="hint"><b>Learn runs</b> · ${hub.intelligence?.runs ?? 0}</div>
            <div class="hint"><b>Safe fixes</b> · ${hub.intelligence?.improvements_applied ?? 0}</div>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px">
            ${(hub.intelligence?.phases || []).map((p) => `
              <span class="pill ${p.done ? "ok" : "warn"}" title="${p.desc || ""}">${p.done ? "✓" : "○"} ${p.name || p.id}</span>
            `).join("") || `<span class="hint">Run Learn Full to start curriculum</span>`}
          </div>
          ${hub.intelligence?.advance?.recommendation ? `<p class="hint"><b>Advance</b> · ${hub.intelligence.advance.recommendation}</p>` : ""}
          ${table(["Severity", "Gap", "Fixable", "Status"], (hub.intelligence?.open_gaps || []).slice(0, 12).map((g) => [
            g.severity, g.title, g.fixable ? "yes" : "no", g.status || "open",
          ]))}
          ${(hub.intelligence?.playbook || []).length ? `
            <h3 style="font-size:13px;margin:12px 0 6px">Internal playbook (learned rules)</h3>
            ${table(["Kind", "Evidence", "Advice"], (hub.intelligence.playbook || []).slice(0, 8).map((r) => [
              r.kind, r.evidence, r.advice,
            ]))}
          ` : ""}
          <p class="hint">${hub.intelligence?.pitch || ""}</p>
        </div>
      </div>

      <div class="panel glass"><div class="panel-hd"><h2>Third-party app hooks</h2>
        <span class="pill ok">Marg · Busy · Vyapar · Custom</span></div>
        <div class="panel-bd">
          <p class="hint" style="margin-top:0">Pehle se koi app chal raha ho — <b>ek hi hook model</b>. Preset = label/events; transport = webhook in/out. Cap 40 hooks.</p>
          <div class="grid-2" style="margin-bottom:12px">
            <div class="field"><label>Preset</label>
              <select id="hk-preset">${presets.map((p) => `<option value="${p.id}">${p.label}</option>`).join("") || `<option value="custom">Custom</option>`}</select></div>
            <div class="field"><label>Name</label><input id="hk-name" placeholder="Plant Marg link" /></div>
            <div class="field"><label>Direction</label>
              <select id="hk-dir"><option value="both">both</option><option value="out">out</option><option value="in">in</option></select></div>
            <div class="field"><label>Outbound webhook URL</label><input id="hk-url" placeholder="https://their-app/webhook" /></div>
          </div>
          <button type="button" class="btn btn-primary btn-sm" id="hk-create">Create hook</button>
          <div style="margin-top:14px">${hookItems.map((h) => `
            <div class="readiness-item readiness-item--${h.status === "active" ? "ready" : "planned"}" style="margin-bottom:8px;flex-direction:column;align-items:stretch">
              <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap">
                <div>
                  <strong>${h.name}</strong> · ${h.label || h.preset}
                  <span class="pill ${h.status === "active" ? "ok" : "warn"}">${h.status}</span>
                  <span class="hint" style="display:block">${h.direction} · pushed ${h.stats?.pushed || 0} · recv ${h.stats?.received || 0}</span>
                  <span class="hint" style="display:block">IN <code>${h.inbound_path || ""}</code> · fp <code>${h.token_fingerprint || ""}</code></span>
                  ${h.outbound_url ? `<span class="hint">OUT ${h.outbound_url}</span>` : `<span class="hint">OUT local queue</span>`}
                </div>
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                  <button type="button" class="btn btn-accent btn-sm" data-hk-test="${h.id}">Test push</button>
                  <button type="button" class="btn btn-ghost btn-sm" data-hk-pause="${h.id}">${h.status === "active" ? "Pause" : "Activate"}</button>
                  <button type="button" class="btn btn-ghost btn-sm" data-hk-del="${h.id}">Delete</button>
                </div>
              </div>
            </div>`).join("") || `<p class="hint">No hooks yet — create Marg/Busy/Custom.</p>`}
          </div>
          <div class="grid-2" style="margin-top:12px">
            <div><h3 style="font-size:13px;margin:0 0 6px">Inbound inbox</h3>
              ${table(["When", "Preset", "Event", "Status"], (hooks.inbox || []).slice(0, 8).map((x) => [(x.received_at || "").slice(0, 19), x.preset || "—", x.event, x.status]))}
            </div>
            <div><h3 style="font-size:13px;margin:0 0 6px">Hook activity</h3>
              ${table(["When", "Dir", "Event", "Status"], (hooks.log || []).slice(0, 8).map((x) => [(x.at || "").slice(0, 19), x.dir, x.event, x.status]))}
            </div>
          </div>
        </div>
      </div>

      <div class="panel glass"><div class="panel-hd"><h2>Tally sync desk (SBAC)</h2>
        <span class="pill ok">Parent · Inactive · Errors</span>
        <button type="button" class="btn btn-ghost btn-sm" id="ty-refresh">Refresh</button></div>
        <div class="panel-bd">
          <p class="hint" style="margin-top:0">Live parity: TallyErpparentmapping · InactiveLedger/Item · Tallyerror — fresh Kanha flags only</p>
          <div class="grid-2" style="gap:12px">
            <div>
              <h3 style="font-size:13px;margin:0 0 8px">Parent mapping</h3>
              <div class="field"><label>ERP Parent (ddlerp)</label>
                <select id="ty-parent">${(hub.tally_sync?.erp_parents || ["Sundry Debtors","Sundry Creditors","Sales Accounts","Purchase Accounts","Cash-in-hand","Bank Accounts"]).map((p) => `<option>${p}</option>`).join("")}</select></div>
              <div class="field"><label>Tally Name (txttally)</label><input id="ty-tally-name" placeholder="Tally ledger / group name" /></div>
              <button type="button" class="btn btn-primary btn-sm" id="ty-map-save">Submit mapping</button>
              <div style="margin-top:10px">${table(
                ["ERP Parent", "Tally Name", "When"],
                (hub.tally_sync?.parent_mappings || []).slice(-12).map((r) => [
                  r.erp_parent, r.tally_name, (r.updated_at || r.created_at || "").slice(0, 19) || "—",
                ])
              )}</div>
            </div>
            <div>
              <h3 style="font-size:13px;margin:0 0 8px">Inactive for Tally</h3>
              <div class="field"><label>Ledger / Party (txtpartyname)</label><input id="ty-led-name" placeholder="Search / name" /></div>
              <div class="field"><label>Code (optional)</label><input id="ty-led-code" placeholder="COA code" /></div>
              <button type="button" class="btn btn-accent btn-sm" id="ty-led-off">Mark ledger inactive</button>
              <div class="field" style="margin-top:10px"><label>Item (txtitem)</label><input id="ty-item-name" placeholder="Item name" /></div>
              <div class="field"><label>SKU (optional)</label><input id="ty-item-sku" placeholder="SKU" /></div>
              <button type="button" class="btn btn-accent btn-sm" id="ty-item-off">Mark item inactive</button>
              <div style="margin-top:10px" class="grid-2">
                <div>${table(["Ledger", "Code"], (hub.tally_sync?.inactive_ledgers || []).slice(-8).map((r) => [r.name, r.code || "—"]))}</div>
                <div>${table(["Item", "SKU"], (hub.tally_sync?.inactive_items || []).slice(-8).map((r) => [r.name, r.sku || "—"]))}</div>
              </div>
            </div>
          </div>
          <h3 style="font-size:13px;margin:16px 0 8px">Tally Error queue</h3>
          <div class="row" style="gap:8px;flex-wrap:wrap;margin-bottom:8px;align-items:end">
            <div class="field"><label>From</label><input id="ty-err-from" type="date" /></div>
            <div class="field"><label>To</label><input id="ty-err-to" type="date" /></div>
            <div class="field"><label>Doc type</label>
              <select id="ty-err-doc">
                <option value="">All</option>
                <option>Contra</option><option>Journal</option><option>Payment</option>
                <option>Purchase</option><option>Receipt</option><option>Sale</option>
              </select></div>
            <button type="button" class="btn btn-primary btn-sm" id="ty-err-search">Search</button>
            <button type="button" class="btn btn-ghost btn-sm" id="ty-err-log">Log error</button>
          </div>
          <div id="ty-err-box">${table(
            ["When", "Doc", "Ref", "Message", "Status"],
            (hub.tally_sync?.errors || []).slice(0, 15).map((e) => [
              (e.at || "").slice(0, 19), e.doc_type || "—", e.ref || "—", e.message || "—", e.status || "—",
            ])
          )}</div>
          <p class="hint">Counts · maps ${hub.tally_sync?.counts?.mappings || 0} · inactive ledgers ${hub.tally_sync?.counts?.inactive_ledgers || 0} · items ${hub.tally_sync?.counts?.inactive_items || 0} · errors ${hub.tally_sync?.counts?.errors || 0}</p>
        </div>
      </div>

      <div class="panel glass"><div class="panel-hd"><h2>Dual-mode channels</h2></div>
        <div class="panel-bd">
          ${channels.map((c) => `
            <div class="readiness-item readiness-item--${c.mode === "native" ? "planned" : "ready"}" style="margin-bottom:10px;flex-direction:column;align-items:stretch">
              <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">
                <div><strong>${c.title}</strong> ${modePill(c.mode)}
                  <span class="hint" style="display:block">${c.why}</span></div>
                <div class="hint">${(c.connectivity && c.connectivity.status_label) || ""}</div>
              </div>
              <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;align-items:center">
                <label class="hint">${c.native?.label || ""} ↔ ${c.bridge?.label || ""}</label>
                <select data-br-mode="${c.id}" style="margin-left:auto;min-width:140px">
                  ${(c.modes || ["native", "bridge", "hybrid"]).map((m) => `<option value="${m}" ${c.mode === m ? "selected" : ""}>${m}</option>`).join("")}
                </select>
                <button type="button" class="btn btn-primary btn-sm" data-br-save="${c.id}">Save</button>
              </div>
            </div>`).join("") || "<p class='hint'>No channels</p>"}
        </div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Bridge outbox</h2>
        <button type="button" class="btn btn-ghost btn-sm" id="br-refresh">Refresh</button></div>
        <div class="panel-bd">${table(["When", "Channel", "Action", "Title", "Status", ""], outbox.map((j) => [
          (j.created_at || "").slice(0, 19), j.channel, j.action, j.title || "—",
          `<span class="pill ${j.status === "synced" || j.status === "exported" || j.status === "imported" ? "ok" : "warn"}">${j.status}</span>`,
          j.status === "queued" ? `<button class="btn btn-ghost btn-sm" data-br-run="${j.id}">Run sync</button>` : "—",
        ]))}</div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Tally import buffer</h2></div>
        <div class="panel-bd">
          <textarea id="br-tally-import" rows="3" placeholder='[{"date":"2026-07-28","amount":15000}]'></textarea>
          <button type="button" class="btn btn-accent btn-sm" id="br-tally-imp" style="margin-top:8px">Import to bridge</button>
        </div>
      </div>`;
    $("#bi-learn-full")?.addEventListener("click", async () => {
      if (!confirm("Full curriculum (9 phases) including safe improve of EMPTY masters only. Money conflicts never auto-fixed. Continue?")) return;
      try {
        const r = await API.post("/api/bridges/intelligence/learn-full", {});
        toast(r.message || "Full learn done");
        showSavedDetail("Learn Full · all phases", r);
        pageBridges(el);
      } catch (e) { toast(e.message || "Learn Full failed"); }
    });
    $("#bi-learn")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/bridges/intelligence/learn", {});
        toast(r.message || "Learn done");
        showSavedDetail("Bridge Intelligence learn", r);
        pageBridges(el);
      } catch (e) { toast(e.message || "Learn failed"); }
    });
    $("#bi-improve")?.addEventListener("click", async () => {
      if (!confirm("Safe improve only fills EMPTY GSTIN/barcode/missing party. Money conflicts stay for human. Continue?")) return;
      try {
        const r = await API.post("/api/bridges/intelligence/improve", {});
        toast(r.message || "Improved");
        showSavedDetail("Safe improvements", r);
        pageBridges(el);
      } catch (e) { toast(e.message || "Improve failed"); }
    });
    $("#hk-create")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/bridges/hooks", {
          preset: $("#hk-preset")?.value || "custom",
          name: $("#hk-name")?.value || "",
          direction: $("#hk-dir")?.value || "both",
          outbound_url: $("#hk-url")?.value || "",
        });
        toast(r.message || "Hook created");
        if (r.hook?.inbound_token) {
          showSavedDetail("Hook credentials (save token)", {
            inbound_path: `/api/bridges/hooks/inbound/${r.hook.id}`,
            inbound_token: r.hook.inbound_token,
            outbound_url: r.hook.outbound_url || "(local queue)",
          });
        }
        pageBridges(el);
      } catch (e) { toast(e.message || "Create failed"); }
    });
    el.querySelectorAll("[data-hk-test]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const r = await API.post("/api/bridges/hooks/push", {
            hook_id: btn.dataset.hkTest, event: "generic",
            payload: { test: true, at: new Date().toISOString() },
          });
          toast(`Push · ${(r.results || []).length} hook(s)`);
          showSavedDetail("Hook push result", r);
          pageBridges(el);
        } catch (e) { toast(e.message || "Push failed"); }
      });
    });
    el.querySelectorAll("[data-hk-pause]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const row = hookItems.find((h) => h.id === btn.dataset.hkPause);
        const next = row?.status === "active" ? "paused" : "active";
        try {
          await API.post(`/api/bridges/hooks/${btn.dataset.hkPause}`, { status: next });
          toast(`Hook ${next}`);
          pageBridges(el);
        } catch (e) { toast(e.message || "Update failed"); }
      });
    });
    el.querySelectorAll("[data-hk-del]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this third-party hook?")) return;
        try {
          await API.post(`/api/bridges/hooks/${btn.dataset.hkDel}/delete`, {});
          toast("Hook removed");
          pageBridges(el);
        } catch (e) { toast(e.message || "Delete failed"); }
      });
    });
    el.querySelectorAll("[data-br-save]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.brSave;
        const mode = el.querySelector(`[data-br-mode="${id}"]`)?.value || "native";
        try {
          const r = await API.post(`/api/bridges/${id}/mode`, { mode });
          toast(r.message || `${id} → ${mode}`);
          pageBridges(el);
        } catch (e) { toast(e.message || "Save failed"); }
      });
    });
    el.querySelectorAll("[data-br-run]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const r = await API.post(`/api/bridges/outbox/${btn.dataset.brRun}/run`, {});
          toast(r.message || "Synced");
          pageBridges(el);
        } catch (e) { toast(e.message || "Run failed"); }
      });
    });
    $("#ty-refresh")?.addEventListener("click", () => pageBridges(el));
    $("#ty-map-save")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/bridges/tally/parent-mapping", {
          erp_parent: $("#ty-parent")?.value || "",
          tally_name: $("#ty-tally-name")?.value || "",
        });
        toast(r.message || "Mapped");
        pageBridges(el);
      } catch (e) { toast(e.message || "Map failed"); }
    });
    $("#ty-led-off")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/bridges/tally/inactive-ledgers", {
          name: $("#ty-led-name")?.value || "",
          code: $("#ty-led-code")?.value || "",
          inactive: true,
        });
        toast(r.message || "Ledger inactive");
        pageBridges(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
    $("#ty-item-off")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/bridges/tally/inactive-items", {
          name: $("#ty-item-name")?.value || "",
          sku: $("#ty-item-sku")?.value || "",
          inactive: true,
        });
        toast(r.message || "Item inactive");
        pageBridges(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
    $("#ty-err-search")?.addEventListener("click", async () => {
      try {
        const q = new URLSearchParams({
          from_date: $("#ty-err-from")?.value || "",
          to_date: $("#ty-err-to")?.value || "",
          doc_type: $("#ty-err-doc")?.value || "",
        });
        const r = await API.get(`/api/bridges/tally/errors?${q}`);
        const box = $("#ty-err-box");
        if (box) {
          box.innerHTML = table(
            ["When", "Doc", "Ref", "Message", "Status"],
            (r.errors || []).map((e) => [
              (e.at || "").slice(0, 19), e.doc_type || "—", e.ref || "—", e.message || "—", e.status || "—",
            ])
          );
        }
        toast(`${r.count || 0} errors`);
      } catch (e) { toast(e.message || "Search failed"); }
    });
    $("#ty-err-log")?.addEventListener("click", async () => {
      const msg = prompt("Error message / note");
      if (!msg) return;
      try {
        const r = await API.post("/api/bridges/tally/errors", {
          doc_type: $("#ty-err-doc")?.value || "Sale",
          message: msg,
          from_date: $("#ty-err-from")?.value || "",
          to_date: $("#ty-err-to")?.value || "",
        });
        toast(r.message || "Logged");
        pageBridges(el);
      } catch (e) { toast(e.message || "Log failed"); }
    });
    $("#br-refresh")?.addEventListener("click", () => pageBridges(el));
    $("#br-tally-export")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/bridges/tally/export", {});
        toast(r.message || "Tally pack ready");
        showSavedDetail("Tally export pack", r.pack || r);
        pageBridges(el);
      } catch (e) { toast(e.message || "Export failed"); }
    });
    el.querySelectorAll("[data-erp-export]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const target = btn.dataset.erpExport;
        try {
          const path = target === "tally" ? "/api/bridges/tally/export" : `/api/bridges/erp/${target}/export`;
          const r = await API.post(path, {});
          toast(r.message || `${target} pack ready`);
          showSavedDetail(`${(r.pack && r.pack.target_label) || target} export pack`, r.pack || r);
          pageBridges(el);
        } catch (e) { toast(e.message || "Export failed"); }
      });
    });
    el.querySelectorAll("[data-erp-hook]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const target = btn.dataset.erpHook;
        const preset = target === "other" ? "custom" : (["marg", "busy", "vyapar", "tally"].includes(target) ? target : "custom");
        try {
          const r = await API.post("/api/bridges/hooks", {
            preset,
            name: `${target} data link`,
            direction: "both",
          });
          toast(r.message || "Hook created");
          if (r.hook?.inbound_token) {
            showSavedDetail("Hook credentials (save token)", {
              inbound_path: `/api/bridges/hooks/inbound/${r.hook.id}`,
              inbound_token: r.hook.inbound_token,
            });
          }
          pageBridges(el);
        } catch (e) { toast(e.message || "Hook failed"); }
      });
    });
    $("#br-erp-imp")?.addEventListener("click", async () => {
      const target = $("#br-erp-target")?.value || "marg";
      const raw = $("#br-erp-import")?.value || "[]";
      let rows = [];
      try { rows = JSON.parse(raw); } catch { return toast("Invalid JSON array"); }
      if (!Array.isArray(rows)) return toast("Need JSON array");
      try {
        const path = target === "tally" ? "/api/bridges/tally/import" : `/api/bridges/erp/${target}/import`;
        const r = await API.post(path, { rows, source: `${target}_csv` });
        toast(r.message || "Imported");
        pageBridges(el);
      } catch (e) { toast(e.message || "Import failed"); }
    });
    $("#br-tally-imp")?.addEventListener("click", async () => {
      const raw = $("#br-tally-import")?.value || "[]";
      let rows = [];
      try { rows = JSON.parse(raw); } catch { return toast("Invalid JSON array"); }
      if (!Array.isArray(rows)) return toast("Need JSON array");
      try {
        const r = await API.post("/api/bridges/tally/import", { rows, source: "tally_csv" });
        toast(r.message || "Imported");
        pageBridges(el);
      } catch (e) { toast(e.message || "Import failed"); }
    });
  }

  async function pageApps(el) {
    const a = BRAND.apps.android;
    const i = BRAND.apps.ios;
    const [tracking, expenses, health] = await Promise.all([
      API.get("/api/hrms/tracking/live").catch(() => ({ staff: [] })),
      API.get("/api/hrms/expenses").catch(() => []),
      API.get("/api/health").catch(() => ({})),
    ]);
    const integ = health.integrations || {};
    const mode = (on, label) => on
      ? `<span class="pill ok">LIVE · ${label}</span>`
      : `<span class="pill">DEMO · working</span>`;
    el.innerHTML = `
      ${moduleIntro("Mobile Apps", "Native store slots + PWA. External tools (Tally, Razorpay, GSP, Meta…) → Connected Apps bridges.", {
        field_staff: (tracking.staff || tracking.live || []).length || 0,
        expense_claims: (expenses || []).length,
        demo_mode: health.demo_mode !== false,
      }, `<a class="btn btn-accent btn-sm" href="#/bridges">Open Bridges</a>`)}
      <div class="panel glass">
        <div class="panel-hd"><h2>Connectivity matrix (demo ↔ live)</h2></div>
        <div class="panel-bd">${table(
          ["Channel", "Status", "What works now", "Go-live key"],
          [
            ["WhatsApp", mode(integ.whatsapp, "Meta"), "Send / templates / automation outbox", "WHATSAPP_TOKEN + PHONE_ID"],
            ["AI / LLM", mode(integ.llm, "OpenAI"), "Demo AI brain on ERP data", "LLM_API_KEY"],
            ["Payments", mode(integ.razorpay, "Razorpay"), "Intent → capture → invoice settle (demo-live)", "RAZORPAY_KEY_ID/SECRET"],
            ["e-Invoice GSP", mode(integ.gsp, "GSP"), "Local IRN + demo push path", "GSP credentials"],
            ["Maps / GPS", `<span class="pill ok">PHONE GPS</span>`, "Device lat/lng realtime ping", "Legal gate: gps_always_on + consent"],
            ["Email / SMTP", mode(integ.smtp, "SMTP"), "Overdue email outbox (demo or live)", "SMTP_*"],
            ["Mobile PWA", `<span class="pill ok">WORKING</span>`, "Service worker + Add to Home Screen", "Store URLs optional"],
          ]
        )}</div>
      </div>
      <div class="panel glass">
        <div class="panel-hd"><h2>KanhaERP on phone (working now)</h2>
          <button type="button" class="btn btn-accent btn-sm" id="apps-install">Install PWA</button></div>
        <div class="panel-bd">
          <p class="hint">Phone browser me same URL → login → HRMS / Expenses / Live Monitor / WhatsApp / AI. Chrome → <b>Add to Home Screen</b> = app icon.</p>
          <div class="auto-actions" style="margin-top:10px">
            <a class="btn btn-primary" href="#/hrms">Open HRMS + GPS</a>
            <a class="btn btn-accent" href="#/watch">Live Monitor</a>
            <a class="btn btn-ghost" href="#/whatsapp">WhatsApp OS</a>
            <a class="btn btn-ghost" href="#/ai">AI Assistant</a>
            <button type="button" class="btn btn-ghost" id="apps-ping">Simulate field ping</button>
          </div>
          <div class="dl-row dl-row--page" style="margin-top:16px">
            ${storeBadge("android")}
            ${storeBadge("ios")}
          </div>
          <div class="dl-store-links">
            <div><span>Play Store slot</span><code>${a.url}</code></div>
            <div><span>App Store slot</span><code>${i.url}</code></div>
          </div>
          ${stubNote("Play/App Store = publish slot. Abhi phone browser + PWA (service worker) full ERP — Install / Add to Home Screen.")}
        </div>
      </div>
      <div class="panel glass">
        <div class="panel-hd"><h2>Mobile-ready features (API live)</h2></div>
        <div class="panel-bd">${table(
          ["Feature", "Status", "Open"],
          [
            ["Live field GPS tracking", "Working", `<a href="#/hrms">HRMS</a>`],
            ["Expense claim + approve", `${(expenses || []).length} claims`, `<a href="#/hrms">HRMS</a>`],
            ["Live site cameras + chat", "Working", `<a href="#/watch">Watch</a>`],
            ["WhatsApp inbox / chase", "Working", `<a href="#/whatsapp">WhatsApp</a>`],
            ["AI assistant (demo/LLM)", "Working", `<a href="#/ai">AI</a>`],
            ["Full ERP modules", "Same login", `<a href="#/dashboard">Dashboard</a>`],
          ]
        )}</div>
      </div>`;
    $("#apps-ping")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/hrms/tracking/simulate");
        toast(r.message || "Field ping simulated");
        showSavedDetail("Field GPS ping saved", r);
      } catch (e) {
        toast(e.message || "Simulate failed — open HRMS → Simulate");
      }
    });
    $("#apps-install")?.addEventListener("click", async () => {
      if (window.__kanhaPwaPrompt) {
        window.__kanhaPwaPrompt.prompt();
        const choice = await window.__kanhaPwaPrompt.userChoice;
        toast(choice?.outcome === "accepted" ? "PWA installing…" : "Install dismissed");
        return;
      }
      toast("Browser me menu → Add to Home Screen (PWA). Chrome/Edge pe available.");
    });
  }

  async function pageActivity(el) {
    let data = { items: [], logins_24h: [], pulse_24h: {} };
    let users = [];
    const filterUser = state.activityUserId || "";
    const filterAction = state.activityAction || "";
    try {
      const qs = new URLSearchParams({ limit: "200" });
      if (filterUser) qs.set("user_id", filterUser);
      if (filterAction) qs.set("action", filterAction);
      [data, users] = await Promise.all([
        API.get(`/api/activity?${qs}`),
        API.get("/api/users").catch(() => []),
      ]);
    } catch (e) {
      el.innerHTML = `<div class="panel glass"><div class="panel-bd error">${e.message || "Need Admin / Approvals permission for activity tracking"}</div></div>`;
      return;
    }
    const pulse = data.pulse_24h || {};
    el.innerHTML = `
      ${moduleIntro("Activity / Tracking", "Kaun kab login hua, kaun sa screen khola, kya save/pay kiya — issue pe turant samajh aaye.", {
        logins_24h: pulse.logins || 0,
        failed: pulse.login_failed || 0,
        screens: pulse.page_views || 0,
        active: pulse.active_users || 0,
      })}
      <div class="kpi-grid">
        ${kpiCard("Logins (24h)", "", { icon: "↗", tone: "emerald", raw: pulse.logins || 0 })}
        ${kpiCard("Failed logins", "", { icon: "!", tone: "amber", raw: pulse.login_failed || 0 })}
        ${kpiCard("Screens opened", "", { icon: "▣", tone: "blue", raw: pulse.page_views || 0 })}
        ${kpiCard("Active users", "", { icon: "◉", tone: "violet", raw: pulse.active_users || 0 })}
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Who logged in (last 24h)</h2>
        <button type="button" class="btn btn-ghost btn-sm" id="act-refresh">Refresh</button></div>
        <div class="panel-bd">${table(
          ["User", "Email", "Logins", "Last login"],
          (data.logins_24h || []).map((u) => [
            u.user_name, u.user_email, u.logins, (u.last_login || "—").replace("T", " ").slice(0, 19),
          ]),
          "No logins in last 24h yet — login once to start the trail."
        )}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Live activity feed</h2>
        <div class="row" style="gap:8px;flex-wrap:wrap">
          <select id="act-user"><option value="">All users</option>${(users || []).map((u) => `<option value="${u.id}" ${String(filterUser) === String(u.id) ? "selected" : ""}>${u.full_name || u.email}</option>`).join("")}</select>
          <select id="act-action">
            <option value="">All actions</option>
            ${["login", "login_failed", "logout", "page", "create", "update", "pos_checkout", "books_voucher", "vendor_payment", "whatsapp_send"].map((a) => `<option value="${a}" ${filterAction === a ? "selected" : ""}>${a}</option>`).join("")}
          </select>
          <button type="button" class="btn btn-primary btn-sm" id="act-filter">Filter</button>
        </div></div>
        <div class="panel-bd">${table(
          ["When", "Who", "What happened", "IP"],
          (data.items || []).map((a) => [
            (a.when || "—").replace("T", " ").slice(0, 19),
            `${a.user_name || "—"}${a.user_email ? `<div class="hint">${a.user_email}</div>` : ""}`,
            `<strong>${a.summary || a.action}</strong><div class="hint">${a.action}${a.entity ? " · " + a.entity : ""}${a.entity_id ? " · " + a.entity_id : ""}</div>`,
            a.ip || "—",
          ]),
          "No activity rows yet."
        )}
        <p class="hint" style="margin-top:10px">${data.note || ""} · Also in Settings → Audit Trail</p>
      </div></div>`;
    $("#act-refresh")?.addEventListener("click", () => pageActivity(el));
    $("#act-filter")?.addEventListener("click", () => {
      state.activityUserId = $("#act-user")?.value || "";
      state.activityAction = $("#act-action")?.value || "";
      pageActivity(el);
    });
  }

  async function pageWatch(el) {
    let hub = { sites: [], stores_video: false };
    let policy = {};
    let chat = { messages: [] };
    try {
      policy = await API.get("/api/watch/policy");
      hub = await API.get("/api/watch/sites");
    } catch (e) {
      el.innerHTML = `<div class="panel glass"><div class="panel-bd"><p>${e.message || "Watch unavailable"}</p>
        <button type="button" class="btn btn-primary" id="watch-seed">Seed demo sites</button></div></div>`;
      $("#watch-seed")?.addEventListener("click", async () => {
        try { await API.post("/api/watch/seed-demo"); toast("Demo sites ready"); pageWatch(el); }
        catch (err) { toast(err.message || "Failed"); }
      });
      return;
    }
    if (!(hub.sites || []).length) {
      try { await API.post("/api/watch/seed-demo"); hub = await API.get("/api/watch/sites"); } catch (_) {}
    }
    const sites = hub.sites || [];
    const siteId = state.watchSiteId || (sites[0] && sites[0].id);
    state.watchSiteId = siteId;
    const site = sites.find((s) => s.id === siteId) || sites[0];
    try {
      chat = await API.get(`/api/watch/chat?site_id=${siteId || ""}`);
    } catch (_) {}
    const cams = (site && site.cameras) || [];
    el.innerHTML = `
      ${moduleIntro("Live Monitor", "Har office / plant / warehouse site ke cameras live open — chat bhi. Video ERP me save nahi; DVR/NVR aapka. Data size ERP pe nahi aata.", {
        sites: sites.length, cameras: sites.reduce((n, s) => n + ((s.cameras || []).length), 0), chats: (chat.messages || []).length,
      })}
      <div class="panel glass"><div class="panel-hd"><h2>Live Monitor — multi-site watch</h2>
        <div class="row" style="gap:8px">
          <button type="button" class="btn btn-ghost btn-sm" id="watch-seed">Demo sites</button>
          <button type="button" class="btn btn-primary btn-sm" id="watch-add-site">+ Site</button>
          <button type="button" class="btn btn-accent btn-sm" id="watch-add-cam">+ Camera URL</button>
        </div></div>
        <div class="panel-bd">
          <p class="hint"><b>Video ERP me store nahi hota.</b> ${policy.policy || "Sirf live stream open — recording aapke DVR/NVR pe."}</p>
          <div class="row" style="gap:8px;flex-wrap:wrap;margin:10px 0">
            ${sites.map((s) => `<button type="button" class="btn btn-sm ${s.id === siteId ? "btn-primary" : "btn-ghost"} watch-site" data-id="${s.id}">${s.name}${s.city ? " · " + s.city : ""} (${(s.cameras||[]).length})</button>`).join("")}
          </div>
        </div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>${site ? site.name : "No site"} — cameras</h2></div>
          <div class="panel-bd">
            ${cams.length ? cams.map((c) => `
              <div class="watch-cam" style="margin-bottom:14px">
                <div class="hint"><b>${c.name}</b> · ${c.location_label || c.kind} · ${c.vendor}</div>
                ${c.embed_url ? `
                  <video controls playsinline muted style="width:100%;max-height:240px;background:#0b1220;border-radius:8px"
                    src="${c.embed_url}"></video>
                  <div class="hint">Agar play na ho: NVR HTTPS/HLS/embed URL lagao.
                    <a href="${c.embed_url}" target="_blank" rel="noopener">Open stream</a></div>
                ` : `<div class="hint">No stream URL</div>`}
              </div>`).join("") : `<div class="hint">Is site pe camera nahi — + Camera URL (DVR live link)</div>`}
          </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Live ops chat</h2></div>
          <div class="panel-bd">
            <div id="watch-chat" style="max-height:280px;overflow:auto;margin-bottom:10px">
              ${(chat.messages || []).map((m) => `<div class="hint" style="margin:4px 0"><b>${m.user_name}</b>: ${m.body}
                <span style="opacity:.6">${(m.created_at || "").slice(11, 16)}</span></div>`).join("") || `<div class="hint">Chat empty — site pe baat karein</div>`}
            </div>
            <div class="row" style="gap:8px">
              <input id="watch-msg" placeholder="Message to team on this site…" style="flex:1" />
              <button type="button" class="btn btn-primary btn-sm" id="watch-send">Send</button>
            </div>
          </div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Add camera (external DVR only)</h2></div>
        <div class="panel-bd grid-2">
          <div class="field"><label>Site</label>
            <select id="cam-site">${sites.map((s) => `<option value="${s.id}" ${s.id === siteId ? "selected" : ""}>${s.name}</option>`).join("")}</select>
          </div>
          <div class="field"><label>Name</label><input id="cam-name" placeholder="Gate / Line-A" /></div>
          <div class="field"><label>Live stream / embed URL (HTTPS HLS)</label><input id="cam-url" placeholder="https://nvr.example/live/...m3u8" /></div>
          <div class="field"><label>Kind</label>
            <select id="cam-kind"><option value="office">office</option><option value="plant">plant</option><option value="gate">gate</option><option value="employee_mobile">employee_mobile</option></select>
          </div>
          <button type="button" class="btn btn-accent" id="cam-save">Link camera (no video upload)</button>
        </div></div>`;
    el.querySelectorAll(".watch-site").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.watchSiteId = Number(btn.dataset.id);
        pageWatch(el);
      });
    });
    $("#watch-seed")?.addEventListener("click", async () => {
      try { toast((await API.post("/api/watch/seed-demo")).message || "Seeded"); pageWatch(el); }
      catch (e) { toast(e.message || "Failed"); }
    });
    $("#watch-add-site")?.addEventListener("click", async () => {
      const name = prompt("Site / office / plant name?");
      if (!name) return;
      try {
        await API.post("/api/watch/sites", { name, city: prompt("City?") || "" });
        toast("Site added"); pageWatch(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
    $("#cam-save")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/watch/cameras", {
          site_id: Number($("#cam-site")?.value),
          name: $("#cam-name")?.value || "Camera",
          stream_url: $("#cam-url")?.value,
          embed_url: $("#cam-url")?.value,
          kind: $("#cam-kind")?.value || "office",
        });
        toast(r.message || "Linked"); pageWatch(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
    $("#watch-add-cam")?.addEventListener("click", () => $("#cam-url")?.focus());
    $("#watch-send")?.addEventListener("click", async () => {
      const body = ($("#watch-msg")?.value || "").trim();
      if (!body) return;
      try {
        await API.post("/api/watch/chat", { site_id: siteId, body });
        if ($("#watch-msg")) $("#watch-msg").value = "";
        pageWatch(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
  }

  async function pageExtras(el) {
    const [chase, waHub, notifs, health, waLogin, slots] = await Promise.all([
      API.get("/api/advanced/chase/overdue").catch(() => ({ drafts: [], count: 0 })),
      API.get("/api/automation/whatsapp/hub").catch(() => ({ live: false, outbox: [], templates: [] })),
      API.get("/api/notifications").catch(() => []),
      API.get("/api/health").catch(() => ({})),
      API.get("/api/extras/whatsapp-login").catch(() => ({ mobile: "", login_type: "Default", status: "demo" })),
      API.get("/api/extras/store-slots").catch(() => ({ android_url: BRAND.apps.android.url, ios_url: BRAND.apps.ios.url })),
    ]);
    const integ = health.integrations || {};
    const canInstall = !!(window.deferredPrompt || window.matchMedia("(display-mode: standalone)").matches);
    if (slots.android_url) BRAND.apps.android.url = slots.android_url;
    if (slots.ios_url) BRAND.apps.ios.url = slots.ios_url;
    el.innerHTML = `
      ${moduleIntro("Kanha Extras", "Parity ke baad — Chase · Meta webhook · OCR · WhatsApp Login · PWA / store slots.", {
        chase: chase.count || 0,
        wa_outbox: (waHub.outbox || []).length,
        alerts: (notifs || []).filter((n) => !n.read).length,
        pwa: canInstall ? "ready" : "browser",
      }, `<button type="button" class="btn btn-primary btn-sm" id="ex-chase-all">Send all chases</button>
          <button type="button" class="btn btn-accent btn-sm" id="ex-ai">Open AI dock</button>
          <button type="button" class="btn btn-ghost btn-sm" id="ex-overdue">Run overdue autos</button>`)}

      <div class="panel glass"><div class="panel-hd"><h2>Ops Chase Pack</h2>
        <span class="pill ok">WhatsApp ${waHub.live ? "Meta LIVE" : "Demo ON"}</span></div>
        <div class="panel-bd">
          <p class="hint" style="margin-top:0">Overdue invoices → draft → Send WA → outbox + bell. Phone blank ho to demo number use hota hai.</p>
          ${table(
            ["Invoice", "Party", "Days", "Balance", ""],
            (chase.drafts || []).slice(0, 12).map((d, idx) => [
              d.invoice, d.party, d.days_overdue, money(d.balance),
              `<button class="btn btn-accent btn-sm" data-ex-chase="${idx}">Send WA</button>`,
            ])
          ) || `<p class="hint">No overdue — sales invoices with due date past + unpaid balance banavo.</p>`}
        </div></div>

      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>WhatsApp Login (SBAC)</h2>
          <span class="pill">${waLogin.status || "demo"}</span></div>
          <div class="panel-bd">
            <p class="hint" style="margin-top:0">whatsappset · Mobile · Type Default/User · Create Instance · Get QR · Reset</p>
            <div class="field"><label>Mobile No</label><input id="ex-wa-mobile" value="${waLogin.mobile || ''}" placeholder="txtmobileno" /></div>
            <div class="field"><label>Type</label>
              <select id="ex-wa-type">
                <option value="Default" ${waLogin.login_type === "Default" ? "selected" : ""}>Default</option>
                <option value="User" ${waLogin.login_type === "User" ? "selected" : ""}>User</option>
              </select></div>
            <div class="row" style="gap:6px;flex-wrap:wrap;margin-top:8px">
              <button type="button" class="btn btn-primary btn-sm" id="ex-wa-save">Save</button>
              <button type="button" class="btn btn-accent btn-sm" id="ex-wa-inst">Create Instance</button>
              <button type="button" class="btn btn-ghost btn-sm" id="ex-wa-qr">Get QR</button>
              <button type="button" class="btn btn-ghost btn-sm" id="ex-wa-reset">Reset</button>
            </div>
            <p class="hint" style="margin-top:8px">Instance: <code>${waLogin.instance_id || "—"}</code><br>${waLogin.qr_hint || ""}</p>
            <p class="hint">Meta webhook: <code>${waLogin.webhook_path || "/api/meta/whatsapp/webhook"}</code> · verify token in env <code>WHATSAPP_VERIFY_TOKEN</code></p>
          </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Bill OCR (demo)</h2></div>
          <div class="panel-bd">
            <p class="hint" style="margin-top:0">Paste invoice / PO text → GSTIN · Invoice No · Amount · Date · Party (no external OCR key)</p>
            <textarea id="ex-ocr-text" rows="5" style="width:100%" placeholder="Invoice No: INV-1001&#10;Bill To: Acme Steels&#10;GSTIN: 22AAAAA0000A1Z5&#10;Grand Total: 11800&#10;Date: 02/08/2026"></textarea>
            <button type="button" class="btn btn-primary btn-sm" id="ex-ocr-run" style="margin-top:8px">Parse</button>
            <div id="ex-ocr-out" class="hint" style="margin-top:8px">Results yahan</div>
          </div></div>
      </div>

      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>AI + Agents</h2></div>
          <div class="panel-bd action-hub">
            <a class="action-chip" href="#/ai">AI Assistant</a>
            <a class="action-chip" href="#/agents">Kanha Agents</a>
            <button type="button" class="action-chip" id="ex-ai-2">AI dock · Chase overdue</button>
            <p class="hint" style="margin-top:10px">Orb se dock kholo · chips: Chase overdue / Draft WhatsApp · Send draft button.</p>
          </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>WhatsApp + Automation</h2></div>
          <div class="panel-bd action-hub">
            <a class="action-chip" href="#/whatsapp">WhatsApp OS</a>
            <a class="action-chip" href="#/automation">Automation hub</a>
            <a class="action-chip" href="#/payments-ops">AR chase desk</a>
            <p class="hint" style="margin-top:10px">Templates · Run ALL autos · Overdue reminders — sab live demo path.</p>
          </div></div>
      </div>

      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Mobile / PWA + Store slots</h2></div>
          <div class="panel-bd">
            <p class="hint">PWA abhi kaam karti hai. Play / App Store = publish URL slots.</p>
            <div class="field"><label>Android URL</label><input id="ex-and-url" value="${slots.android_url || BRAND.apps.android.url}" /></div>
            <div class="field"><label>iOS URL</label><input id="ex-ios-url" value="${slots.ios_url || BRAND.apps.ios.url}" /></div>
            <div class="row" style="gap:8px;flex-wrap:wrap;margin-top:8px">
              <button type="button" class="btn btn-primary btn-sm" id="ex-slots-save">Save store slots</button>
              <a class="btn btn-ghost btn-sm" href="#/apps">Mobile Apps</a>
              <button type="button" class="btn btn-ghost btn-sm" id="ex-pwa">Install / Add to Home</button>
            </div>
            <p class="hint" style="margin-top:8px">Standalone: ${window.matchMedia("(display-mode: standalone)").matches ? "yes (installed)" : "no — browser tab"}</p>
          </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>More Kanha extras</h2></div>
          <div class="panel-bd action-hub">
            <a class="action-chip" href="#/bridges">ERP Bridges (Tally+Marg)</a>
            <a class="action-chip" href="#/logistics">e-Invoice / e-Way</a>
            <a class="action-chip" href="#/compliance">Legal / Risk board</a>
            <a class="action-chip" href="#/mis">MIS desk</a>
            <a class="action-chip" href="#/hrms">Field GPS</a>
            <a class="action-chip" href="#/documents">Documents</a>
          </div></div>
      </div>

      <div class="panel glass"><div class="panel-hd"><h2>Connectivity snapshot</h2></div>
        <div class="panel-bd">${table(
          ["Channel", "Mode"],
          [
            ["WhatsApp", waHub.live || integ.whatsapp_live ? "LIVE keys" : "Demo adapter"],
            ["Meta webhook", waLogin.verify_token_set ? "Verify token set" : "Set WHATSAPP_VERIFY_TOKEN"],
            ["AI / LLM", integ.llm_live ? "LIVE" : "Kanha Core demo"],
            ["GSP e-Invoice", integ.gsp_live ? "LIVE" : "DEMO-IRN"],
            ["Razorpay", integ.razorpay_live ? "LIVE" : "Demo settle"],
            ["OCR", "Demo regex parser"],
          ]
        )}</div></div>`;

    const openDockChase = () => {
      const orb = $("#ai-orb");
      const dock = $("#ai-dock");
      const input = $("#ai-dock-input");
      if (dock) dock.hidden = false;
      document.body.classList.add("ai-dock-open");
      orb?.classList.add("is-open");
      if (input) {
        input.value = "Chase overdue invoices — draft WhatsApp messages";
        $("#ai-dock-send")?.click();
      }
    };
    $("#ex-ai")?.addEventListener("click", openDockChase);
    $("#ex-ai-2")?.addEventListener("click", openDockChase);
    $("#ex-chase-all")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/advanced/chase/send-all", { limit: 10 });
        toast(r.message || "Chase batch done");
        flowSave("Extras chase batch", r, "WhatsApp OS + notifications.");
        pageExtras(el);
      } catch (e) { toast(e.message || "Failed"); }
    });
    el.querySelectorAll("[data-ex-chase]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const d = (chase.drafts || [])[Number(btn.dataset.exChase)];
        if (!d) return;
        try {
          const r = await API.post("/api/advanced/chase/send", { invoice: d.invoice, phone: d.phone || "" });
          toast(r.message || "Sent");
          flowSave(`Chase ${d.invoice}`, r, "Outbox + bell.");
        } catch (e) { toast(e.message || "Send failed"); }
      });
    });
    $("#ex-overdue")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/automation/run/overdue");
        toast(r.message || "Overdue autos ran");
        showSavedDetail("Overdue automation", r);
      } catch (e) { toast(e.message || "Failed"); }
    });
    const waAct = async (action) => {
      try {
        const r = await API.post("/api/extras/whatsapp-login", {
          mobile: $("#ex-wa-mobile")?.value || "",
          login_type: $("#ex-wa-type")?.value || "Default",
          action,
        });
        toast(r.message || action);
        pageExtras(el);
      } catch (e) { toast(e.message || "WA login failed"); }
    };
    $("#ex-wa-save")?.addEventListener("click", () => waAct("save"));
    $("#ex-wa-inst")?.addEventListener("click", () => waAct("instance"));
    $("#ex-wa-qr")?.addEventListener("click", () => waAct("qr"));
    $("#ex-wa-reset")?.addEventListener("click", () => waAct("reset"));
    $("#ex-ocr-run")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/extras/ocr/parse", {
          text: $("#ex-ocr-text")?.value || "",
          doc_kind: "invoice",
        });
        const f = r.fields || {};
        const box = $("#ex-ocr-out");
        if (box) {
          box.innerHTML = table(
            ["Field", "Value"],
            [
              ["Confidence", `${Math.round((r.confidence || 0) * 100)}%`],
              ["Invoice", f.invoice_no || "—"],
              ["Party", f.party || "—"],
              ["GSTIN", f.gstin || "—"],
              ["Amount", money(f.amount || 0)],
              ["Date", f.date || "—"],
              ["Phone", f.phone || "—"],
            ]
          );
        }
        toast(r.message || "Parsed");
        showSavedDetail("OCR result", r);
      } catch (e) { toast(e.message || "OCR failed"); }
    });
    $("#ex-slots-save")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/extras/store-slots", {
          android_url: $("#ex-and-url")?.value || "",
          ios_url: $("#ex-ios-url")?.value || "",
        });
        if (r.android_url) BRAND.apps.android.url = r.android_url;
        if (r.ios_url) BRAND.apps.ios.url = r.ios_url;
        toast(r.message || "Slots saved");
      } catch (e) { toast(e.message || "Save failed"); }
    });
    $("#ex-pwa")?.addEventListener("click", async () => {
      if (window.deferredPrompt) {
        window.deferredPrompt.prompt();
        try {
          await window.deferredPrompt.userChoice;
        } catch (_) {}
        toast("Install prompt shown");
      } else if (window.matchMedia("(display-mode: standalone)").matches) {
        toast("Already installed as PWA");
      } else {
        toast("Browser menu → Add to Home Screen / Install app");
      }
    });
  }

  async function pageAutomation(el) {
    const [jobs, suggest, waHub, rulesPack, proposals] = await Promise.all([
      API.get("/api/automation/jobs"),
      API.post("/api/ai/purchase-suggest"),
      API.get("/api/automation/whatsapp/hub").catch(() => ({ templates: [], jobs: [], outbox: [], flows: [] })),
      API.get("/api/rules").catch(() => ({ rules: [] })),
      API.get("/api/rules/proposals?status=pending").catch(() => ({ proposals: [] })),
    ]);
    const rules = rulesPack.rules || [];
    const props = proposals.proposals || [];
    const templates = waHub.templates || [];
    const waJobs = waHub.jobs || [];
    const outbox = waHub.outbox || [];
    const flows = waHub.flows || [];
    el.innerHTML = `
      <div class="panel glass"><div class="panel-hd"><h2>Live Automation Hub</h2>
        <span class="pill ok">WhatsApp ${waHub.live ? "Meta LIVE" : "Demo adapter ON"}</span>
        <a class="btn btn-ghost btn-sm" href="#/extras">Extras hub</a></div>
        <div class="panel-bd">
        <p class="hint" style="margin:0 0 12px">${waHub.principle || "Templates + autos fully working. Demo pe status=sent (wamid.DEMO…). Meta keys = live Cloud."} · <b>Hero:</b> Overdue reminders / Run ALL WhatsApp.</p>
        <div class="auto-actions">
          <button type="button" class="btn btn-accent" id="run-overdue">★ Overdue reminders (chase)</button>
          <button type="button" class="btn btn-primary" id="wa-run-all">Run ALL WhatsApp autos</button>
          ${(flows.filter((f) => f.id !== "all").map((f) =>
            `<button type="button" class="btn btn-ghost btn-sm wa-flow" data-flow="${f.id}">${f.label}</button>`
          ).join(""))}
          <button type="button" class="btn btn-ghost" id="run-reorder">Low-stock → draft PO</button>
          <button type="button" class="btn btn-ghost" id="rules-learn">Rules Agent</button>
          <a class="btn btn-ghost" href="#/whatsapp">WhatsApp OS</a>
          <a class="btn btn-ghost" href="#/ai">AI Chat</a>
          <a class="btn btn-ghost" href="#/payments-ops">AR chase</a>
        </div>
        <div id="auto-out" class="auto-out"></div>
      </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>WhatsApp templates (Automation)</h2></div>
        <div class="panel-bd">
          <p class="hint">Har message copy yahin — {{name}} {{amount}} {{number}} variables. Preview + Send template demo pe bhi live path.</p>
          ${table(
            ["Code", "Name", "Category", "Trigger", "Active", ""],
            templates.map((t) => [
              t.code,
              t.name,
              t.category,
              t.auto_trigger || "—",
              t.active ? "yes" : "no",
              `<button type="button" class="btn btn-sm btn-ghost wa-tpl-preview" data-code="${t.code}">Preview</button>
               <button type="button" class="btn btn-sm btn-accent wa-tpl-send" data-code="${t.code}">Send</button>
               <button type="button" class="btn btn-sm btn-ghost wa-tpl-toggle" data-code="${t.code}">Toggle</button>
               <button type="button" class="btn btn-sm btn-ghost wa-tpl-edit" data-code="${t.code}">Edit</button>`,
            ])
          )}
          <div id="wa-tpl-preview-out" class="hint" style="margin-top:10px"></div>
          <div class="grid-2" style="margin-top:12px">
            <div>
              <h3 style="font-size:14px;margin:0 0 8px">Edit / add template</h3>
              <div class="field"><label>Code</label><input id="wa-code" placeholder="lead_followup" /></div>
              <div class="field"><label>Name</label><input id="wa-name" /></div>
              <div class="field"><label>Category</label>
                <select id="wa-cat"><option>crm</option><option>sales</option><option>collection</option><option>ops</option></select>
              </div>
              <div class="field"><label>Auto trigger</label><input id="wa-trig" placeholder="lead_open" /></div>
              <div class="field"><label>Body</label><textarea id="wa-body" rows="4" placeholder="Namaste {{name}}..."></textarea></div>
              <button type="button" class="btn btn-primary btn-sm" id="wa-tpl-save">Save template</button>
            </div>
            <div>
              <h3 style="font-size:14px;margin:0 0 8px">WhatsApp auto jobs</h3>
              ${table(
                ["Job", "Trigger", "Active", ""],
                waJobs.map((j) => [
                  j.name,
                  j.trigger,
                  j.active ? "yes" : "no",
                  `<button type="button" class="btn btn-sm btn-ghost wa-job-toggle" data-id="${j.id}">Toggle</button>`,
                ])
              )}
              ${!waJobs.length ? `<div class="hint">Jobs seed on first hub open.</div>` : ""}
            </div>
          </div>
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>WhatsApp outbox (auto)</h2>
        <button type="button" class="btn btn-sm btn-ghost" id="wa-refresh">Refresh</button></div>
        <div class="panel-bd">${table(
          ["To", "Phone", "Template", "Status", "Preview"],
          outbox.map((m) => [m.to_name || "—", m.to_phone, m.template, `<span class="pill ${m.status === "sent" ? "ok" : ""}">${m.status}</span>`, (m.body || "")])
        ) || `<div class="hint">Empty — Run ALL WhatsApp autos</div>`}</div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Rules Studio — scoped · time-based</h2></div>
        <div class="panel-bd">
          ${table(
            ["Code", "Scope", "Name", "Ver", "Status", ""],
            rules.map((r) => [
              r.code, r.scope, r.name, r.version, r.status,
              `<button type="button" class="btn btn-sm btn-ghost rule-pause" data-id="${r.id}">Pause</button>
               <button type="button" class="btn btn-sm btn-ghost rule-retire" data-id="${r.id}">Retire</button>`,
            ])
          )}
          ${props.length ? table(
            ["ID", "Scope", "Title", "Why", ""],
            props.map((p) => [
              p.id,
              p.scope || "—",
              p.title || p.code || "proposal",
              (p.rationale || p.reason || p.description || "—").toString().slice(0, 80),
              `<button type="button" class="btn btn-sm btn-primary prop-ok" data-id="${p.id}">Approve</button>
               <button type="button" class="btn btn-sm btn-ghost prop-no" data-id="${p.id}">Reject</button>`,
            ])
          ) : `<div class="hint" style="margin-top:8px">No pending AI proposals — click Rules Agent to learn seasonal suggestions.</div>`}
        </div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Other jobs</h2></div><div class="panel-bd">
          ${table(["Name", "Trigger", "Action", "Active"], jobs.map((j) => [j.name, j.trigger, j.action, j.active ? "yes" : "no"]))}
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Low stock</h2></div><div class="panel-bd">
          ${table(
            ["SKU", "On hand", "Point", "Suggest"],
            (suggest.suggestions || []).map((s) => [s.sku, s.qty, s.reorder_point, s.suggest_order_qty])
          ) || `<div class="hint">${suggest.note || "Healthy"}</div>`}
        </div></div>
      </div>`;
    const show = (r) => {
      $("#auto-out").innerHTML = `<pre class="report-pre">${JSON.stringify(r, null, 2)}</pre>`;
    };
    const reload = () => setTimeout(() => pageAutomation(el), 600);
    const tplByCode = Object.fromEntries(templates.map((t) => [t.code, t]));
    $("#wa-run-all")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/automation/run/whatsapp?flow=all");
        show(r); toast(r.message || "WhatsApp autos ran"); reload();
      } catch (e) { toast(e.message || "Failed"); }
    });
    el.querySelectorAll(".wa-flow").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const r = await API.post(`/api/automation/run/whatsapp?flow=${btn.dataset.flow}`);
          show(r); toast(r.message || "Flow ran"); reload();
        } catch (e) { toast(e.message || "Failed"); }
      });
    });
    el.querySelectorAll(".wa-tpl-toggle").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const r = await API.post(`/api/automation/whatsapp/templates/${btn.dataset.code}/toggle`);
          toast(r.active ? "Template ON" : "Template OFF"); reload();
        } catch (e) { toast(e.message || "Failed"); }
      });
    });
    el.querySelectorAll(".wa-tpl-preview").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const r = await API.get(`/api/automation/whatsapp/templates/${encodeURIComponent(btn.dataset.code)}/preview`);
          const box = $("#wa-tpl-preview-out");
          if (box) box.innerHTML = `<b>${btn.dataset.code}</b><pre class="report-pre">${r.preview || ""}</pre>`;
          show(r);
        } catch (e) { toast(e.message || "Preview failed"); }
      });
    });
    el.querySelectorAll(".wa-tpl-send").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const r = await API.post("/api/comms/whatsapp/send-template", {
            template_code: btn.dataset.code,
            to_phone: "919876543210",
            to_name: "Aarav Traders",
            variables: { name: "Aarav", amount: "48,500", number: "INV-DEMO-001", value: "2,50,000" },
          });
          show(r);
          toast(r.message || "Template sent (demo)");
          reload();
        } catch (e) { toast(e.message || "Send failed"); }
      });
    });
    el.querySelectorAll(".wa-tpl-edit").forEach((btn) => {
      btn.addEventListener("click", () => {
        const t = tplByCode[btn.dataset.code];
        if (!t) return;
        if ($("#wa-code")) $("#wa-code").value = t.code;
        if ($("#wa-name")) $("#wa-name").value = t.name;
        if ($("#wa-cat")) $("#wa-cat").value = t.category;
        if ($("#wa-trig")) $("#wa-trig").value = t.auto_trigger || "";
        if ($("#wa-body")) $("#wa-body").value = t.body || "";
      });
    });
    $("#wa-tpl-save")?.addEventListener("click", async () => {
      try {
        const r = await API.put("/api/automation/whatsapp/templates", {
          code: $("#wa-code")?.value,
          name: $("#wa-name")?.value,
          category: $("#wa-cat")?.value,
          auto_trigger: $("#wa-trig")?.value,
          body: $("#wa-body")?.value,
          active: true,
        });
        toast(r.message || "Saved"); reload();
      } catch (e) { toast(e.message || "Failed"); }
    });
    el.querySelectorAll(".wa-job-toggle").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await API.post(`/api/automation/whatsapp/jobs/${btn.dataset.id}/toggle`);
          toast("Job toggled"); reload();
        } catch (e) { toast(e.message || "Failed"); }
      });
    });
    $("#run-reorder")?.addEventListener("click", async () => {
      try { const r = await API.post("/api/automation/run/reorder"); show(r); toast(r.message || "Done"); }
      catch (e) { toast(e.message || "Failed"); }
    });
    $("#run-overdue")?.addEventListener("click", async () => {
      try { const r = await API.post("/api/automation/run/overdue"); show(r); toast(r.message || "Done"); }
      catch (e) { toast(e.message || "Failed"); }
    });
    $("#rules-learn")?.addEventListener("click", async () => {
      try { const r = await API.post("/api/rules/agent/learn"); show(r); toast(r.message || "Proposals"); reload(); }
      catch (e) { toast(e.message || "Failed"); }
    });
    el.querySelectorAll(".prop-ok").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const r = await API.post(`/api/rules/proposals/${btn.dataset.id}/approve`);
          toast(r.message || "Proposal approved → rule active");
          reload();
        } catch (e) { toast(e.message || "Failed"); }
      });
    });
    el.querySelectorAll(".prop-no").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await API.post(`/api/rules/proposals/${btn.dataset.id}/reject`);
          toast("Proposal rejected");
          reload();
        } catch (e) { toast(e.message || "Failed"); }
      });
    });
    el.querySelectorAll(".rule-pause").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try { await API.post(`/api/rules/${btn.dataset.id}/pause`); toast("Paused"); reload(); }
        catch (e) { toast(e.message || "Failed"); }
      });
    });
    el.querySelectorAll(".rule-retire").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try { await API.post(`/api/rules/${btn.dataset.id}/retire`); toast("Retired"); reload(); }
        catch (e) { toast(e.message || "Failed"); }
      });
    });
    $("#wa-refresh")?.addEventListener("click", () => pageAutomation(el));
  }

  async function pageHA(el) {
    let st = {};
    let failed = { entries: [] };
    try {
      st = await API.get("/api/ha/status");
    } catch (e) {
      el.innerHTML = `<div class="panel glass"><div class="panel-bd"><p class="hint">${e.message || "HA status unavailable"}</p>
        <p>Enable <code>CLUSTER_ENABLED=true</code> and see <code>HA_ARCHITECTURE.md</code>.</p></div></div>`;
      return;
    }
    try {
      failed = await API.get("/api/ha/failed-entries?status=pending");
    } catch (_) { failed = { entries: [] }; }
    let risks = { risks: [], open_count: 0 };
    try {
      risks = await API.get("/api/ha/risks");
    } catch (_) {}
    const nodes = st.nodes || [];
    const mirrors = st.mirrors || [];
    const entries = failed.entries || [];
    const draft = API.getFailedDraft && API.getFailedDraft();
    const role = (st.self && st.self.role) || st.role || "—";
    const seq = st.seq ?? st.head_seq ?? "—";
    const primary = st.primary_url || (st.self && st.self.primary_url) || "—";
    const openRisks = (risks.risks || []).filter((r) => !r.ok);
    let blackout = { active: false };
    let autoCfg = null;
    try { blackout = await API.get("/api/ha/blackout"); } catch (_) {}
    try { autoCfg = await API.get("/api/ha/auto-config"); } catch (_) {}
    el.innerHTML = `
      <div class="panel glass" style="${blackout.active ? "border:1px solid #b91c1c" : ""}">
        <div class="panel-hd"><h2>Emergency Blackout · Portable ERP</h2>
          <span class="pill ${blackout.active ? "danger" : "ok"}">${blackout.active ? "BLACKOUT ON" : "LIVE"}</span></div>
        <div class="panel-bd">
          <p class="hint" style="margin:0 0 10px">Disaster / complete blackout: <b>Engage</b> → saari entries band, data portable ZIP me freeze.
            Connectivity kisi bhi server pe mile → pack restore + <b>Adopt primary</b> / Auto-configure.</p>
          <div class="auto-actions">
            <button type="button" class="btn btn-danger" id="bo-engage" ${blackout.active ? "disabled" : ""}>Engage BLACKOUT</button>
            <button type="button" class="btn btn-primary" id="bo-unlock" ${blackout.active ? "" : "disabled"}>Unlock → LIVE</button>
            <button type="button" class="btn btn-accent" id="bo-download">Download portable ERP</button>
            <button type="button" class="btn btn-ghost" id="bo-autoconf">Auto-configure now</button>
            <button type="button" class="btn btn-ghost" id="bo-adopt">Adopt other primary URL</button>
          </div>
          <div class="hint" style="margin-top:10px">${blackout.message || ""} ${blackout.portable?.checksum ? `· pack checksum ${(blackout.portable.checksum || "").slice(0, 12)}…` : ""}</div>
          ${autoCfg ? `<div class="hint" style="margin-top:8px">Auto-config host: <b>${autoCfg.hostname}</b> · suggest node <code>${autoCfg.suggestions?.cluster_node_id || ""}</code> · URL <code>${autoCfg.suggestions?.cluster_public_url || ""}</code></div>` : ""}
        </div>
      </div>
      <div class="panel glass agents-hero"><div class="panel-hd"><h2>Resilience — zero-stop ERP</h2>
        <div class="row" style="gap:8px;flex-wrap:wrap">
          <button type="button" class="btn btn-primary btn-sm" id="ha-sync">Sync now</button>
          <button type="button" class="btn btn-ghost btn-sm" id="ha-publish">Publish snapshot</button>
          <button type="button" class="btn btn-ghost btn-sm" id="ha-mirror">Mirror all sites</button>
          <button type="button" class="btn btn-accent btn-sm" id="ha-tick">Run HA tick</button>
          <button type="button" class="btn btn-danger btn-sm" id="ha-promote">Promote this node</button>
        </div></div>
        <div class="panel-bd">
          <p class="hint"><b>Primary</b> = abhi jo node <u>writes</u> accept karta hai (sirf ek). Crash → live replica
            <b>auto primary</b> (fence epoch). Open risks: <b>${risks.open_count || 0}</b> · fence <b>${st.fence_epoch || risks.fence_epoch || "—"}</b></p>
          <div class="grid-3" style="margin-top:12px">
            ${kpiCard("Role", role, { tone: role === "primary" ? "green" : "blue", icon: "◎" })}
            ${kpiCard("Seq", String(seq), { tone: "blue", icon: "#" })}
            ${kpiCard("Open risks", String(risks.open_count || 0), { tone: (risks.open_count || 0) ? "orange" : "green", icon: "!" })}
          </div>
          <div class="hint" style="margin-top:10px">Primary URL: <b>${primary}</b> · Node: <b>${(st.self && st.self.node_id) || st.node_id || "—"}</b></div>
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Realtime risks (protected now)</h2>
        <a class="btn btn-ghost btn-sm" href="#" onclick="return false" title="See HA_RISKS.md">HA_RISKS.md</a></div>
        <div class="panel-bd">
          <div class="readiness-grid">
            ${(risks.risks || []).map((r) => `<div class="readiness-item readiness-item--${r.ok ? "ready" : "planned"}">
              <span class="readiness-dot"></span>
              <div><strong>${r.title}</strong>
                <span>${r.ok ? "Protected: " + (r.protection || "OK") : "ACTION: " + (r.protection || r.issue)}</span>
                <span class="hint">${r.issue}</span>
              </div>
            </div>`).join("")}
          </div>
          ${openRisks.length ? `<div class="hint" style="margin-top:10px;color:var(--danger,#b45309)">Config abhi fix karo: ${openRisks.map((r) => r.id).join(", ")}</div>` : ""}
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Failed entries — auto-heal / Re-enter</h2></div>
        <div class="panel-bd">
          <p class="hint">Entry / API crash → write <b>rollback</b> → yahan queue. Data corrupt nahi hota.
            <b>Re-enter</b> se wahi payload dubara chalti hai.</p>
          ${draft ? `<div class="hint" style="margin:8px 0;padding:8px;border:1px solid rgba(0,0,0,.08)">Browser draft: <code>${draft.method} ${draft.path}</code>
            <button type="button" class="btn btn-sm btn-accent" id="ha-replay-draft">Re-enter draft</button></div>` : ""}
          ${table(
            ["ID", "Module", "Path", "Error", "Action"],
            entries.map((e) => [
              e.id,
              e.module || "—",
              `${e.method} ${e.path}`,
              (e.error || "").slice(0, 80),
              `<button type="button" class="btn btn-sm btn-primary ha-reenter" data-id="${e.id}">Re-enter</button>
               <button type="button" class="btn btn-sm btn-ghost ha-dismiss" data-id="${e.id}">Dismiss</button>`,
            ])
          )}
          ${!entries.length ? `<div class="hint">No pending failed entries — system clean.</div>` : ""}
        </div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Cluster nodes</h2></div>
          <div class="panel-bd">${table(
            ["Node", "Role", "URL", "Seq", "Priority", "Seen"],
            nodes.map((n) => [
              n.node_id || "—",
              n.role || "—",
              n.public_url || n.url || "—",
              n.last_seq ?? "—",
              n.priority ?? "—",
              n.last_heartbeat || n.heartbeat || "—",
            ])
          )}
          ${!nodes.length ? `<div class="hint">No peers yet — set CLUSTER_PEERS + shared CLUSTER_TOKEN.</div>` : ""}
          </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Mirror sites (identical packs)</h2></div>
          <div class="panel-bd">${table(
            ["Site", "Path", "LATEST", "Checksum"],
            mirrors.map((m) => [
              m.site || "—",
              m.path || "—",
              m.has_latest ? "yes" : "no",
              (m.checksum || "").slice(0, 12) || "—",
            ])
          )}
          <div class="hint" style="margin-top:8px">Set BACKUP_MIRROR_1..5 + BACKUP_USER_PACK in .env (USB/NAS). Empty → auto <code>data/mirrors/site-N</code>.</div>
          </div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>What actually happens</h2></div><div class="panel-bd">
        <ol class="hint" style="margin:0;padding-left:18px;line-height:1.7">
          <li><b>Server crash:</b> replica auto-promote → users keep working on surviving node.</li>
          <li><b>Entry crash:</b> bad write rollback + Failed entry queue → Re-enter (no corrupt half-data).</li>
          <li><b>Market / site down:</b> open another mirror / replica — same latest seq — ERP turant chalega.</li>
          <li>Dead machine repair optional; naya server pe portable pack + replica join = catch-up auto.</li>
        </ol>
      </div></div>`;
    const reload = () => setTimeout(() => pageHA(el), 600);
    $("#bo-engage")?.addEventListener("click", async () => {
      const phrase = prompt('Type BLACKOUT NOW to freeze all entries + save portable ERP', "");
      if (!phrase) return;
      try {
        const r = await API.post("/api/ha/blackout/engage", { confirm: phrase, reason: "disaster / blackout" });
        toast(r.message || "BLACKOUT ON");
        showSavedDetail("Blackout engaged · portable frozen", r.blackout || r);
        reload();
      } catch (e) { toast(e.message || "Engage failed"); }
    });
    $("#bo-unlock")?.addEventListener("click", async () => {
      const phrase = prompt('Type RESUME LIVE to allow entries again', "");
      if (!phrase) return;
      try {
        const r = await API.post("/api/ha/blackout/unlock", { confirm: phrase });
        toast(r.message || "LIVE again");
        reload();
      } catch (e) { toast(e.message || "Unlock failed"); }
    });
    $("#bo-download")?.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/ha/portable/download", {
          headers: { Authorization: `Bearer ${API.token}` },
        });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Download failed");
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "kanha_portable_erp.zip";
        a.click();
        URL.revokeObjectURL(a.href);
        toast("Portable ERP downloading…");
      } catch (e) { toast(e.message || "Download failed"); }
    });
    $("#bo-autoconf")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/ha/auto-config/apply", { adopt_mirrors: true });
        toast(r.message || "Auto-configured");
        showSavedDetail("Auto-configure applied", r.applied || r);
        reload();
      } catch (e) { toast(e.message || "Auto-config failed"); }
    });
    $("#bo-adopt")?.addEventListener("click", async () => {
      const url = prompt("Primary server URL (connectivity milne pe)", primary !== "—" ? primary : "http://127.0.0.1:8080");
      if (!url) return;
      const role = prompt("This node role? replica or primary", "replica") || "replica";
      try {
        const r = await API.post("/api/ha/adopt", { primary_url: url, role });
        toast(r.message || "Adopted");
        showSavedDetail("Adopted primary", r);
        if (r.primary_url) API.setPrimaryUrl(r.primary_url);
        reload();
      } catch (e) { toast(e.message || "Adopt failed"); }
    });
    $("#ha-sync")?.addEventListener("click", async () => {
      try { toast((await API.post("/api/ha/sync-now")).message || "Synced"); reload(); }
      catch (e) { toast(e.message || "Sync failed"); }
    });
    $("#ha-publish")?.addEventListener("click", async () => {
      try { toast((await API.post("/api/ha/publish")).message || "Published"); reload(); }
      catch (e) { toast(e.message || "Publish failed"); }
    });
    $("#ha-mirror")?.addEventListener("click", async () => {
      try { const r = await API.post("/api/ha/mirror-all"); toast(r.message || `Mirrored ${r.count || ""}`); reload(); }
      catch (e) { toast(e.message || "Mirror failed"); }
    });
    $("#ha-tick")?.addEventListener("click", async () => {
      try { toast((await API.post("/api/ha/tick")).message || "HA tick done"); reload(); }
      catch (e) { toast(e.message || "Tick failed"); }
    });
    $("#ha-promote")?.addEventListener("click", async () => {
      if (!confirm("Promote this node to PRIMARY writer? Use only if current primary is down.")) return;
      try { toast((await API.post("/api/ha/promote")).message || "Promoted"); reload(); }
      catch (e) { toast(e.message || "Promote failed"); }
    });
    $("#ha-replay-draft")?.addEventListener("click", async () => {
      if (!draft) return;
      try {
        const body = typeof draft.body === "string" ? JSON.parse(draft.body) : draft.body;
        await API.replay(draft.path, draft.method, body, draft.idem || `draft-${draft.path}`);
        toast("Draft re-entered OK");
        localStorage.removeItem("kanha_failed_write");
        reload();
      } catch (e) { toast(e.message || "Re-enter failed"); }
    });
    el.querySelectorAll(".ha-reenter").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        try {
          const r = await API.post(`/api/ha/failed-entries/${id}/reenter`);
          const re = r.reentry;
          await API.replay(re.path, re.method, re.body, `failed-entry-${id}`);
          await API.post(`/api/ha/failed-entries/${id}/heal`, { status: "reentered", note: "Re-entered from Resilience UI" });
          toast("Entry re-entered successfully");
          reload();
        } catch (e) { toast(e.message || "Re-enter failed"); }
      });
    });
    el.querySelectorAll(".ha-dismiss").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        try {
          await API.post(`/api/ha/failed-entries/${id}/heal`, { status: "dismissed", note: "Dismissed" });
          toast("Dismissed");
          reload();
        } catch (e) { toast(e.message || "Dismiss failed"); }
      });
    });
  }

  async function pageSettings(el) {
    const [mods, fields, roles, workflows, audit, users, brand, health, drafts, anomalies, profiles, overview] = await Promise.all([
      API.get("/api/modules"),
      API.get("/api/custom-fields"),
      API.get("/api/roles"),
      API.get("/api/workflows"),
      API.get("/api/audit"),
      API.get("/api/users"),
      API.get("/api/brand").catch(() => ({})),
      API.get("/api/health").catch(() => ({})),
      API.listDrafts(true).catch(() => ({ drafts: [] })),
      API.get("/api/security/anomalies?hours=48").catch(() => ({ flags: [], summary: {} })),
      API.get("/api/company/profiles").catch(() => ({ profiles: [], current: "hybrid" })),
      API.get("/api/ops/modules-overview").catch(() => ({ modules: [], purge_allowed: false, demo_mode: state.demoMode })),
    ]);
    state.modules = dedupeModules((mods.modules || []).filter((m) => canModule(m.key)));
    applyBrand(brand);
    const integ = health.integrations || {};
    const checklist = (health.golive && health.golive.checklist) || [];
    const waiting = (health.golive && health.golive.waiting_on_connectivity) || [];
    const myDrafts = drafts.drafts || [];
    const flags = anomalies.flags || [];
    const profList = profiles.profiles || [];
    const profCur = profiles.current || "hybrid";
    const ovMods = overview.modules || [];
    const purgeOk = !!overview.purge_allowed && !!state.demoMode;
    const phrase = overview.purge_confirm_phrase || "DELETE DEMO SAMPLE";
    el.innerHTML = `
      <div class="panel glass readiness-panel"><div class="panel-hd"><h2>Go-Live Control Center</h2>
        <div class="row" style="gap:8px">
          <a class="btn btn-ghost btn-sm" href="#/ha">Resilience / HA</a>
          <a class="btn btn-ghost btn-sm" href="#/watch">Live Monitor</a>
          <button type="button" class="btn btn-accent btn-sm" id="btn-backup">Backup DB now</button>
        </div></div>
        <div class="panel-bd">
          <p class="readiness-intro">${BRAND.name} — ek ERP, alag company type. Profile choose karo: manufacture / service / retail / solo.</p>
          <div class="hint" style="margin-bottom:10px">Waiting on keys: <b>${waiting.length ? waiting.join(", ") : "none — or optional"}</b>
            ${health.cluster ? ` · Cluster <b>${health.cluster.role || "?"}</b> · mirrors <b>${health.cluster.mirrors || 0}</b>` : ""}
          </div>
          <div class="readiness-grid">
            ${checklist.map((c) => `<div class="readiness-item readiness-item--${c.ok ? "ready" : (c.need === "connectivity" ? "stub" : "planned")}">
              <span class="readiness-dot"></span>
              <div><strong>${c.label}</strong><span>${c.ok ? "OK" : (c.need === "connectivity" ? "Paste key in .env" : "Set in .env")}</span></div>
            </div>`).join("")}
          </div>
          <div class="hint" style="margin-top:12px">Live adapters:
            WhatsApp <b>${integ.whatsapp ? "ON · Meta Cloud" : "off · paste WHATSAPP_TOKEN + PHONE_NUMBER_ID"}</b> ·
            Razorpay <b>${integ.razorpay ? "ON" : "off"}</b> ·
            GSP <b>${integ.gsp ? "ON · IRN/e-Way live path" : "off · paste GSP_BASE_URL + GSP_API_KEY"}</b> ·
            Maps <b>${integ.maps ? "ON" : "off"}</b> ·
            LLM <b>${integ.llm ? "ON" : "off"}</b> ·
            Postgres <b>${integ.postgres ? "ON" : "sqlite"}</b>
          </div>
          <div class="stub-note" style="margin-top:10px">
            <b>Go-live 4 steps:</b>
            1) Purge demo sample below →
            2) Enter real products/customers/vendors →
            3) Paste WhatsApp + GSP keys in <code>.env</code> →
            4) Set <code>DEMO_MODE=false</code> + restart. Purge ke baad demo rows restart pe wapas nahi aate.
          </div>
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>One-click purge · demo / sample data only</h2>
        ${purgeOk
          ? `<button type="button" class="btn btn-danger btn-sm" id="btn-purge-demo">Purge demo sample</button>`
          : `<button type="button" class="btn btn-ghost btn-sm" disabled title="Blocked when DEMO_MODE=false">Purge blocked (live)</button>`}
        </div>
        <div class="panel-bd">
          <p class="hint">${overview.purge_note || "Demo purge only works while DEMO_MODE=true."}</p>
          <div class="hint" style="margin:8px 0">Demo bundle: <b>${overview.demo_bundle ? "yes" : "no"}</b>
            ${overview.demo_purged_at ? ` · last purge <b>${overview.demo_purged_at}</b>` : ""}
            · DEMO_MODE <b>${overview.demo_mode ? "true" : "false"}</b></div>
          ${purgeOk ? `
            <div class="field" style="max-width:28rem;margin-top:10px">
              <label>Confirm phrase (exact)</label>
              <input id="purge-confirm" placeholder="${phrase}" autocomplete="off" />
            </div>
            <div class="hint">Deletes leads, invoices, stock, HR sample, RFQ/visits/approvals demo, etc. <b>Keeps</b> ${(overview.kept_on_purge || []).join(", ")}.
              After purge, restart will <b>not</b> re-seed demo. Real live pe button band — <code>DEMO_MODE=false</code>.</div>
          ` : `<div class="stub-note" style="margin-top:8px">Live mode: mass-delete disabled. Real operational data protected.</div>`}
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Module completeness · what's inside</h2></div>
        <div class="panel-bd">
          <p class="hint">Har module me abhi kya data hai — incomplete feel hatane ke liye counts.</p>
          ${table(
            ["Module", "What it does", "Counts"],
            ovMods.map((m) => [
              m.name,
              m.what,
              Object.entries(m.counts || {}).map(([k, v]) => `${k}:${v}`).join(" · ") || "—",
            ])
          )}
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Company type / industry profile</h2></div>
        <div class="panel-bd">
          <p class="hint">Manufacturing → BOM/WO/MRP on. Service → tickets/projects. Retail → POS. Solo → lean. Same kernel, alag scope.</p>
          <div class="readiness-grid">
            ${profList.map((p) => `<button type="button" class="readiness-item readiness-item--${p.id === profCur ? "ready" : "planned"} prof-pick" data-id="${p.id}" style="cursor:pointer;text-align:left;border:0;width:100%">
              <span class="readiness-dot"></span>
              <div><strong>${p.label}</strong><span>${p.blurb} · ${p.module_count} modules</span></div>
            </button>`).join("")}
          </div>
          <div class="hint" style="margin-top:8px">Current: <b>${profCur}</b></div>
        </div></div>
      <div class="panel glass"><div class="panel-hd"><h2>Security — stolen phone / drafts / accountability</h2>
        <button type="button" class="btn btn-danger btn-sm" id="btn-revoke-me">Logout all my devices</button></div>
        <div class="panel-bd">
          <p class="hint">Mobile chori → <b>Logout all devices</b> (sessions mar). Notes/form jo app me the → <b>server drafts</b> me safe.
            Cheat/time-waste → audit signals (spyware nahi). Policy: important work <b>sirf Kanha app</b> me — WhatsApp personal pe nahi.</p>
          <div class="grid-2" style="margin-top:10px">
            <div>
              <h3 style="margin:0 0 8px;font-size:14px">My open drafts (${myDrafts.length})</h3>
              ${table(["Key", "Title", "Updated", ""], myDrafts.map((d) => [
                d.draft_key,
                d.title || "—",
                d.updated_at || "—",
                `<button type="button" class="btn btn-sm btn-ghost draft-discard" data-id="${d.id}">Discard</button>`,
              ]))}
              ${!myDrafts.length ? `<div class="hint">No open drafts — forms autosave when wired with API.saveDraft.</div>` : ""}
            </div>
            <div>
              <h3 style="margin:0 0 8px;font-size:14px">Anomaly signals (48h)</h3>
              ${table(["Sev", "User", "Signal"], flags.slice(0, 12).map((f) => [f.severity, f.user || "—", f.message || f.code]))}
              ${!flags.length ? `<div class="hint">${anomalies.message || "Clean — no unusual patterns"}</div>` : ""}
              <div class="hint" style="margin-top:8px">High: backup burst / mass delete. Revoke user from Users table actions below.</div>
            </div>
          </div>
        </div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>White-label brand</h2></div><div class="panel-bd">
          <div class="field"><label>App name</label><input id="br-name" value="${brand.app_name || BRAND.name}" /></div>
          <div class="field"><label>Tagline</label><input id="br-tag" value="${brand.tagline || BRAND.tagline}" /></div>
          <div class="field"><label>Logo URL</label><input id="br-logo" value="${brand.logo_url || ""}" /></div>
          <div class="field"><label>Primary color</label><input id="br-primary" value="${brand.primary || "#1d4ed8"}" /></div>
          <div class="field"><label>Company name</label><input id="br-co" value="${brand.company_name || ""}" /></div>
          <div class="field"><label>GSTIN</label><input id="br-gstin" value="${brand.company_gstin || ""}" /></div>
          <button type="button" class="btn btn-primary" id="br-save">Save white-label</button>
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Change my password</h2></div><div class="panel-bd">
          <div class="field"><label>Current</label><input id="pw-cur" type="password" autocomplete="current-password" /></div>
          <div class="field"><label>New</label><input id="pw-new" type="password" autocomplete="new-password" /></div>
          <button type="button" class="btn btn-accent" id="pw-save">Update password</button>
          <div class="hint" style="margin-top:8px">Production: min 8 chars + letters + numbers.</div>
        </div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Users</h2>
        <button class="btn btn-primary btn-sm" id="add-user">+ User</button></div>
        <div class="panel-bd">${table(
          ["Name", "Email", "Role", "Active", "Security"],
          users.map((u) => [
            u.full_name,
            u.email,
            u.role_name || u.role_code || "—",
            u.is_active ? "yes" : "no",
            `<button type="button" class="btn btn-sm btn-ghost revoke-user" data-id="${u.id}" data-email="${u.email}">Revoke devices</button>`,
          ])
        )}
        ${state.demoMode ? `<div class="hint" style="margin-top:8px">Seed sales login: <b>sales@kanhaerp.com</b> / <b>sales123</b></div>` : ""}
        </div></div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Module Registry</h2></div><div class="panel-bd" id="mod-list">
          ${dedupeModules(mods.modules || []).map((m) => `<div class="toggle-row"><span>${m.name}</span><div class="switch ${m.enabled ? "on" : ""}" data-key="${m.key}"></div></div>`).join("")}
          <div class="row" style="margin-top:14px"><button class="btn btn-primary" id="save-mods">Save modules</button></div>
        </div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Custom Fields</h2><button class="btn btn-sm btn-ghost" id="add-cf">+ Field</button></div>
          <div class="panel-bd">${table(["Entity", "Key", "Label", "Type"], fields.map((f) => [f.entity, f.field_key, f.label, f.field_type]))}</div></div>
      </div>
      <div class="grid-2">
        <div class="panel glass"><div class="panel-hd"><h2>Roles & Permissions</h2></div><div class="panel-bd">${table(["Code", "Name", "Perms"], roles.map((r) => [r.code, r.name, (r.permissions || []).length]))}</div></div>
        <div class="panel glass"><div class="panel-hd"><h2>Approval Workflows</h2></div><div class="panel-bd">${table(["Name", "Entity", "Steps"], workflows.map((w) => [w.name, w.entity, (w.steps || []).length]))}</div></div>
      </div>
      <div class="panel glass"><div class="panel-hd"><h2>Audit Trail</h2>
        <a class="btn btn-accent btn-sm" href="#/activity">Full activity tracking</a></div>
        <div class="panel-bd">${table(
          ["Who", "Action", "What", "When"],
          (audit || []).slice(0, 25).map((a) => [
            a.user_name || a.user_email || "—",
            a.action,
            `${a.entity || ""} ${a.entity_id || ""}`.trim(),
            (a.created_at || "—").replace("T", " ").slice(0, 19),
          ])
        )}</div></div>`;
    const enabled = {};
    mods.modules.forEach((m) => { enabled[m.key] = m.enabled; });
    el.querySelectorAll(".switch").forEach((sw) => {
      sw.addEventListener("click", () => {
        sw.classList.toggle("on");
        enabled[sw.dataset.key] = sw.classList.contains("on");
      });
    });
    $("#btn-purge-demo")?.addEventListener("click", async () => {
      const typed = ($("#purge-confirm")?.value || "").trim();
      if (typed.toUpperCase() !== phrase) {
        toast(`Type exactly: ${phrase}`);
        return;
      }
      if (!confirm("This deletes ALL demo/sample transactional data (invoices, stock, HR sample, etc). Masters (users/COA) stay. Continue?")) return;
      try {
        const r = await API.post("/api/ops/purge-demo", { confirm: phrase });
        toast(r.message || `Purged ${r.total_rows} rows`);
        flowSave("Demo purged · go-live ready", {
          deleted: r.total_rows,
          reseed_blocked: r.reseed_blocked,
          next_steps: r.next_steps || [],
        }, "Ab real masters enter karo · WhatsApp/GSP keys .env me · DEMO_MODE=false.");
        pageSettings(el);
      } catch (e) {
        toast(e.message || "Purge blocked / failed");
      }
    });
    $("#btn-revoke-me")?.addEventListener("click", async () => {
      if (!confirm("Logout ALL your devices / browsers? You will need to login again.")) return;
      try {
        await API.post("/api/auth/revoke-sessions");
        API.clear();
        toast("All sessions revoked");
        location.hash = "#/login";
      } catch (e) { toast(e.message || "Failed"); }
    });
    el.querySelectorAll(".prof-pick").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        if (!confirm(`Apply industry profile "${id}"? Modules will match that business type.`)) return;
        try {
          const r = await API.put("/api/company/profile", { profile: id, apply_modules: true });
          toast(r.message || "Profile applied");
          state.modules = [];
          render();
        } catch (e) { toast(e.message || "Failed"); }
      });
    });
    el.querySelectorAll(".revoke-user").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        const email = btn.getAttribute("data-email");
        if (!confirm(`Revoke all devices for ${email}? (phone stolen / security)`)) return;
        try {
          const r = await API.post("/api/security/revoke-user-sessions", { user_id: Number(id), reason: "admin_security" });
          toast(r.message || "Revoked");
        } catch (e) { toast(e.message || "Failed"); }
      });
    });
    el.querySelectorAll(".draft-discard").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await API.post(`/api/drafts/${btn.getAttribute("data-id")}/discard`);
          toast("Draft discarded");
          pageSettings(el);
        } catch (e) { toast(e.message || "Failed"); }
      });
    });
    $("#save-mods")?.addEventListener("click", async () => {
      await API.put("/api/modules", { modules: enabled });
      state.modules = [];
      toast("Modules saved");
      render();
    });
    $("#br-save")?.addEventListener("click", async () => {
      try {
        const r = await API.put("/api/brand", {
          app_name: $("#br-name")?.value,
          tagline: $("#br-tag")?.value,
          logo_url: $("#br-logo")?.value,
          primary: $("#br-primary")?.value,
          company_name: $("#br-co")?.value,
          company_gstin: $("#br-gstin")?.value,
        });
        applyBrand(r);
        toast("White-label saved");
      } catch (e) {
        toast(e.message || "Save failed");
      }
    });
    $("#pw-save")?.addEventListener("click", async () => {
      try {
        await API.post("/api/auth/change-password", {
          current_password: $("#pw-cur")?.value,
          new_password: $("#pw-new")?.value,
        });
        toast("Password updated");
        if ($("#pw-cur")) $("#pw-cur").value = "";
        if ($("#pw-new")) $("#pw-new").value = "";
      } catch (e) {
        toast(e.message || "Failed");
      }
    });
    $("#btn-backup")?.addEventListener("click", async () => {
      try {
        const r = await API.post("/api/ops/backup");
        toast(r.ok ? `Backup OK · ${r.path}` : (r.note || r.error || "Backup info"));
      } catch (e) {
        toast(e.message || "Backup failed");
      }
    });
    $("#add-cf")?.addEventListener("click", async () => {
      await API.post("/api/custom-fields", {
        entity: "customer",
        field_key: "region_" + Date.now().toString().slice(-4),
        label: "Region",
        field_type: "text",
      });
      toast("Custom field added");
      pageSettings(el);
    });
    $("#add-user")?.addEventListener("click", async () => {
      const full_name = prompt("Full name");
      if (!full_name) return;
      const email = prompt("Email", `user${Date.now().toString().slice(-4)}@company.com`);
      if (!email) return;
      const password = prompt("Temp password (min 8, letters+numbers in prod)", "Welcome9x");
      if (!password) return;
      const role_id = roles[0]?.id || null;
      await API.post("/api/users", { full_name, email, password, role_id });
      toast("User created");
      pageSettings(el);
    });
  }

  async function pageHrFlow(el) {
    const f = state.hrFlow;
    const steps = ["Hire", "Attendance", "Leave", "Payroll + Payslip", "Bank Disburse", "Expense", "Done"];
    el.innerHTML = `
      <div class="panel glass">
        <div class="panel-hd"><h2>HR Live Flow</h2><span class="pill">Hire → Attendance → Leave → Payroll → Bank → Expense</span></div>
        <div class="panel-bd">
          <div class="flow-steps">${steps.map((s, i) => `<div class="flow-step ${i < f.step ? "done" : ""} ${i === f.step ? "active" : ""}">${i + 1}. ${s}</div>`).join("")}</div>
          <p style="color:var(--muted);margin-top:0">Complete people cycle on demo data — baad mein real employees / salary / bank details replace kar dena.</p>
          <div class="row">
            <button class="btn btn-accent" id="hr-flow-next">${f.step >= 6 ? "Restart HR tour" : "Run next HR step"}</button>
            <button class="btn btn-ghost" id="hr-flow-reset">Reset</button>
            <a class="btn btn-ghost btn-sm" href="#/hrms">Open HRMS</a>
          </div>
          <div style="margin-top:16px">${table(["Step", "Result"], f.log.map((l) => [l.step, l.result]))}</div>
          ${f.payslip ? `<div class="hint" style="margin-top:14px">Payslip · <b>${f.payslip.name}</b> · Basic ${money(f.payslip.basic)} · PF ${money(f.payslip.pf)} · ESIC ${money(f.payslip.esic)} · <b>Net ${money(f.payslip.net)}</b></div>` : ""}
        </div>
      </div>`;
    $("#hr-flow-reset")?.addEventListener("click", () => {
      state.hrFlow = { step: 0, empId: null, empCode: null, leaveId: null, payrollId: null, payslip: null, expenseId: null, log: [] };
      pageHrFlow(el);
    });
    $("#hr-flow-next")?.addEventListener("click", async () => {
      try {
        if (f.step >= 6) {
          state.hrFlow = { step: 0, empId: null, empCode: null, leaveId: null, payrollId: null, payslip: null, expenseId: null, log: [] };
          pageHrFlow(el);
          return;
        }
        if (f.step === 0) {
          const tag = Date.now().toString().slice(-4);
          const emp = await API.post("/api/hrms/employees", {
            full_name: "Flow Emp " + tag,
            email: `flow.emp${tag}@kanhaerp.com`,
            phone: "98" + tag + "00123",
            department: "Marketing",
            designation: "Field Executive",
            basic_salary: 30000,
            work_type: "marketing",
            track_live: true,
            shift: "general",
            bank_name: "ICICI Bank",
            ifsc: "ICIC0000456",
          });
          f.empId = emp.id;
          f.empCode = emp.code;
          f.log.push({ step: "Hire", result: `${emp.code} · ${emp.full_name} · bank linked` });
          f.step = 1;
        } else if (f.step === 1) {
          const r = await API.post("/api/hrms/attendance", {
            employee_id: f.empId,
            status: "present",
            check_in: "09:30",
            check_out: "18:00",
            source: "manual",
          });
          f.log.push({ step: "Attendance", result: `${r.day} · ${r.status} · ${r.check_in}–${r.check_out}` });
          f.step = 2;
        } else if (f.step === 2) {
          const leave = await API.post("/api/hrms/leaves", {
            employee_id: f.empId,
            leave_type: "casual",
            reason: "HR flow demo leave",
          });
          await API.post(`/api/hrms/leaves/${leave.id}/decide`, { status: "approved", decision_note: "Auto-approved in HR flow" });
          f.leaveId = leave.id;
          f.log.push({ step: "Leave", result: `#${leave.id} casual · approved` });
          f.step = 3;
        } else if (f.step === 3) {
          const r = await API.post("/api/hrms/payroll/run");
          f.payrollId = r.id;
          await API.post(`/api/hrms/payroll/${r.id}/confirm`);
          await API.post(`/api/hrms/payroll/${r.id}/approve`);
          const slip = (r.lines || []).find((l) => l.employee_id === f.empId) || (r.lines || [])[0];
          f.payslip = slip;
          f.log.push({ step: "Payroll", result: `${r.period} draft→confirm→approve · ${r.employees} emps · net ${money(slip?.net || 0)}` });
          f.step = 4;
        } else if (f.step === 4) {
          const r = await API.post("/api/hrms/disbursements/from-payroll");
          f.log.push({ step: "Bank Disburse", result: `${money(r.total_amount)} · ${r.status} · ${(r.lines || []).length} UTRs` });
          f.step = 5;
        } else if (f.step === 5) {
          const exp = await API.post("/api/hrms/expenses", {
            employee_id: f.empId,
            category: "travel",
            amount: 1500,
            description: "HR flow field travel",
          });
          await API.post(`/api/hrms/expenses/${exp.id}/decide`, { status: "approved", decision_note: "Approved in HR flow" });
          f.expenseId = exp.id;
          await API.post("/api/hrms/tracking/simulate");
          f.log.push({ step: "Expense + Track", result: `₹1,500 approved · GPS simulate done` });
          f.step = 6;
          toast("HR Live Flow complete");
        }
        pageHrFlow(el);
      } catch (e) {
        toast(e.message);
      }
    });
  }

  async function pageFlow(el) {
    const f = state.flow;
    const steps = ["Lead", "Quotation", "Sales Order", "Delivery + Invoice", "Done"];
    el.innerHTML = `
      <div class="panel glass">
        <div class="panel-hd"><h2>Live business flow</h2><span class="pill">Lead → Quote → SO → Invoice</span></div>
        <div class="panel-bd">
          <div class="flow-steps">${steps.map((s, i) => `<div class="flow-step ${i < f.step ? "done" : ""} ${i === f.step ? "active" : ""}">${i + 1}. ${s}</div>`).join("")}</div>
          <p style="color:var(--muted);margin-top:0">Same trading logic production modules use — demo company pe one-click chalao.</p>
          <div class="row">
            <button class="btn btn-accent" id="flow-next">${f.step >= 4 ? "Restart tour" : "Run next step"}</button>
            <button class="btn btn-ghost" id="flow-reset">Reset</button>
          </div>
          <div style="margin-top:16px">${table(["Step", "Result"], f.log.map((l) => [l.step, l.result]))}</div>
          ${f.invoice ? `<div class="hint" style="margin-top:14px">Latest invoice <b>${f.invoice.number}</b> · Total ${money(f.invoice.total)} · GST split ready in accounting.</div>` : ""}
        </div>
      </div>`;
    $("#flow-reset")?.addEventListener("click", () => {
      state.flow = { step: 0, leadId: null, quoteId: null, orderId: null, invoice: null, log: [] };
      pageFlow(el);
    });
    $("#flow-next")?.addEventListener("click", async () => {
      try {
        if (f.step >= 4) {
          state.flow = { step: 0, leadId: null, quoteId: null, orderId: null, invoice: null, log: [] };
          pageFlow(el);
          return;
        }
        if (f.step === 0) {
          const lead = await API.post("/api/crm/leads", {
            name: "Demo Buyer " + Date.now().toString().slice(-4),
            company_name: "Flow Demo Traders",
            email: "demo@flow.in",
            phone: "+91-9000000000",
            stage: "qualified",
            value: 180000,
            source: "live_flow",
            custom: { priority: "High" },
          });
          f.leadId = lead.id;
          f.log.push({ step: "Lead", result: `#${lead.id} ${lead.name}` });
          f.step = 1;
        } else if (f.step === 1) {
          const r = await API.post(`/api/crm/flow/lead-to-quote/${f.leadId}`);
          f.quoteId = r.quotation.id;
          f.log.push({ step: "Quotation", result: `${r.quotation.number} · ${money(r.quotation.total)}` });
          f.step = 2;
        } else if (f.step === 2) {
          const r = await API.post(`/api/sales/flow/quote-to-order/${f.quoteId}`);
          f.orderId = r.id;
          f.log.push({ step: "Sales Order", result: `${r.number} · approval ${r.approval_status}` });
          f.step = 3;
        } else if (f.step === 3) {
          const r = await API.post(`/api/sales/flow/order-to-invoice/${f.orderId}`);
          f.invoice = r.invoice;
          f.log.push({ step: "Delivery + Invoice", result: `${r.delivery_number} → ${r.invoice.number}` });
          f.step = 4;
          toast("Live flow complete");
        }
        pageFlow(el);
      } catch (e) {
        toast(e.message);
      }
    });
  }

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    window.__kanhaPwaPrompt = e;
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    });
  }

  boot().catch((err) => {
    console.error(err);
    const root = document.getElementById("app");
    if (root) {
      root.innerHTML = `<div class="login-shell"><div class="login-card glass" style="padding:24px;max-width:420px;margin:10vh auto">
        <h2>KanhaERP load issue</h2>
        <p style="color:var(--ink-muted)">${String(err && err.message ? err.message : err)}</p>
        <button class="btn btn-primary" type="button" id="kanha-recover">Clear session &amp; reload</button>
      </div></div>`;
      document.getElementById("kanha-recover")?.addEventListener("click", () => {
        try {
          localStorage.removeItem("kanha_token");
          localStorage.removeItem("kanha_user");
          localStorage.removeItem("kanha_primary_url");
        } catch (_) {}
        location.hash = "#/login";
        location.reload();
      });
    }
  });
})();
