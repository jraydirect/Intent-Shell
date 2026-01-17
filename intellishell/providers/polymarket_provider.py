"""Polymarket provider for market data and trading operations."""

import json
import os
import hmac
import hashlib
import time
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from intellishell.providers.base import (
    BaseProvider,
    IntentTrigger,
    ExecutionResult,
    ProviderCapability
)
import logging

# Try to import OllamaClient for LLM interpretation
try:
    from intellishell.ai_bridge import OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    OllamaClient = None

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests library not available. Polymarket provider will have limited functionality.")


class PolymarketAPI:
    """Client for Polymarket API interactions."""
    
    GAMMA_API_BASE = "https://gamma-api.polymarket.com"
    CLOB_API_BASE = "https://clob.polymarket.com"
    DATA_API_BASE = "https://data-api.polymarket.com"
    # GraphQL Subgraph endpoints (alternative to Gamma API)
    GRAPHQL_SUBGRAPH_BASE = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs"
    
    def __init__(self, api_key: Optional[str] = None, secret: Optional[str] = None, 
                 passphrase: Optional[str] = None, wallet_address: Optional[str] = None):
        """
        Initialize Polymarket API client.
        
        Args:
            api_key: L2 API key
            secret: L2 API secret
            passphrase: L2 API passphrase
            wallet_address: Wallet address for authentication
        """
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.wallet_address = wallet_address
        self._authenticated = bool(api_key and secret and passphrase and wallet_address)
    
    def _sign_request(self, method: str, path: str, body: str = "", timestamp: Optional[int] = None) -> str:
        """
        Generate HMAC signature for L2 authentication.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            body: Request body as string
            timestamp: Unix timestamp (uses current if None)
            
        Returns:
            HMAC-SHA256 signature
        """
        if not self.secret:
            raise ValueError("API secret not configured")
        
        if timestamp is None:
            timestamp = int(time.time())
        
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _get_auth_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """
        Get authentication headers for L2 API requests.
        
        Args:
            method: HTTP method
            path: API path
            body: Request body
            
        Returns:
            Dictionary of headers
        """
        if not self._authenticated:
            return {}
        
        timestamp = int(time.time())
        signature = self._sign_request(method, path, body, timestamp)
        
        return {
            "POLY_ADDRESS": self.wallet_address,
            "POLY_API_KEY": self.api_key,
            "POLY_PASSPHRASE": self.passphrase,
            "POLY_SIGNATURE": signature,
            "POLY_TIMESTAMP": str(timestamp),
            "Content-Type": "application/json"
        }
    
    def get_top_markets(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get top markets by volume.
        
        Args:
            limit: Number of markets to return
            
        Returns:
            API response with markets data
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library required for Polymarket API")
        
        url = f"{self.GAMMA_API_BASE}/markets"
        # Clamp limit to API max (100)
        limit = min(limit, 100)
        params = {
            "limit": limit,
            "offset": 0,
            "order": "volume_num",
            "ascending": False,  # Boolean, not string
            "closed": False  # Only active markets (boolean)
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching top markets: {e}")
            raise
    
    def get_expiring_markets(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get markets expiring soon.
        
        Args:
            limit: Number of markets to return
            
        Returns:
            API response with markets data
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library required for Polymarket API")
        
        url = f"{self.GAMMA_API_BASE}/markets"
        # Clamp limit to API max (100)
        limit = min(limit, 100)
        params = {
            "limit": limit,
            "offset": 0,
            "order": "endDateISO",
            "ascending": True,  # Earliest first (boolean)
            "closed": False  # Only active markets (boolean)
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching expiring markets: {e}")
            raise
    
    def search_markets_graphql(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search markets using GraphQL subgraph (alternative to REST API).
        
        Args:
            query: Search query
            limit: Number of results to return
            
        Returns:
            List of markets matching the query
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library required for Polymarket API")
        
        # GraphQL query to search markets
        graphql_query = """
        query SearchMarkets($first: Int!, $query: String!) {
            markets(
                first: $first,
                where: {
                    active: true,
                    closed: false
                },
                orderBy: volume,
                orderDirection: desc
            ) {
                id
                question
                slug
                conditionId
                endDate
                volume
                liquidity
                outcomes
                outcomePrices
            }
        }
        """
        
        # Note: GraphQL subgraphs don't support full-text search directly
        # This would need client-side filtering, so we'll use REST API instead
        # Keeping this method structure for potential future use
        return []
    
    def search_markets(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search markets by query string.
        
        Note: Polymarket's Gamma API doesn't have a direct markets search endpoint.
        We use a hybrid approach:
        1. Try public-search endpoint (searches events, extracts markets)
        2. Fallback: Fetch top markets and filter client-side
        
        Args:
            query: Search query
            limit: Number of results to return
            
        Returns:
            List of markets matching the query
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library required for Polymarket API")
        
        markets = []
        query_lower = query.lower()
        
        # Approach 1: Use public-search endpoint (searches events)
        try:
            url = f"{self.GAMMA_API_BASE}/public-search"
            params = {
                "q": query,
                "limit_per_type": min(limit * 3, 50),  # Get more events to extract markets from
                "page": 1,
                "keep_closed_markets": 0,  # Only active markets
                "sort": "volume",
                "ascending": False,
                "search_tags": False,
                "search_profiles": False,
                "events_status": "active"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract markets from events
            events = data.get("events", [])
            for event in events:
                event_markets = event.get("markets", [])
                for market in event_markets:
                    # Only include active markets
                    if not market.get("closed", False):
                        # Try to get prices from event level if not in market
                        if not market.get("outcomePrices") and event.get("outcomePrices"):
                            market["outcomePrices"] = event.get("outcomePrices")
                        if not market.get("outcomes") and event.get("outcomes"):
                            market["outcomes"] = event.get("outcomes")
                        
                        # Store event reference for potential price lookup
                        market["_event_data"] = event
                        markets.append(market)
            
            logger.debug(f"Found {len(markets)} markets from public-search for query: {query}")
        except requests.RequestException as e:
            logger.warning(f"public-search endpoint failed: {e}, trying fallback")
        
        # Approach 2: Fetch more markets and filter client-side
        # The /markets endpoint doesn't support text search, so we fetch a larger set
        # and filter by question/description/slug on the client side
        # Only try this if we have very few results from public-search
        if len(markets) < min(limit, 5):  # Only fallback if we have very few results
            try:
                url = f"{self.GAMMA_API_BASE}/markets"
                # Don't send unsupported query parameters - fetch more markets and filter client-side
                # Clamp limit to API max
                fetch_limit = min(100, limit * 5)
                params = {
                    "limit": fetch_limit,
                    "offset": 0,
                    "closed": False,
                    "order": "volume_num",
                    "ascending": False
                }
                # Note: We do NOT send q, query, or search params as they cause 422 errors
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # Handle response format
                if isinstance(data, list):
                    all_markets = data
                else:
                    all_markets = data.get("data", [])
                
                # If API filtered, use those results; otherwise filter client-side
                if len(all_markets) <= limit * 2:  # If small result set, might be filtered
                    for market in all_markets:
                        market_id = market.get("conditionId") or market.get("id")
                        if not any(m.get("conditionId") == market_id or m.get("id") == market_id 
                                  for m in markets):
                            markets.append(market)
                else:
                    # Large result set, filter client-side with better matching
                    query_words = set(query_lower.split())
                    # Remove common stop words for better matching
                    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
                    query_words = {w for w in query_words if w not in stop_words and len(w) > 2}
                    
                    for market in all_markets:
                        question = market.get("question", "").lower()
                        description = market.get("description", "").lower()
                        slug = str(market.get("slug", "")).lower()
                        title = market.get("title", "").lower()
                        text = market.get("text", "").lower()
                        
                        # Normalize variations in market text
                        market_text = f"{question} {description} {slug} {title} {text}"
                        market_text = market_text.replace("u.s.", "us").replace("u.s", "us")
                        
                        # Check if significant query words appear in market text
                        matching_words = sum(1 for word in query_words if word in market_text)
                        # Require at least 2 matching words (or 1 if query is very short)
                        min_matches = 2 if len(query_words) > 2 else 1
                        
                        if matching_words >= min_matches or query_lower in market_text:
                            market_id = market.get("conditionId") or market.get("id")
                            if not any(m.get("conditionId") == market_id or m.get("id") == market_id 
                                      for m in markets):
                                markets.append(market)
                
                logger.debug(f"Added {len(markets)} total markets after /markets fallback search")
            except requests.RequestException as e:
                # Silently fail - this is just a fallback, primary search already worked
                logger.debug(f"/markets fallback search failed (non-critical): {e}")
        
        # Approach 3: Try alternative endpoint patterns
        if len(markets) < limit:
            alternative_endpoints = [
                f"{self.GAMMA_API_BASE}/markets/search",
                f"{self.GAMMA_API_BASE}/search/markets",
                f"{self.DATA_API_BASE}/markets/search",
            ]
            
            for endpoint_url in alternative_endpoints:
                try:
                    params = {"q": query, "limit": limit, "closed": False}
                    response = requests.get(endpoint_url, params=params, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list):
                            found_markets = data
                        elif isinstance(data, dict):
                            found_markets = data.get("data", []) or data.get("markets", [])
                        else:
                            found_markets = []
                        
                        for market in found_markets:
                            market_id = market.get("conditionId") or market.get("id")
                            if not any(m.get("conditionId") == market_id or m.get("id") == market_id 
                                      for m in markets):
                                markets.append(market)
                        
                        logger.info(f"Found {len(found_markets)} markets via {endpoint_url}")
                        break  # Success, stop trying other endpoints
                except requests.RequestException:
                    continue  # Try next endpoint
        
        # Filter out expired markets
        active_markets = PolymarketProvider._filter_active_markets(markets)
        
        # Return as list (consistent with other methods)
        return active_markets[:limit]
    
    def get_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed market information including outcome prices.
        
        Args:
            market_id: Market condition ID or slug
            
        Returns:
            Market data with prices or None if not found
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library required for Polymarket API")
        
        # Method 1: Direct endpoint by conditionId (BEST METHOD - most reliable)
        # Try this FIRST for all market IDs (conditionIds are typically 0x... format)
        try:
            url = f"{self.GAMMA_API_BASE}/markets/{market_id}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                market = response.json()
                logger.debug(f"Successfully fetched market {market_id} via direct endpoint")
                # Log what we got for debugging
                if market.get("outcomePrices"):
                    logger.debug(f"Found outcomePrices in response")
                return market
            elif response.status_code == 404:
                logger.debug(f"Market {market_id} not found at direct endpoint (404)")
        except requests.RequestException as e:
            logger.debug(f"Direct endpoint /markets/{market_id} failed: {e}")
        
        # Method 2: Filter by condition_ids parameter (array format)
        try:
            url = f"{self.GAMMA_API_BASE}/markets"
            # Try condition_ids as JSON array string
            params = {"condition_ids": json.dumps([market_id]), "limit": 1}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    logger.debug(f"Found market via condition_ids array param")
                    return data[0]
                elif isinstance(data, dict):
                    markets = data.get("data", [])
                    if markets:
                        logger.debug(f"Found market via condition_ids array param (dict response)")
                        return markets[0]
        except requests.RequestException as e:
            logger.debug(f"condition_ids array param failed: {e}")
        
        # Method 3: Fetch markets and filter client-side by conditionId (fallback)
        try:
            url = f"{self.GAMMA_API_BASE}/markets"
            params = {"limit": 100, "closed": False}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                markets_list = data if isinstance(data, list) else data.get("data", [])
                # Find matching market by conditionId
                for m in markets_list:
                    if (m.get("conditionId") == market_id or 
                        m.get("id") == market_id or
                        str(m.get("conditionId", "")).lower() == str(market_id).lower()):
                        logger.debug(f"Found market by conditionId in fetched list: {market_id}")
                        return m
        except requests.RequestException as e:
            logger.debug(f"Client-side filtering failed: {e}")
        
        # Method 4: Try by slug
        try:
            url = f"{self.GAMMA_API_BASE}/markets"
            params = {"slug": [market_id], "limit": 1}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    return data[0]
                elif isinstance(data, dict):
                    markets = data.get("data", [])
                    if markets:
                        return markets[0]
        except requests.RequestException as e:
            logger.debug(f"Failed to fetch market by slug {market_id}: {e}")
        
        # Only log warning if we actually tried (don't spam if market_id is None)
        if market_id:
            logger.debug(f"Could not fetch market details for {market_id} using any method")
        return None
    
    def place_order(self, market_id: str, outcome: str, side: str, size: str, price: str) -> Dict[str, Any]:
        """
        Place an order on Polymarket.
        
        Args:
            market_id: Market condition ID
            outcome: Outcome token ID (e.g., "0x..." for YES/NO)
            side: "BUY" or "SELL"
            size: Order size (as string, e.g., "1.5")
            price: Price per share (as string, e.g., "0.65")
            
        Returns:
            API response with order data
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library required for Polymarket API")
        
        if not self._authenticated:
            raise ValueError("API credentials required for placing orders")
        
        url = f"{self.CLOB_API_BASE}/orders"
        
        # Construct order payload
        order_data = {
            "market": market_id,
            "asset_id": outcome,
            "side": side.upper(),
            "size": size,
            "price": price,
            "fee_rate": "0.03",  # Default fee rate (3%)
            "expiration": int(time.time()) + 86400,  # 24 hours from now
        }
        
        body = json.dumps(order_data)
        headers = self._get_auth_headers("POST", "/orders", body)
        
        try:
            response = requests.post(url, headers=headers, data=body, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error placing order: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise


class PolymarketConfig:
    """Manages Polymarket API credentials storage."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config manager.
        
        Args:
            config_path: Path to config file (default: ~/.intellishell/polymarket.json)
        """
        if config_path is None:
            config_dir = Path.home() / ".intellishell"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "polymarket.json"
        
        self.config_path = config_path
        self._config: Dict[str, str] = {}
        self._load()
    
    def _load(self) -> None:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Error loading Polymarket config: {e}")
                self._config = {}
        else:
            self._config = {}
    
    def _save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            # Set restrictive permissions (owner read/write only)
            os.chmod(self.config_path, 0o600)
        except IOError as e:
            logger.error(f"Error saving Polymarket config: {e}")
            raise
    
    def set_credentials(self, api_key: str, secret: str, passphrase: str, wallet_address: str) -> None:
        """
        Store API credentials.
        
        Args:
            api_key: L2 API key
            secret: L2 API secret
            passphrase: L2 API passphrase
            wallet_address: Wallet address
        """
        self._config = {
            "api_key": api_key,
            "secret": secret,
            "passphrase": passphrase,
            "wallet_address": wallet_address
        }
        self._save()
        logger.info("Polymarket credentials saved")
    
    def get_credentials(self) -> Optional[Dict[str, str]]:
        """
        Get stored API credentials.
        
        Returns:
            Dictionary with credentials or None if not configured
        """
        if not self._config or not all(k in self._config for k in ["api_key", "secret", "passphrase", "wallet_address"]):
            return None
        return self._config.copy()
    
    def clear_credentials(self) -> None:
        """Clear stored credentials."""
        self._config = {}
        if self.config_path.exists():
            self.config_path.unlink()
        logger.info("Polymarket credentials cleared")
    
    def is_configured(self) -> bool:
        """Check if credentials are configured."""
        return self.get_credentials() is not None


class PolymarketProvider(BaseProvider):
    """Provider for Polymarket market data and trading operations."""
    
    def __init__(self):
        """Initialize Polymarket provider."""
        super().__init__()
        self.config = PolymarketConfig()
        self._api: Optional[PolymarketAPI] = None
        self._ollama: Optional[Any] = None
        # Store recent market results for context (indexed by number)
        self._recent_markets: List[Dict[str, Any]] = []
        self._initialize_api()
        self._initialize_llm()
    
    def _initialize_llm(self) -> None:
        """Initialize LLM client for interpreting market data."""
        if OLLAMA_AVAILABLE and OllamaClient:
            try:
                self._ollama = OllamaClient()
                if not self._ollama.is_available():
                    self._ollama = None
                    logger.debug("Ollama not available for market interpretation")
            except Exception as e:
                logger.debug(f"Could not initialize Ollama: {e}")
                self._ollama = None
    
    @staticmethod
    def _format_currency(value: Any) -> str:
        """
        Safely format a currency value that might be a number, string, or None.
        
        Args:
            value: Value to format (can be int, float, str, or None)
            
        Returns:
            Formatted string like "$1,234" or "N/A"
        """
        if value is None:
            return "N/A"
        
        try:
            # Try to convert to float first
            num_value = float(value)
            return f"${num_value:,.0f}"
        except (ValueError, TypeError):
            # If conversion fails, return as string or N/A
            return str(value) if value else "N/A"
    
    @staticmethod
    def _get_end_date(market: Dict[str, Any]) -> str:
        """
        Extract end date from market data, trying multiple field names.
        
        Args:
            market: Market data dictionary
            
        Returns:
            Formatted date string or "N/A"
        """
        # Try various date field names
        date_fields = [
            "endDateISO",
            "endDate",
            "end_date_iso",
            "end_date",
            "endDateIso",
            "endTime",
            "end_time",
            "resolutionDate",
            "resolution_date"
        ]
        
        for field in date_fields:
            date_value = market.get(field)
            if date_value:
                # Format date string (handle ISO format)
                try:
                    if isinstance(date_value, str):
                        # Extract date part if it's ISO format with time
                        if "T" in date_value:
                            return date_value.split("T")[0]
                        return date_value[:10] if len(date_value) >= 10 else date_value
                    return str(date_value)
                except Exception:
                    return str(date_value)
        
        return "N/A"
    
    @staticmethod
    def _get_end_date_datetime(market: Dict[str, Any]) -> Optional[datetime]:
        """
        Extract end date as datetime object for comparison.
        
        Args:
            market: Market data dictionary
            
        Returns:
            datetime object or None if not found/invalid
        """
        date_fields = [
            "endDateISO",
            "endDate",
            "end_date_iso",
            "end_date",
            "endDateIso",
            "endTime",
            "end_time",
            "resolutionDate",
            "resolution_date"
        ]
        
        for field in date_fields:
            date_value = market.get(field)
            if date_value:
                try:
                    if isinstance(date_value, str):
                        # Parse ISO format dates
                        if "T" in date_value:
                            # Try parsing with timezone info
                            try:
                                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                            except ValueError:
                                # Fallback: parse just the date part
                                date_part = date_value.split("T")[0]
                                return datetime.strptime(date_part, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        else:
                            # Just date string
                            return datetime.strptime(date_value[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    elif isinstance(date_value, (int, float)):
                        # Unix timestamp
                        return datetime.fromtimestamp(date_value, tz=timezone.utc)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Error parsing date {date_value}: {e}")
                    continue
        
        return None
    
    @staticmethod
    def _filter_active_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out markets that have already ended.
        
        Args:
            markets: List of market dictionaries
            
        Returns:
            Filtered list containing only active (not expired) markets
        """
        now = datetime.now(timezone.utc)
        active_markets = []
        
        for market in markets:
            end_date = PolymarketProvider._get_end_date_datetime(market)
            # Include market if:
            # 1. No end date (assume active)
            # 2. End date is in the future
            if end_date is None or end_date > now:
                active_markets.append(market)
        
        return active_markets
    
    def _initialize_api(self) -> None:
        """Initialize API client with stored credentials."""
        creds = self.config.get_credentials()
        if creds:
            self._api = PolymarketAPI(
                api_key=creds.get("api_key"),
                secret=creds.get("secret"),
                passphrase=creds.get("passphrase"),
                wallet_address=creds.get("wallet_address")
            )
        else:
            self._api = PolymarketAPI()
    
    @property
    def name(self) -> str:
        return "polymarket"
    
    @property
    def description(self) -> str:
        return "Polymarket market data and trading operations"
    
    def _initialize_triggers(self) -> None:
        """Initialize Polymarket-related triggers."""
        self.capabilities = [
            ProviderCapability.READ_ONLY,
            ProviderCapability.ASYNC,
        ]
        
        self.triggers = [
            IntentTrigger(
                pattern="poly top markets",
                intent_name="poly_top_markets",
                weight=1.0,
                aliases=[
                    "polymarket top markets",
                    "poly top",
                    "show top markets",
                    "top polymarket markets",
                    "poly trending"
                ]
            ),
            IntentTrigger(
                pattern="poly expiring",
                intent_name="poly_expiring",
                weight=1.0,
                aliases=[
                    "polymarket expiring",
                    "poly expiring soon",
                    "expiring markets",
                    "poly markets expiring",
                    "soon expiring markets"
                ]
            ),
            IntentTrigger(
                pattern="poly search",
                intent_name="poly_search",
                weight=1.0,
                aliases=[
                    "polymarket search",
                    "search polymarket",
                    "poly find",
                    "find market",
                    "search markets"
                ]
            ),
            IntentTrigger(
                pattern="poly connect",
                intent_name="poly_connect",
                weight=1.0,
                aliases=[
                    "polymarket connect",
                    "poly api key",
                    "connect polymarket",
                    "poly setup",
                    "polymarket setup"
                ]
            ),
            IntentTrigger(
                pattern="poly place bet",
                intent_name="poly_place_bet",
                weight=1.0,
                aliases=[
                    "polymarket bet",
                    "poly bet",
                    "place bet",
                    "poly buy",
                    "poly sell",
                    "polymarket trade"
                ]
            ),
            IntentTrigger(
                pattern="poly status",
                intent_name="poly_status",
                weight=1.0,
                aliases=[
                    "polymarket status",
                    "poly account",
                    "poly connected"
                ]
            ),
            IntentTrigger(
                pattern="what are the odds",
                intent_name="poly_search",
                weight=1.2,  # Higher weight to match probability questions
                aliases=[
                    "what's the probability",
                    "what is the probability",
                    "what are the chances",
                    "what's the chance",
                    "odds that",
                    "probability that",
                    "chance that",
                    "what percent chance",
                    "what percentage",
                    "how likely",
                    "what are the odds that",
                    "what's the probability that",
                    "what is the probability that",
                    "what are the chances that",
                    "how likely is it that",
                    "how likely that"
                ]
            ),
            IntentTrigger(
                pattern="will the",
                intent_name="poly_search",
                weight=1.3,  # Very high weight for "will the" prediction questions
                aliases=[
                    "will the us",
                    "will the united states",
                    "will trump",
                    "will biden",
                    "will [country]",
                    "will [person]",
                    "will [event] happen",
                    "will [something] happen",
                    "will [question]"
                ]
            ),
            IntentTrigger(
                pattern="will",
                intent_name="poly_search",
                weight=1.2,  # High weight for "will" prediction questions
                aliases=[
                    "will [something]",
                    "will [event]",
                    "will [question]",
                    "will [person]",
                    "will [country]"
                ]
            ),
            IntentTrigger(
                pattern="open market",
                intent_name="poly_open_market",
                weight=1.2,  # Higher weight to prioritize over place_bet
                aliases=[
                    "open market",
                    "open market [number]",
                    "open market 1",
                    "open market 2",
                    "open market 3",
                    "open polymarket",
                    "open polymarket [number]",
                    "view market",
                    "view market [number]",
                    "show market",
                    "show market [number]",
                    "go to market",
                    "go to market [number]",
                    "poly open",
                    "poly open [number]",
                    "open the market",
                    "open that market"
                ]
            ),
        ]
    
    async def execute(
        self,
        intent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute Polymarket intent."""
        context = context or {}
        
        try:
            if intent_name == "poly_top_markets":
                return await self._top_markets(context)
            elif intent_name == "poly_expiring":
                return await self._expiring_markets(context)
            elif intent_name == "poly_search":
                return await self._search_markets(context)
            elif intent_name == "poly_connect":
                return await self._connect_account(context)
            elif intent_name == "poly_place_bet":
                return await self._place_bet(context)
            elif intent_name == "poly_status":
                return await self._check_status(context)
            elif intent_name == "poly_open_market":
                return await self._open_market(context)
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown Polymarket intent: {intent_name}"
                )
        except Exception as e:
            logger.exception(f"Polymarket provider error: {e}")
            return ExecutionResult(
                success=False,
                message=f"Polymarket operation failed: {e}"
            )
    
    async def _top_markets(self, context: Dict[str, Any]) -> ExecutionResult:
        """Get top markets by volume."""
        if not REQUESTS_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="requests library required. Install with: pip install requests"
            )
        
        # Extract limit from context
        limit = 20
        if "entities" in context:
            for entity in context["entities"]:
                if entity.type == "number":
                    try:
                        limit = int(entity.value)
                        limit = max(1, min(100, limit))  # Clamp between 1-100
                    except ValueError:
                        pass
        
        try:
            # Request more markets to account for filtering out expired ones
            fetch_limit = min(limit * 3, 100)  # API max is 100
            data = self._api.get_top_markets(limit=fetch_limit)
            # Handle both list and dict responses
            if isinstance(data, list):
                markets = data
            else:
                markets = data.get("data", [])
            
            # Filter out expired markets
            markets = self._filter_active_markets(markets)
            # Limit to requested amount after filtering
            markets = markets[:limit]
            
            if not markets:
                return ExecutionResult(
                    success=True,
                    message="No markets found",
                    data={"markets": []}
                )
            
            # Format output
            lines = [f"\nTop {len(markets)} Polymarket Markets (by volume)"]
            lines.append("=" * 80)
            
            for i, market in enumerate(markets[:limit], 1):
                question = market.get("question", "N/A")
                volume = market.get("volume", 0)
                liquidity = market.get("liquidity", 0)
                end_date = self._get_end_date(market)
                market_id = market.get("conditionId", "N/A")
                
                # Format volume and liquidity
                vol_str = self._format_currency(volume)
                liq_str = self._format_currency(liquidity)
                
                lines.append(f"\n{i}. {question}")
                lines.append(f"   Volume: {vol_str} | Liquidity: {liq_str}")
                lines.append(f"   Ends: {end_date}")
                lines.append(f"   ID: {market_id[:20]}...")
            
            message = "\n".join(lines)
            
            return ExecutionResult(
                success=True,
                message=message,
                data={"markets": markets, "count": len(markets)}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error fetching top markets: {e}"
            )
    
    async def _expiring_markets(self, context: Dict[str, Any]) -> ExecutionResult:
        """Get markets expiring soon."""
        if not REQUESTS_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="requests library required. Install with: pip install requests"
            )
        
        # Extract limit from context
        limit = 20
        if "entities" in context:
            for entity in context["entities"]:
                if entity.type == "number":
                    try:
                        limit = int(entity.value)
                        limit = max(1, min(100, limit))
                    except ValueError:
                        pass
        
        try:
            # Request more markets to account for filtering out expired ones
            fetch_limit = min(limit * 3, 100)  # API max is 100
            data = self._api.get_expiring_markets(limit=fetch_limit)
            # Handle both list and dict responses
            if isinstance(data, list):
                markets = data
            else:
                markets = data.get("data", [])
            
            # Filter out expired markets (only show active ones)
            markets = self._filter_active_markets(markets)
            # Limit to requested amount after filtering
            markets = markets[:limit]
            
            if not markets:
                return ExecutionResult(
                    success=True,
                    message="No expiring markets found",
                    data={"markets": []}
                )
            
            # Format output
            lines = [f"\nPolymarket Markets Expiring Soon ({len(markets)} markets)"]
            lines.append("=" * 80)
            
            for i, market in enumerate(markets[:limit], 1):
                question = market.get("question", "N/A")
                end_date = self._get_end_date(market)
                volume = market.get("volume", 0)
                market_id = market.get("conditionId", "N/A")
                
                vol_str = self._format_currency(volume)
                
                lines.append(f"\n{i}. {question}")
                lines.append(f"   Expires: {end_date}")
                lines.append(f"   Volume: {vol_str}")
                lines.append(f"   ID: {market_id[:20]}...")
            
            message = "\n".join(lines)
            
            # Store markets in context for "open market" command
            self._recent_markets = markets[:limit]
            
            return ExecutionResult(
                success=True,
                message=message,
                data={"markets": markets, "count": len(markets)}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error fetching expiring markets: {e}"
            )
    
    async def _search_markets(self, context: Dict[str, Any]) -> ExecutionResult:
        """Search markets by query."""
        if not REQUESTS_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="requests library required. Install with: pip install requests"
            )
        
        # Extract search query from context
        query = ""
        original_input = context.get("original_input", "").lower()
        
        # Try to extract query after "search" keyword
        search_keywords = ["search", "find"]
        for keyword in search_keywords:
            if keyword in original_input:
                parts = original_input.split(keyword, 1)
                if len(parts) > 1:
                    query = parts[1].strip()
                    # Remove "poly" and "polymarket" if present
                    query = query.replace("poly", "").replace("polymarket", "").strip()
                    break
        
        # Also check parameters from LLM
        if not query and context.get("parameters"):
            params = context["parameters"]
            query = params.get("query") or params.get("search") or params.get("market")
        
        if not query:
            return ExecutionResult(
                success=False,
                message="Please provide a search query. Example: 'poly search election'"
            )
        
        # Extract limit
        limit = 20
        if "entities" in context:
            for entity in context["entities"]:
                if entity.type == "number":
                    try:
                        limit = int(entity.value)
                        limit = max(1, min(100, limit))
                    except ValueError:
                        pass
        
        try:
            # Search now returns a list directly from public-search endpoint
            markets = self._api.search_markets(query, limit=limit)
            
            # Ensure it's a list
            if not isinstance(markets, list):
                markets = []
            
            if not markets:
                return ExecutionResult(
                    success=True,
                    message=f"No markets found matching '{query}'. Try a different search term or browse top markets with 'poly top markets'.",
                    data={"markets": [], "query": query}
                )
            
            # Format output
            lines = [f"\nPolymarket Search Results for '{query}' ({len(markets)} found)"]
            lines.append("=" * 80)
            
            for i, market in enumerate(markets[:limit], 1):
                question = market.get("question", "N/A")
                volume = market.get("volume", 0)
                end_date = self._get_end_date(market)
                market_id = market.get("conditionId", "N/A")
                
                vol_str = self._format_currency(volume)
                
                # Extract and show probability if available
                prob_data = self._extract_probability(market, fetch_details=True)
                
                lines.append(f"\n{i}. {question}")
                
                if prob_data and prob_data.get("probability") is not None:
                    if prob_data.get("all_probabilities") and len(prob_data["all_probabilities"]) > 1:
                        # Show all outcomes
                        prob_info = " | ".join([f"{outcome}: {prob:.1f}%" 
                                               for outcome, prob in prob_data["all_probabilities"].items()])
                        lines.append(f"   Odds: {prob_info}")
                    else:
                        # Show primary probability
                        lines.append(f"   Odds ({prob_data['probability_label']}): {prob_data['probability']:.1f}%")
                
                lines.append(f"   Volume: {vol_str} | Ends: {end_date}")
                lines.append(f"   ID: {market_id[:20]}...")
            
            message = "\n".join(lines)
            
            # If this looks like a probability question, add LLM interpretation
            original_input = context.get("original_input", "").lower()
            is_probability_question = any(phrase in original_input for phrase in [
                "odds", "probability", "chance", "likely", "percent"
            ])
            
            llm_interpretation = None
            if is_probability_question and markets:
                try:
                    # Extract probabilities from markets (always try to fetch details for probability questions)
                    market_data_with_probs = []
                    for market in markets[:5]:
                        prob_data = self._extract_probability(market, fetch_details=True)
                        volume = market.get("volume", 0) or market.get("volume24hr", 0) or 0
                        
                        market_info = {
                            "question": market.get("question", "N/A"),
                            "volume": volume,
                            "volume_str": self._format_currency(volume)
                        }
                        
                        if prob_data:
                            market_info.update({
                                "probability": prob_data.get("probability"),
                                "probability_label": prob_data.get("probability_label"),
                                "all_probabilities": prob_data.get("all_probabilities")
                            })
                            market_data_with_probs.append(market_info)
                        else:
                            # Include even without probability for context
                            market_data_with_probs.append(market_info)
                    
                    # Generate LLM interpretation if we have markets (with or without probabilities)
                    if market_data_with_probs:
                        if self._ollama and self._ollama.is_available():
                            try:
                                llm_interpretation = self._generate_llm_interpretation(
                                    original_input=context.get("original_input", query),
                                    query=query,
                                    markets=market_data_with_probs,
                                    probabilities_summary={
                                        "primary_probability": market_data_with_probs[0].get("probability") if market_data_with_probs and market_data_with_probs[0].get("probability") else None,
                                        "all_markets": market_data_with_probs
                                    }
                                )
                            except Exception as e:
                                logger.debug(f"LLM interpretation generation failed: {e}")
                        else:
                            logger.debug("Ollama not available for LLM interpretation")
                except Exception as e:
                    logger.exception(f"LLM interpretation in search failed: {e}")
            
            final_message = message
            if llm_interpretation:
                final_message = f"{llm_interpretation}\n\n{message}"
            
            # Store markets in context for "open market" command
            self._recent_markets = markets[:limit]
            
            return ExecutionResult(
                success=True,
                message=final_message,
                data={
                    "markets": markets,
                    "query": query,
                    "count": len(markets),
                    "llm_interpretation": llm_interpretation
                }
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error searching markets: {e}"
            )
    
    async def _connect_account(self, context: Dict[str, Any]) -> ExecutionResult:
        """Connect Polymarket account with API credentials."""
        # Extract credentials from context
        original_input = context.get("original_input", "")
        parameters = context.get("parameters", {})
        
        # Try to get from parameters first (LLM extracted)
        api_key = parameters.get("api_key") or parameters.get("apiKey")
        secret = parameters.get("secret")
        passphrase = parameters.get("passphrase")
        wallet_address = parameters.get("wallet_address") or parameters.get("walletAddress") or parameters.get("address")
        
        # If not in parameters, try to parse from input
        # This is a fallback - ideally LLM should extract these
        if not all([api_key, secret, passphrase, wallet_address]):
            # Open browser to Polymarket API key generation page
            api_key_url = "https://polymarket.com/settings/api-keys"
            try:
                # Try to open Brave first
                brave_paths = [
                    "brave.exe",
                    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                    os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
                ]
                
                brave_found = False
                for brave_path in brave_paths:
                    if os.path.exists(brave_path) or brave_path == "brave.exe":
                        try:
                            subprocess.Popen([brave_path, api_key_url], shell=False)
                            brave_found = True
                            break
                        except Exception as e:
                            logger.debug(f"Failed to launch Brave from {brave_path}: {e}")
                            continue
                
                if not brave_found:
                    # Fallback: use default browser
                    os.startfile(api_key_url)
                
                return ExecutionResult(
                    success=False,
                    message=f"""Opening Polymarket API key settings in your browser...

To connect your Polymarket account, you need to:
1. Sign in to Polymarket (if not already signed in)
2. Generate L2 API credentials from the settings page
3. Then run: poly connect api_key=YOUR_KEY secret=YOUR_SECRET passphrase=YOUR_PASSPHRASE wallet_address=YOUR_ADDRESS

Your credentials will be stored securely in ~/.intellishell/polymarket.json

Note: API keys are only needed for placing bets. You can view markets without connecting."""
                )
            except Exception as e:
                logger.debug(f"Could not open browser: {e}")
                return ExecutionResult(
                    success=False,
                    message=f"""To connect your Polymarket account, provide your API credentials:
                    
Usage: poly connect <api_key> <secret> <passphrase> <wallet_address>

Or use the format:
  poly connect api_key=YOUR_KEY secret=YOUR_SECRET passphrase=YOUR_PASSPHRASE wallet_address=YOUR_ADDRESS

Note: You need to generate L2 API credentials from your Polymarket account first.
Visit: https://polymarket.com/settings/api-keys
These credentials are stored securely in ~/.intellishell/polymarket.json"""
                )
        
        try:
            self.config.set_credentials(api_key, secret, passphrase, wallet_address)
            self._initialize_api()
            
            return ExecutionResult(
                success=True,
                message="Polymarket account connected successfully! Credentials saved.",
                data={"configured": True}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error saving credentials: {e}"
            )
    
    async def _place_bet(self, context: Dict[str, Any]) -> ExecutionResult:
        """Place a bet/order on Polymarket."""
        if not self.config.is_configured():
            return ExecutionResult(
                success=False,
                message="Polymarket account not connected. Use 'poly connect' first."
            )
        
        if not REQUESTS_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="requests library required. Install with: pip install requests"
            )
        
        # Extract order parameters
        parameters = context.get("parameters", {})
        original_input = context.get("original_input", "")
        
        market_id = parameters.get("market_id") or parameters.get("market")
        outcome = parameters.get("outcome") or parameters.get("token")
        side = parameters.get("side") or "BUY"
        size = parameters.get("size") or parameters.get("amount")
        price = parameters.get("price")
        
        # Validate required parameters
        if not all([market_id, outcome, size, price]):
            return ExecutionResult(
                success=False,
                message="""Missing required parameters for placing a bet.

Required:
  - market_id: Market condition ID
  - outcome: Outcome token ID (e.g., "0x..." for YES/NO)
  - size: Order size (e.g., "1.5")
  - price: Price per share (e.g., "0.65")
  - side: "BUY" or "SELL" (default: BUY)

Example: poly place bet market_id=0x... outcome=0x... size=1.5 price=0.65 side=BUY"""
            )
        
        try:
            result = self._api.place_order(
                market_id=market_id,
                outcome=outcome,
                side=side.upper(),
                size=str(size),
                price=str(price)
            )
            
            return ExecutionResult(
                success=True,
                message=f"Order placed successfully! Order ID: {result.get('id', 'N/A')}",
                data={"order": result}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Error placing order: {e}"
            )
    
    async def _check_status(self, context: Dict[str, Any]) -> ExecutionResult:
        """Check Polymarket connection status."""
        is_configured = self.config.is_configured()
        
        if is_configured:
            creds = self.config.get_credentials()
            wallet = creds.get("wallet_address", "N/A") if creds else "N/A"
            message = f"Polymarket account connected\nWallet: {wallet[:10]}...{wallet[-6:] if len(wallet) > 16 else wallet}"
        else:
            message = "Polymarket account not connected. Use 'poly connect' to set up API credentials."
        
        return ExecutionResult(
            success=is_configured,
            message=message,
            data={"configured": is_configured}
        )
    
    def _extract_probability(self, market: Dict[str, Any], fetch_details: bool = True) -> Optional[Dict[str, Any]]:
        """
        Extract probability data from a market.
        
        If prices aren't available, tries to fetch detailed market data.
        Handles outcomePrices as both arrays and JSON-encoded strings.
        Also checks for prices in nested event data or other field names.
        
        Args:
            market: Market data dictionary
            fetch_details: Whether to fetch detailed market data if prices missing
            
        Returns:
            Dict with 'probability', 'probability_label', 'outcomes', 'outcome_prices' or None
        """
        # Try multiple field names and locations for outcomes and prices
        outcomes = (market.get("outcomes") or 
                   market.get("outcomeNames") or
                   market.get("outcome") or
                   [])
        outcome_prices = (market.get("outcomePrices") or 
                         market.get("prices") or
                         market.get("outcome_prices") or
                         market.get("outcomePrices") or
                         [])
        
        # Check if prices might be in a nested structure (e.g., from event data)
        if not outcome_prices and "event" in market:
            event_data = market.get("event", {})
            outcome_prices = event_data.get("outcomePrices") or outcome_prices
        
        # Handle case where outcomes/outcomePrices might be JSON-encoded strings
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except (json.JSONDecodeError, TypeError):
                pass
        
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Also check if it's a single value that needs to be converted
        if not isinstance(outcome_prices, list) and outcome_prices:
            if isinstance(outcome_prices, (int, float)):
                # Single price value - create array
                outcome_prices = [outcome_prices]
            elif isinstance(outcome_prices, str) and outcome_prices.replace(".", "").isdigit():
                # Single price as string
                try:
                    outcome_prices = [float(outcome_prices)]
                except ValueError:
                    pass
        
        # If no prices, try to fetch detailed market data
        if (not outcomes or not outcome_prices) and fetch_details:
            # Try multiple ID fields - conditionId is most reliable, but also try market ID
            market_id = (market.get("conditionId") or 
                        market.get("id") or 
                        market.get("marketId") or
                        market.get("slug"))
            
            # Also check event data for prices
            event_data = market.get("_event_data") or market.get("event")
            if event_data and not outcome_prices:
                event_prices = event_data.get("outcomePrices")
                event_outcomes = event_data.get("outcomes")
                if event_prices:
                    outcome_prices = event_prices
                if event_outcomes:
                    outcomes = event_outcomes
            
            if market_id and (not outcomes or not outcome_prices):
                try:
                    # Try conditionId first, then market ID if different
                    ids_to_try = [str(market_id)]
                    if market.get("id") and str(market.get("id")) != str(market_id):
                        ids_to_try.append(str(market.get("id")))
                    
                    detailed_market = None
                    for try_id in ids_to_try:
                        logger.debug(f"Fetching market details for {try_id} to get outcome prices")
                        detailed_market = self._api.get_market_details(try_id)
                        if detailed_market:
                            logger.debug(f"Successfully fetched details using ID: {try_id}")
                            break
                    
                    if detailed_market:
                        # Try multiple field names for outcomes and prices
                        fetched_outcomes = (detailed_market.get("outcomes") or 
                                          detailed_market.get("outcomeNames") or 
                                          detailed_market.get("outcome"))
                        fetched_prices = (detailed_market.get("outcomePrices") or 
                                        detailed_market.get("prices") or
                                        detailed_market.get("outcome_prices"))
                        
                        # Handle JSON-encoded strings
                        if isinstance(fetched_outcomes, str):
                            try:
                                fetched_outcomes = json.loads(fetched_outcomes)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        
                        if isinstance(fetched_prices, str):
                            try:
                                fetched_prices = json.loads(fetched_prices)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        
                        if fetched_outcomes:
                            outcomes = fetched_outcomes
                        if fetched_prices:
                            outcome_prices = fetched_prices
                        
                        # Update market with fetched data
                        if outcomes:
                            market["outcomes"] = outcomes
                        if outcome_prices:
                            market["outcomePrices"] = outcome_prices
                        
                        logger.debug(f"Fetched market details for {market_id}: outcomes={len(outcomes) if outcomes else 0}, prices={len(outcome_prices) if outcome_prices else 0}")
                        if outcome_prices:
                            logger.debug(f"Sample prices: {outcome_prices[:2] if len(outcome_prices) >= 2 else outcome_prices}")
                    else:
                        logger.debug(f"No detailed market data found for {market_id}")
                except Exception as e:
                    logger.debug(f"Could not fetch market details for {market_id}: {e}")
        
        if not outcomes or not outcome_prices:
            logger.debug(f"No outcomes or prices found. outcomes={outcomes}, prices={outcome_prices}")
            return None
        
        # Try to find "Yes" outcome first
        for i, outcome in enumerate(outcomes):
            if outcome.lower() in ["yes", "true", "will happen", "happens", "will occur"]:
                if i < len(outcome_prices):
                    try:
                        price = float(outcome_prices[i])
                        return {
                            "probability": price * 100,  # Convert to percentage
                            "probability_label": outcome,
                            "outcomes": outcomes,
                            "outcome_prices": outcome_prices,
                            "all_probabilities": {outcomes[j]: float(outcome_prices[j]) * 100 
                                                for j in range(min(len(outcomes), len(outcome_prices)))}
                        }
                    except (ValueError, TypeError, IndexError):
                        pass
        
        # If no "Yes" found, return all outcomes with probabilities
        try:
            all_probs = {}
            for i in range(min(len(outcomes), len(outcome_prices))):
                price = float(outcome_prices[i])
                all_probs[outcomes[i]] = price * 100
            
            # Use first outcome as primary
            primary_outcome = outcomes[0]
            primary_prob = all_probs.get(primary_outcome, 0)
            
            return {
                "probability": primary_prob,
                "probability_label": primary_outcome,
                "outcomes": outcomes,
                "outcome_prices": outcome_prices,
                "all_probabilities": all_probs
            }
        except (ValueError, TypeError, IndexError):
            return None
    
    async def _get_odds(self, context: Dict[str, Any]) -> ExecutionResult:
        """
        Get probability/odds for a question by searching Polymarket markets.
        
        Returns multiple related markets with probabilities for LLM interpretation.
        """
        if not REQUESTS_AVAILABLE:
            return ExecutionResult(
                success=False,
                message="requests library required. Install with: pip install requests"
            )
        
        # Extract the question from user input
        original_input = context.get("original_input", "")
        original_input_lower = original_input.lower()
        
        # Remove common probability question phrases to get the actual question
        question_phrases = [
            "what are the odds that",
            "what's the probability that",
            "what is the probability that",
            "what are the chances that",
            "what's the chance that",
            "odds that",
            "probability that",
            "chance that",
            "what percent chance that",
            "what percentage chance that",
            "how likely is it that",
            "how likely that",
            "what are the odds",
            "what's the probability",
            "what is the probability",
            "what are the chances",
            "what's the chance",
            "the odds",
            "the probability",
            "the chance"
        ]
        
        query = original_input_lower
        for phrase in question_phrases:
            if phrase in query:
                query = query.replace(phrase, "").strip()
                break
        
        # If query starts with "will", keep it as is (it's a prediction question)
        if query.startswith("will"):
            query = query.strip()
        elif not query or len(query) < 3:
            # Fallback: use original input if query extraction failed
            query = original_input_lower.strip()
        
        # Also check parameters from LLM
        if context.get("parameters"):
            params = context["parameters"]
            llm_query = params.get("query") or params.get("question") or params.get("event")
            if llm_query:
                # Use LLM extracted query - it's usually better
                query = llm_query.lower() if isinstance(llm_query, str) else str(llm_query).lower()
        
        # Clean up query - remove question marks, extra spaces, but preserve important words
        query = query.strip().rstrip("?").strip()
        
        # Normalize common variations
        query = query.replace("u.s.", "us").replace("u.s", "us").replace("the us", "us")
        query = query.replace("  ", " ").strip()
        
        if not query or len(query) < 3:
            return ExecutionResult(
                success=False,
                message="Please provide a question. Example: 'what are the odds that trump invades greenland'"
            )
        
        logger.debug(f"Searching for markets with query: '{query}'")
        
        try:
            # Search for markets matching the query - get more results for better analysis
            markets = self._api.search_markets(query, limit=15)
            
            logger.debug(f"Found {len(markets) if markets else 0} markets for query: '{query}'")
            
            if not markets:
                return ExecutionResult(
                    success=True,
                    message=f"No active markets found for: '{query}'\n\nThis question may not have a market on Polymarket, or the market may have closed.",
                    data={"query": query, "markets": [], "probabilities": []}
                )
            
            # Process all markets and extract probabilities
            market_data = []
            for market in markets:
                prob_data = self._extract_probability(market, fetch_details=True)
                volume = market.get("volume", 0) or market.get("volume24hr", 0) or 0
                
                market_info = {
                    "question": market.get("question", "N/A"),
                    "volume": volume,
                    "volume_str": self._format_currency(volume),
                    "end_date": self._get_end_date(market),
                    "market_id": market.get("conditionId", "N/A"),
                    "probability": prob_data.get("probability") if prob_data else None,
                    "probability_label": prob_data.get("probability_label") if prob_data else None,
                    "all_probabilities": prob_data.get("all_probabilities") if prob_data else None,
                    "outcomes": prob_data.get("outcomes") if prob_data else market.get("outcomes", []),
                    "raw_market": market
                }
                market_data.append(market_info)
            
            # Sort by volume (highest first)
            market_data.sort(key=lambda x: x["volume"], reverse=True)
            
            # Filter to top markets with probability data
            markets_with_probs = [m for m in market_data if m["probability"] is not None]
            top_markets = markets_with_probs[:5] if markets_with_probs else market_data[:3]
            
            # Build formatted message for LLM
            lines = [f"Polymarket Probability Analysis for: '{query}'"]
            lines.append("=" * 80)
            
            if not markets_with_probs:
                lines.append("\n⚠️  Found markets but probability data not available:")
                for i, m in top_markets[:3]:
                    lines.append(f"\n{i+1}. {m['question']}")
                    lines.append(f"   Volume: {m['volume_str']}")
            else:
                lines.append(f"\n📊 Found {len(markets_with_probs)} market(s) with probability data:")
                
                for i, market in enumerate(top_markets, 1):
                    lines.append(f"\n{i}. {market['question']}")
                    
                    if market['all_probabilities'] and len(market['all_probabilities']) > 1:
                        # Show all outcomes
                        prob_lines = []
                        for outcome, prob in market['all_probabilities'].items():
                            prob_lines.append(f"   {outcome}: {prob:.1f}%")
                        lines.append("\n".join(prob_lines))
                    else:
                        # Show primary probability
                        lines.append(f"   Probability ({market['probability_label']}): {market['probability']:.1f}%")
                    
                    lines.append(f"   Volume: {market['volume_str']} | Ends: {market['end_date']}")
                
                # Summary for LLM
                if len(top_markets) > 0:
                    primary_market = top_markets[0]
                    lines.append(f"\n🎯 Primary Market Probability: {primary_market['probability']:.1f}%")
                    if len(top_markets) > 1:
                        avg_prob = sum(m['probability'] for m in top_markets if m['probability']) / len([m for m in top_markets if m['probability']])
                        lines.append(f"📈 Average across {len(top_markets)} markets: {avg_prob:.1f}%")
            
            message = "\n".join(lines)
            
            # Prepare structured data for LLM
            probabilities_summary = {
                "primary_probability": top_markets[0]["probability"] if top_markets and top_markets[0]["probability"] else None,
                "primary_market": top_markets[0]["question"] if top_markets else None,
                "all_markets": [
                    {
                        "question": m["question"],
                        "probability": m["probability"],
                        "probability_label": m["probability_label"],
                        "all_probabilities": m["all_probabilities"],
                        "volume": m["volume"]
                    }
                    for m in top_markets
                ],
                "market_count": len(markets_with_probs),
                "total_markets_found": len(markets)
            }
            
            # Generate LLM interpretation if available
            llm_interpretation = None
            if self._ollama and top_markets and markets_with_probs:
                try:
                    llm_interpretation = self._generate_llm_interpretation(
                        original_input=context.get("original_input", query),
                        query=query,
                        markets=top_markets,
                        probabilities_summary=probabilities_summary
                    )
                except Exception as e:
                    logger.debug(f"LLM interpretation failed: {e}")
            
            # Combine formatted data with LLM interpretation
            final_message = message
            if llm_interpretation:
                final_message = f"{llm_interpretation}\n\n{message}"
            
            # Store markets in context for "open market" command
            # Convert market_data to format compatible with _open_market
            self._recent_markets = [m.get("raw_market", m) for m in market_data[:10]]
            
            return ExecutionResult(
                success=True,
                message=final_message,
                data={
                    "query": query,
                    "markets": market_data,
                    "probabilities": probabilities_summary,
                    "formatted_for_llm": True,
                    "llm_interpretation": llm_interpretation
                }
            )
                
        except Exception as e:
            logger.exception(f"Error getting odds: {e}")
            return ExecutionResult(
                success=False,
                message=f"Error searching for market odds: {e}"
            )
    
    def _generate_llm_interpretation(
        self,
        original_input: str,
        query: str,
        markets: List[Dict[str, Any]],
        probabilities_summary: Dict[str, Any]
    ) -> Optional[str]:
        """
        Use LLM to interpret Polymarket data and generate natural language response.
        
        Args:
            original_input: Original user question
            query: Extracted query
            markets: List of market data with probabilities
            probabilities_summary: Summary of probabilities
            
        Returns:
            Natural language interpretation or None if LLM unavailable
        """
        if not self._ollama or not self._ollama.is_available():
            return None
        
        # Build prompt for LLM
        system_prompt = """You are a helpful assistant that interprets Polymarket prediction market data.
Your role is to provide clear, natural language answers about probabilities and odds based on real market data.
Always reference that the data comes from Polymarket prediction markets.
Be concise but informative."""
        
        # Build market data summary
        market_summary = []
        for i, market in enumerate(markets[:3], 1):  # Top 3 markets
            market_text = f"Market {i}: {market['question']}"
            if market.get('all_probabilities'):
                probs = ", ".join([f"{outcome}: {prob:.1f}%" 
                                 for outcome, prob in market['all_probabilities'].items()])
                market_text += f"\n  Probabilities: {probs}"
            elif market.get('probability'):
                market_text += f"\n  Probability ({market['probability_label']}): {market['probability']:.1f}%"
            market_text += f"\n  Volume: {market['volume_str']}"
            market_summary.append(market_text)
        
        # Format primary probability
        primary_prob = probabilities_summary.get('primary_probability')
        prob_text = f"{primary_prob:.1f}%" if primary_prob is not None else "not available"
        
        user_prompt = f"""User asked: "{original_input}"

Based on Polymarket prediction market data, here are the relevant markets:

{chr(10).join(market_summary)}

Primary probability: {prob_text}

Please provide a natural language answer to the user's question, interpreting the Polymarket data.
Reference the specific probabilities and markets when available. Be conversational and helpful.
If probability data isn't available, mention that the market exists but pricing data isn't accessible.
Keep it concise (2-3 sentences). Always mention that the data comes from Polymarket prediction markets."""
        
        try:
            response = self._ollama.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3  # Lower temperature for more factual responses
            )
            return response.strip() if response else None
        except Exception as e:
            logger.debug(f"LLM generation failed: {e}")
            return None
    
    def _build_market_url(self, market: Dict[str, Any]) -> Optional[str]:
        """
        Build Polymarket URL for a market.
        
        Args:
            market: Market data dictionary
            
        Returns:
            URL string or None if unable to build
        """
        # Try slug first (most user-friendly)
        slug = market.get("slug")
        if slug:
            return f"https://polymarket.com/event/{slug}"
        
        # Fall back to conditionId
        condition_id = market.get("conditionId")
        if condition_id:
            return f"https://polymarket.com/market/{condition_id}"
        
        # Try market ID
        market_id = market.get("id") or market.get("marketId")
        if market_id:
            return f"https://polymarket.com/market/{market_id}"
        
        return None
    
    async def _open_market(self, context: Dict[str, Any]) -> ExecutionResult:
        """
        Open a market in Brave browser using context from previous results.
        
        Supports:
        - "open market" (opens first market)
        - "open market 2" (opens second market)
        - "open market [number]" (opens market by number)
        """
        if not self._recent_markets:
            return ExecutionResult(
                success=False,
                message="No recent market results found. Please search for markets first using 'poly search' or 'poly top markets'."
            )
        
        # Extract market number from input
        original_input = context.get("original_input", "").lower()
        market_number = 1  # Default to first market
        
        # Try to extract number from input
        number_patterns = [
            r"market\s+(\d+)",
            r"open\s+(\d+)",
            r"(\d+)",
        ]
        
        for pattern in number_patterns:
            match = re.search(pattern, original_input)
            if match:
                try:
                    market_number = int(match.group(1))
                    break
                except ValueError:
                    pass
        
        # Also check entities from parser
        if "entities" in context:
            for entity in context["entities"]:
                if entity.type == "number":
                    try:
                        market_number = int(entity.value)
                        break
                    except ValueError:
                        pass
        
        # Validate market number
        if market_number < 1 or market_number > len(self._recent_markets):
            return ExecutionResult(
                success=False,
                message=f"Market number {market_number} not found. Available markets: 1-{len(self._recent_markets)}"
            )
        
        # Get the market (convert to 0-based index)
        market = self._recent_markets[market_number - 1]
        market_url = self._build_market_url(market)
        
        if not market_url:
            return ExecutionResult(
                success=False,
                message=f"Could not build URL for market {market_number}. Market may be missing required fields."
            )
        
        # Try to open Brave with the URL
        try:
            # Try common Brave executable paths
            brave_paths = [
                "brave.exe",
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ]
            
            brave_found = False
            for brave_path in brave_paths:
                if os.path.exists(brave_path) or brave_path == "brave.exe":
                    try:
                        # Use subprocess to launch Brave with URL
                        subprocess.Popen([brave_path, market_url], shell=False)
                        brave_found = True
                        break
                    except Exception as e:
                        logger.debug(f"Failed to launch Brave from {brave_path}: {e}")
                        continue
            
            if not brave_found:
                # Fallback: try using os.startfile (Windows default browser)
                try:
                    os.startfile(market_url)
                except Exception as e:
                    return ExecutionResult(
                        success=False,
                        message=f"Could not open browser. Error: {e}"
                    )
            
            market_question = market.get("question", f"Market {market_number}")
            return ExecutionResult(
                success=True,
                message=f"Opening market {market_number} in Brave: {market_question}\nURL: {market_url}",
                data={"market_number": market_number, "url": market_url, "market": market}
            )
        except Exception as e:
            logger.exception(f"Error opening market in Brave: {e}")
            return ExecutionResult(
                success=False,
                message=f"Error opening browser: {e}"
            )
