"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");
const http = require("http");
const net = require("net");

const DEFAULT_CDP_HOST = "127.0.0.1";
const COMMON_CDP_PORTS = [9222, 9229, 9333];
const STATIC_RESOURCE_TYPES = new Set(["Image", "Stylesheet", "Font", "Media", "Script"]);
const SNAPSHOT_TEXT_LIMIT = 12000;

const TOOL_DEFS = [
  tool("browser_navigate", "Navigate the current CDP tab to a URL.", { url: "string" }),
  tool("browser_snapshot", "Capture a text snapshot of the current CDP tab.", { filename: "string?" }),
  tool("browser_click", "Click an element in the current CDP tab. In native CDP mode, ref is treated as a CSS selector.", { ref: "string?", selector: "string?", element: "string?", button: "string?", doubleClick: "boolean?" }),
  tool("browser_type", "Type text into an element in the current CDP tab. In native CDP mode, ref is treated as a CSS selector.", { ref: "string?", selector: "string?", element: "string?", text: "string", slowly: "boolean?", submit: "boolean?" }),
  tool("browser_press_key", "Press a key in the current CDP tab.", { key: "string" }),
  tool("browser_wait_for", "Wait for text to appear, disappear, or a fixed duration.", { text: "string?", textGone: "string?", time: "number?" }),
  tool("browser_network_requests", "Return network requests seen on the current CDP tab since attachment.", { filename: "string?", includeStatic: "boolean?" }),
  tool("browser_run_code", "Run page-context JavaScript in the current CDP tab.", { code: "string" }),
  tool("browser_take_screenshot", "Capture a screenshot from the current CDP tab.", { type: "string?", filename: "string?", fullPage: "boolean?", ref: "string?", selector: "string?", element: "string?" })
];

function tool(name, description, shape) {
  const properties = {};
  const required = [];
  for (const [key, value] of Object.entries(shape)) {
    const optional = value.endsWith("?");
    const type = optional ? value.slice(0, -1) : value;
    properties[key] = { type };
    if (!optional) {
      required.push(key);
    }
  }
  return {
    name,
    description,
    inputSchema: {
      type: "object",
      properties,
      required,
      additionalProperties: true
    }
  };
}

class NativeCdpBackend {
  constructor(options = {}) {
    this._options = {
      cdpHost: options.cdpHost || DEFAULT_CDP_HOST,
      cdpPort: options.cdpPort ? Number(options.cdpPort) : undefined,
      outputDir: options.outputDir || process.cwd()
    };
    this._connection = new NativeCdpConnection(this._options);
    this._primaryTargetId = null;
    this._ownedTargets = new Set();
  }

  async initialize() {
    await this._connection.connect();
    await this.ensurePrimaryTarget();
  }

  async runtimeState() {
    const info = await this._connection.connectionInfo();
    return {
      browserName: "chrome",
      channel: "current-chrome-cdp",
      outputDir: this._options.outputDir,
      cdpHost: info.host,
      cdpPort: info.port,
      cdpEndpoint: info.browserWsUrl
    };
  }

  async ensurePrimaryTarget() {
    if (this._primaryTargetId) {
      const existing = await this._connection.getPageTarget(this._primaryTargetId);
      if (existing) {
        return this._primaryTargetId;
      }
    }
    const targetId = await this._connection.createTarget("about:blank");
    this._primaryTargetId = targetId;
    this._ownedTargets.add(targetId);
    await this._connection.ensureTargetReady(targetId);
    return targetId;
  }

  async listTools() {
    return TOOL_DEFS.map((item) => ({ ...item }));
  }

  async listPageTargets() {
    return this._connection.listPageTargets();
  }

  async getTarget(targetId) {
    return this._connection.getPageTarget(targetId);
  }

  async createWorkerTarget(url) {
    const targetId = await this._connection.createTarget(url || "about:blank");
    this._ownedTargets.add(targetId);
    await this._connection.ensureTargetReady(targetId);
    return targetId;
  }

  async closeTarget(targetId) {
    await this._connection.closeTarget(targetId);
    this._ownedTargets.delete(targetId);
    if (targetId === this._primaryTargetId) {
      this._primaryTargetId = null;
    }
  }

