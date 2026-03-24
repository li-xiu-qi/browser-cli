#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const http = require("http");
const net = require("net");
const { spawn } = require("child_process");

const fsp = fs.promises;
const {
  NativeCdpBackend,
  NativeCdpTabWorkerManager,
  probeCurrentChrome
} = require("./native-cdp-backend");

const SOURCE_DIR = __dirname;
const PROJECT_DIR = path.resolve(SOURCE_DIR, "..");
const RUNTIME_DIR = path.join(PROJECT_DIR, ".runtime");
const OUTPUT_DIR = path.join(RUNTIME_DIR, "output");
const LOG_DIR = path.join(RUNTIME_DIR, "logs");
const STATE_FILE = path.join(RUNTIME_DIR, "server.json");

const DEFAULT_HOST = "127.0.0.1";
const DEFAULT_PORT = 54000;
const DEFAULT_START_TIMEOUT_MS = 30000;
const DEFAULT_REQUEST_TIMEOUT_MS = 40000;
const DEFAULT_HEALTH_TIMEOUT_MS = 3000;

const BOOLEAN_FLAGS = new Set([
  "json-output",
  "raw",
  "include-static",
  "slowly",
  "submit",
  "double-click",
  "full-page",
  "close-tab"
]);

const TOOL_ALIASES = {
  navigate: "browser_navigate",
  snapshot: "browser_snapshot",
  click: "browser_click",
  type: "browser_type",
  "press-key": "browser_press_key",
  "wait-for": "browser_wait_for",
  "network-requests": "browser_network_requests",
  "run-code": "browser_run_code",
  screenshot: "browser_take_screenshot"
};

async function main() {
  const argv = process.argv.slice(2);
  const command = argv.shift() || "help";

  switch (command) {
    case "help":
      printHelp();
      return;
    case "doctor":
      await runDoctor(argv);
      return;
    case "serve":
      await runServe(argv);
      return;
    case "start":
      await runStart(argv);
      return;
    default:
      break;
  }

  const parsed = parseArgs(argv);

  switch (command) {
    case "status":
      await runStatus(parsed.flags);
      return;
    case "stop":
      await runStop(parsed.flags);
      return;
    case "tools":
      await runTools(parsed.flags);
      return;
    case "tab-workers":
      await runTabWorkers(parsed.flags);
      return;
    case "tab-open":
      await runTabOpen(parsed, parsed.flags);
      return;
    case "tab-open-batch":
      await runTabOpenBatch(parsed, parsed.flags);
      return;
    case "tab-close":
      await runTabClose(parsed, parsed.flags);
      return;
    case "call":
      await runCall(parsed, parsed.flags);
      return;
    case "call-workers":
      await runCallWorkers(parsed, parsed.flags);
      return;
    case "call-batch":
      await runCallBatch(parsed, parsed.flags);
      return;
    default:
      if (command.startsWith("browser_")) {
        parsed.positionals.unshift(command);
        await runCall(parsed, parsed.flags);
        return;
      }
      if (TOOL_ALIASES[command]) {
        await runAlias(command, parsed);
        return;
      }
      throw new Error(`Unknown command: ${command}`);
  }
}

function parseArgs(argv) {
  const flags = Object.create(null);
  const positionals = [];
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--") || token === "--") {
      positionals.push(token);
      continue;
    }
    const equalsIndex = token.indexOf("=");
    const name = token.slice(2, equalsIndex === -1 ? undefined : equalsIndex);
    if (!name) {
      throw new Error(`Invalid flag: ${token}`);
    }
    if (equalsIndex !== -1) {
      addFlag(flags, name, token.slice(equalsIndex + 1));
      continue;
    }
    if (BOOLEAN_FLAGS.has(name)) {
      addFlag(flags, name, true);
      continue;
    }
    if (i + 1 >= argv.length) {
      throw new Error(`Missing value for --${name}`);
    }
    i += 1;
    addFlag(flags, name, argv[i]);
  }
  return { flags, positionals };
}

function addFlag(flags, name, value) {
  if (flags[name] === undefined) {
    flags[name] = value;
  } else if (Array.isArray(flags[name])) {
    flags[name].push(value);
  } else {
    flags[name] = [flags[name], value];
  }
}

function getSingleFlag(flags, name) {
  const value = flags[name];
  return Array.isArray(value) ? value[value.length - 1] : value;
}

function flagEnabled(flags, name) {
  return Boolean(getSingleFlag(flags, name));
}

