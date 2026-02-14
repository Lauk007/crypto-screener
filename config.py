"""
加密货币选币系统配置文件
"""

# 数据库配置
DATABASE_URL = "sqlite:///crypto_selection.db"

# DEXScreener API 配置
DEXSCREENER_BASE_URL = "https://api.dexscreener.com"

# 请求超时
REQUEST_TIMEOUT = 30

# 代理配置（如需要代理，设置为 {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}）
PROXIES = None