  async callTool(name, rawArguments) {
    try {
      const targetId = await this._resolveTargetId(rawArguments);
      switch (name) {
        case "browser_navigate":
          return await this._navigate(targetId, rawArguments);
        case "browser_snapshot":
          return await this._snapshot(targetId, rawArguments);
        case "browser_click":
          return await this._click(targetId, rawArguments);
        case "browser_type":
          return await this._type(targetId, rawArguments);
        case "browser_press_key":
          return await this._pressKey(targetId, rawArguments);
        case "browser_wait_for":
          return await this._waitFor(targetId, rawArguments);
        case "browser_network_requests":
          return await this._networkRequests(targetId, rawArguments);
        case "browser_run_code":
          return await this._runCode(targetId, rawArguments);
        case "browser_take_screenshot":
          return await this._takeScreenshot(targetId, rawArguments);
        default:
          return errorResponse(`Tool "${name}" not found`);
      }
    } catch (error) {
      return errorResponse(String(error && error.message ? error.message : error));
    }
  }

  async serverClosed() {
    const ownedTargets = [...this._ownedTargets];
    for (const targetId of ownedTargets) {
      await this._connection.closeTarget(targetId).catch(() => {});
    }
    this._ownedTargets.clear();
    await this._connection.close().catch(() => {});
  }

  async _resolveTargetId(rawArguments) {
    const meta = rawArguments && typeof rawArguments._meta === "object" ? rawArguments._meta : {};
    const requestedTargetId = meta.targetId || rawArguments.targetId;
    if (requestedTargetId) {
      const target = await this._connection.getPageTarget(String(requestedTargetId));
      if (!target) {
        throw new Error(`Target "${requestedTargetId}" not found`);
      }
      return String(requestedTargetId);
    }
    return this.ensurePrimaryTarget();
  }

  async _navigate(targetId, rawArguments) {
    const url = requiredString(rawArguments.url, "url");
    await this._connection.navigate(targetId, url);
    const page = await this._connection.pageSummary(targetId);
    const tabs = await this._connection.renderOpenTabs(targetId);
    return okResponse(renderSections([
      ["Navigation", `Navigated to ${page.url || url}`],
      ["Page", renderPageSummary(page)],
      ["Open tabs", fence("text", tabs)]
    ]));
  }

  async _snapshot(targetId, rawArguments) {
    const page = await this._connection.pageSummary(targetId);
    const tabs = await this._connection.renderOpenTabs(targetId);
    const snapshot = await this._connection.pageTextSnapshot(targetId, SNAPSHOT_TEXT_LIMIT);
    const filename = rawArguments.filename
      ? resolveOutputPath(this._options.outputDir, requiredString(rawArguments.filename, "filename"))
      : null;
    const text = renderSections([
      ["Page", renderPageSummary(page)],
      ["Open tabs", fence("text", tabs)],
      ["Snapshot", fence("text", snapshot || "(empty page text)")],
      filename ? ["Saved", filename] : null
    ]);
    if (filename) {
      await writeTextFile(filename, text);
    }
    return okResponse(text);
  }

  async _click(targetId, rawArguments) {
    const button = rawArguments.button ? String(rawArguments.button).toLowerCase() : "left";
    if (!["left", "main", "primary"].includes(button)) {
      throw new Error(`Unsupported button for native CDP click: ${rawArguments.button}`);
    }
    const selector = resolveSelector(rawArguments);
    const result = await this._connection.clickSelector(targetId, selector, {
      doubleClick: rawArguments.doubleClick === true
    });
    const page = await this._connection.pageSummary(targetId);
    return okResponse(renderSections([
      ["Click", renderValueBody(result)],
      ["Page", renderPageSummary(page)]
    ]));
  }

  async _type(targetId, rawArguments) {
    const selector = resolveSelector(rawArguments);
    const textValue = requiredString(rawArguments.text, "text");
    const result = await this._connection.typeIntoSelector(targetId, selector, textValue, {
      slowly: rawArguments.slowly === true,
      submit: rawArguments.submit === true
    });
    const page = await this._connection.pageSummary(targetId);
    return okResponse(renderSections([
      ["Type", renderValueBody(result)],
      ["Page", renderPageSummary(page)]
    ]));
  }

  async _pressKey(targetId, rawArguments) {
    const key = requiredString(rawArguments.key, "key");
    const result = await this._connection.pressKey(targetId, key);
    const page = await this._connection.pageSummary(targetId);
    return okResponse(renderSections([
      ["Key", renderValueBody(result)],
      ["Page", renderPageSummary(page)]
    ]));
  }

