from database import LISTING, PROPERTY_AMENITIES, PROPERTY_APPLIANCES, PROPERTY_PARKING, ROW_INDEX, PROPERTY
from sqlalchemy import Column, Date, Float, Integer, String, Boolean
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

LISTING_DB_COLUMNS: list[str] = Listing.table_columns()

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
    children_welcome = Column(Integer(), name='Children Welcome')
    pets_allowed = Column(Integer(), name='Pets Allowed')
    utility_payments = Column(Integer(), name='Utility Payments')
    listing = Base.add_foreign_key(Integer(), f'{LISTING}.{ROW_INDEX}', name=LISTING)

PROPERTY_DB_COLUMNS: list[str] = Property.table_columns()

def property_id_fk():
    return Base.add_foreign_key(Integer(), f'{PROPERTY}.{ROW_INDEX}', name="Property_ID", primary_key=True)

def feature_fk(type_name: str):
    return Base.add_foreign_key(String(), f'{type_name}.type', primary_key=True, name=f'{type_name}_type')

class Property_Amenities(Base): 
    __tablename__ = PROPERTY_AMENITIES
    property_id = property_id_fk()
    Amenities_type = feature_fk(AMENITIES)
    property = relationship('Property', backref=AMENITIES)
    amenity = relationship('Amenity', backref=PROPERTY)

class Property_Appliances(Base):
    __tablename__ = PROPERTY_APPLIANCES
    property_id = property_id_fk()
    Appliances_type = feature_fk(APPLIANCES)
    property = relationship(PROPERTY, backref=APPLIANCES)
    appliance = relationship(APPLIANCES, backref=PROPERTY)

class Property_Parking(Base):
    __tablename__ = PROPERTY_PARKING
    property_id = property_id_fk()
    parking_type = feature_fk(PARKING)
    property = relationship('Property', backref=PARKING)
    parking = relationship('Parking', backref=PROPERTY)