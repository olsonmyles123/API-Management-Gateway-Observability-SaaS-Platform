import uuid
import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    metric_type = Column(String(50), nullable=False)  # "p95_latency", "error_rate", "req_count"
    threshold = Column(Float, nullable=False)          # e.g., 500.0 (ms) or 5.0 (%)
    window_minutes = Column(Integer, default=5, nullable=False)
    webhook_url = Column(String(1024), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="alert_rules", lazy="selectin")
    history = relationship("AlertHistory", back_populates="rule", cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "metric_type": self.metric_type,
            "threshold": self.threshold,
            "window_minutes": self.window_minutes,
            "webhook_url": self.webhook_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String(36), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)
    triggered_value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    status = Column(String(50), default="sent", nullable=False)  # "sent", "failed"
    payload = Column(Text, nullable=True)
    triggered_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    rule = relationship("AlertRule", back_populates="history", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "tenant_id": self.tenant_id,
            "metric_type": self.metric_type,
            "triggered_value": self.triggered_value,
            "threshold": self.threshold,
            "status": self.status,
            "payload": self.payload,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
        }
