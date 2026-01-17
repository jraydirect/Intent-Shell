"""Yahoo Finance provider for stock data and financial news."""

import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from intellishell.providers.base import (
    BaseProvider,
    IntentTrigger,
    ExecutionResult,
    ProviderCapability
)
import logging

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance library not available. Yahoo Finance provider will have limited functionality.")


class YahooFinanceAPI:
    """Client for Yahoo Finance API interactions using yfinance."""
    
    def __init__(self):
        """Initialize Yahoo Finance API client."""
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library required for Yahoo Finance API")
    
    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get stock information for a ticker symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")
            
        Returns:
            Dictionary with stock information or None if not found
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library required")
        
        try:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info
            
            if not info or "symbol" not in info:
                return None
            
            return info
        except Exception as e:
            logger.error(f"Error fetching stock info for {symbol}: {e}")
            return None
    
    def get_stock_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current stock quote (price, change, etc.).
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with quote data or None if not found
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library required")
        
        try:
            ticker = yf.Ticker(symbol.upper())
            # Get fast info for quick quote
            fast_info = ticker.fast_info
            
            # Also get info for additional data
            info = ticker.info
            
            if not info or "symbol" not in info:
                return None
            
            quote = {
                "symbol": info.get("symbol", symbol.upper()),
                "name": info.get("longName") or info.get("shortName", "N/A"),
                "price": fast_info.get("lastPrice") or info.get("currentPrice") or info.get("regularMarketPrice"),
                "previous_close": fast_info.get("previousClose") or info.get("previousClose"),
                "change": None,
                "change_percent": None,
                "market_cap": info.get("marketCap"),
                "volume": fast_info.get("regularMarketVolume") or info.get("volume"),
                "day_high": fast_info.get("dayHigh") or info.get("dayHigh"),
                "day_low": fast_info.get("dayLow") or info.get("dayLow"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "currency": info.get("currency", "USD"),
            }
            
            # Calculate change if we have price and previous close
            if quote["price"] and quote["previous_close"]:
                change = quote["price"] - quote["previous_close"]
                quote["change"] = change
                if quote["previous_close"] != 0:
                    quote["change_percent"] = (change / quote["previous_close"]) * 100
            
            return quote
        except Exception as e:
            logger.error(f"Error fetching stock quote for {symbol}: {e}")
            return None
    
    def get_stock_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d"
    ) -> Optional[Any]:
        """
        Get historical stock data.
        
        Args:
            symbol: Stock ticker symbol
            period: Period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            
        Returns:
            DataFrame with historical data or None if error
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library required")
        
        try:
            ticker = yf.Ticker(symbol.upper())
            history = ticker.history(period=period, interval=interval)
            return history
        except Exception as e:
            logger.error(f"Error fetching stock history for {symbol}: {e}")
            return None
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get news articles for a stock.
        
        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of news articles to return
            
        Returns:
            List of news article dictionaries
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library required")
        
        try:
            ticker = yf.Ticker(symbol.upper())
            news = ticker.news
            
            if not news:
                return []
            
            # Format news articles
            formatted_news = []
            for article in news[:limit]:
                formatted_article = {
                    "title": article.get("title", "No title"),
                    "publisher": article.get("publisher", "Unknown"),
                    "published": self._format_timestamp(article.get("providerPublishTime")),
                    "link": article.get("link", ""),
                    "related_tickers": article.get("relatedTickers", [])
                }
                formatted_news.append(formatted_article)
            
            return formatted_news
        except Exception as e:
            logger.error(f"Error fetching stock news for {symbol}: {e}")
            return []
    
    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for stocks by query using yfinance Lookup.
        
        Args:
            query: Search query (company name or ticker)
            limit: Maximum number of results
            
        Returns:
            List of matching stock dictionaries
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library required")
        
        try:
            # Use yfinance Lookup for better results
            lookup = yf.Lookup(query)
            
            # Try to get stocks first (most common)
            results = lookup.get_stock(count=limit)
            
            if not results or len(results) == 0:
                # If no stocks found, try all types
                results = lookup.get_all(count=limit)
            
            if not results or len(results) == 0:
                return []
            
            # Format results
            formatted_results = []
            for result in results[:limit]:
                formatted_result = {
                    "symbol": result.get("symbol", ""),
                    "name": result.get("longname") or result.get("shortname") or result.get("name", "N/A"),
                    "exchange": result.get("exchange") or result.get("exchDisp", "N/A"),
                    "quoteType": result.get("quoteType") or result.get("typeDisp", "N/A")
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
        except AttributeError as e:
            # Lookup might not be available in older yfinance versions
            logger.warning(f"yf.Lookup not available: {e}. Trying Search fallback...")
            try:
                # Fallback to Search
                search = yf.Search(query, max_results=limit)
                results = search.quotes
                
                if not results:
                    return []
                
                formatted_results = []
                for result in results[:limit]:
                    formatted_result = {
                        "symbol": result.get("symbol", ""),
                        "name": result.get("longname") or result.get("shortname") or result.get("name", "N/A"),
                        "exchange": result.get("exchange") or result.get("exchDisp", "N/A"),
                        "quoteType": result.get("quoteType") or result.get("typeDisp", "N/A")
                    }
                    formatted_results.append(formatted_result)
                
                return formatted_results
            except Exception as e2:
                logger.warning(f"Search fallback also failed: {e2}. Trying direct ticker lookup...")
        except Exception as e:
            logger.warning(f"Error searching stocks: {e}. Trying direct ticker lookup...")
        
        # Final fallback: try to get info for the query as a ticker
        try:
            ticker = yf.Ticker(query.upper())
            info = ticker.info
            if info and "symbol" in info:
                return [{
                    "symbol": info.get("symbol"),
                    "name": info.get("longName") or info.get("shortName", "N/A"),
                    "exchange": info.get("exchange", "N/A"),
                    "quoteType": info.get("quoteType", "N/A")
                }]
        except Exception:
            pass
        
        return []
    
    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get quotes for multiple stocks at once.
        
        Args:
            symbols: List of ticker symbols
            
        Returns:
            Dictionary mapping symbols to their quote data
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library required")
        
        results = {}
        for symbol in symbols:
            results[symbol.upper()] = self.get_stock_quote(symbol)
        
        return results
    
    def get_earnings_calendar(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 50
    ) -> Optional[Any]:
        """
        Get earnings calendar.
        
        Args:
            start: Start date (default: today)
            end: End date (default: start + 7 days)
            limit: Maximum number of results (default: 50, max: 100)
            
        Returns:
            DataFrame with earnings calendar or None if error
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library required")
        
        try:
            calendars = yf.Calendars(start=start, end=end)
            earnings = calendars.get_earnings_calendar(limit=limit)
            return earnings
        except Exception as e:
            logger.error(f"Error fetching earnings calendar: {e}")
            return None
    
    def get_economic_events_calendar(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 50
    ) -> Optional[Any]:
        """
        Get economic events calendar.
        
        Args:
            start: Start date (default: today)
            end: End date (default: start + 7 days)
            limit: Maximum number of results (default: 50, max: 100)
            
        Returns:
            DataFrame with economic events calendar or None if error
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library required")
        
        try:
            calendars = yf.Calendars(start=start, end=end)
            events = calendars.get_economic_events_calendar(limit=limit)
            return events
        except Exception as e:
            logger.error(f"Error fetching economic events calendar: {e}")
            return None
    
    def get_stock_earnings_dates(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get earnings dates for a specific stock.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with earnings dates or None if error
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance library required")
        
        try:
            ticker = yf.Ticker(symbol.upper())
            earnings_dates = ticker.earnings_dates
            
            if earnings_dates is None or earnings_dates.empty:
                return None
            
            # Get the most recent earnings dates
            latest_earnings = earnings_dates.head(4)  # Last 4 quarters
            
            return {
                "symbol": symbol.upper(),
                "earnings_dates": latest_earnings.to_dict('records') if hasattr(latest_earnings, 'to_dict') else None,
                "dataframe": latest_earnings
            }
        except Exception as e:
            logger.error(f"Error fetching earnings dates for {symbol}: {e}")
            return None
    
    @staticmethod
    def _format_timestamp(timestamp: Optional[int]) -> str:
        """Format Unix timestamp to readable date string."""
        if not timestamp:
            return "Unknown date"
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return "Unknown date"


class YahooFinanceProvider(BaseProvider):
    """Provider for Yahoo Finance stock data and news."""
    
    def __init__(self):
        """Initialize Yahoo Finance provider."""
        super().__init__()
        self._api: Optional[YahooFinanceAPI] = None
        self._recent_results: List[Dict[str, Any]] = []
        self._initialize_api()
    
    def _initialize_api(self) -> None:
        """Initialize API client."""
        if YFINANCE_AVAILABLE:
            try:
                self._api = YahooFinanceAPI()
            except Exception as e:
                logger.warning(f"Could not initialize Yahoo Finance API: {e}")
                self._api = None
    
    @property
    def name(self) -> str:
        return "yfinance"
    
    @property
    def description(self) -> str:
        return "Yahoo Finance stock data and financial news"
    
    def _initialize_triggers(self) -> None:
        """Initialize Yahoo Finance-related triggers."""
        self.capabilities = [
            ProviderCapability.READ_ONLY,
            ProviderCapability.ASYNC,
        ]
        
        self.triggers = [
            IntentTrigger(
                pattern="yahoo quote",
                intent_name="yahoo_quote",
                weight=1.0,
                aliases=[
                    "stock quote",
                    "stock price",
                    "quote",
                    "price",
                    "stock",
                    "yahoo stock",
                    "finance quote",
                    "get quote",
                    "what is the current price",
                    "what's the price",
                    "what is the price",
                    "current price",
                    "trading at",
                    "whats trading at",
                    "what's trading at",
                    "what is trading at",
                    "trading price",
                    "how much is",
                    "what's it trading",
                    "what is it trading"
                ]
            ),
            IntentTrigger(
                pattern="yahoo news",
                intent_name="yahoo_news",
                weight=1.0,
                aliases=[
                    "stock news",
                    "finance news",
                    "yahoo finance news",
                    "financial news",
                    "stock articles",
                    "market news"
                ]
            ),
            IntentTrigger(
                pattern="yahoo history",
                intent_name="yahoo_history",
                weight=1.0,
                aliases=[
                    "stock history",
                    "stock chart",
                    "stock data",
                    "yahoo chart",
                    "price history",
                    "historical data"
                ]
            ),
            IntentTrigger(
                pattern="yahoo search",
                intent_name="yahoo_search",
                weight=1.0,
                aliases=[
                    "search stock",
                    "find stock",
                    "lookup stock",
                    "stock search",
                    "yahoo lookup"
                ]
            ),
            IntentTrigger(
                pattern="yahoo info",
                intent_name="yahoo_info",
                weight=1.0,
                aliases=[
                    "stock info",
                    "stock information",
                    "yahoo finance info",
                    "company info",
                    "ticker info"
                ]
            ),
            IntentTrigger(
                pattern="yahoo status",
                intent_name="yahoo_status",
                weight=1.0,
                aliases=[
                    "finance status",
                    "yahoo finance status",
                    "yfinance status"
                ]
            ),
            IntentTrigger(
                pattern="yahoo earnings",
                intent_name="yahoo_earnings",
                weight=1.2,  # Higher weight to prioritize over economic events
                aliases=[
                    "earnings calendar",
                    "earnings reports",
                    "upcoming earnings",
                    "earnings today",
                    "were there any earnings",
                    "were there any earnings reports",
                    "earnings schedule",
                    "stock earnings",
                    "company earnings",
                    "upcoming stock calendar events",
                    "upcoming calendar events",
                    "stock calendar events",
                    "calendar events",
                    "any earnings reports",
                    "some earnings reports",
                    "upcoming earnings reports"
                ]
            ),
            IntentTrigger(
                pattern="yahoo economic events",
                intent_name="yahoo_economic_events",
                weight=1.0,
                aliases=[
                    "economic calendar",
                    "economic events",
                    "upcoming economic events",
                    "economic events today",
                    "market events"
                ]
            ),
        ]
    
    async def execute(
        self,
        intent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute Yahoo Finance intent."""
        context = context or {}
        
        try:
            if intent_name == "yahoo_quote":
                return await self._get_quote(context)
            elif intent_name == "yahoo_news":
                return await self._get_news(context)
            elif intent_name == "yahoo_history":
                return await self._get_history(context)
            elif intent_name == "yahoo_search":
                return await self._search_stocks(context)
            elif intent_name == "yahoo_info":
                return await self._get_info(context)
            elif intent_name == "yahoo_status":
                return await self._check_status(context)
            elif intent_name == "yahoo_earnings":
                return await self._get_earnings(context)
            elif intent_name == "yahoo_economic_events":
                return await self._get_economic_events(context)
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown Yahoo Finance intent: {intent_name}"
                )
        except Exception as e:
            logger.exception(f"Yahoo Finance provider error: {e}")
            return ExecutionResult(
                success=False,
                message=f"Yahoo Finance operation failed: {e}"
            )
    
    def _convert_to_ticker(self, symbol: str) -> Optional[str]:
        """
        Convert a company name or symbol to a ticker symbol.
        
        Args:
            symbol: Company name or ticker symbol
            
        Returns:
            Ticker symbol or None if not found
        """
        if not symbol:
            return None
        
        symbol_upper = symbol.upper()
        
        # Check if it looks like a ticker (1-5 uppercase letters) or a company name
        if len(symbol_upper) <= 5 and symbol_upper.isalpha():
            # Could be a ticker, but let's verify it's not a common company name
            common_company_names = {
                "APPLE", "TESLA", "GOOGLE", "AMAZON", "MICROSOFT", "META", 
                "NVIDIA", "INTEL", "AMD", "IBM", "ORACLE", "CISCO",
                "NETFLIX", "UBER", "LYFT", "ZOOM", "SLACK", "ADOBE",
                "PAYPAL", "VISA", "SHOPIFY", "TWITTER", "SNAP"
            }
            
            if symbol_upper in common_company_names:
                # This is a company name, search for ticker
                logger.info(f"'{symbol}' is a known company name, searching for ticker...")
                if self._api:
                    try:
                        search_results = self._api.search_stocks(symbol, limit=1)
                        if search_results and len(search_results) > 0:
                            ticker = search_results[0].get("symbol", "").upper()
                            logger.info(f"Converted '{symbol}' → '{ticker}'")
                            return ticker
                    except Exception as e:
                        logger.debug(f"Could not search for '{symbol}': {e}")
            
            # Otherwise, assume it's a valid ticker
            return symbol_upper
        else:
            # Longer than 5 chars - definitely a company name
            logger.info(f"'{symbol}' is a company name, searching for ticker...")
            if self._api:
                try:
                    search_results = self._api.search_stocks(symbol, limit=1)
                    if search_results and len(search_results) > 0:
                        ticker = search_results[0].get("symbol", "").upper()
                        logger.info(f"Converted '{symbol}' → '{ticker}'")
                        return ticker
                except Exception as e:
                    logger.debug(f"Could not search for '{symbol}': {e}")
            
            # If search failed, return as-is
            return symbol_upper
    
    def _extract_symbol(self, context: Dict[str, Any]) -> Optional[str]:
        """Extract stock symbol from context. Handles both ticker symbols and company names."""
        # Check parameters first (from LLM)
        parameters = context.get("parameters", {})
        symbol = parameters.get("symbol") or parameters.get("ticker") or parameters.get("stock")
        
        if symbol:
            return self._convert_to_ticker(symbol)
        
        # Extract from original input
        original_input = context.get("original_input", "")
        original_input_upper = original_input.upper()
        
        # First, try to find ticker-like patterns (all caps, 1-5 letters)
        ticker_pattern = r'\b([A-Z]{1,5})\b'
        matches = re.findall(ticker_pattern, original_input_upper)
        
        # Filter out common words
        exclude_words = {
            "YAHOO", "FINANCE", "STOCK", "QUOTE", "NEWS", "PRICE", "HISTORY", "INFO", "SEARCH",
            "THE", "IS", "AT", "IT", "NOW", "TODAY", "TRADING", "CURRENT", "WHAT", "HOW", "MUCH"
        }
        for match in matches:
            if match not in exclude_words and len(match) >= 2:
                return match
        
        # If no ticker found, try to extract company name and search for it
        # Look for company names after common phrases
        company_patterns = [
            r'(?:price|quote|stock|trading|earnings|news|info|history)\s+(?:of|for)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:stock|price|quote|trading|earnings|news)',
            r'(?:what|how|get|show)\s+(?:is|the|a|an)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, original_input)
            if match:
                company_name = match.group(1)
                # Skip common words that aren't company names
                if company_name.lower() not in ["the", "current", "today", "upcoming", "some", "any"]:
                    # Try to convert company name to ticker using search
                    if self._api:
                        try:
                            search_results = self._api.search_stocks(company_name, limit=1)
                            if search_results and len(search_results) > 0:
                                return search_results[0].get("symbol", "").upper()
                        except Exception as e:
                            logger.debug(f"Could not search for company name '{company_name}': {e}")
        
        # Also check entities
        if "entities" in context:
            for entity in context["entities"]:
                if hasattr(entity, "value"):
                    value = entity.value
                    if isinstance(value, str):
                        # Try as ticker first
                        if value.isupper() and 1 <= len(value) <= 5 and value not in exclude_words:
                            return value.upper()
                        # Try as company name
                        if value and not value.isupper() and len(value) > 2:
                            if self._api:
                                try:
                                    search_results = self._api.search_stocks(value, limit=1)
                                    if search_results and len(search_results) > 0:
                                        return search_results[0].get("symbol", "").upper()
                                except Exception:
                                    pass
        
        return None
    
    def _format_currency(self, value: Any, currency: str = "USD") -> str:
        """Format currency value."""
        if value is None:
            return "N/A"
        try:
            num_value = float(value)
            if abs(num_value) >= 1_000_000_000:
                return f"${num_value / 1_000_000_000:.2f}B {currency}"
            elif abs(num_value) >= 1_000_000:
                return f"${num_value / 1_000_000:.2f}M {currency}"
            elif abs(num_value) >= 1_000:
                return f"${num_value / 1_000:.1f}K {currency}"
            else:
                return f"${num_value:.2f} {currency}"
        except (ValueError, TypeError):
            return str(value) if value else "N/A"
    
    async def _get_quote(self, context: Dict[str, Any]) -> ExecutionResult:
        """Get stock quote(s). Supports multiple symbols."""
        if not YFINANCE_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="yfinance library required. Install with: pip install yfinance"
            )
        
        if not self._api:
            return ExecutionResult(
                success=False,
                message="Yahoo Finance API not initialized"
            )
        
        # Check if multiple symbols were requested
        parameters = context.get("parameters", {})
        symbols_param = parameters.get("symbols") or parameters.get("tickers")
        
        symbols = []
        if symbols_param:
            # Handle list of symbols
            if isinstance(symbols_param, list):
                symbols = symbols_param
            elif isinstance(symbols_param, str):
                # Split by common delimiters
                symbols = [s.strip() for s in re.split(r'[,;/\s]+(?:and\s+)?', symbols_param) if s.strip()]
        
        # If no symbols from parameters, try single symbol extraction
        if not symbols:
            symbol = self._extract_symbol(context)
            if symbol:
                symbols = [symbol]
        
        if not symbols:
            return ExecutionResult(
                success=False,
                message="Please provide a stock symbol. Example: 'yahoo quote AAPL' or 'stock price MSFT'"
            )
        
        # Convert company names to tickers for all symbols
        converted_symbols = []
        for sym in symbols:
            converted = self._convert_to_ticker(sym)
            if converted:
                converted_symbols.append(converted)
        
        if not converted_symbols:
            return ExecutionResult(
                success=False,
                message=f"Could not find tickers for: {', '.join(symbols)}"
            )
        
        # Handle single symbol case
        if len(converted_symbols) == 1:
            symbol = converted_symbols[0]
        
        # Handle multiple symbols
        if len(converted_symbols) > 1:
            try:
                quotes = self._api.get_multiple_quotes(converted_symbols)
                
                if not quotes or all(q is None for q in quotes.values()):
                    return ExecutionResult(
                        success=False,
                        message=f"Could not fetch quotes for any of: {', '.join(converted_symbols)}"
                    )
                
                # Format output for multiple quotes
                lines = [
                    f"\nStock Quotes ({len([q for q in quotes.values() if q])} stocks)",
                    "=" * 80
                ]
                
                for sym, quote in quotes.items():
                    if not quote:
                        lines.append(f"\n{sym}: Could not fetch quote")
                        continue
                    
                    price_str = self._format_currency(quote.get("price"), quote.get("currency", "USD"))
                    change = quote.get("change")
                    change_pct = quote.get("change_percent")
                    
                    lines.append(f"\n{quote['symbol']} - {quote['name']}")
                    lines.append(f"   Price: {price_str}")
                    
                    if change is not None and change_pct is not None:
                        change_sign = "+" if change >= 0 else ""
                        lines.append(f"   Change: {change_sign}{change:.2f} ({change_sign}{change_pct:.2f}%)")
                    
                    if quote.get("volume"):
                        volume_str = f"{quote['volume']:,}"
                        lines.append(f"   Volume: {volume_str}")
                
                message = "\n".join(lines)
                
                # Store in recent results
                self._recent_results = [q for q in quotes.values() if q]
                
                return ExecutionResult(
                    success=True,
                    message=message,
                    data={"quotes": quotes, "symbols": converted_symbols}
                )
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    message=f"Error fetching quotes: {e}"
                )
        
        # Single symbol case
        try:
            quote = self._api.get_stock_quote(symbol)
            
            if not quote:
                return ExecutionResult(
                    success=False,
                    message=f"Could not fetch quote for {symbol}. Symbol may be invalid."
                )
            
            # Format output
            lines = [
                f"\nStock Quote: {quote['symbol']} - {quote['name']}",
                "=" * 80
            ]
            
            price_str = self._format_currency(quote.get("price"), quote.get("currency", "USD"))
            lines.append(f"\nPrice: {price_str}")
            
            if quote.get("change") is not None and quote.get("change_percent") is not None:
                change_sign = "+" if quote["change"] >= 0 else ""
                change_color = "green" if quote["change"] >= 0 else "red"
                lines.append(
                    f"Change: {change_sign}{quote['change']:.2f} "
                    f"({change_sign}{quote['change_percent']:.2f}%)"
                )
            
            if quote.get("previous_close"):
                prev_close_str = self._format_currency(quote.get("previous_close"), quote.get("currency", "USD"))
                lines.append(f"Previous Close: {prev_close_str}")
            
            if quote.get("day_high") and quote.get("day_low"):
                day_high_str = self._format_currency(quote.get("day_high"), quote.get("currency", "USD"))
                day_low_str = self._format_currency(quote.get("day_low"), quote.get("currency", "USD"))
                lines.append(f"Day Range: {day_low_str} - {day_high_str}")
            
            if quote.get("52_week_high") and quote.get("52_week_low"):
                week_high_str = self._format_currency(quote.get("52_week_high"), quote.get("currency", "USD"))
                week_low_str = self._format_currency(quote.get("52_week_low"), quote.get("currency", "USD"))
                lines.append(f"52 Week Range: {week_low_str} - {week_high_str}")
            
            if quote.get("volume"):
                volume_str = f"{quote['volume']:,}"
                lines.append(f"Volume: {volume_str}")
            
            if quote.get("market_cap"):
                market_cap_str = self._format_currency(quote.get("market_cap"), quote.get("currency", "USD"))
                lines.append(f"Market Cap: {market_cap_str}")
            
            message = "\n".join(lines)
            
            # Store in recent results
            self._recent_results = [quote]
            
            return ExecutionResult(
                success=True,
                message=message,
                data={"quote": quote, "symbol": symbol}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error fetching quote: {e}"
            )
    
    async def _get_news(self, context: Dict[str, Any]) -> ExecutionResult:
        """Get stock news."""
        if not YFINANCE_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="yfinance library required. Install with: pip install yfinance"
            )
        
        if not self._api:
            return ExecutionResult(
                success=False,
                message="Yahoo Finance API not initialized"
            )
        
        symbol = self._extract_symbol(context)
        if not symbol:
            return ExecutionResult(
                success=False,
                message="Please provide a stock symbol. Example: 'yahoo news AAPL' or 'finance news MSFT'"
            )
        
        # Extract limit
        limit = 10
        if "entities" in context:
            for entity in context["entities"]:
                if entity.type == "number":
                    try:
                        limit = int(entity.value)
                        limit = max(1, min(50, limit))
                    except ValueError:
                        pass
        
        try:
            news = self._api.get_stock_news(symbol, limit=limit)
            
            if not news:
                return ExecutionResult(
                    success=True,
                    message=f"No news found for {symbol}",
                    data={"news": [], "symbol": symbol}
                )
            
            # Format output
            lines = [
                f"\nFinancial News for {symbol} ({len(news)} articles)",
                "=" * 80
            ]
            
            for i, article in enumerate(news, 1):
                lines.append(f"\n{i}. {article['title']}")
                lines.append(f"   Publisher: {article['publisher']}")
                lines.append(f"   Published: {article['published']}")
                if article.get("link"):
                    lines.append(f"   Link: {article['link']}")
            
            message = "\n".join(lines)
            
            return ExecutionResult(
                success=True,
                message=message,
                data={"news": news, "symbol": symbol, "count": len(news)}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error fetching news: {e}"
            )
    
    async def _get_history(self, context: Dict[str, Any]) -> ExecutionResult:
        """Get stock history/chart data."""
        if not YFINANCE_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="yfinance library required. Install with: pip install yfinance"
            )
        
        if not self._api:
            return ExecutionResult(
                success=False,
                message="Yahoo Finance API not initialized"
            )
        
        symbol = self._extract_symbol(context)
        if not symbol:
            return ExecutionResult(
                success=False,
                message="Please provide a stock symbol. Example: 'yahoo history AAPL' or 'stock chart MSFT'"
            )
        
        # Extract period and interval from context
        parameters = context.get("parameters", {})
        period = parameters.get("period") or "1mo"
        interval = parameters.get("interval") or "1d"
        
        # Common period aliases
        period_map = {
            "day": "1d", "daily": "1d",
            "week": "5d", "weekly": "1wk",
            "month": "1mo", "monthly": "1mo",
            "year": "1y", "yearly": "1y"
        }
        
        original_input = context.get("original_input", "").lower()
        for key, value in period_map.items():
            if key in original_input:
                period = value
                break
        
        try:
            history = self._api.get_stock_history(symbol, period=period, interval=interval)
            
            if history is None or history.empty:
                return ExecutionResult(
                    success=False,
                    message=f"Could not fetch history for {symbol}"
                )
            
            # Format output
            lines = [
                f"\nStock History: {symbol} ({period}, {interval} interval)",
                "=" * 80
            ]
            
            # Show summary statistics
            if not history.empty:
                latest = history.iloc[-1]
                oldest = history.iloc[0]
                
                lines.append(f"\nPeriod: {history.index[0].strftime('%Y-%m-%d')} to {history.index[-1].strftime('%Y-%m-%d')}")
                lines.append(f"Data Points: {len(history)}")
                
                if "Close" in history.columns:
                    lines.append(f"\nLatest Close: ${latest['Close']:.2f}")
                    lines.append(f"Opening Close: ${oldest['Close']:.2f}")
                    
                    price_change = latest['Close'] - oldest['Close']
                    price_change_pct = (price_change / oldest['Close']) * 100 if oldest['Close'] != 0 else 0
                    change_sign = "+" if price_change >= 0 else ""
                    lines.append(f"Period Change: {change_sign}{price_change:.2f} ({change_sign}{price_change_pct:.2f}%)")
                    
                    high = history['High'].max() if "High" in history.columns else None
                    low = history['Low'].min() if "Low" in history.columns else None
                    if high and low:
                        lines.append(f"Period High: ${high:.2f}")
                        lines.append(f"Period Low: ${low:.2f}")
                
                # Show last 5 data points
                lines.append("\nRecent Data Points:")
                lines.append("-" * 80)
                for idx, row in history.tail(5).iterrows():
                    date_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)
                    close = row.get('Close', 'N/A')
                    volume = row.get('Volume', 'N/A')
                    if isinstance(close, (int, float)):
                        close_str = f"${close:.2f}"
                    else:
                        close_str = str(close)
                    if isinstance(volume, (int, float)):
                        volume_str = f"{volume:,}"
                    else:
                        volume_str = str(volume)
                    lines.append(f"{date_str}: Close={close_str}, Volume={volume_str}")
            
            message = "\n".join(lines)
            
            return ExecutionResult(
                success=True,
                message=message,
                data={"history": history, "symbol": symbol, "period": period, "interval": interval}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error fetching history: {e}"
            )
    
    async def _search_stocks(self, context: Dict[str, Any]) -> ExecutionResult:
        """Search for stocks."""
        if not YFINANCE_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="yfinance library required. Install with: pip install yfinance"
            )
        
        if not self._api:
            return ExecutionResult(
                success=False,
                message="Yahoo Finance API not initialized"
            )
        
        # Extract query
        parameters = context.get("parameters", {})
        query = parameters.get("query") or parameters.get("search")
        
        if not query:
            original_input = context.get("original_input", "").lower()
            # Remove search keywords
            search_keywords = ["search", "find", "lookup", "yahoo", "finance", "stock"]
            query = original_input
            for keyword in search_keywords:
                query = query.replace(keyword, "").strip()
            
            if not query or len(query) < 2:
                return ExecutionResult(
                    success=False,
                    message="Please provide a search query. Example: 'yahoo search Apple' or 'find stock Microsoft'"
                )
        
        # Extract limit
        limit = 10
        if "entities" in context:
            for entity in context["entities"]:
                if entity.type == "number":
                    try:
                        limit = int(entity.value)
                        limit = max(1, min(20, limit))
                    except ValueError:
                        pass
        
        try:
            results = self._api.search_stocks(query, limit=limit)
            
            if not results:
                return ExecutionResult(
                    success=True,
                    message=f"No stocks found matching '{query}'",
                    data={"results": [], "query": query}
                )
            
            # Format output
            lines = [
                f"\nStock Search Results for '{query}' ({len(results)} found)",
                "=" * 80
            ]
            
            for i, result in enumerate(results, 1):
                lines.append(f"\n{i}. {result['symbol']} - {result['name']}")
                lines.append(f"   Exchange: {result['exchange']} | Type: {result['quoteType']}")
            
            message = "\n".join(lines)
            
            # Store in recent results
            self._recent_results = results
            
            return ExecutionResult(
                success=True,
                message=message,
                data={"results": results, "query": query, "count": len(results)}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error searching stocks: {e}"
            )
    
    async def _get_info(self, context: Dict[str, Any]) -> ExecutionResult:
        """Get detailed stock information."""
        if not YFINANCE_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="yfinance library required. Install with: pip install yfinance"
            )
        
        if not self._api:
            return ExecutionResult(
                success=False,
                message="Yahoo Finance API not initialized"
            )
        
        symbol = self._extract_symbol(context)
        if not symbol:
            return ExecutionResult(
                success=False,
                message="Please provide a stock symbol. Example: 'yahoo info AAPL' or 'stock info MSFT'"
            )
        
        try:
            info = self._api.get_stock_info(symbol)
            
            if not info:
                return ExecutionResult(
                    success=False,
                    message=f"Could not fetch information for {symbol}. Symbol may be invalid."
                )
            
            # Format output
            lines = [
                f"\nStock Information: {info.get('symbol', symbol)} - {info.get('longName') or info.get('shortName', 'N/A')}",
                "=" * 80
            ]
            
            # Key information fields
            key_fields = {
                "Sector": info.get("sector"),
                "Industry": info.get("industry"),
                "Country": info.get("country"),
                "Website": info.get("website"),
                "Business Summary": info.get("longBusinessSummary"),
                "Market Cap": info.get("marketCap"),
                "Employees": info.get("fullTimeEmployees"),
                "P/E Ratio": info.get("trailingPE"),
                "Forward P/E": info.get("forwardPE"),
                "EPS": info.get("trailingEps"),
                "Dividend Yield": info.get("dividendYield"),
                "52 Week High": info.get("fiftyTwoWeekHigh"),
                "52 Week Low": info.get("fiftyTwoWeekLow"),
                "Average Volume": info.get("averageVolume"),
            }
            
            for key, value in key_fields.items():
                if value is not None:
                    if key in ["Market Cap", "52 Week High", "52 Week Low"]:
                        value_str = self._format_currency(value, info.get("currency", "USD"))
                    elif key == "Business Summary":
                        if value:
                            summary = value[:200] + "..." if len(value) > 200 else value
                            lines.append(f"\n{key}:")
                            lines.append(f"  {summary}")
                        continue
                    elif key == "Dividend Yield" and isinstance(value, (int, float)):
                        value_str = f"{value * 100:.2f}%"
                    elif isinstance(value, (int, float)) and key == "EPS":
                        value_str = f"{value:.2f}"
                    elif isinstance(value, (int, float)) and "P/E" in key:
                        value_str = f"{value:.2f}"
                    else:
                        value_str = str(value)
                    
                    lines.append(f"{key}: {value_str}")
            
            message = "\n".join(lines)
            
            return ExecutionResult(
                success=True,
                message=message,
                data={"info": info, "symbol": symbol}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error fetching stock information: {e}"
            )
    
    async def _get_earnings(self, context: Dict[str, Any]) -> ExecutionResult:
        """Get earnings calendar."""
        if not YFINANCE_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="yfinance library required. Install with: pip install yfinance"
            )
        
        if not self._api:
            return ExecutionResult(
                success=False,
                message="Yahoo Finance API not initialized"
            )
        
        # Extract date range from context
        parameters = context.get("parameters", {})
        original_input = context.get("original_input", "").lower()
        
        start = parameters.get("start")
        end = parameters.get("end")
        
        # Check if asking for today's earnings
        today = datetime.now().date()
        if "today" in original_input:
            start = today.strftime("%Y-%m-%d")
            end = today.strftime("%Y-%m-%d")
        elif "this week" in original_input or "upcoming" in original_input:
            start = today.strftime("%Y-%m-%d")
            end_date = today + timedelta(days=7)
            end = end_date.strftime("%Y-%m-%d")
        
        # Extract limit
        limit = 50
        if "entities" in context:
            for entity in context["entities"]:
                if entity.type == "number":
                    try:
                        limit = int(entity.value)
                        limit = max(1, min(100, limit))
                    except ValueError:
                        pass
        
        try:
            earnings = self._api.get_earnings_calendar(start=start, end=end, limit=limit)
            
            # Debug: log the structure
            if earnings is not None:
                logger.info(f"Earnings calendar type: {type(earnings)}")
                if hasattr(earnings, 'columns'):
                    logger.info(f"Earnings calendar columns: {list(earnings.columns)}")
                if hasattr(earnings, 'shape'):
                    logger.info(f"Earnings calendar shape: {earnings.shape}")
                if not earnings.empty and hasattr(earnings, 'head'):
                    logger.info(f"First row sample: {earnings.head(1).to_dict('records') if hasattr(earnings.head(1), 'to_dict') else 'N/A'}")
            
            if earnings is None or earnings.empty:
                date_range = f" from {start} to {end}" if start else ""
                return ExecutionResult(
                    success=True,
                    message=f"No earnings reports found{date_range}.",
                    data={"earnings": [], "start": start, "end": end}
                )
            
            # Format output
            lines = [
                f"\nEarnings Calendar ({len(earnings)} companies)",
                "=" * 80
            ]
            
            if start:
                lines.append(f"Date Range: {start} to {end or 'default'}")
            
            # Display earnings calendar
            # Convert DataFrame to formatted output
            # First, let's check what columns we actually have
            if hasattr(earnings, 'columns'):
                logger.debug(f"Earnings calendar columns: {list(earnings.columns)}")
            
            for idx, row in earnings.head(limit).iterrows():
                # Try to access columns by position if names don't work
                try:
                    # Get all available data from the row
                    row_dict = row.to_dict() if hasattr(row, 'to_dict') else {}
                    
                    # Try different column name variations
                    symbol = (row_dict.get('Symbol') or row_dict.get('symbol') or 
                             row_dict.get('Ticker') or row_dict.get('ticker') or 'N/A')
                    company = (row_dict.get('Company') or row_dict.get('Company Name') or 
                              row_dict.get('company') or row_dict.get('companyshortname') or 'N/A')
                    earnings_date = (row_dict.get('Earnings Date') or row_dict.get('Date') or 
                                   row_dict.get('earnings_date') or row_dict.get('earningsdate') or 
                                   row_dict.get('startdatetime') or idx if hasattr(idx, 'strftime') else 'N/A')
                    eps_estimate = (row_dict.get('EPS Estimate') or row_dict.get('eps_estimate') or 
                                  row_dict.get('epsestimate') or 'N/A')
                    reported_eps = (row_dict.get('Reported EPS') or row_dict.get('reported_eps') or 
                                  row_dict.get('EPS') or row_dict.get('epsactual') or 'N/A')
                    
                    # Skip if we have no useful data
                    if symbol == 'N/A' and company == 'N/A':
                        continue
                    
                    lines.append(f"\n{symbol} - {company}")
                    if earnings_date and str(earnings_date) != 'N/A':
                        lines.append(f"   Earnings Date: {earnings_date}")
                    if eps_estimate and str(eps_estimate) not in ['nan', 'N/A', 'None']:
                        lines.append(f"   EPS Estimate: {eps_estimate}")
                    if reported_eps and str(reported_eps) not in ['nan', 'N/A', 'None']:
                        lines.append(f"   Reported EPS: {reported_eps}")
                except Exception as e:
                    logger.debug(f"Error processing earnings row: {e}")
                    continue
            
            message = "\n".join(lines)
            
            return ExecutionResult(
                success=True,
                message=message,
                data={"earnings": earnings, "start": start, "end": end, "count": len(earnings)}
            )
        except Exception as e:
            logger.exception(f"Error fetching earnings calendar: {e}")
            return ExecutionResult(
                success=False,
                message=f"Error fetching earnings calendar: {e}"
            )
    
    async def _get_economic_events(self, context: Dict[str, Any]) -> ExecutionResult:
        """Get economic events calendar."""
        if not YFINANCE_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="yfinance library required. Install with: pip install yfinance"
            )
        
        if not self._api:
            return ExecutionResult(
                success=False,
                message="Yahoo Finance API not initialized"
            )
        
        # Extract date range from context
        parameters = context.get("parameters", {})
        original_input = context.get("original_input", "").lower()
        
        start = parameters.get("start")
        end = parameters.get("end")
        
        # Check if asking for today's events
        today = datetime.now().date()
        if "today" in original_input:
            start = today.strftime("%Y-%m-%d")
            end = today.strftime("%Y-%m-%d")
        elif "this week" in original_input or "upcoming" in original_input:
            start = today.strftime("%Y-%m-%d")
            end_date = today + timedelta(days=7)
            end = end_date.strftime("%Y-%m-%d")
        
        # Extract limit
        limit = 50
        if "entities" in context:
            for entity in context["entities"]:
                if entity.type == "number":
                    try:
                        limit = int(entity.value)
                        limit = max(1, min(100, limit))
                    except ValueError:
                        pass
        
        try:
            events = self._api.get_economic_events_calendar(start=start, end=end, limit=limit)
            
            # Debug: log the structure
            if events is not None:
                logger.info(f"Economic events type: {type(events)}")
                if hasattr(events, 'columns'):
                    logger.info(f"Economic events columns: {list(events.columns)}")
                if hasattr(events, 'shape'):
                    logger.info(f"Economic events shape: {events.shape}")
                if not events.empty and hasattr(events, 'head'):
                    logger.info(f"First row sample: {events.head(1).to_dict('records') if hasattr(events.head(1), 'to_dict') else 'N/A'}")
            
            if events is None or events.empty:
                date_range = f" from {start} to {end}" if start else ""
                return ExecutionResult(
                    success=True,
                    message=f"No economic events found{date_range}.",
                    data={"events": [], "start": start, "end": end}
                )
            
            # Format output
            lines = [
                f"\nEconomic Events Calendar ({len(events)} events)",
                "=" * 80
            ]
            
            if start:
                lines.append(f"Date Range: {start} to {end or 'default'}")
            
            # Display economic events
            # First, let's check what columns we actually have
            if hasattr(events, 'columns'):
                logger.debug(f"Economic events columns: {list(events.columns)}")
            
            for idx, row in events.head(limit).iterrows():
                try:
                    # Get all available data from the row
                    row_dict = row.to_dict() if hasattr(row, 'to_dict') else {}
                    
                    # Try different column name variations
                    event = (row_dict.get('Event') or row_dict.get('event') or 
                            row_dict.get('Name') or row_dict.get('name') or 
                            row_dict.get('eventname') or 'N/A')
                    date = (row_dict.get('Date') or row_dict.get('date') or 
                           row_dict.get('gmtdatetime') or row_dict.get('startdatetime') or 
                           idx if hasattr(idx, 'strftime') else 'N/A')
                    country = (row_dict.get('Country') or row_dict.get('country') or 
                              row_dict.get('countrycode') or 'N/A')
                    impact = (row_dict.get('Impact') or row_dict.get('impact') or 
                             row_dict.get('importance') or 'N/A')
                    
                    # Skip if we have no useful data
                    if event == 'N/A':
                        continue
                    
                    lines.append(f"\n{event}")
                    if date and str(date) != 'N/A':
                        lines.append(f"   Date: {date}")
                    if country and str(country) not in ['nan', 'N/A', 'None']:
                        lines.append(f"   Country: {country}")
                    if impact and str(impact) not in ['nan', 'N/A', 'None']:
                        lines.append(f"   Impact: {impact}")
                except Exception as e:
                    logger.debug(f"Error processing economic event row: {e}")
                    continue
            
            message = "\n".join(lines)
            
            return ExecutionResult(
                success=True,
                message=message,
                data={"events": events, "start": start, "end": end, "count": len(events)}
            )
        except Exception as e:
            logger.exception(f"Error fetching economic events calendar: {e}")
            return ExecutionResult(
                success=False,
                message=f"Error fetching economic events calendar: {e}"
            )
    
    async def _check_status(self, context: Dict[str, Any]) -> ExecutionResult:
        """Check Yahoo Finance provider status."""
        is_available = YFINANCE_AVAILABLE and self._api is not None
        
        if is_available:
            message = "Yahoo Finance provider is active and ready to use.\n\nAvailable commands:\n- yahoo quote <SYMBOL> - Get stock quote\n- yahoo news <SYMBOL> - Get stock news\n- yahoo history <SYMBOL> - Get historical data\n- yahoo search <QUERY> - Search for stocks\n- yahoo info <SYMBOL> - Get detailed stock information\n- yahoo earnings - Get earnings calendar\n- yahoo economic events - Get economic events calendar"
        else:
            message = "Yahoo Finance provider not available. Install yfinance library with: pip install yfinance"
        
        return ExecutionResult(
            success=is_available,
            message=message,
            data={"available": is_available}
        )
