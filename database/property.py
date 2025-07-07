from database import LISTING, ROW_INDEX, PROPERTY, PROPERTY_AMENITIES, PROPERTY_APPLIANCES, PROPERTY_PARKING
from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship
from database.base import Base
from scripts.csv_columns import *

class Renovation(Base):
    __tablename__ = RENOVATION
    type = Column(String(), primary_key=True)

class Construction(Base):
    __tablename__ = CONSTRUCTION
    type = Column(String(), primary_key=True)

class Listing(Base):
    __tablename__ = LISTING
    id = Column(Integer(), primary_key=True, name=ROW_INDEX)
    date = Column(Date(), name=DATE)
    price = Column(Float(), name=PRICE)
    currency = Base.add_foreign_key(String(4), f'{CURRENCY}.code', name=CURRENCY)
    duration = Column(String(), name=DURATION)

LISTING_COLUMNS: list[str] = Listing.columns()

class Property(Base):
    __tablename__ = PROPERTY
    id = Column(Integer(), primary_key=True, name=ROW_INDEX)
    address = Base.add_foreign_key(Integer(), f'{ADDRESS}.{ROW_INDEX}', name=ADDRESS)
    floor = Column(Integer(), name=FLOOR)
    floors = Column(Integer(), name=FLOORS)
    floor_area = Column(Integer(), name=FLOOR_AREA)
    rooms = Column(Integer(), name=ROOMS)
    bathrooms = Column(Integer(), name=BATHROOMS)
    ceiling_height = Column(Float(), name=CEILING_HEIGHT)
    renovation = Base.add_foreign_key(String(), f'{RENOVATION}.type', name=RENOVATION)
    construction = Base.add_foreign_key(String(), f'{CONSTRUCTION}.type', name=CONSTRUCTION)
    balcony = Column(Boolean(), name=BALCONY)
    furnished = Column(Boolean(), name=FURNISHED)
    elevator = Column(Boolean(), name=ELEVATOR)
    listing = Base.add_foreign_key(Integer(), f'{LISTING}.{ROW_INDEX}', name=LISTING)

PROPERTY_COLUMNS: list[str] = Property.columns(exclude=set(ADDRESS, LISTING)) # Replaced by ID_KEY

class Feature(Base):
    __abstract__ = True
    type = Column(String(), primary_key=True)

'''////////////////////////////////////////////////////////////////////////////'''

class Amenity(Feature):
    __tablename__ = AMENITIES

class Property_Amenities(Base): 
    __tablename__ = PROPERTY_AMENITIES
    property_id = Column(ForeignKey(f'{PROPERTY}.{ROW_INDEX}'), primary_key=True)
    amenity_id = Column(ForeignKey(f'{AMENITIES}.type'), primary_key=True)
    property = relationship('Property', backref=AMENITIES)
    amenity = relationship('Amenity', backref=PROPERTY)

'''////////////////////////////////////////////////////////////////////////////'''

class Appliance(Feature):
    __tablename__ = APPLIANCES

class Property_Appliances(Base):
    __tablename__ = PROPERTY_APPLIANCES
    property_id = Column(ForeignKey(f'{PROPERTY}.{ROW_INDEX}'), primary_key=True)
    appliance_id = Column(ForeignKey(f'{APPLIANCES}.type'), primary_key=True)
    property = relationship('Property', backref=APPLIANCES)
    appliance = relationship('Appliance', backref=PROPERTY)

'''////////////////////////////////////////////////////////////////////////////'''

class Parking(Feature):
    __tablename__ = PARKING

class Property_Parking(Base):
    __tablename__ = PROPERTY_PARKING
    property_id = Column(ForeignKey(f'{PROPERTY}.{ROW_INDEX}'), primary_key=True)
    parking_id = Column(ForeignKey(f'{PARKING}.type'), primary_key=True)
    property = relationship('Property', backref=PARKING)
    parking = relationship('Parking', backref=PROPERTY)