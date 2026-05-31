# TradingView MCP — Setup Notes

These files are produced for the [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp)
server. They are committed here so they survive the ephemeral Claude-on-the-web container.

## IMPORTANT — where this must run

The TradingView MCP works by attaching to a **live TradingView Desktop app** over the
Chrome DevTools Protocol (`--remote-debugging-port=9222`). It is **not** a web API.

That means the install + launch + health-check steps must be run on **your own machine**
(Mac / Windows / Linux desktop) where TradingView Desktop is installed and logged in —
**not** inside the cloud container, which is headless (no display, no desktop app, no GUI)
and gets reclaimed after the session ends.

## Install on your machine

```bash
# 1. Clone + install
git clone https://github.com/tradesdontlie/tradingview-mcp.git ~/tradingview-mcp
cd ~/tradingview-mcp
npm install

# 2. Copy rules.json next to the server
cp /path/to/this/repo/tradingview-mcp-setup/rules.json ~/tradingview-mcp/rules.json
```

## Add to Claude Code MCP config

Merge `mcp.json` into your `~/.claude/.mcp.json` (replace `/root` with your real home path,
e.g. `/Users/you` on Mac or `C:\\Users\\you` on Windows). If you already have other MCP
servers, only add the `tradingview` key — don't overwrite the rest.

```json
{
  "mcpServers": {
    "tradingview": {
      "command": "node",
      "args": ["<YOUR_HOME>/tradingview-mcp/src/server.js"]
    }
  }
}
```

Then **restart Claude Code** so the server loads.

## Launch TradingView Desktop with the debug port

- **Mac:**     `/Applications/TradingView.app/Contents/MacOS/TradingView --remote-debugging-port=9222`
- **Windows:** `%LOCALAPPDATA%\TradingView\TradingView.exe --remote-debugging-port=9222`
- **Linux:**   `/opt/TradingView/tradingview --remote-debugging-port=9222`

Or, once the MCP is connected, just call the `tv_launch` tool (auto-detects the platform).

## Verify

Call `tv_health_check`. You want `cdp_connected: true`. Then `quote_get` BTCUSDT for a live price.

## What `rules.json` does

Beyond the watchlist/bias/risk config, it encodes the trade-decision logic you asked for —
for **any** coin: pick **long/short** from the bias criteria, apply **3x default leverage**,
set a **structure-based stop** sized to ≤1% portfolio risk, and compute **entry (cost),
liquidation price, and TP1/TP2/TP3 targets**. See `analysis_workflow_per_symbol` and
`trade_plan_formulas` inside `rules.json`.