function printHelp() {
  console.log(`browser-cli usage

  browser-cli.cmd start [--port 54000] [--host 127.0.0.1] [--cdp-host 127.0.0.1] [--cdp-port 9222]
  browser-cli.cmd doctor [--cdp-host 127.0.0.1] [--cdp-port 9222]
  browser-cli.cmd serve [--port 54000] [--host 127.0.0.1] [--cdp-host 127.0.0.1] [--cdp-port 9222]
  browser-cli.cmd status
  browser-cli.cmd stop
  browser-cli.cmd tools [--json-output]
  browser-cli.cmd tab-workers [--json-output]
  browser-cli.cmd tab-open [--tab 0] [--url https://example.com] [--id tab-gemini-1]
  browser-cli.cmd tab-open-batch [count] [--prefix gemini] [--url https://example.com]
  browser-cli.cmd tab-close <worker-id> [--close-tab]
  browser-cli.cmd call <tool-name> [--json "{...}"] [--file args.json]
  browser-cli.cmd call <tool-name> --worker <worker-id> [--json "{...}"] [--file args.json]
  browser-cli.cmd call-workers <tool-name> [worker-id...] [--workers tab-1,tab-2] [--json "{...}"] [--file args.json]
  browser-cli.cmd call-batch --file batch.json

high-frequency aliases

  browser-cli.cmd navigate [--worker <worker-id>] <url>
  browser-cli.cmd snapshot [--worker <worker-id>]
  browser-cli.cmd click [--worker <worker-id>] --json "{...}"
  browser-cli.cmd type [--worker <worker-id>] --json "{...}"
  browser-cli.cmd press-key [--worker <worker-id>] <key>
  browser-cli.cmd wait-for [--worker <worker-id>] --text "Done"
  browser-cli.cmd network-requests [--worker <worker-id>] [--include-static]
  browser-cli.cmd run-code [--worker <worker-id>] --code "async (page) => await page.title()"
  browser-cli.cmd screenshot [--worker <worker-id>] --json "{...}"

examples

  browser-cli.cmd doctor
  browser-cli.cmd start
  browser-cli.cmd tab-open --url https://example.com
  browser-cli.cmd tab-open-batch 4 --prefix gemini --url https://example.com
  browser-cli.cmd call browser_navigate --json "{\\"url\\":\\"https://example.com\\"}"
  browser-cli.cmd snapshot
  browser-cli.cmd run-code --code "async (page) => ({ title: await page.title() })"

tip

  browser-cli now talks to the current Chrome through native CDP instead of Playwright MCP
  enable remote debugging in the current Chrome before running start or doctor
  use tab-open to create a worker-bound tab, then add --worker <id> to normal tool calls
`);
}

async function runStart(rawArgv) {
  const startup = resolveDaemonOptions(rawArgv);
  const info = await ensureServerRunning(startup, {
    quiet: false,
    waitTimeoutMs: DEFAULT_START_TIMEOUT_MS
  });
  if (flagEnabled(startup.flags, "json-output")) {
    console.log(JSON.stringify(info, null, 2));
    return;
  }
  const alreadyRunning = info.mode === "existing";
  const prefix = alreadyRunning ? "[browser-cli] already running" : "[browser-cli] started";
  console.log(`${prefix} on http://${info.host}:${info.port}`);
  console.log(`[browser-cli] pid: ${info.pid}`);
  console.log(`[browser-cli] mode: ${info.modeLabel}`);
  console.log(`[browser-cli] session: ${info.sessionModel}`);
  console.log(`[browser-cli] cdp: ${info.cdpHost}:${info.cdpPort}`);
  console.log(`[browser-cli] output: ${toProjectRelative(info.outputDir)}`);
  if (!alreadyRunning) {
    console.log(`[browser-cli] logs: ${toProjectRelative(path.join(LOG_DIR, "server.out.log"))}`);
  }
}

async function runDoctor(rawArgv) {
  const startup = resolveDaemonOptions(rawArgv);
  const status = await inspectServer(startup.flags).catch(() => ({ running: false, state: null }));
  let report;
  try {
    if (status.running && status.state?.modeKey === "current-browser-cdp") {
      report = {
        ok: true,
        daemon: {
          host: status.state.host,
          port: status.state.port,
          running: true,
          statePath: toProjectRelative(STATE_FILE)
        },
        chrome: {
          cdpHost: status.state.cdpHost,
          cdpPort: status.state.cdpPort,
          cdpEndpoint: status.state.cdpEndpoint || null,
          pageCount: null,
          source: "existing-daemon"
        },
        mode: {
          key: "current-browser-cdp",
          label: "current Chrome via native CDP",
          sessionModel: "shared browser state in the current Chrome instance"
        },
        notes: [
          "The existing browser-cli daemon is already attached to the current Chrome session.",
          "Reusing that daemon avoids opening a second direct CDP attachment that may wait on a Chrome approval prompt.",
          "Use status, tab-open, and snapshot against the same daemon for the lowest-friction workflow."
        ]
      };
    } else {
      const chrome = await probeCurrentChrome(startup.cliOptions);
      report = {
        ok: true,
        daemon: {
          host: startup.host,
          port: startup.port,
          running: Boolean(status.running),
          statePath: toProjectRelative(STATE_FILE)
        },
        chrome: {
          cdpHost: chrome.host,
          cdpPort: chrome.port,
          cdpEndpoint: chrome.browserWsUrl,
          pageCount: chrome.pageCount,
          source: "direct-probe"
        },
        mode: {
          key: "current-browser-cdp",
          label: "current Chrome via native CDP",
          sessionModel: "shared browser state in the current Chrome instance"
        },
        notes: [
          "This mode reuses the current Chrome through the browser's native CDP endpoint.",
          "Expect shared-browser contention on tabs, focus, navigation, screenshots, and login state.",
          "Enable remote debugging in the current Chrome before running start."
        ]
      };
    }
  } catch (error) {
    report = {
      ok: false,
      daemon: {
        host: status.state?.host || startup.host,
        port: status.state?.port || startup.port,
        running: Boolean(status.running),
        statePath: toProjectRelative(STATE_FILE)
      },
      chrome: {
        cdpHost: startup.cliOptions.cdpHost,
        cdpPort: startup.cliOptions.cdpPort || null,
        cdpEndpoint: null,
        pageCount: 0,
        source: "direct-probe"
      },
      mode: {
        key: "current-browser-cdp",
        label: "current Chrome via native CDP",
        sessionModel: "shared browser state in the current Chrome instance"
      },
      error: String(error && error.message ? error.message : error)
    };
  }

  if (flagEnabled(startup.flags, "json-output")) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    console.log("[browser-cli] doctor");
    console.log(`[browser-cli] mode: ${report.mode.label}`);
    console.log(`[browser-cli] session: ${report.mode.sessionModel}`);
    console.log(`[browser-cli] daemon target: http://${report.daemon.host}:${report.daemon.port}`);
    console.log(`[browser-cli] chrome cdp host: ${report.chrome.cdpHost}`);
    console.log(`[browser-cli] chrome cdp port: ${report.chrome.cdpPort ?? "(auto-discover)"}`);
    if (report.ok) {
      console.log(`[browser-cli] chrome cdp endpoint: ${report.chrome.cdpEndpoint}`);
      if (report.chrome.pageCount === null) {
        console.log("[browser-cli] visible page targets: (reusing existing daemon)");
      } else {
        console.log(`[browser-cli] visible page targets: ${report.chrome.pageCount}`);
      }
      console.log(`[browser-cli] daemon already running: ${report.daemon.running}`);
      if (report.notes) {
        console.log("[browser-cli] notes:");
        for (const note of report.notes) {
          console.log(`- ${note}`);
        }
      }
    } else {
      console.log(`[browser-cli] error: ${report.error}`);
      process.exitCode = 1;
    }
  }
}

