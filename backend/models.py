"""
数据库模型定义
记录每次分析请求和结果
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from database import Base


class AnalysisRecord(Base):
    """分析记录表"""
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    input_type = Column(String(10), nullable=False, comment="输入类型: image / url")
    input_value = Column(Text, nullable=True, comment="输入的 URL 或图片文件名")
    risk_level = Column(String(10), nullable=True, comment="风险等级: 低 / 中 / 高")
    summary = Column(Text, nullable=True, comment="商品概述")
    report_json = Column(Text, nullable=True, comment="完整报告 JSON 字符串")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    def __repr__(self):
        return f"<AnalysisRecord id={self.id} type={self.input_type} risk={self.risk_level}>"