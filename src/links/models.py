from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column, declared_attr
from src.database import DbBase


class Link(DbBase):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True)
    short_code = Column(String, nullable=False, unique=True, index=True)
    long_url = Column(String, nullable=False)
    redirect_counter = Column(Integer, nullable=False, default=0)
    author_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id"),
        index=True,
        nullable=True
    )

    @declared_attr
    def author(cls) -> Mapped["User"]:
        from src.auth.users import User
        return relationship("User", back_populates="links", lazy="selectin")

    # alias = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=False), nullable=False,
                        default=lambda: datetime.utcnow().replace(second=0, microsecond=0))
    updated_at = Column(DateTime(timezone=False), nullable=False,
                        default=lambda: datetime.utcnow().replace(second=0, microsecond=0),
                        onupdate=lambda: datetime.utcnow().replace(second=0, microsecond=0))
    expires_at = Column(DateTime(timezone=False), nullable=True)
    last_used_at = Column(DateTime(timezone=False), nullable=True)
