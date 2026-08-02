const API = {
  token: localStorage.getItem("kanha_token") || "",
  user: (() => {
    try {
      return JSON.parse(localStorage.getItem("kanha_user") || "null");
    } catch {
      localStorage.removeItem("kanha_user");
      localStorage.removeItem("kanha_token");
      return null;
    }
  })(),
  primaryUrl: localStorage.getItem("kanha_primary_url") || "",

  setSession(token, user) {
    this.token = token;
    this.user = user;
    localStorage.setItem("kanha_token", token);
    localStorage.setItem("kanha_user", JSON.stringify(user));
  },

  clear() {
    this.token = "";
    this.user = null;
    localStorage.removeItem("kanha_token");
    localStorage.removeItem("kanha_user");
  },

  setPrimaryUrl(url) {
    if (!url) return;
    this.primaryUrl = url;
    localStorage.setItem("kanha_primary_url", url);
  },

  _idemKey(path, method, body) {
    // Stable per payload so network retry of same click doesn't double-create
    const base = `${method}:${path}:${typeof body === "string" ? body : JSON.stringify(body || {})}`;
    let h = 0;
    for (let i = 0; i < base.length; i++) h = ((h << 5) - h + base.charCodeAt(i)) | 0;
    return `idem-${Math.abs(h)}`;
  },

  async request(path, opts = {}) {
    const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    const method = (opts.method || "GET").toUpperCase();
    const isWrite = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
    if (isWrite && !headers["X-Idempotency-Key"] && !opts.skipIdem) {
      headers["X-Idempotency-Key"] = opts.idempotencyKey || this._idemKey(path, method, opts.body);
    }
    if (isWrite && opts.body) {
      try {
        localStorage.setItem("kanha_last_write", JSON.stringify({
          path, method, body: opts.body, at: Date.now(), idem: headers["X-Idempotency-Key"],
        }));
      } catch (_) { /* ignore quota */ }
    }
    const res = await fetch(path, { ...opts, headers });
    if (res.status === 401) {
      this.clear();
      location.hash = "#/login";
      throw new Error("Session expired");
    }
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
    if (!res.ok) {
      if (res.status === 409 && data && data.redirect_writes && data.primary_url) {
        this.setPrimaryUrl(data.primary_url);
        const msg = data.detail || "Replica node — opening primary for writes";
        if (confirm(`${msg}\n\nOpen primary now?\n${data.primary_url}`)) {
          window.location.href = data.primary_url + (location.hash || "/#/");
        }
        throw new Error(msg);
      }
      if (res.status === 503 && data && data.blackout) {
        throw new Error(data.detail || "EMERGENCY BLACKOUT — entries locked. Open Resilience.");
      }
      let detail = (data && (data.detail || data.message)) || res.statusText;
      if (Array.isArray(detail)) {
        detail = detail.map((d) => d.msg || d.message || JSON.stringify(d)).join("; ");
      } else if (detail && typeof detail === "object") {
        detail = detail.msg || JSON.stringify(detail);
      }
      if (isWrite && res.status >= 500) {
        try {
          localStorage.setItem("kanha_failed_write", JSON.stringify({
            path, method, body: opts.body, error: detail, at: Date.now(),
            healed: !!(data && data.healed),
            idem: headers["X-Idempotency-Key"],
          }));
        } catch (_) {}
      }
      throw new Error(detail);
    }
    if (isWrite) {
      try { localStorage.removeItem("kanha_failed_write"); } catch (_) {}
    }
    return data;
  },

  getFailedDraft() {
    try { return JSON.parse(localStorage.getItem("kanha_failed_write") || "null"); }
    catch { return null; }
  },

  get(path) { return this.request(path); },
  post(path, body, extra = {}) {
    return this.request(path, {
      method: "POST",
      body: JSON.stringify(body || {}),
      idempotencyKey: extra.idempotencyKey,
      headers: extra.headers,
    });
  },
  put(path, body, extra = {}) {
    return this.request(path, {
      method: "PUT",
      body: JSON.stringify(body || {}),
      idempotencyKey: extra.idempotencyKey,
    });
  },
  patch(path, body, extra = {}) {
    return this.request(path, {
      method: "PATCH",
      body: JSON.stringify(body || {}),
      idempotencyKey: extra.idempotencyKey,
    });
  },

  async replay(path, method, body, idemKey) {
    const m = (method || "POST").toUpperCase();
    const payload = typeof body === "string" ? JSON.parse(body || "{}") : (body || {});
    const key = idemKey || `reenter-${path}-${JSON.stringify(payload).slice(0, 80)}`;
    if (m === "PUT") return this.put(path, payload, { idempotencyKey: key });
    if (m === "PATCH") {
      return this.request(path, {
        method: "PATCH",
        body: JSON.stringify(payload),
        idempotencyKey: key,
      });
    }
    if (m === "DELETE") {
      return this.request(path, {
        method: "DELETE",
        body: JSON.stringify(payload),
        idempotencyKey: key,
      });
    }
    return this.post(path, payload, { idempotencyKey: key });
  },

  async upload(path, file, fields = {}) {
    const fd = new FormData();
    fd.append("file", file);
    Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
    const headers = {};
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    const res = await fetch(path, { method: "POST", headers, body: fd });
    if (res.status === 401) {
      this.clear();
      location.hash = "#/login";
      throw new Error("Session expired");
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
    return data;
  },

  async uploadMany(path, files) {
    const fd = new FormData();
    [...files].forEach((f) => fd.append("files", f, f.name));
    const headers = {};
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    const res = await fetch(path, { method: "POST", headers, body: fd });
    if (res.status === 401) {
      this.clear();
      location.hash = "#/login";
      throw new Error("Session expired");
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.message || res.statusText);
    return data;
  },

  async del(path) {
    return this.request(path, { method: "DELETE" });
  },

  /** Server draft sync — phone lost pe bhi company ke paas form data */
  async saveDraft(draftKey, payload, meta = {}) {
    return this.put("/api/drafts", {
      draft_key: draftKey,
      payload: payload || {},
      module: meta.module || "",
      title: meta.title || draftKey,
      client: meta.client || "web",
    });
  },

  async listDrafts(mine = true) {
    return this.get(`/api/drafts?mine=${mine ? "true" : "false"}&status=open`);
  },

  draftAutosave(draftKey, getPayload, meta = {}, everyMs = 8000) {
    let t = null;
    const tick = async () => {
      try {
        const payload = typeof getPayload === "function" ? getPayload() : getPayload;
        if (!payload || (typeof payload === "object" && !Object.keys(payload).length)) return;
        await this.saveDraft(draftKey, payload, meta);
      } catch (_) { /* offline — next tick */ }
    };
    t = setInterval(tick, everyMs);
    tick();
    return () => clearInterval(t);
  },
};