async function runStatus(flags) {
  const status = await inspectServer(flags);
  if (flagEnabled(flags, "json-output")) {
    console.log(JSON.stringify(status, null, 2));
    process.exitCode = status.running ? 0 : 1;
    return;
  }
  if (!status.state) {
    console.log("[browser-cli] not running");
    process.exitCode = 1;
    return;
  }
  if (!status.running) {
    console.log("[browser-cli] state file exists but daemon is not responding");
    console.log(`[browser-cli] expected pid: ${status.state.pid}`);
    console.log(`[browser-cli] expected url: http://${status.state.host}:${status.state.port}`);
    console.log(`[browser-cli] logs: ${toProjectRelative(path.join(LOG_DIR, "server.err.log"))}`);
    process.exitCode = 1;
    return;
  }
  const state = status.state;
  console.log("[browser-cli] running");
  console.log(`[browser-cli] url: http://${state.host}:${state.port}`);
  console.log(`[browser-cli] pid: ${state.pid}`);
  console.log(`[browser-cli] started: ${state.startedAt}`);
  console.log(`[browser-cli] browser: ${state.browserName}${state.channel ? ` (${state.channel})` : ""}`);
  console.log(`[browser-cli] mode: ${state.modeLabel}`);
  console.log(`[browser-cli] session: ${state.sessionModel}`);
  console.log(`[browser-cli] cdp: ${state.cdpHost}:${state.cdpPort}`);
  console.log(`[browser-cli] output: ${toProjectRelative(state.outputDir)}`);
}

async function runStop(flags) {
  const status = await inspectServer(flags);
  if (!status.state) {
    console.log("[browser-cli] not running");
    return;
  }
  if (status.running) {
    await requestJson(status.state, "POST", "/shutdown", {});
    await waitForServerDown(status.state, 10000);
  } else if (status.state.pid) {
    try {
      process.kill(status.state.pid);
    } catch (error) {
      if (error.code !== "ESRCH") {
        throw error;
      }
    }
  }
  await safeUnlink(STATE_FILE);
  if (flagEnabled(flags, "json-output")) {
    console.log(JSON.stringify({ stopped: true }, null, 2));
    return;
  }
  console.log("[browser-cli] stopped");
}

async function runTools(flags) {
  const server = await ensureServerRunning(flags, { quiet: true });
  const response = await requestJson(server, "GET", "/tools");
  if (flagEnabled(flags, "json-output")) {
    console.log(JSON.stringify(response.tools, null, 2));
    return;
  }
  for (const tool of response.tools) {
    const description = compactText(tool.description || "");
    console.log(`${tool.name}${description ? ` - ${description}` : ""}`);
  }
}

async function runTabWorkers(flags) {
  const server = await ensureServerRunning(flags, { quiet: true });
  const response = await requestJson(server, "GET", "/tab-workers");
  if (flagEnabled(flags, "json-output")) {
    console.log(JSON.stringify(response.workers || [], null, 2));
    return;
  }
  const workers = response.workers || [];
  if (!workers.length) {
    console.log("[browser-cli] no tab workers");
    return;
  }
  for (const worker of workers) {
    console.log(`${worker.id} - tab ${worker.tabIndex >= 0 ? worker.tabIndex : "?"} - ${worker.source} - ${worker.title || "(untitled)"} - ${worker.url || "about:blank"}`);
  }
}

async function runTabOpen(parsed, flags) {
  const server = await ensureServerRunning(flags, { quiet: true });
  const payload = buildTabOpenPayload(flags);
  const response = await requestJson(server, "POST", "/tab-workers/open", payload);
  if (flagEnabled(flags, "json-output")) {
    console.log(JSON.stringify(response, null, 2));
    return;
  }
  const worker = response.worker;
  console.log(`[browser-cli] tab worker ready: ${worker.id}`);
  console.log(`[browser-cli] source: ${worker.source}`);
  console.log(`[browser-cli] tab: ${worker.tabIndex}`);
  console.log(`[browser-cli] title: ${worker.title || "(untitled)"}`);
  console.log(`[browser-cli] url: ${worker.url || "about:blank"}`);
  if (response.navigation?.text) {
    console.log(response.navigation.text);
  }
}

