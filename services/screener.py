"""
代币筛选引擎 - 币安优先策略

策略说明：
1. 从币安（现货+期货）获取所有 USDT 交易对
2. 筛选币安 24h 成交量 >= 阈值的代币
3. 获取这些代币的市值数据（通过 DEXScreener）
4. 获取 BSC 代币的前十持有者集中度（通过 TokenPocket）
5. 应用最终筛选条件
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from services.tokenpocket import tp_api
from services.binance import binance_api
from services.dexscreener import dex_api
from database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class FilterCriteria:
    """筛选条件"""
    min_market_cap: float = 0
    max_market_cap: float = float("inf")
    min_top10_holders_pct: Optional[float] = None
    min_binance_volume: Optional[float] = None
    check_binance: bool = False


class TokenScreener:
    """代币筛选器 - 币安优先策略"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def fetch_and_filter(self, criteria: FilterCriteria, fetch_top10_holders: bool = True) -> List[Dict[str, Any]]:
        """获取代币数据并根据条件筛选"""
        logger.info("开始获取代币数据（币安优先策略）...")

        # 1. 从币安获取所有交易对数据
        binance_tickers = binance_api.get_all_tickers()
        if not binance_tickers:
            logger.error("币安 API 获取失败")
            return []

        logger.info(f"币安获取到 {len(binance_tickers)} 个交易对")

        # 2. 筛选币安成交量 >= 阈值的代币
        min_binance_vol = criteria.min_binance_volume if criteria.check_binance else 0
        binance_tokens = []

        for symbol, ticker in binance_tickers.items():
            if not symbol.endswith("USDT"):
                continue

            volume_24h = float(ticker.get("quoteVolume", 0) or 0)
            if min_binance_vol > 0 and volume_24h < min_binance_vol:
                continue

            token_symbol = symbol.replace("USDT", "").replace("USD", "")
            binance_tokens.append({
                "symbol": token_symbol,
                "binance_symbol": symbol,
                "binance_volume_24h": volume_24h,
                "binance_price": float(ticker.get("lastPrice", 0) or 0),
                "binance_price_change": float(ticker.get("priceChangePercent", 0) or 0),
            })

        logger.info(f"币安成交量筛选后剩余 {len(binance_tokens)} 个代币")

        # 3. 获取市值数据
        enriched_tokens = self._enrich_with_market_data(binance_tokens)

        # 4. 获取前十持有者数据
        if fetch_top10_holders and criteria.min_top10_holders_pct is not None:
            enriched_tokens = self._enrich_with_top10_holders(enriched_tokens)

        # 5. 应用筛选条件
        filtered = self._apply_filters(enriched_tokens, criteria)

        logger.info(f"最终筛选结果: {len(filtered)} 个代币")

        # 6. 保存到数据库
        self._save_tokens(filtered)

        return filtered

    def _enrich_with_market_data(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为币安代币补充市值数据"""
        logger.info(f"正在获取 {len(tokens)} 个代币的市值数据...")
        enriched = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self._get_market_data_for_token, token): token for token in tokens}
            for future in as_completed(futures):
                token = futures[future]
                try:
                    result = future.result()
                    if result:
                        enriched.append(result)
                except Exception:
                    token["market_cap"] = None
                    token["chain"] = "unknown"
                    enriched.append(token)

        return enriched

    def _get_market_data_for_token(self, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取单个代币的市值数据"""
        symbol = token.get("symbol", "")
        if not symbol:
            return token

        try:
            pairs = dex_api.search_tokens(symbol)
            if pairs:
                # 优先选择 BSC 链
                bsc_pairs = [p for p in pairs if p.get("chainId") == "bsc"]
                if bsc_pairs:
                    best_pair = max(bsc_pairs, key=lambda p: float(p.get("fdv") or 0))
                else:
                    best_pair = max(pairs, key=lambda p: float(p.get("fdv") or 0))

                parsed = dex_api.parse_pair_data(best_pair)
                token["market_cap"] = parsed.get("market_cap")
                token["chain"] = parsed.get("chain", "unknown")
                token["address"] = parsed.get("address", "")
                token["name"] = parsed.get("name", symbol)
                token["price"] = parsed.get("price")
                token["chg_24h"] = parsed.get("price_change_24h")
                token["volume"] = parsed.get("volume_24h")
                return token
        except Exception:
            pass

        token["market_cap"] = None
        token["chain"] = "unknown"
        token["price"] = token.get("binance_price")
        return token

    def _enrich_with_top10_holders(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为代币添加前十持有者占比数据"""
        enriched = []

        bsc_tokens = [t for t in tokens if t.get("chain", "").lower() in ["bsc", "bnbchain"]]
        other_tokens = [t for t in tokens if t.get("chain", "").lower() not in ["bsc", "bnbchain"]]

        logger.info(f"正在获取 {len(bsc_tokens)} 个 BSC 代币的前十持有者数据...")

        for token in other_tokens:
            token["top10_holders_pct"] = None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self._get_top10_for_token, token): token for token in bsc_tokens}
            for future in as_completed(futures):
                token = futures[future]
                try:
                    token["top10_holders_pct"] = future.result()
                except Exception:
                    token["top10_holders_pct"] = None
                enriched.append(token)

        enriched.extend(other_tokens)
        return enriched

    def _get_top10_for_token(self, token: Dict[str, Any]) -> Optional[float]:
        """获取单个代币的前十持有者占比"""
        address = token.get("address", "")
        symbol = token.get("symbol", "")

        if not address or not symbol:
            return None

        try:
            return tp_api.get_top10_holders_pct(address, symbol)
        except Exception:
            return None

    def _apply_filters(self, tokens: List[Dict[str, Any]], criteria: FilterCriteria) -> List[Dict[str, Any]]:
        """应用筛选条件"""
        filtered = []

        for token in tokens:
            market_cap = token.get("market_cap")
            if market_cap is None:
                continue
            if market_cap < criteria.min_market_cap or market_cap > criteria.max_market_cap:
                continue

            if criteria.min_top10_holders_pct is not None:
                top10_pct = token.get("top10_holders_pct")
                if top10_pct is None or top10_pct < criteria.min_top10_holders_pct:
                    continue

            filtered.append(token)

        filtered.sort(key=lambda x: x.get("market_cap", 0) or 0, reverse=True)
        return filtered

    def _save_tokens(self, tokens: List[Dict[str, Any]]):
        """保存代币到数据库"""
        try:
            db_tokens = []
            for token in tokens:
                db_tokens.append({
                    "address": token.get("address", ""),
                    "symbol": token.get("symbol", ""),
                    "name": token.get("name", ""),
                    "chain": token.get("chain", "bsc"),
                    "market_cap": token.get("market_cap"),
                    "volume_24h": token.get("volume"),
                    "holders": token.get("holder_count"),
                    "price": token.get("price"),
                    "price_change_24h": token.get("chg_24h"),
                })
            self.db.bulk_upsert_tokens(db_tokens)
        except Exception as e:
            logger.error(f"保存代币数据失败: {e}")


def create_filter_criteria(
    min_market_cap: float = None,
    max_market_cap: float = None,
    min_top10_holders_pct: float = None,
    min_binance_volume: float = None,
    check_binance: bool = False,
) -> FilterCriteria:
    """创建筛选条件对象"""
    return FilterCriteria(
        min_market_cap=min_market_cap if min_market_cap is not None else 0,
        max_market_cap=max_market_cap if max_market_cap is not None else float("inf"),
        min_top10_holders_pct=min_top10_holders_pct,
        min_binance_volume=min_binance_volume,
        check_binance=check_binance,
    )
