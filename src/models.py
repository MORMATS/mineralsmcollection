from __future__ import annotations

from datetime import UTC, date, datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


mineral_chakras = Table(
    "mineral_chakras",
    Base.metadata,
    Column("mineral_id", ForeignKey("mineral_species.id"), primary_key=True),
    Column("chakra_id", ForeignKey("chakras.id"), primary_key=True),
)

mineral_zodiac_signs = Table(
    "mineral_zodiac_signs",
    Base.metadata,
    Column("mineral_id", ForeignKey("mineral_species.id"), primary_key=True),
    Column("zodiac_id", ForeignKey("zodiac_signs.id"), primary_key=True),
)


class Chakra(Base):
    __tablename__ = "chakras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(80))
    element: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)

    minerals: Mapped[list["MineralSpecies"]] = relationship(
        secondary=mineral_chakras, back_populates="chakras"
    )


class ZodiacSign(Base):
    __tablename__ = "zodiac_signs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    minerals: Mapped[list["MineralSpecies"]] = relationship(
        secondary=mineral_zodiac_signs, back_populates="zodiac_signs"
    )


class MineralSpecies(Base):
    __tablename__ = "mineral_species"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mindat_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    rruff_id: Mapped[str | None] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    formula: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(160))
    crystal_system: Mapped[str | None] = mapped_column(String(120))
    hardness_min: Mapped[float | None] = mapped_column(Float)
    hardness_max: Mapped[float | None] = mapped_column(Float)
    color: Mapped[str | None] = mapped_column(String(255))
    luster: Mapped[str | None] = mapped_column(String(160))
    streak: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(500))
    api_raw_json: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    chakras: Mapped[list[Chakra]] = relationship(
        secondary=mineral_chakras, back_populates="minerals"
    )
    zodiac_signs: Mapped[list[ZodiacSign]] = relationship(
        secondary=mineral_zodiac_signs, back_populates="minerals"
    )
    items: Mapped[list["CollectionItem"]] = relationship(back_populates="mineral")


class Locality(Base):
    __tablename__ = "localities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mindat_locality_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    name: Mapped[str | None] = mapped_column(String(255))
    mine: Mapped[str | None] = mapped_column(String(255))
    region: Mapped[str | None] = mapped_column(String(255))
    country: Mapped[str | None] = mapped_column(String(120), index=True)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["CollectionItem"]] = relationship(back_populates="locality")


class CollectionItem(Base):
    __tablename__ = "collection_items"
    __table_args__ = (UniqueConstraint("item_code", name="uq_collection_item_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(180))
    mineral_id: Mapped[int] = mapped_column(ForeignKey("mineral_species.id"), nullable=False)
    locality_id: Mapped[int | None] = mapped_column(ForeignKey("localities.id"))
    acquisition_date: Mapped[date | None] = mapped_column(Date)
    acquisition_source: Mapped[str | None] = mapped_column(String(255))
    purchase_price: Mapped[float | None] = mapped_column(Float)
    sale_price: Mapped[float | None] = mapped_column(Float)
    sold: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sold_at: Mapped[date | None] = mapped_column(Date)
    purchase_link: Mapped[str | None] = mapped_column(String(800))
    special_features: Mapped[str | None] = mapped_column(Text)
    secondary_minerals: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    mineral: Mapped[MineralSpecies] = relationship(back_populates="items")
    locality: Mapped[Locality | None] = relationship(back_populates="items")
    images: Mapped[list["ItemImage"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class ItemImage(Base):
    __tablename__ = "item_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("collection_items.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(255))
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False)

    item: Mapped[CollectionItem] = relationship(back_populates="images")