async function runTabOpenBatch(parsed, flags) {
  const server = await ensureServerRunning(flags, { quiet: true });
  const countValue = parsed.positionals[0] || getSingleFlag(flags, "count");
  const count = Number(countValue || 0);
  if (!Number.isInteger(count) || count <= 0) {
    throw new Error("tab-open-batch requires a positive count");
  }
  const prefix = getSingleFlag(flags, "prefix");
  const basePayload = buildTabOpenPayload(flags);
  if (basePayload.tabIndex !== undefined && count > 1) {
    throw new Error("tab-open-batch does not support --tab with count > 1");
  }
  if (getSingleFlag(flags, "id") && !prefix && count > 1) {
    throw new Error("tab-open-batch with count > 1 requires --prefix instead of --id");
  }
  delete basePayload.workerId;

  const results = [];
  for (let index = 0; index < count; index += 1) {
    const payload = { ...basePayload };
    if (prefix) {
      payload.workerId = `${String(prefix)}-${index + 1}`;
    }
    const response = await requestJson(server, "POST", "/tab-workers/open", payload);
    results.push({ index, ok: Boolean(response.ok), worker: response.worker, navigation: response.navigation });
  }

  const batch = { ok: results.every((item) => item.ok), results };
  if (flagEnabled(flags, "raw") || flagEnabled(flags, "json-output")) {
    console.log(JSON.stringify(batch, null, 2));
    return;
  }
  for (const item of results) {
    console.log(`[browser-cli] batch worker ready: ${item.worker.id} tab=${item.worker.tabIndex} url=${item.worker.url || "about:blank"}`);
    if (item.navigation?.text) {
      console.log(item.navigation.text);
    }
  }
}

async function runTabClose(parsed, flags) {
  const workerId = parsed.positionals[0] || getSingleFlag(flags, "id");
  if (!workerId) {
    throw new Error("tab-close requires a worker id");
  }
  const server = await ensureServerRunning(flags, { quiet: true });
  const payload = { workerId: String(workerId) };
  if (flags["close-tab"] !== undefined) {
    payload.closeTab = flagEnabled(flags, "close-tab");
  }
  const response = await requestJson(server, "POST", "/tab-workers/close", payload);
  if (flagEnabled(flags, "json-output")) {
    console.log(JSON.stringify(response, null, 2));
    return;
  }
  console.log(`[browser-cli] closed worker: ${response.workerId}`);
  console.log(`[browser-cli] tab closed: ${response.pageClosed}`);
}

async function runCall(parsed, flags) {
  const toolName = parsed.positionals[0];
  if (!toolName) {
    throw new Error("call requires a tool name");
  }
  const payload = await buildPayloadFromInput(parsed, () => ({}));
  const server = await ensureServerRunning(flags, { quiet: true });
  const response = await requestToolCall(server, toolName, payload, flags);
  printCallResult(response, flags);
  if (!response.ok) {
    process.exitCode = 1;
  }
}

async function runCallWorkers(parsed, flags) {
  const toolName = parsed.positionals[0];
  if (!toolName) {
    throw new Error("call-workers requires a tool name");
  }
  const workerIds = normalizeWorkerIds([...parsed.positionals.slice(1), ...readCsvFlag(flags, "workers")]);
  if (!workerIds.length) {
    throw new Error("call-workers requires worker ids via positional args or --workers");
  }
  const payload = await buildPayloadFromInput(parsed, () => ({}));
  const server = await ensureServerRunning(flags, { quiet: true });
  const results = await executeBatchEntries(server, workerIds.map((workerId) => ({ workerId, name: toolName, arguments: payload })), flags);
  printBatchResults(results, flags);
}

async function runCallBatch(parsed, flags) {
  const entries = await buildBatchEntriesFromInput(parsed);
  const server = await ensureServerRunning(flags, { quiet: true });
  const results = await executeBatchEntries(server, entries, flags);
  printBatchResults(results, flags);
}

