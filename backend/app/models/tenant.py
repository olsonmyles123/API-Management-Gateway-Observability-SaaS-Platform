import uuid
import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    upstream_url = Column(String(1024), nullable=False)
    plan_tier = Column(String(50), default="free", nullable=False)  # free, pro, enterprise
    rate_limit_rpm = Column(Integer, default=60, nullable=False)   # Requests per minute
    burst_limit = Column(Integer, default=10, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", lazy="selectin")
    api_keys = relationship("ApiKey", back_populates="tenant", cascade="all, delete-orphan", lazy="selectin")
    alert_rules = relationship("AlertRule", back_populates="tenant", cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "slug": self.slug,
            "upstream_url": self.upstream_url,
            "plan_tier": self.plan_tier,
            "rate_limit_rpm": self.rate_limit_rpm,
            "burst_limit": self.burst_limit,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
