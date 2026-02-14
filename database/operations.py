"""
数据库操作函数
"""

from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config import DATABASE_URL
from .models import Base, Token, History


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._ensure_tables()

    def _ensure_tables(self):
        """确保数据库表已创建"""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def bulk_upsert_tokens(self, tokens_data: List[Dict[str, Any]]):
        """批量插入或更新代币数据"""
        with self.get_session() as session:
            for token_data in tokens_data:
                token = (
                    session.query(Token)
                    .filter(Token.address == token_data["address"])
                    .first()
                )
                if token:
                    for key, value in token_data.items():
                        if hasattr(token, key):
                            setattr(token, key, value)
                    token.updated_at = datetime.utcnow()
                else:
                    token = Token(**token_data)
                    session.add(token)

    def save_cached_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """保存缓存的筛选结果（保留最新一次）"""
        with self.get_session() as session:
            session.query(History).delete()
            history = History(
                results=results,
                result_count=len(results),
            )
            session.add(history)
            session.flush()
            session.refresh(history)
            return history.to_dict()

    def get_cached_results(self) -> Optional[Dict[str, Any]]:
        """获取缓存的筛选结果"""
        with self.get_session() as session:
            history = session.query(History).first()
            return history.to_dict() if history else None