async function runAlias(command, parsed) {
  const flags = parsed.flags;
  let builder;
  switch (command) {
    case "navigate":
      builder = () => ({ url: requiredString(parsed.positionals[0] || getSingleFlag(flags, "url"), "url") });
      break;
    case "snapshot":
      builder = () => {
        const filename = getSingleFlag(flags, "filename");
        return filename ? { filename } : {};
      };
      break;
    case "click":
      builder = () => {
        const ref = parsed.positionals[0] || getSingleFlag(flags, "ref");
        if (!ref) throw new Error("click requires --json/--file or a ref");
        const args = { ref };
        const element = getSingleFlag(flags, "element");
        const button = getSingleFlag(flags, "button");
        if (element) args.element = element;
        if (button) args.button = button;
        if (flagEnabled(flags, "double-click")) args.doubleClick = true;
        return args;
      };
      break;
    case "type":
      builder = () => {
        const ref = parsed.positionals[0] || getSingleFlag(flags, "ref");
        const text = parsed.positionals[1] || getSingleFlag(flags, "text");
        if (!ref || text === undefined) throw new Error("type requires --json/--file or <ref> <text>");
        return { ref, text, slowly: flagEnabled(flags, "slowly"), submit: flagEnabled(flags, "submit") };
      };
      break;
    case "press-key":
      builder = () => ({ key: requiredString(parsed.positionals[0] || getSingleFlag(flags, "key"), "key") });
      break;
    case "wait-for":
      builder = () => {
        const args = {};
        const text = getSingleFlag(flags, "text") || parsed.positionals[0];
        const textGone = getSingleFlag(flags, "text-gone");
        const time = getSingleFlag(flags, "time");
        if (text) args.text = text;
        if (textGone) args.textGone = textGone;
        if (time !== undefined) args.time = Number(time);
        if (!Object.keys(args).length) throw new Error("wait-for requires --text, --text-gone or --time");
        return args;
      };
      break;
    case "network-requests":
      builder = () => {
        const args = { includeStatic: flagEnabled(flags, "include-static") };
        const filename = getSingleFlag(flags, "filename");
        if (filename) args.filename = filename;
        return args;
      };
      break;
    case "run-code":
      builder = () => ({ code: requiredString(getSingleFlag(flags, "code") || parsed.positionals.join(" ").trim(), "code") });
      break;
    case "screenshot":
      builder = () => {
        const args = { type: getSingleFlag(flags, "type") || "png" };
        const filename = getSingleFlag(flags, "filename");
        const ref = getSingleFlag(flags, "ref");
        const element = getSingleFlag(flags, "element");
        if (filename) args.filename = filename;
        if (flagEnabled(flags, "full-page")) args.fullPage = true;
        if (ref) args.ref = ref;
        if (element) args.element = element;
        return args;
      };
      break;
    default:
      throw new Error(`Alias builder not implemented for ${command}`);
  }
  const payload = await buildPayloadFromInput(parsed, builder);
  const server = await ensureServerRunning(flags, { quiet: true });
  const response = await requestToolCall(server, TOOL_ALIASES[command], payload, flags);
  printCallResult(response, flags);
  if (!response.ok) {
    process.exitCode = 1;
  }
}

async function buildPayloadFromInput(parsed, fallbackBuilder) {
  const jsonValue = getSingleFlag(parsed.flags, "json");
  const fileValue = getSingleFlag(parsed.flags, "file");
  if (jsonValue !== undefined && fileValue !== undefined) {
    throw new Error("Use either --json or --file, not both");
  }
  if (jsonValue !== undefined) {
    return parseJsonText(jsonValue, "--json");
  }
  if (fileValue !== undefined) {
    const filePath = path.resolve(process.cwd(), fileValue);
    const text = await fsp.readFile(filePath, "utf8");
    return parseJsonText(text, filePath);
  }
  return fallbackBuilder();
}

function parseJsonText(text, label) {
  try {
    const value = JSON.parse(normalizeJsonInputText(text));
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new Error("must be an object");
    }
    return value;
  } catch (error) {
    throw new Error(`Invalid JSON from ${label}: ${error.message}`);
  }
}

function parseJsonArrayText(text, label) {
  try {
    const value = JSON.parse(normalizeJsonInputText(text));
    if (!Array.isArray(value)) {
      throw new Error("must be an array");
    }
    return value;
  } catch (error) {
    throw new Error(`Invalid JSON from ${label}: ${error.message}`);
  }
}

function normalizeJsonInputText(text) {
  return String(text).replace(/^\uFEFF/, "");
}

function withClientMeta(payload) {
  const next = { ...payload };
  if (next._meta && typeof next._meta === "object") {
    next._meta = { ...next._meta };
  }
  return next;
}

function printCallResult(response, flags) {
  if (flagEnabled(flags, "raw")) {
    console.log(JSON.stringify(response, null, 2));
    return;
  }
  if (flagEnabled(flags, "json-output")) {
    console.log(JSON.stringify({ ok: response.ok, parsed: response.parsed }, null, 2));
    return;
  }
  const text = response.parsed?.text || response.response?.content?.[0]?.text || "";
  if (text) {
    console.log(text);
  }
}

async function requestToolCall(server, toolName, payload, flags) {
  const workerId = getSingleFlag(flags, "worker");
  const body = { name: toolName, arguments: withClientMeta(payload) };
  if (workerId) {
    body.workerId = String(workerId);
    return requestJson(server, "POST", "/call-tab", body);
  }
  return requestJson(server, "POST", "/call", body);
}

function buildTabOpenPayload(flags) {
  const tabValue = getSingleFlag(flags, "tab");
  const payload = {};
  if (tabValue !== undefined) {
    const tabIndex = Number(tabValue);
    if (!Number.isInteger(tabIndex) || tabIndex < 0) throw new Error(`Invalid tab index: ${tabValue}`);
    payload.tabIndex = tabIndex;
  }
  const workerId = getSingleFlag(flags, "id");
  if (workerId) payload.workerId = String(workerId);
  const url = getSingleFlag(flags, "url");
  if (url) payload.url = String(url);
  return payload;
}

function normalizeWorkerIds(workerIds) {
  const seen = new Set();
  const normalized = [];
  for (const workerId of workerIds) {
    const value = String(workerId || "").trim();
    if (!value || seen.has(value)) continue;
    seen.add(value);
    normalized.push(value);
  }
  return normalized;
}

async function buildBatchEntriesFromInput(parsed) {
  const jsonValue = getSingleFlag(parsed.flags, "json");
  const fileValue = getSingleFlag(parsed.flags, "file");
  if (jsonValue !== undefined && fileValue !== undefined) throw new Error("Use either --json or --file, not both");
  if (jsonValue === undefined && fileValue === undefined) throw new Error("call-batch requires --json or --file");
  if (jsonValue !== undefined) return parseJsonArrayText(jsonValue, "--json");
  const filePath = path.resolve(process.cwd(), fileValue);
  const text = await fsp.readFile(filePath, "utf8");
  return parseJsonArrayText(text, filePath);
}

