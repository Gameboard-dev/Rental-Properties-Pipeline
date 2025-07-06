from sqlalchemy import Column, Float, PrimaryKeyConstraint, String, Date
from database.base import Base

class Currency(Base):
    __tablename__ = 'currency'
    code = Column(String(), primary_key=True)


class ExchangeRate(Base):
    __tablename__ = 'exchange_rate'

    date = Column(Date, nullable=False)
    currency = Base.add_foreign_key(String(4), 'currency.code', nullable=False)
    usd = Column(Float, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('date', 'currency'),
    )


