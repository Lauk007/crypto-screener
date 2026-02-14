"""
DEXScreener API 封装
"""

import logging
from typing import List, Dict, Any, Optional

import requests

from config import DEXSCREENER_BASE_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class DexScreenerAPI:
    """DEXScreener API 客户端"""

    def __init__(self, base_url: str = DEXSCREENER_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """发送 API 请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                pass  # 查询参数问题，静默处理
            else:
                logger.warning(f"API 请求失败: {url}")
            return {}
        except requests.exceptions.RequestException:
            logger.warning(f"API 请求失败: {url}")
            return {}

    def search_tokens(self, query: str) -> List[Dict[str, Any]]:
        """搜索代币"""
        if not query or len(query.strip()) < 2:
            return []
        data = self._request("/latest/dex/search", params={"q": query})
        return data.get("pairs", [])

    def parse_pair_data(self, pair: Dict[str, Any]) -> Dict[str, Any]:
        """解析交易对数据"""
        if not pair:
            return {}

        base_token = pair.get("baseToken", {})
        volume = pair.get("volume", {})
        price_change = pair.get("priceChange", {})
        chain_id = pair.get("chainId", "")

        return {
            "address": base_token.get("address", ""),
            "symbol": base_token.get("symbol", ""),
            "name": base_token.get("name", ""),
            "chain": chain_id,
            "market_cap": pair.get("fdv"),
            "volume_24h": volume.get("h24"),
            "price": float(pair.get("priceUsd", 0) or 0),
            "price_change_24h": price_change.get("h24"),
        }


dex_api = DexScreenerAPI()
