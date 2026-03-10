"""
加密货币选币系统 - Web 界面
启动命令: streamlit run app.py
"""

import logging
import sys
import importlib
import streamlit as st
import pandas as pd
from datetime import datetime

# 强制重新加载模块，避免缓存问题
for mod_name in ['services.screener', 'services.binance', 'services.dexscreener', 'services.tokenpocket']:
    if mod_name in sys.modules:
        importlib.reload(sys.modules[mod_name])

from services.screener import TokenScreener, create_filter_criteria
from database import DatabaseManager

# 配置日志
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ==================== 浅色主题 CSS ====================
LIGHT_THEME_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: #f5f7fa;
    }

    /* 侧边栏 */
    section[data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }

    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #1e293b !important;
    }

    /* 表格 */
    .stDataFrame {
        background: #ffffff;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }

    .stDataFrame thead th {
        background: #f8fafc !important;
        color: #64748b !important;
        font-weight: 600;
        font-size: 0.7rem;
        padding: 0.75rem 0.5rem !important;
    }

    .stDataFrame tbody td {
        background: #ffffff !important;
        color: #334155 !important;
        padding: 0.5rem !important;
        font-size: 0.85rem;
    }

    .stDataFrame tbody tr:hover td {
        background: #f8fafc !important;
    }

    /* 按钮 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        font-weight: 600;
        padding: 0.6rem 1.5rem;
        border-radius: 8px;
        width: 100%;
    }

    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }

    /* 输入框 */
    .stNumberInput input {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 6px;
    }

    /* 下拉框 - 关键修复 */
    .stSelectbox > div > div {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 6px;
        min-height: 38px;
    }

    .stSelectbox > div > div > div {
        color: #1e293b !important;
    }

    /* 下拉菜单弹出层 */
    div[data-baseweb="popover"] {
        z-index: 9999 !important;
    }

    div[data-baseweb="popover"] ul[role="listbox"] {
        background: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15) !important;
        max-height: 200px !important;
    }

    div[data-baseweb="popover"] li[role="option"] {
        color: #1e293b !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
        cursor: pointer !important;
    }

    div[data-baseweb="popover"] li[role="option"]:hover {
        background: #eff6ff !important;
    }

    div[data-baseweb="popover"] li[role="option"][aria-selected="true"] {
        background: #dbeafe !important;
        color: #1e40af !important;
    }

    /* 滑块 */
    .stSlider > div > div > div {
        background: #3b82f6;
    }

    /* 分隔线 */
    hr {
        border-color: #e2e8f0;
    }

    /* 空状态 */
    .empty-state {
        text-align: center;
        padding: 3rem 1.5rem;
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }

    .empty-state .icon { font-size: 3rem; margin-bottom: 0.75rem; }
    .empty-state .title { font-size: 1.1rem; color: #334155; font-weight: 600; margin-bottom: 0.25rem; }
    .empty-state .desc { color: #94a3b8; font-size: 0.85rem; }

    /* 手机端自适应 */
    @media (max-width: 768px) {
        .stDataFrame tbody td { font-size: 0.75rem; padding: 0.4rem !important; }
    }

    /* 隐藏右上角菜单 */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
"""


def format_number(num) -> str:
    """格式化数字"""
    if num is None:
        return "-"
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return f"{num:.2f}"


# 页面配置
st.set_page_config(
    page_title="Crypto Screener",
    page_icon="chart",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None,
)

# 注入 CSS
st.markdown(LIGHT_THEME_CSS, unsafe_allow_html=True)


def get_screener():
    return TokenScreener()


def init_session_state():
    """初始化会话状态，从数据库加载缓存结果"""
    if "results" not in st.session_state:
        # 尝试从数据库加载缓存
        try:
            db = DatabaseManager()
            cached = db.get_cached_results()
            if cached and cached.get("results"):
                st.session_state.results = cached["results"]
                st.session_state.last_update = cached.get("screened_at")
                if isinstance(st.session_state.last_update, str):
                    from datetime import datetime
                    st.session_state.last_update = datetime.fromisoformat(st.session_state.last_update.replace("Z", "+00:00"))
            else:
                st.session_state.results = []
                st.session_state.last_update = None
        except Exception:
            st.session_state.results = []
            st.session_state.last_update = None
    if "last_update" not in st.session_state:
        st.session_state.last_update = None


def tokens_to_dataframe(tokens: list) -> pd.DataFrame:
    """转换为 DataFrame"""
    if not tokens:
        return pd.DataFrame()

    data = []
    for token in tokens:
        t = token if isinstance(token, dict) else token
        top20 = t.get("top20_holders_pct")
        price = t.get("price") or 0

        data.append({
            "代币": t.get("symbol", "-"),
            "价格": f"${price:.6f}" if price < 1 else f"${price:.4f}",
            "市值": format_number(t.get("market_cap")),
            "前二十": f"{top20:.1f}%" if top20 is not None else "-",
            "币安量": format_number(t.get("binance_volume_24h")),
        })

    return pd.DataFrame(data)


def main():
    init_session_state()

    # 侧边栏
    with st.sidebar:
        # 市值
        st.markdown("**市值范围**")
        c1, c2 = st.columns(2)
        with c1:
            min_cap_val = st.number_input("最小", value=10.0, step=1.0, key="min_cap")
        with c2:
            min_cap_unit = st.selectbox("单位", ["K", "M", "B"], index=1, key="min_unit")

        c3, c4 = st.columns(2)
        with c3:
            max_cap_val = st.number_input("最大", value=300.0, step=10.0, key="max_cap")
        with c4:
            max_cap_unit = st.selectbox("单位", ["K", "M", "B"], index=1, key="max_unit")

        units = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
        min_cap = int(min_cap_val * units[min_cap_unit])
        max_cap = int(max_cap_val * units[max_cap_unit])

        st.divider()

        # 前二十持仓
        min_top20 = st.slider("前二十持仓%", 0, 100, 98, key="top20_slider")

        st.divider()

        # 币安量
        st.markdown("**币安成交量**")
        c1, c2 = st.columns(2)
        with c1:
            binance_vol = st.number_input("最小", value=300.0, step=10.0, key="binance_vol")
        with c2:
            binance_unit = st.selectbox("单位", ["万", "M"], index=0, key="binance_unit")

        vol_mult = {"万": 10_000, "M": 1_000_000}
        min_binance = int(binance_vol * vol_mult[binance_unit])

        st.divider()
        filter_btn = st.button("🔍 开始筛选", type="primary", use_container_width=True)

    results = st.session_state.results

    # 筛选逻辑
    if filter_btn:
        with st.spinner("筛选中..."):
            try:
                criteria = create_filter_criteria(
                    min_market_cap=min_cap,
                    max_market_cap=max_cap,
                    min_top20_holders_pct=min_top20,
                    min_binance_volume=min_binance,
                    check_binance=True,
                )
                results = get_screener().fetch_and_filter(criteria, fetch_top20_holders=True)
                st.session_state.results = results
                st.session_state.last_update = datetime.now()
                # 保存到数据库缓存
                try:
                    DatabaseManager().save_cached_results(results)
                except Exception:
                    pass
                st.success(f"完成! 共 {len(results)} 个代币")
                st.rerun()
            except Exception as e:
                import traceback
                st.error(f"失败: {e}")
                st.code(traceback.format_exc())

    # 结果
    if st.session_state.results:
        df = tokens_to_dataframe(st.session_state.results)
        st.dataframe(df, use_container_width=True, hide_index=True, height=450)
    else:
        st.markdown("""
            <div class="empty-state">
                <div class="icon">🔍</div>
                <div class="title">开始筛选</div>
                <div class="desc">设置条件后点击「开始筛选」</div>
            </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