  async _waitFor(targetId, rawArguments) {
    if (!rawArguments.text && !rawArguments.textGone && rawArguments.time === undefined) {
      throw new Error("browser_wait_for requires text, textGone, or time");
    }
    const options = {};
    if (rawArguments.text !== undefined) options.text = String(rawArguments.text);
    if (rawArguments.textGone !== undefined) options.textGone = String(rawArguments.textGone);
    if (rawArguments.time !== undefined) {
      const seconds = Number(rawArguments.time);
      if (!Number.isFinite(seconds) || seconds < 0) {
        throw new Error(`Invalid wait time: ${rawArguments.time}`);
      }
      options.time = seconds;
    }
    const result = await this._connection.waitFor(targetId, options);
    const page = await this._connection.pageSummary(targetId);
    return okResponse(renderSections([
      ["Wait", renderValueBody(result)],
      ["Page", renderPageSummary(page)]
    ]));
  }

  async _networkRequests(targetId, rawArguments) {
    const requests = await this._connection.networkRequests(targetId, {
      includeStatic: rawArguments.includeStatic === true
    });
    const filename = rawArguments.filename
      ? resolveOutputPath(this._options.outputDir, requiredString(rawArguments.filename, "filename"))
      : null;
    const serialized = JSON.stringify(requests, null, 2);
    if (filename) {
      await writeTextFile(filename, serialized);
    }
    const preview = trimText(requests.length ? serialized : "[]", SNAPSHOT_TEXT_LIMIT);
    return okResponse(renderSections([
      ["Summary", `Captured ${requests.length} request(s)`],
      ["Requests", fence("json", preview)],
      filename ? ["Saved", filename] : null
    ]));
  }

  async _runCode(targetId, rawArguments) {
    const code = requiredString(rawArguments.code, "code");
    const result = await this._connection.runUserCode(targetId, code);
    const page = await this._connection.pageSummary(targetId);
    return okResponse(renderSections([
      ["Result", renderValueBody(result)],
      ["Page", renderPageSummary(page)]
    ]));
  }

  async _takeScreenshot(targetId, rawArguments) {
    const selector = rawArguments.selector || rawArguments.ref || rawArguments.element || undefined;
    const filename = rawArguments.filename
      ? resolveOutputPath(this._options.outputDir, requiredString(rawArguments.filename, "filename"))
      : null;
    const result = await this._connection.captureScreenshot(targetId, {
      format: normalizeScreenshotFormat(rawArguments.type),
      fullPage: rawArguments.fullPage === true,
      selector: selector ? String(selector) : undefined,
      filename
    });
    return okResponse(renderSections([
      ["Screenshot", renderValueBody(result)],
      filename ? ["Saved", filename] : null
    ]));
  }
}

class NativeCdpTabWorkerManager {
  constructor(backend) {
    this._backend = backend;
    this._workers = new Map();
    this._nextWorkerNumber = 1;
  }

  async listWorkers() {
    const workers = [];
    for (const worker of this._workers.values()) {
      workers.push(await this._describeWorker(worker));
    }
    return workers;
  }

  async openWorker(options = {}) {
    const source = options.tabIndex !== undefined ? "bound" : "created";
    let targetId;
    if (options.tabIndex !== undefined) {
      const pages = await this._backend.listPageTargets();
      const target = pages[options.tabIndex];
      if (!target) {
        throw new Error(`Tab ${options.tabIndex} not found`);
      }
      targetId = target.targetId;
    } else {
      targetId = await this._backend.createWorkerTarget(options.url || "about:blank");
    }

    const workerId = options.workerId ? String(options.workerId) : this._allocateWorkerId();
    if (this._workers.has(workerId)) {
      throw new Error(`Tab worker "${workerId}" already exists`);
    }

    const worker = { id: workerId, targetId, source, createdAt: new Date().toISOString() };
    this._workers.set(workerId, worker);

    let navigation;
    if (options.url && source === "bound") {
      navigation = await this.callWorker(workerId, "browser_navigate", { url: options.url });
    }

    return {
      worker: await this._describeWorker(worker),
      navigation: navigation ? { text: navigation.content?.[0]?.text || "" } : undefined
    };
  }

