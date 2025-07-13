import json
from typing import TypedDict
import pandas as pd
from sqlalchemy import Column, Float, PrimaryKeyConstraint, String, Date
from database import EXCHANGE_RATE
from scripts.csv_columns import CURRENCY, DATE
from database.base import Base
from settings import EXCHANGE_RATES_PATH


class CurrencyBundle(TypedDict):
    date: pd.Timestamp
    currency: str
    USD: float

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
    def load_exchange_rates() -> dict[pd.Timestamp, dict[str, float]]:
        if not EXCHANGE_RATES_PATH.exists():
            raise FileNotFoundError(f"There is no file in {EXCHANGE_RATES_PATH}")
        with open(EXCHANGE_RATES_PATH, 'r') as file:
            data: dict = json.load(file)
            return {
                pd.to_datetime(date): rates
                for date, rates in data.items()
            }

    @staticmethod
    def database_entries() -> list[CurrencyBundle]:
        exchange_rates = ExchangeRate.load_exchange_rates()
        return [
            {DATE: date, CURRENCY: currency, 'USD': rate}
            for date, rates in exchange_rates.items()
            for currency, rate in rates.items()
        ]





