# Comparison

`browser-cli`, `web-access`, and `Playwright MCP` are adjacent tools, but they do not sit at the same layer.

## At a glance

| Tool | Best description | Best fit |
|---|---|---|
| `browser-cli` | Local control plane for the current Chrome | Daemon reuse, worker tabs, explicit local control, current-browser attachment |
| `web-access` | Agent-facing online skill | Search, reading, browser access, and agent workflow orchestration |
| `Playwright MCP` | General browser MCP server | Standard MCP exposure for a broader browser tool surface |

Choose `browser-cli` when the main problem is not generic automation, but stable reuse of the Chrome session that is already open.

## browser-cli vs web-access

Both projects care about browser reuse and low-friction access to authenticated sessions.

The difference is product shape and scope.

`web-access` is an agent-facing skill. It combines browsing strategy, search, reading, and browser operations into a higher-level workflow for online tasks.

`browser-cli` is intentionally narrower. It focuses on:

- attaching to the current Chrome
- keeping a reusable local daemon
- managing named tab workers
- exposing the workflow through an explicit CLI and a distributable skill repo

Choose `browser-cli` when you want a standalone local browser control surface that scripts and agents can share.

Choose `web-access` when you want a broader online skill that includes browser access as one part of a larger agent workflow.

## browser-cli vs Playwright MCP

`Playwright MCP` is a better fit when the goal is to expose browser tools through MCP to different clients in a more standard way.

`browser-cli` is a better fit when the goal is to keep current-Chrome control local, explicit, and easy to reuse without introducing MCP transport as the first abstraction.

`browser-cli` is especially opinionated about:

- current Chrome first
- local daemon first
- worker reuse first
- Windows-friendly launcher flow

`Playwright MCP` is especially strong when you need a broader browser tool surface and a protocol-first integration story.

## What browser-cli is not trying to be

To keep the repository boundary clear, `browser-cli` is not trying to become:

- a full browser framework
- a general-purpose MCP server replacement
- a browsing strategy system
- a larger site-specific automation platform

It is meant to stay small and explicit:

- current-Chrome attachment
- daemon lifecycle
- CLI surface
- worker and batch control
