import json
from collections import defaultdict
from datetime import datetime
from sqlalchemy import Column, Float, PrimaryKeyConstraint, String, Date
from database import EXCHANGE_RATE
from scripts.csv_columns import CURRENCY, DATE
from database.base import Base
from settings import EXCHANGE_RATES


class Currency(Base):
    __tablename__ = CURRENCY
    code = Column(String(), primary_key=True)

class ExchangeRate(Base):
    __tablename__ = EXCHANGE_RATE

    date = Column(Date(), nullable=False, name=DATE, primary_key=True)
    currency = Base.add_foreign_key(String(4), f'{CURRENCY}.code', nullable=False, name=CURRENCY, primary_key=True)
    rate = Column(Float(), nullable=False, name='USD')

    __table_args__ = (
        PrimaryKeyConstraint(DATE, CURRENCY),
    )

    @staticmethod
    def load_exchange_rates():
        with open(EXCHANGE_RATES, 'r') as file:
            data: dict[str, dict[str, float]] = json.load(file)

        row_values: list[dict[str, float]] = []
        for _date, rates in data.items():
            for currency, rate in rates.items():
                date = datetime.strptime(_date, '%Y-%m-%d').date()
                row_values.append({DATE: date, CURRENCY: currency, 'USD': rate})

        return row_values




