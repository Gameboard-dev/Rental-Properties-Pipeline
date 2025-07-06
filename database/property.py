from typing import Dict
from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, Boolean
from sqlalchemy.types import TypeEngine
from sqlalchemy.orm import relationship
from model.base import Base


class Renovation(Base):
    __tablename__ = 'renovation'
    type = Column(String(), primary_key=True)


class Construction(Base):
    __tablename__ = 'construction'
    type = Column(String(), primary_key=True)


class Listing(Base):
    __tablename__ = 'listing'
    id = Column(Integer(), primary_key=True)
    date = Column(Date(), name='Date')
    price = Column(Float(), name='Price')
    currency = Base.foreign_key(String(4), 'currency.code', name='Currency')
    duration = Column(String(), name='Duration')


class Property(Base):
    __tablename__ = 'property'
    id = Column(Integer(), primary_key=True)
    address = Base.foreign_key(Integer(), 'address.id')
    floor = Column(Integer(), name='Floor')
    floors = Column(Integer(), name='Floors_in_the_building')
    floor_area = Column(Integer(), name='Floor_area')
    rooms = Column(Integer(), name="Number_of_rooms")
    bathrooms = Column(Integer(), name="Number_of_bathrooms")
    ceiling_height = Column(Float(), name="Ceiling_height")
    renovation = Base.foreign_key(String(), 'renovation.type', name='Renovation')
    construction = Base.foreign_key(String(), 'construction.type', name='Construction')
    balcony = Column(Boolean(), name='Balcony')
    furnished = Column(Boolean(), name='Furnished')
    elevator = Column(Boolean(), name='Elevator')
    listing = Base.foreign_key(Integer(), 'listing.id')


PROPERTY_COLUMNS: Dict[str, TypeEngine] = dict(Property.columns(exclude=['id'], typified=True))


class Feature(Base):
    __abstract__ = True
    type = Column(String(), primary_key=True)

'''////////////////////////////////////////////////////////////////////////////'''

class Amenity(Feature):
    __tablename__ = 'amenities'

class Property_Amenities(Base): 
    __tablename__ = 'property_amenities'
    property_id = Column(ForeignKey('property.id'), primary_key=True)
    amenity_id = Column(ForeignKey('amenities.id'), primary_key=True)
    property = relationship('Property', backref='amenity_links')
    amenity = relationship('Amenity', backref='property_links')

'''////////////////////////////////////////////////////////////////////////////'''

class Appliance(Feature):
    __tablename__ = 'appliances'

class Property_Appliances(Base):
    __tablename__ = 'property_appliances'
    property_id = Column(ForeignKey('property.id'), primary_key=True)
    appliance_id = Column(ForeignKey('appliances.id'), primary_key=True)
    property = relationship('Property', backref='appliance_links')
    appliance = relationship('Appliance', backref='property_links')

'''////////////////////////////////////////////////////////////////////////////'''

class Parking(Feature):
    __tablename__ = 'parking'

class Property_Parking(Base):
    __tablename__ = 'property_parking'
    property_id = Column(ForeignKey('property.id'), primary_key=True)
    parking_id = Column(ForeignKey('parking.id'), primary_key=True)
    property = relationship('Property', backref='parking_links')
    parking = relationship('Parking', backref='property_links')