  async closeWorker(workerId, options = {}) {
    const worker = this._workers.get(workerId);
    if (!worker) {
      throw new Error(`Tab worker "${workerId}" not found`);
    }
    this._workers.delete(workerId);
    const closeTab = options.closeTab === true || (options.closeTab !== false && worker.source === "created");
    if (closeTab) {
      await this._backend.closeTarget(worker.targetId).catch(() => {});
    }
    return { workerId, closeTab, pageClosed: closeTab };
  }

  async callWorker(workerId, name, rawArguments) {
    const worker = this._workers.get(workerId);
    if (!worker) {
      throw new Error(`Tab worker "${workerId}" not found`);
    }
    const nextArguments = { ...(rawArguments || {}) };
    const meta = nextArguments._meta && typeof nextArguments._meta === "object" ? { ...nextArguments._meta } : {};
    meta.targetId = worker.targetId;
    nextArguments._meta = meta;
    return this._backend.callTool(name, nextArguments);
  }

  async serverClosed() {
    this._workers.clear();
  }

  _allocateWorkerId() {
    while (this._workers.has(`tab-${this._nextWorkerNumber}`)) {
      this._nextWorkerNumber += 1;
    }
    return `tab-${this._nextWorkerNumber++}`;
  }

  async _describeWorker(worker) {
    const target = await this._backend.getTarget(worker.targetId);
    return {
      id: worker.id,
      source: worker.source,
      createdAt: worker.createdAt,
      open: Boolean(target),
      tabIndex: await this._tabIndex(worker.targetId),
      url: target?.url || "",
      title: target?.title || ""
    };
  }

  async _tabIndex(targetId) {
    const pages = await this._backend.listPageTargets();
    return pages.findIndex((page) => page.targetId === targetId);
  }
}

class NativeCdpConnection {
  constructor(options = {}) {
    this._host = options.cdpHost || DEFAULT_CDP_HOST;
    this._requestedPort = options.cdpPort ? Number(options.cdpPort) : undefined;
    this._ws = null;
    this._browserWsUrl = null;
    this._browserPort = null;
    this._nextId = 0;
    this._pending = new Map();
    this._sessionByTarget = new Map();
    this._targetBySession = new Map();
    this._networkByTarget = new Map();
    this._initializedSessions = new Set();
  }

  async connect() {
    if (this._ws && this._ws.readyState === 1) {
      return;
    }
    const endpoint = await discoverBrowserWsEndpoint(this._host, this._requestedPort);
    this._browserWsUrl = endpoint.browserWsUrl;
    this._browserPort = endpoint.port;
    this._ws = new WebSocket(endpoint.browserWsUrl);
    await new Promise((resolve, reject) => {
      const rejectConnection = (detail) => reject(new Error(formatChromeConnectionError(endpoint.browserWsUrl, detail)));
      const timer = setTimeout(() => rejectConnection("Timed out connecting to Chrome CDP endpoint"), 5000);
      this._ws.addEventListener("open", () => {
        clearTimeout(timer);
        resolve();
      }, { once: true });
      this._ws.addEventListener("error", (event) => {
        clearTimeout(timer);
        rejectConnection(event.message || "Received network error or non-101 status code");
      }, { once: true });
    });
    this._ws.addEventListener("message", (event) => this._handleMessage(event.data));
    this._ws.addEventListener("close", () => {
      for (const pending of this._pending.values()) {
        clearTimeout(pending.timer);
        pending.reject(new Error("Chrome CDP connection closed"));
      }
      this._pending.clear();
    });
  }

