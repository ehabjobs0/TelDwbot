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

## trdr.io — no public API (checked)

`trdr.io` does **not** expose a public developer API: the `api.trdr.io` host doesn't
resolve, the site is bot-blocked (HTTP 403), and the docs mention no API key / REST
endpoint / webhook. So it can't be queried programmatically.

Workaround: TRDR is "powered by TradingView" — its **Liquidations** and **Order Book
Top Levels** heatmap are TradingView indicators. Add them to the chart on TradingView
Desktop and the MCP reads their plotted output via `data_get_pine_lines` /
`data_get_pine_boxes` / `data_get_pine_labels`. See `liquidation_and_orderbook` in
`rules.json`.

### Free liquidation-map alternative: `liquidation_heatmap.pine`

Since trdr.io has no API, this repo ships `liquidation_heatmap.pine` — an **estimated**
liquidation-levels indicator (no API needed). It marks where leveraged longs/shorts
likely get liquidated, based on swing highs/lows + volume + leverage tiers (10/25/50/100x),
and prints a "magnet" table with the nearest cluster above/below price.

**Important:** it's an *estimate* from price/volume, not real exchange liquidation data
(Pine can't access order books or open interest). It's a close visual proxy for
Coinglass/TRDR heatmaps.

Load it:
1. TradingView Desktop → Pine Editor → paste the file → "Add to chart".
2. Or via the MCP once connected: `pine_set_source` → `pine_smart_compile`.

The MCP reads it with `data_get_pine_lines` / `data_get_pine_labels` /
`data_get_pine_tables` using `study_filter="Liquidation"`.

## What `rules.json` does

Beyond the watchlist/bias/risk config, it encodes the trade-decision logic you asked for —
for **any** coin: pick **long/short** from the bias criteria, apply **3x default leverage**,
set a **structure-based stop** sized to ≤1% portfolio risk, and compute **entry (cost),
liquidation price, and TP1/TP2/TP3 targets**. See `analysis_workflow_per_symbol` and
`trade_plan_formulas` inside `rules.json`.
