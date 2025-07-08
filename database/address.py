from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String
from database import ROW_INDEX
from database.base import Base
from scripts.csv_columns import *


class Town(Base):
    __tablename__ = TOWN
    name = Column(String(), primary_key=True)

class Province(Base):
    __tablename__ = PROVINCE
    name = Column(String(), primary_key=True)

class AdministrativeDivision(Base):
    # Assertion: All unique valid or hardcoded administrative divisions have a province with enough data
    __tablename__ = ADMINISTRATIVE_UNIT
    name = Column(String(), primary_key=True)
    province = Column(
        String(),
        ForeignKey(
            f'{PROVINCE}.name',
            ondelete='CASCADE',
            onupdate='CASCADE'
        ),
        primary_key=True,
    )

class Address(Base):
    __tablename__ = ADDRESS
    id = Column(Integer(), primary_key=True, name=ROW_INDEX)
    administrative_division = Column(String(), name=ADMINISTRATIVE_UNIT)
    province = Base.add_foreign_key(String(), f'{PROVINCE}.name', name=PROVINCE)
    building = Column(String(), name=BUILDING)
    street_number = Column(String(), name=STREET_NUMBER)
    street = Column(String(), name=STREET)
    block = Column(String(), name=BLOCK)
    lane = Column(String(), name=LANE)
    town = Base.add_foreign_key(String(), f'{TOWN}.name', name=TOWN)
    neighborhood = Column(String(), name=NEIGHBOURHOOD)

    __table_args__ = (
        ForeignKeyConstraint(
            [administrative_division, province],
            [f'{ADMINISTRATIVE_UNIT}.name', f'{ADMINISTRATIVE_UNIT}.province'],
            name='fk_admin_division',
            deferrable=True,
            initially='DEFERRED'
            # This composite foreign key overwrites the default 'province' foreign key.
            # by linking both 'administrative_division' and 'province' together in a composite foreign key.
            # The constraint is deferred, meaning it's checked at the end of the transaction.
            # If both columns are NULL, the constraint is omitted or skipped for the row.
        ),
    )

ADDRESS_DB_COLUMNS: list[str] = Address.table_columns()


