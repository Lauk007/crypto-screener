# Crypto Screener

加密货币筛选系统 - 币安期货 + DEXScreener + TokenPocket

## 功能

- **数据来源**: 币安期货 + DEXScreener + TokenPocket
- **筛选条件**:
  - 市值范围
  - 币安期货 24h 成交量
  - 前十持有者集中度（BSC 链）
- **结果缓存**: 筛选结果自动保存，刷新页面不丢失

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用

```bash
streamlit run app.py
```

浏览器打开 http://localhost:8501

## 筛选条件

| 条件 | 说明 |
|------|------|
| 市值 | 代币的全稀释估值 (FDV) |
| 前十持仓% | 前10大持有者的持仓占比（≥ 表示更集中）|
| 币安成交量 | 币安期货 24h 成交量 (USDT) |

## 项目结构

```
crypto_selection/
├── app.py              # Streamlit 主程序
├── config.py           # 配置文件
├── requirements.txt    # 依赖包
├── database/
│   ├── models.py       # 数据模型
│   └── operations.py   # 数据库操作
└── services/
    ├── binance.py      # 币安期货 API
    ├── dexscreener.py  # DEXScreener API
    ├── tokenpocket.py  # TokenPocket API
    └── screener.py     # 筛选引擎
```

## License

MIT
