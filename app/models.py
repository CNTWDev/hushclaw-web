from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    tokens = relationship("UserToken", back_populates="user", cascade="all, delete-orphan")


class EmailOTP(Base):
    __tablename__ = "email_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0)


class UserToken(Base):
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    token_prefix = Column(String(10), nullable=False)
    name = Column(String(100), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="tokens")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    icon = Column(String(10), default="📦")
    created_at = Column(DateTime, default=datetime.utcnow)

    skills = relationship("Skill", back_populates="category")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    short_desc = Column(String(300), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    platform = Column(String(20), default="all")  # all / mac / windows
    install_count = Column(Integer, default=0)
    rating_sum = Column(Integer, default=0)
    rating_count = Column(Integer, default=0)
    author = Column(String(100), default="Hushclaw Team")
    tags = Column(String(500), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Upload / review fields
    client_id = Column(String(36), index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    skill_slug = Column(String(200), index=True, nullable=True)
    content_hash = Column(String(64), index=True, nullable=True)
    version = Column(String(20), default="1.0.0")
    status = Column(String(20), default="pending")  # pending / approved / rejected
    review_note = Column(Text, nullable=True)
    source_file = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("skills.id"), nullable=True)

    category = relationship("Category", back_populates="skills")
    ratings = relationship("Rating", back_populates="skill")
    submitter = relationship("User", foreign_keys=[user_id])

    @property
    def avg_rating(self):
        if self.rating_count == 0:
            return 0.0
        return round(self.rating_sum / self.rating_count, 1)

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    ip_address = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    score = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("skill_id", "ip_address", name="uq_skill_ip"),
        UniqueConstraint("skill_id", "user_id",    name="uq_skill_user"),
    )

    skill = relationship("Skill", back_populates="ratings")
