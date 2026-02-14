"""
TokenPocket API 封装
"""

import logging
from typing import Dict, Any, Optional

import requests

from config import REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


class TokenPocketAPI:
    """TokenPocket API 客户端"""

    def __init__(self, base_url: str = "https://preserver.mytokenpocket.vip"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """发送 API 请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"API 请求失败: {url}")
            return {}

    def get_holder_info(self, address: str, symbol: str, chain_id: int = 56, blockchain_id: int = 12) -> Dict[str, Any]:
        """获取代币持有者信息"""
        data = self._request(
            "/v1/token/holder_info",
            params={
                "address": address,
                "chain_id": chain_id,
                "blockchain_id": blockchain_id,
                "ns": "ethereum",
                "bl_symbol": symbol,
            }
        )
        return data.get("data", {})

    def get_top10_holders_pct(self, address: str, symbol: str, chain_id: int = 56, blockchain_id: int = 12) -> Optional[float]:
        """获取前十持有者占比"""
        try:
            holder_info = self.get_holder_info(address, symbol, chain_id, blockchain_id)
            if not holder_info:
                return None

            top_1_10 = holder_info.get("top_1_10")
            total_supply = holder_info.get("total_supply")

            if not top_1_10 or not total_supply:
                return None

            top_1_10 = float(top_1_10)
            total_supply = float(total_supply)

            if total_supply == 0:
                return None

            pct = (top_1_10 / total_supply) * 100
            return round(pct, 2)

        except Exception:
            return None


tp_api = TokenPocketAPI()
