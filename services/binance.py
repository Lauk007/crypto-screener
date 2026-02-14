"""
币安 API 封装（仅期货）

期货 API: https://developers.binance.com/docs/zh-CN/binance-futures-api-docs/rest-api/market-data-endpoints
"""

import logging
from typing import Dict, Any, Optional

import requests

from config import REQUEST_TIMEOUT, PROXIES

logger = logging.getLogger(__name__)

# 币安期货 API 域名列表
BINANCE_FUTURES_URLS = [
    "https://fapi.binance.com",
]


class BinanceFuturesAPI:
    """币安期货 API 客户端"""

    def __init__(self, proxies: dict = None):
        self.proxies = proxies or PROXIES
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        self._cache = None

    def _request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """发送 API 请求"""
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT, proxies=self.proxies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"币安 API 请求失败: {url}, 错误: {e}")
            return {}

    def get_all_tickers(self) -> Dict[str, Dict[str, Any]]:
        """获取期货所有交易对数据"""
        if self._cache is not None:
            return self._cache

        for base_url in BINANCE_FUTURES_URLS:
            url = f"{base_url}/fapi/v1/ticker/24hr"
            data = self._request(url)
            if isinstance(data, list):
                result = {}
                for t in data:
                    symbol = t.get("symbol")
                    if symbol and symbol.endswith("USDT"):
                        t["_source"] = "futures"
                        result[symbol] = t
                self._cache = result
                logger.info(f"币安期货获取到 {len(result)} 个交易对")
                return result

        logger.error("币安期货 API 所有域名均不可用")
        return {}

    def get_ticker_by_symbol(self, token_symbol: str) -> Optional[Dict[str, Any]]:
        """根据代币符号获取币安数据"""
        all_tickers = self.get_all_tickers()
        symbol = f"{token_symbol.upper()}USDT"
        return all_tickers.get(symbol)

    def get_volume_24h(self, token_symbol: str) -> Optional[float]:
        """获取24小时成交量（USDT）"""
        ticker = self.get_ticker_by_symbol(token_symbol)
        if ticker:
            volume = ticker.get("quoteVolume")
            if volume:
                return float(volume)
        return None

    def check_token_on_binance(self, token_symbol: str, min_volume_usdt: float = 0) -> Dict[str, Any]:
        """检查代币是否在币安期货交易"""
        result = {
            "exists": False,
            "symbol": None,
            "volume_24h": 0,
            "price": 0,
            "price_change": 0,
            "source": "futures",
        }

        ticker = self.get_ticker_by_symbol(token_symbol)
        if ticker:
            result["exists"] = True
            result["symbol"] = ticker.get("symbol")
            result["volume_24h"] = float(ticker.get("quoteVolume", 0))
            result["price"] = float(ticker.get("lastPrice", 0))
            result["price_change"] = float(ticker.get("priceChangePercent", 0))

        return result


# 兼容旧代码的别名
BinanceCombinedAPI = BinanceFuturesAPI
BinanceSpotAPI = BinanceFuturesAPI

# 创建默认实例
binance_api = BinanceFuturesAPI()