  async close() {
    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }
  }

  async connectionInfo() {
    await this.connect();
    return {
      host: this._host,
      port: this._browserPort,
      browserWsUrl: this._browserWsUrl
    };
  }

  async listPageTargets() {
    const response = await this.send("Target.getTargets");
    return (response.result?.targetInfos || [])
      .filter((target) => target.type === "page")
      .filter((target) => !String(target.url || "").startsWith("chrome-extension://"))
      .map((target) => ({
        targetId: target.targetId,
        title: target.title || "",
        url: target.url || "",
        attached: Boolean(target.attached)
      }));
  }

  async getPageTarget(targetId) {
    const pages = await this.listPageTargets();
    return pages.find((page) => page.targetId === targetId) || null;
  }

  async createTarget(url) {
    const response = await this.send("Target.createTarget", { url, background: true });
    return response.result.targetId;
  }

  async closeTarget(targetId) {
    await this.send("Target.closeTarget", { targetId });
    this._sessionByTarget.delete(targetId);
    this._networkByTarget.delete(targetId);
  }

  async ensureTargetReady(targetId) {
    await this.ensureSession(targetId);
    await this.waitForLoad(targetId);
  }

  async ensureSession(targetId) {
    const existing = this._sessionByTarget.get(targetId);
    if (existing) {
      return existing;
    }
    const response = await this.send("Target.attachToTarget", { targetId, flatten: true });
    const sessionId = response.result?.sessionId;
    if (!sessionId) {
      throw new Error(`Failed to attach to target ${targetId}`);
    }
    this._sessionByTarget.set(targetId, sessionId);
    this._targetBySession.set(sessionId, targetId);
    await this._initializeSession(sessionId, targetId);
    return sessionId;
  }

  async pageSummary(targetId) {
    const json = await this.evaluateValue(targetId, `JSON.stringify({ title: document.title, url: location.href, readyState: document.readyState })`);
    return json ? JSON.parse(json) : {};
  }

  async pageTextSnapshot(targetId, limit) {
    const text = await this.evaluateValue(targetId, `(() => document.body ? (document.body.innerText || document.body.textContent || "") : "")()`);
    return trimText(String(text || "").trim(), limit);
  }

  async renderOpenTabs(currentTargetId) {
    const pages = await this.listPageTargets();
    if (!pages.length) {
      return "(no page targets)";
    }
    return pages.map((page, index) => {
      const marker = page.targetId === currentTargetId ? "*" : "-";
      return `${marker} [${index}] ${page.title || "(untitled)"} - ${page.url || "about:blank"}`;
    }).join("\n");
  }

  async navigate(targetId, url) {
    const sessionId = await this.ensureSession(targetId);
    await this.send("Page.navigate", { url }, sessionId);
    await this.waitForLoad(targetId);
  }

  async clickSelector(targetId, selector, options = {}) {
    return this._evaluateStructured(targetId, `(() => {
      const selector = ${JSON.stringify(selector)};
      const element = document.querySelector(selector);
      if (!element) throw new Error("Element not found: " + selector);
      element.scrollIntoView({ block: "center", inline: "center" });
      element.click();
      if (${options.doubleClick ? "true" : "false"}) element.click();
      return { selector, tagName: element.tagName, text: (element.innerText || element.textContent || "").trim().slice(0, 200) };
    })()`);
  }

  async typeIntoSelector(targetId, selector, textValue, options = {}) {
    return this._evaluateStructured(targetId, `(() => {
      const selector = ${JSON.stringify(selector)};
      const text = ${JSON.stringify(textValue)};
      const element = document.querySelector(selector);
      if (!element) throw new Error("Element not found: " + selector);
      element.scrollIntoView({ block: "center", inline: "center" });
      element.focus();
      const tag = element.tagName.toLowerCase();
      if (tag === "input" || tag === "textarea") {
        element.value = text;
        element.dispatchEvent(new Event("input", { bubbles: true }));
        element.dispatchEvent(new Event("change", { bubbles: true }));
      } else if (element.isContentEditable) {
        element.textContent = text;
        element.dispatchEvent(new Event("input", { bubbles: true }));
      } else {
        throw new Error("Element is not editable");
      }
      if (${options.submit ? "true" : "false"}) {
        const form = element.form || element.closest("form");
        if (form && typeof form.requestSubmit === "function") form.requestSubmit();
      }
      return { selector, length: text.length, submit: ${options.submit ? "true" : "false"} };
    })()`);
  }

  async pressKey(targetId, key) {
    return this._evaluateStructured(targetId, `(() => {
      const key = ${JSON.stringify(key)};
      const active = document.activeElement || document.body;
      const init = { key, code: key, bubbles: true, cancelable: true };
      active.dispatchEvent(new KeyboardEvent("keydown", init));
      if (key.length === 1 && "value" in active && typeof active.value === "string") {
        const start = typeof active.selectionStart === "number" ? active.selectionStart : active.value.length;
        const end = typeof active.selectionEnd === "number" ? active.selectionEnd : active.value.length;
        active.value = active.value.slice(0, start) + key + active.value.slice(end);
        active.dispatchEvent(new Event("input", { bubbles: true }));
      } else if (key === "Enter") {
        const form = active.form || active.closest?.("form");
        if (form && typeof form.requestSubmit === "function") form.requestSubmit();
      }
      active.dispatchEvent(new KeyboardEvent("keyup", init));
      return { key };
    })()`);
  }

  async waitFor(targetId, options = {}) {
    if (options.time !== undefined) {
      await sleep(Math.max(0, Number(options.time)) * 1000);
      return { waitedSeconds: Math.max(0, Number(options.time)) };
    }
    const deadline = Date.now() + 30000;
    while (Date.now() < deadline) {
      const bodyText = String(await this.evaluateValue(targetId, `(() => document.body ? (document.body.innerText || document.body.textContent || "") : "")()`));
      if (options.text && bodyText.includes(String(options.text))) return { matchedText: String(options.text) };
      if (options.textGone && !bodyText.includes(String(options.textGone))) return { textGone: String(options.textGone) };
      await sleep(250);
    }
    throw new Error("Timed out waiting for requested text state");
  }

  async networkRequests(targetId, options = {}) {
    await this.ensureSession(targetId);
    const requests = this._networkByTarget.get(targetId) || [];
    if (options.includeStatic) {
      return requests;
    }
    return requests.filter((item) => !STATIC_RESOURCE_TYPES.has(item.resourceType));
  }

  async runUserCode(targetId, code) {
    return this._evaluateStructured(targetId, `(async () => {
      const page = {
        title: async () => document.title,
        url: () => location.href,
        text: async () => document.body ? (document.body.innerText || document.body.textContent || "") : "",
        html: async () => document.documentElement.outerHTML,
        click: async (selector) => {
          const element = document.querySelector(selector);
          if (!element) throw new Error("Element not found: " + selector);
          element.click();
          return true;
        }
      };
      const userValue = (${code});
      if (typeof userValue === "function") return await userValue(page);
      return await userValue;
    })()`);
  }

  async captureScreenshot(targetId, options = {}) {
    const sessionId = await this.ensureSession(targetId);
    let clip = undefined;
    if (options.selector) {
      clip = await this._evaluateStructured(targetId, `(() => {
        const selector = ${JSON.stringify(options.selector)};
        const element = document.querySelector(selector);
        if (!element) throw new Error("Element not found: " + selector);
        element.scrollIntoView({ block: "center", inline: "center" });
        const rect = element.getBoundingClientRect();
        return { x: rect.x, y: rect.y, width: rect.width, height: rect.height, scale: 1 };
      })()`);
    }
    const response = await this.send("Page.captureScreenshot", {
      format: options.format || "png",
      captureBeyondViewport: Boolean(options.fullPage),
      clip
    }, sessionId);
    const base64 = response.result?.data;
    if (!base64) {
      throw new Error("Screenshot did not return image data");
    }
    if (options.filename) {
      await fs.promises.mkdir(path.dirname(options.filename), { recursive: true });
      await fs.promises.writeFile(options.filename, Buffer.from(base64, "base64"));
    }
    return { filename: options.filename || null, format: options.format || "png", bytes: Buffer.byteLength(base64, "base64") };
  }

  async waitForLoad(targetId) {
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline) {
      const readyState = await this.evaluateValue(targetId, "document.readyState");
      if (readyState === "complete" || readyState === "interactive") {
        return readyState;
      }
      await sleep(200);
    }
    return "timeout";
  }

  async evaluateValue(targetId, expression) {
    const sessionId = await this.ensureSession(targetId);
    const response = await this.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true
    }, sessionId);
    if (response.result?.exceptionDetails) {
      throw new Error(response.result.exceptionDetails.text || "Runtime evaluation failed");
    }
    return response.result?.result?.value;
  }

  async _evaluateStructured(targetId, expression) {
    return this.evaluateValue(targetId, expression);
  }

  async send(method, params = {}, sessionId = null) {
    await this.connect();
    if (!this._ws || this._ws.readyState !== 1) {
      throw new Error("Chrome CDP WebSocket is not connected");
    }
    const id = ++this._nextId;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this._pending.delete(id);
        reject(new Error(`CDP command timed out: ${method}`));
      }, 30000);
      this._pending.set(id, { resolve, reject, timer });
      this._ws.send(JSON.stringify(payload));
    });
  }

  async _initializeSession(sessionId, targetId) {
    if (this._initializedSessions.has(sessionId)) return;
    await this.send("Page.enable", {}, sessionId);
    await this.send("Runtime.enable", {}, sessionId);
    await this.send("DOM.enable", {}, sessionId);
    await this.send("Network.enable", {}, sessionId).catch(() => {});
    this._initializedSessions.add(sessionId);
    if (!this._networkByTarget.has(targetId)) this._networkByTarget.set(targetId, []);
  }

  _handleMessage(raw) {
    const text = typeof raw === "string" ? raw : Buffer.from(raw).toString("utf8");
    let message;
    try {
      message = JSON.parse(text);
    } catch (_) {
      return;
    }
    if (message.id && this._pending.has(message.id)) {
      const pending = this._pending.get(message.id);
      clearTimeout(pending.timer);
      this._pending.delete(message.id);
      pending.resolve(message);
      return;
    }
    if (message.method === "Target.attachedToTarget") {
      const targetId = message.params?.targetInfo?.targetId;
      const sessionId = message.params?.sessionId;
      if (targetId && sessionId) {
        this._sessionByTarget.set(targetId, sessionId);
        this._targetBySession.set(sessionId, targetId);
      }
      return;
    }
    if (message.method === "Target.detachedFromTarget") {
      const sessionId = message.params?.sessionId;
      const targetId = this._targetBySession.get(sessionId);
      if (targetId) {
        this._targetBySession.delete(sessionId);
        this._sessionByTarget.delete(targetId);
      }
      return;
    }
    if (message.method === "Network.requestWillBeSent") {
      const targetId = this._targetBySession.get(message.sessionId);
      if (!targetId) return;
      const list = this._networkByTarget.get(targetId) || [];
      list.push({
        url: message.params?.request?.url || "",
        method: message.params?.request?.method || "",
        resourceType: message.params?.type || "",
        documentURL: message.params?.documentURL || "",
        timestamp: message.params?.timestamp || null
      });
      this._networkByTarget.set(targetId, list.slice(-500));
    }
  }
}

