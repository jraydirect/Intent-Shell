# TradingView Integration Feature

## Overview

The yfinance provider now supports opening TradingView charts directly in Brave browser. It automatically remembers the most recent stock you've been discussing, so you can quickly open charts without specifying the symbol again.

## Usage

### Basic Usage

1. **Query a stock first:**
   ```
   yahoo quote AAPL
   ```

2. **Open TradingView chart:**
   ```
   open tradingview
   ```
   This will automatically open TradingView for AAPL (the most recent stock).

### Alternative Commands

You can use any of these phrases:
- `open tradingview`
- `open chart`
- `open stock chart`
- `show chart`
- `show tradingview`
- `tradingview`
- `view chart`

### With Explicit Symbol

You can also specify a symbol directly:
```
open tradingview MSFT
```

This will open TradingView for MSFT, regardless of what stock you discussed before.

## How It Works

1. **Symbol Tracking**: When you use any yfinance command (`yahoo quote`, `yahoo history`, `yahoo news`, `yahoo info`), the provider automatically remembers the stock symbol.

2. **Smart Defaults**: If you say "open tradingview" without specifying a symbol, it uses the most recently discussed stock.

3. **Browser Launch**: The feature tries to open Brave browser first (at common installation paths), and falls back to your default browser if Brave isn't found.

## Examples

### Example 1: Sequential Usage
```
intellishell> yahoo quote AAPL
[Shows AAPL quote]

intellishell> open tradingview
[Opens TradingView for AAPL in Brave]
```

### Example 2: Multiple Stocks
```
intellishell> yahoo quote MSFT
[Shows MSFT quote]

intellishell> yahoo quote GOOGL
[Shows GOOGL quote]

intellishell> open tradingview
[Opens TradingView for GOOGL - the most recent one]
```

### Example 3: Explicit Symbol
```
intellishell> yahoo quote AAPL
[Shows AAPL quote]

intellishell> open tradingview TSLA
[Opens TradingView for TSLA, not AAPL]
```

## Technical Details

- **URL Format**: `https://www.tradingview.com/chart/?symbol={SYMBOL}`
- **Browser Priority**: Brave → Default Browser
- **Symbol Persistence**: Lasts for the session (until you restart IntelliShell)

## Troubleshooting

### "No recent stock found" error

**Solution**: Query a stock first, then open TradingView:
```
yahoo quote AAPL
open tradingview
```

### Browser doesn't open

**Possible causes**:
1. Brave not installed or not in standard location
2. Default browser not set
3. Permission issues

**Solution**: The system will try to use your default browser as a fallback. If that doesn't work, check your browser settings.

### Wrong stock opens

**Solution**: Specify the symbol explicitly:
```
open tradingview AAPL
```

## Integration with Charts

This feature works independently of the chart visualization examples. You can:
- Use the Streamlit/FastAPI chart examples for in-app visualization
- Use this TradingView feature to open full TradingView charts in your browser

Both features complement each other!
