from sqlalchemy import Column, Float, PrimaryKeyConstraint, String, Date
from database import EXCHANGE_RATE
from database.base import Base
from scripts.csv_columns import CURRENCY

class Currency(Base):
    __tablename__ = CURRENCY
    code = Column(String(), primary_key=True)

class ExchangeRate(Base):
    __tablename__ = EXCHANGE_RATE

    date = Column(Date, nullable=False)
    currency = Base.add_foreign_key(String(4), f'{CURRENCY}.code', nullable=False, name=CURRENCY)
    usd = Column(Float, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('date', Currency),
    )


