from sqlalchemy import Column, Float, PrimaryKeyConstraint, String, Date
from database import EXCHANGE_RATE
from scripts.csv_columns import CURRENCY, DATE
from database.base import Base


class Currency(Base):
    __tablename__ = CURRENCY
    code = Column(String(), primary_key=True)

class ExchangeRate(Base):
    __tablename__ = EXCHANGE_RATE

    date = Column(Date, nullable=False, name=DATE)
    currency = Base.add_foreign_key(String(4), f'{CURRENCY}.code', nullable=False, name=CURRENCY)
    rate = Column(Float, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint(DATE, CURRENCY),
    )