async function probeCurrentChrome(options = {}) {
  const endpoint = await discoverBrowserWsEndpoint(options.cdpHost || DEFAULT_CDP_HOST, options.cdpPort);
  let pageCount = 0;
  const connection = new NativeCdpConnection({
    cdpHost: endpoint.host,
    cdpPort: endpoint.port
  });
  try {
    await connection.connect();
    const response = await connection.send("Target.getTargets");
    const targets = Array.isArray(response.result?.targetInfos) ? response.result.targetInfos : [];
    pageCount = targets.filter((target) => target.type === "page").length;
  } finally {
    await connection.close().catch(() => {});
  }
  return {
    ...endpoint,
    pageCount
  };
}

async function discoverBrowserWsEndpoint(host, requestedPort) {
  const activePortInfo = await readDevToolsActivePort(host);
  if (activePortInfo?.browserWsUrl) {
    return {
      host,
      port: activePortInfo.port,
      browserWsUrl: activePortInfo.browserWsUrl
    };
  }
  const ports = uniquePorts([requestedPort, activePortInfo?.port, ...COMMON_CDP_PORTS]);
  let lastError = null;
  for (const port of ports) {
    try {
      const info = await readJson(`http://${host}:${port}/json/version`);
      if (info && info.webSocketDebuggerUrl) {
        return { host, port, browserWsUrl: info.webSocketDebuggerUrl };
      }
    } catch (error) {
      lastError = error;
    }
  }
  const detail = lastError ? ` Last error: ${lastError.message}` : "";
  throw new Error(`Unable to discover a Chrome CDP endpoint on ${host}. Make sure the current Chrome has remote debugging enabled.${detail}`);
}