async function executeBatchEntries(server, entries, flags) {
  const results = await Promise.all(entries.map(async (entry, index) => {
    const name = entry.name;
    if (!name || typeof name !== "string") {
      return { index, label: entry.label, workerId: entry.workerId, ok: false, error: "Missing tool name" };
    }
    try {
      const rawArguments = entry.arguments === undefined ? {} : normalizeToolArguments(entry.arguments, index);
      const response = entry.workerId
        ? await requestJson(server, "POST", "/call-tab", { workerId: String(entry.workerId), name, arguments: withClientMeta(rawArguments) })
        : await requestJson(server, "POST", "/call", { name, arguments: withClientMeta(rawArguments) });
      return { index, label: entry.label, workerId: entry.workerId, name, ok: Boolean(response.ok), parsed: response.parsed, response: response.response };
    } catch (error) {
      return { index, label: entry.label, workerId: entry.workerId, name, ok: false, error: String(error && error.stack ? error.stack : error) };
    }
  }));
  return { ok: results.every((item) => item.ok), results };
}

function normalizeToolArguments(value, index) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`Batch item ${index} arguments must be an object`);
  }
  return value;
}

function printBatchResults(batch, flags) {
  if (flagEnabled(flags, "raw") || flagEnabled(flags, "json-output")) {
    console.log(JSON.stringify(batch, null, 2));
    return;
  }
  if (!batch.results.length) {
    console.log("[browser-cli] empty batch");
    return;
  }
  for (const result of batch.results) {
    const idParts = [`#${result.index}`];
    if (result.workerId) idParts.push(`worker=${result.workerId}`);
    if (result.name) idParts.push(`tool=${result.name}`);
    if (result.label) idParts.push(`label=${result.label}`);
    console.log(`[browser-cli] ${idParts.join(" ")}`);
    if (result.ok) {
      console.log(result.parsed?.text || result.response?.content?.[0]?.text || "(no text response)");
    } else {
      console.log(result.error || result.parsed?.text || "Unknown batch error");
    }
  }
}

async function runServe(rawArgv) {
  await ensureRuntimeDirs();
  const startup = resolveDaemonOptions(rawArgv);
  const backend = new NativeCdpBackend(startup.cliOptions);
  await backend.initialize();
  const tabWorkerManager = new NativeCdpTabWorkerManager(backend);
  const runtimeState = await backend.runtimeState();

  const serverState = {
    pid: process.pid,
    host: startup.host,
    port: startup.port,
    startedAt: new Date().toISOString(),
    browserName: runtimeState.browserName,
    channel: runtimeState.channel,
    outputDir: runtimeState.outputDir,
    cdpHost: runtimeState.cdpHost,
    cdpPort: runtimeState.cdpPort,
    cdpEndpoint: runtimeState.cdpEndpoint,
    modeKey: "current-browser-cdp",
    modeLabel: "current Chrome via native CDP",
    sessionModel: "shared browser state in the current Chrome instance"
  };

  let shuttingDown = false;
  let server;
  const shutdown = async () => {
    if (shuttingDown) return;
    shuttingDown = true;
    await safeUnlink(STATE_FILE);
    await tabWorkerManager.serverClosed();
    await backend.serverClosed();
    if (server) {
      await new Promise((resolve) => server.close(() => resolve()));
    }
  };

  server = http.createServer(async (req, res) => {
    try {
      if (req.method === "GET" && req.url === "/health") {
        sendJson(res, 200, { ok: true, state: { ...serverState, workerCount: (await tabWorkerManager.listWorkers()).length } });
        return;
      }
      if (req.method === "GET" && req.url === "/tools") {
        sendJson(res, 200, { ok: true, tools: await backend.listTools() });
        return;
      }
      if (req.method === "GET" && req.url === "/tab-workers") {
        sendJson(res, 200, { ok: true, workers: await tabWorkerManager.listWorkers() });
        return;
      }
      if (req.method === "POST" && req.url === "/tab-workers/open") {
        const body = await readRequestJson(req);
        sendJson(res, 200, { ok: true, ...(await tabWorkerManager.openWorker(body || {})) });
        return;
      }
      if (req.method === "POST" && req.url === "/tab-workers/close") {
        const body = await readRequestJson(req);
        if (!body?.workerId || typeof body.workerId !== "string") {
          sendJson(res, 400, { ok: false, error: "Missing workerId" });
          return;
        }
        sendJson(res, 200, { ok: true, ...(await tabWorkerManager.closeWorker(body.workerId, { closeTab: typeof body.closeTab === "boolean" ? body.closeTab : undefined })) });
        return;
      }
      if (req.method === "POST" && req.url === "/call") {
        const body = await readRequestJson(req);
        if (!body?.name || typeof body.name !== "string") {
          sendJson(res, 400, { ok: false, error: "Missing tool name" });
          return;
        }
        const rawResponse = await backend.callTool(body.name, body.arguments || {});
        sendJson(res, 200, { ok: !rawResponse.isError, parsed: parseToolResponse(rawResponse), response: rawResponse });
        return;
      }
      if (req.method === "POST" && req.url === "/call-tab") {
        const body = await readRequestJson(req);
        if (!body?.workerId || typeof body.workerId !== "string") {
          sendJson(res, 400, { ok: false, error: "Missing workerId" });
          return;
        }
        if (!body?.name || typeof body.name !== "string") {
          sendJson(res, 400, { ok: false, error: "Missing tool name" });
          return;
        }
        const rawResponse = await tabWorkerManager.callWorker(body.workerId, body.name, body.arguments || {});
        sendJson(res, 200, { ok: !rawResponse.isError, parsed: parseToolResponse(rawResponse), response: rawResponse });
        return;
      }
      if (req.method === "POST" && req.url === "/shutdown") {
        sendJson(res, 200, { ok: true });
        setTimeout(() => shutdown().finally(() => process.exit(0)), 10);
        return;
      }
      sendJson(res, 404, { ok: false, error: "Not found" });
    } catch (error) {
      sendJson(res, 500, { ok: false, error: String(error && error.stack ? error.stack : error) });
    }
  });

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(startup.port, startup.host, resolve);
  });

  await writeJsonFile(STATE_FILE, serverState);
  console.log(`[browser-cli] listening on http://${startup.host}:${startup.port}`);
  const handleSignal = (signal) => {
    console.log(`[browser-cli] shutting down from ${signal}`);
    shutdown().finally(() => process.exit(0));
  };
  process.on("SIGINT", handleSignal);
  process.on("SIGTERM", handleSignal);
}

