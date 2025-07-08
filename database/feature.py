from sqlalchemy import Column, String
from database.base import Base
from scripts.csv_columns import *

class Amenity(Base):
    __tablename__ = AMENITIES
    type = Column(String(), primary_key=True)

class Appliance(Base):
    __tablename__ = APPLIANCES
    type = Column(String(), primary_key=True)

class Parking(Base):
    __tablename__ = PARKING
    type = Column(String(), primary_key=True)