async function readDevToolsActivePort(host) {
  if (host !== "127.0.0.1" && host !== "localhost") return undefined;
  const localAppData = process.env.LOCALAPPDATA || "";
  const home = os.homedir();
  const candidates = process.platform === "win32"
    ? [
        path.join(localAppData, "Google", "Chrome", "User Data", "DevToolsActivePort"),
        path.join(localAppData, "Chromium", "User Data", "DevToolsActivePort")
      ]
    : process.platform === "darwin"
      ? [
          path.join(home, "Library", "Application Support", "Google", "Chrome", "DevToolsActivePort"),
          path.join(home, "Library", "Application Support", "Chromium", "DevToolsActivePort")
        ]
      : [
          path.join(home, ".config", "google-chrome", "DevToolsActivePort"),
          path.join(home, ".config", "chromium", "DevToolsActivePort")
        ];
  for (const filePath of candidates) {
    try {
      const text = await fs.promises.readFile(filePath, "utf8");
      const lines = String(text).trim().split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
      const port = Number(lines[0]);
      if (Number.isInteger(port) && port > 0 && await canConnectTcp(host, port)) {
        const browserWsPath = lines[1];
        return {
          port,
          browserWsUrl: browserWsPath
            ? `ws://${host}:${port}${browserWsPath.startsWith("/") ? browserWsPath : `/${browserWsPath}`}`
            : undefined
        };
      }
    } catch (_) {}
  }
  return undefined;
}

