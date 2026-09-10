import uuid
import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, default="Default API Key")
    key_prefix = Column(String(32), nullable=False)  # e.g., ak_live_ab12
    key_hash = Column(String(64), unique=True, index=True, nullable=False)  # SHA-256 Digest
    rate_limit_override_rpm = Column(Integer, nullable=True)  # Optional override
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "key_prefix": self.key_prefix,
            "rate_limit_override_rpm": self.rate_limit_override_rpm,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }
