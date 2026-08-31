import uuid
from datetime import datetime
from sqlalchemy import Float, ForeignKey, Text, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user: Mapped["User"] = relationship("User")
    
    donation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("donations.id", ondelete="CASCADE"))
    donation: Mapped["Donation"] = relationship("Donation")
    
    comment: Mapped[str] = mapped_column(Text)
    rating: Mapped[float] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'donation_id', name='uq_user_donation_rating'),
    )
