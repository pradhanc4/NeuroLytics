from datetime import date

from sqlalchemy import (
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.engine import Base


class Market(Base):
    """Represents a market/source for historical results."""

    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    historical_results: Mapped[list["HistoricalResult"]] = relationship(
        back_populates="market",
        cascade="all, delete-orphan",
    )


class HistoricalResult(Base):
    """Stores grouped results and their automatically derived digits."""

    __tablename__ = "historical_results"

    __table_args__ = (
        UniqueConstraint(
            "market_id",
            "result_date",
            name="uq_historical_result_market_date",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    market_id: Mapped[int] = mapped_column(
        ForeignKey("markets.id"),
        nullable=False,
        index=True,
    )

    result_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    open_result: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    jodi_result: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    close_result: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    col1: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    col2: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    col3: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    col4: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    col5: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    col6: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    col7: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    col8: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    market: Mapped["Market"] = relationship(
        back_populates="historical_results",
    )


class PannaReference(Base):
    """Stores validated Panna/Panel reference values."""

    __tablename__ = "panna_reference"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    panna: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        unique=True,
        index=True,
    )

    digit_1: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    digit_2: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    digit_3: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    panna_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )


class JodiFamily(Base):
    """Represents a reference family containing Jodi members."""

    __tablename__ = "jodi_families"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    family_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    members: Mapped[list["JodiFamilyMember"]] = relationship(
        back_populates="family",
        cascade="all, delete-orphan",
    )


class JodiFamilyMember(Base):
    """Stores an individual Jodi belonging to a Jodi family."""

    __tablename__ = "jodi_family_members"

    __table_args__ = (
        UniqueConstraint(
            "family_id",
            "jodi",
            name="uq_jodi_family_member_family_jodi",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    family_id: Mapped[int] = mapped_column(
        ForeignKey("jodi_families.id"),
        nullable=False,
        index=True,
    )

    jodi: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        index=True,
    )

    digit_1: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    digit_2: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    family: Mapped["JodiFamily"] = relationship(
        back_populates="members",
    )