function canConnectTcp(host, port) {
  return new Promise((resolve) => {
    const socket = net.createConnection(port, host);
    const timer = setTimeout(() => {
      socket.destroy();
      resolve(false);
    }, 1500);
    socket.once("connect", () => {
      clearTimeout(timer);
      socket.destroy();
      resolve(true);
    });
    socket.once("error", () => {
      clearTimeout(timer);
      resolve(false);
    });
  });
}

function readJson(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout: 2000 }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        try {
          resolve(JSON.parse(Buffer.concat(chunks).toString("utf8")));
        } catch (error) {
          reject(error);
        }
      });
    });
    req.on("timeout", () => req.destroy(new Error("Request timed out")));
    req.on("error", reject);
  });
}

function uniquePorts(values) {
  const seen = new Set();
  const result = [];
  for (const value of values) {
    const port = Number(value);
    if (!Number.isInteger(port) || port <= 0 || seen.has(port)) continue;
    seen.add(port);
    result.push(port);
  }
  return result;
}

function normalizeScreenshotFormat(value) {
  const format = value ? String(value).toLowerCase() : "png";
  if (!["png", "jpeg"].includes(format)) throw new Error(`Unsupported screenshot format: ${value}`);
  return format;
}

function requiredString(value, label) {
  if (value === undefined || value === null || value === "") throw new Error(`Missing ${label}`);
  return String(value);
}

function resolveSelector(rawArguments) {
  return requiredString(rawArguments.selector || rawArguments.ref || rawArguments.element, "selector/ref");
}

function resolveOutputPath(baseDir, targetPath) {
  return path.isAbsolute(targetPath) ? targetPath : path.resolve(baseDir, targetPath);
}

async function writeTextFile(filePath, text) {
  await fs.promises.mkdir(path.dirname(filePath), { recursive: true });
  await fs.promises.writeFile(filePath, text, "utf8");
}

function renderPageSummary(page) {
  return [
    `- URL: ${page.url || "about:blank"}`,
    `- Title: ${page.title || "(untitled)"}`,
    `- Ready state: ${page.readyState || "unknown"}`
  ].join("\n");
}

function renderSections(sections) {
  return sections
    .filter((entry) => Array.isArray(entry) && entry.length >= 2)
    .filter(([, body]) => body !== undefined && body !== null && String(body).trim() !== "")
    .map(([title, body]) => `### ${title}\n${String(body).trimEnd()}`)
    .join("\n\n");
}

function fence(language, body) {
  return `\`\`\`${language}\n${body}\n\`\`\``;
}

function renderValueBody(value) {
  if (typeof value === "string") {
    return value.includes("\n") ? fence("text", value) : value;
  }
  if (value === undefined) {
    return "(undefined)";
  }
  return fence("json", JSON.stringify(value, null, 2));
}

function okResponse(text) {
  return { content: [{ type: "text", text }], isError: false };
}

function errorResponse(message) {
  return { content: [{ type: "text", text: renderSections([["Error", message]]) }], isError: true };
}

function trimText(text, limit) {
  if (text.length <= limit) return text;
  return `${text.slice(0, limit)}\n\n[truncated ${text.length - limit} chars]`;
}

function formatChromeConnectionError(browserWsUrl, detail) {
  const summary = String(detail || "Failed to connect to Chrome CDP endpoint").trim();
  return `${summary}. Endpoint: ${browserWsUrl}. Chrome may be waiting for a remote debugging approval prompt, or you may need to reuse an existing approved browser-cli daemon.`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

module.exports = {
  NativeCdpBackend,
  NativeCdpTabWorkerManager,
  probeCurrentChrome
};
