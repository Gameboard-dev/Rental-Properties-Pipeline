from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, String
from database.base import Base
from scripts.columns import *


class Town(Base):
    __tablename__ = 'town'
    name = Column(String(), primary_key=True)

class Province(Base):
    __tablename__ = 'province'
    name = Column(String(), primary_key=True)

class AdministrativeDivision(Base):
    # Every administrative division has a province.
    __tablename__ = 'administrative_division'
    name = Column(String(), primary_key=True)
    province = Column(
        String(),
        ForeignKey(
            'province.name',
            ondelete='CASCADE',
            onupdate='CASCADE'
        ),
        primary_key=True
    )

class Address(Base):
    __tablename__ = 'address'
    id = Column(Integer(), primary_key=True)
    province = Base.add_foreign_key(String(), 'province.name', name=PROVINCE)
    administrative_division = Column(String(), name=ADMINISTRATIVE_UNIT)
    building = Column(String(), name=BUILDING)
    street_number = Column(String(), name=STREET_NUMBER)
    street = Column(String(), name=STREET)
    block = Column(String(), name=BLOCK)
    lane = Column(String(), name=LANE)
    town = Base.add_foreign_key(String(), 'town.name', name=TOWN)
    neighborhood = Column(String(), name=NEIGHBOURHOOD)

    __table_args__ = (
        ForeignKeyConstraint(
            [administrative_division, province],
            ['administrative_division.name', 'administrative_division.province'],
            name='fk_admin_division',
            deferrable=True,
            initially='DEFERRED'
            # This composite foreign key overwrites the default 'province' foreign key.
            # by linking both 'administrative_division' and 'province' together in a composite foreign key.
            # The constraint is deferred, meaning it's checked at the end of the transaction.
            # If both columns are NULL, the constraint is omitted or skipped for the row.
        ),
    )







