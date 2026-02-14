"""
数据模型定义
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Token(Base):
    """代币数据模型"""

    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String(255), unique=True, nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    name = Column(String(255))
    chain = Column(String(50), nullable=False, index=True)
    market_cap = Column(Float)
    volume_24h = Column(Float)
    holders = Column(Integer)
    price = Column(Float)
    price_change_24h = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "address": self.address,
            "symbol": self.symbol,
            "name": self.name,
            "chain": self.chain,
            "market_cap": self.market_cap,
            "volume_24h": self.volume_24h,
            "holders": self.holders,
            "price": self.price,
            "price_change_24h": self.price_change_24h,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class History(Base):
    """筛选历史记录模型"""

    __tablename__ = "histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    results = Column(JSON, default=list)
    result_count = Column(Integer, default=0)
    screened_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "results": self.results or [],
            "result_count": self.result_count,
            "screened_at": self.screened_at.isoformat() if self.screened_at else None,
        }
