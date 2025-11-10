from sqlalchemy import Column, Integer, String, TIMESTAMP, func
from auth.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    secret = Column(String(255), nullable=False)
    mfa_secret = Column(String(64), nullable=True)
    login_alert_email = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