function resolveDaemonOptions(input) {
  const flags = Array.isArray(input) ? parseArgs(input).flags : (input || {});
  const portValue = getSingleFlag(flags, "port");
  const host = getSingleFlag(flags, "host") || DEFAULT_HOST;
  const port = portValue === undefined ? DEFAULT_PORT : Number(portValue);
  if (!Number.isInteger(port) || port <= 0) {
    throw new Error(`Invalid port: ${portValue}`);
  }
  const cdpPortValue = getSingleFlag(flags, "cdp-port");
  const cdpPort = cdpPortValue === undefined ? undefined : Number(cdpPortValue);
  if (cdpPortValue !== undefined && (!Number.isInteger(cdpPort) || cdpPort <= 0)) {
    throw new Error(`Invalid cdp-port: ${cdpPortValue}`);
  }
  return {
    kind: "native-cdp",
    flags,
    host: String(host),
    port,
    portRequested: portValue !== undefined,
    cliOptions: {
      cdpHost: getSingleFlag(flags, "cdp-host") || "127.0.0.1",
      cdpPort,
      outputDir: getSingleFlag(flags, "output-dir") || OUTPUT_DIR
    }
  };
}

async function ensureServerRunning(input, options = {}) {
  const status = await inspectServer(input);
  if (status.running && status.state?.modeKey === "current-browser-cdp") {
    return { mode: "existing", ...status.state };
  }
  if (status.running && status.state) {
    if (!options.quiet) {
      console.log("[browser-cli] stopping incompatible legacy daemon");
    }
    await terminateIncompatibleServer(status.state);
  }
  const nextOptions = resolveDaemonOptions(input);
  if (nextOptions.portRequested) {
    const available = await isPortAvailable(nextOptions.host, nextOptions.port);
    if (!available) throw new Error(`Port ${nextOptions.port} is already in use`);
  } else {
    nextOptions.port = await findAvailablePort(nextOptions.host, nextOptions.port);
  }
  await ensureRuntimeDirs();
  const outLog = path.join(LOG_DIR, "server.out.log");
  const errLog = path.join(LOG_DIR, "server.err.log");
  const childArgs = [path.join(SOURCE_DIR, "cli.js"), "serve", "--host", nextOptions.host, "--port", String(nextOptions.port)];
  if (nextOptions.cliOptions.cdpHost !== "127.0.0.1") childArgs.push("--cdp-host", nextOptions.cliOptions.cdpHost);
  if (nextOptions.cliOptions.cdpPort !== undefined) childArgs.push("--cdp-port", String(nextOptions.cliOptions.cdpPort));
  if (nextOptions.cliOptions.outputDir !== OUTPUT_DIR) childArgs.push("--output-dir", nextOptions.cliOptions.outputDir);
  launchBackgroundProcess(childArgs, outLog, errLog);
  const runningState = await waitForServer({ host: nextOptions.host, port: nextOptions.port }, options.waitTimeoutMs ?? DEFAULT_START_TIMEOUT_MS);
  if (!options.quiet) {
    console.log(`[browser-cli] boot log: ${toProjectRelative(outLog)}`);
  }
  return { mode: "started", ...runningState };
}

async function inspectServer(input) {
  const explicitTarget = resolveInspectTarget(input);
  if (explicitTarget) {
    try {
      const health = await requestJson(explicitTarget, "GET", "/health", undefined, { timeoutMs: DEFAULT_HEALTH_TIMEOUT_MS });
      return { running: Boolean(health.ok), state: normalizeServerState(health.state) };
    } catch (_) {
      return { running: false, state: { host: explicitTarget.host, port: explicitTarget.port } };
    }
  }
  const state = await readJsonFile(STATE_FILE);
  if (!state) return { running: false, state: null };
  try {
    const health = await requestJson(state, "GET", "/health", undefined, { timeoutMs: DEFAULT_HEALTH_TIMEOUT_MS });
    return { running: Boolean(health.ok), state: normalizeServerState(health.state) };
  } catch (_) {
    return { running: false, state: normalizeServerState(state) };
  }
}

function resolveInspectTarget(input) {
  const options = resolveDaemonOptions(input);
  if (!options.portRequested && options.host === DEFAULT_HOST) {
    return null;
  }
  return { host: options.host, port: options.port };
}

async function waitForServer(target, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const health = await requestJson(target, "GET", "/health", undefined, { timeoutMs: DEFAULT_HEALTH_TIMEOUT_MS });
      const state = normalizeServerState(health.state);
      if (health.ok && state && state.modeKey === "current-browser-cdp") return state;
      lastError = new Error("Incompatible daemon is still responding on the target port");
    } catch (error) {
      lastError = error;
    }
    await sleep(500);
  }
  const detail = lastError ? ` Last error: ${lastError.message}` : "";
  throw new Error(`Timed out waiting for browser-cli on http://${target.host}:${target.port}.${detail}`);
}

async function waitForServerDown(target, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      await requestJson(target, "GET", "/health", undefined, { timeoutMs: DEFAULT_HEALTH_TIMEOUT_MS });
    } catch (_) {
      return;
    }
    await sleep(250);
  }
}

async function terminateIncompatibleServer(state) {
  await requestJson(state, "POST", "/shutdown", {}).catch(() => {});
  await waitForServerDown(state, 3000).catch(() => {});
  if (state.pid) {
    try {
      process.kill(state.pid);
    } catch (error) {
      if (error.code !== "ESRCH") {
        throw error;
      }
    }
  }
  await sleep(500);
  await safeUnlink(STATE_FILE);
}

async function findAvailablePort(host, startPort) {
  for (let port = startPort; port < startPort + 50; port += 1) {
    if (await isPortAvailable(host, port)) return port;
  }
  throw new Error(`No free port found near ${startPort}`);
}

function isPortAvailable(host, port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.listen(port, host, () => server.close(() => resolve(true)));
  });
}

function launchBackgroundProcess(args, outLog, errLog) {
  const outFd = fs.openSync(outLog, "a");
  const errFd = fs.openSync(errLog, "a");
  const child = spawn(process.execPath, args, {
    cwd: PROJECT_DIR,
    detached: true,
    stdio: ["ignore", outFd, errFd],
    windowsHide: true
  });
  child.unref();
  return child.pid || null;
}

function parseToolResponse(response) {
  const text = response?.content?.[0]?.type === "text" ? response.content[0].text : "";
  return { text, isError: Boolean(response?.isError) };
}

function requestJson(target, method, pathname, body, options = {}) {
  return new Promise((resolve, reject) => {
    const payload = body === undefined ? null : Buffer.from(JSON.stringify(body), "utf8");
    const req = http.request({
      host: target.host,
      port: target.port,
      path: pathname,
      method,
      headers: payload ? { "Content-Type": "application/json", "Content-Length": payload.length } : undefined,
      timeout: options.timeoutMs || DEFAULT_REQUEST_TIMEOUT_MS
    }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        const text = Buffer.concat(chunks).toString("utf8");
        if (res.statusCode < 200 || res.statusCode >= 300) {
          reject(new Error(text || `HTTP ${res.statusCode}`));
          return;
        }
        if (!text) {
          resolve({});
          return;
        }
        try {
          resolve(JSON.parse(text));
        } catch (error) {
          reject(new Error(`Invalid JSON response: ${error.message}`));
        }
      });
    });
    req.on("timeout", () => req.destroy(new Error("Request timed out")));
    req.on("error", reject);
    if (payload) req.write(payload);
    req.end();
  });
}

function readRequestJson(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => {
      const text = Buffer.concat(chunks).toString("utf8").trim();
      if (!text) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(text));
      } catch (error) {
        reject(new Error(`Invalid JSON body: ${error.message}`));
      }
    });
    req.on("error", reject);
  });
}

function sendJson(res, statusCode, payload) {
  const body = Buffer.from(JSON.stringify(payload), "utf8");
  res.writeHead(statusCode, { "Content-Type": "application/json", "Content-Length": body.length });
  res.end(body);
}

async function ensureRuntimeDirs() {
  await Promise.all([
    fsp.mkdir(RUNTIME_DIR, { recursive: true }),
    fsp.mkdir(OUTPUT_DIR, { recursive: true }),
    fsp.mkdir(LOG_DIR, { recursive: true })
  ]);
}

async function writeJsonFile(filePath, value) {
  await fsp.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function readJsonFile(filePath) {
  try {
    return JSON.parse(await fsp.readFile(filePath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
}

async function safeUnlink(filePath) {
  try {
    await fsp.unlink(filePath);
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}

function readCsvFlag(flags, name) {
  const raw = getSingleFlag(flags, name);
  if (raw === undefined || raw === "") return [];
  return String(raw).split(",").map((item) => item.trim()).filter(Boolean);
}

function compactText(text) {
  return text.replace(/\s+/g, " ").trim();
}

function normalizeServerState(state) {
  if (!state || typeof state !== "object") {
    return state;
  }
  if (state.modeKey) {
    return state;
  }
  return {
    ...state,
    modeKey: "legacy-playwright-daemon",
    modeLabel: "legacy Playwright-based browser-cli daemon",
    sessionModel: "legacy daemon still running from the previous browser-cli implementation",
    cdpHost: state.cdpHost || null,
    cdpPort: state.cdpPort || null
  };
}

function requiredString(value, label) {
  if (value === undefined || value === null || value === "") throw new Error(`Missing ${label}`);
  return String(value);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function toProjectRelative(targetPath) {
  if (!targetPath) return ".";
  return path.isAbsolute(targetPath) ? (path.relative(PROJECT_DIR, targetPath) || ".") : targetPath;
}

main().catch((error) => {
  const message = error && error.stack ? error.stack : String(error);
  console.error(`[browser-cli] ${message}`);
  process.exit(1);
});
