ADDRESS_INDEX = 'Index'
FURNISHED = "Furnished"
RENOVATION = "Renovation"
CONSTRUCTION = "Construction"
NEW_CONSTRUCTION = "New Construction"
BALCONY = "Balcony"
ELEVATOR = "Elevator"
FLOOR_AREA = "Floor_area"
FLOOR = "Floor"
FLOORS = "Floors"
ROOMS = "Rooms"
BATHROOMS = "Bathrooms"
CEILING_HEIGHT = "Ceiling_height"
DURATION = "Duration"
CHILDREN_WELCOME = "Children Welcome"
PETS_ALLOWED = "Pets Allowed"
UTILITY_PAYMENTS = "Utility Payments"

ADDRESS = "Address"
TRANSLATED = "Translated"
FORMATTED = 'Formatted'
RANK = 'Rank'
LATITUDE = 'Latitude'
LONGITUDE = 'Longitude'
PRICE = "Price"
CURRENCY = "Currency"
DATE = "Date"
AMENITIES = "Amenities"
APPLIANCES = "Appliances"
PARKING = "Parking"
BUILDING = 'Building'
STREET = 'Street'
STREET_NUMBER = "Street Number"
SQUARE = 'Square'
TOWN = 'Town'
VILLAGE = 'Village'
COUNTRY = 'Country'
ADMINISTRATIVE_UNIT = 'Administrative District'
PROVINCE = 'Province'
NEIGHBOURHOOD = 'Neighbourhood'
LANE = 'Lane'
BLOCK = 'Block'
ADDRESS_COLUMNS = [BUILDING, STREET, STREET_NUMBER, TOWN, BLOCK, LANE, ADMINISTRATIVE_UNIT, NEIGHBOURHOOD, PROVINCE, COUNTRY]
STRING_COLUMNS = [CURRENCY, DURATION, RENOVATION, CONSTRUCTION]
NUMERIC_COLUMNS = [BALCONY, FURNISHED, ELEVATOR, PRICE, FLOOR_AREA, FLOOR, FLOORS, ROOMS, BATHROOMS, CEILING_HEIGHT, CHILDREN_WELCOME, PETS_ALLOWED, UTILITY_PAYMENTS, NEW_CONSTRUCTION, UTILITY_PAYMENTS, PETS_ALLOWED, CHILDREN_WELCOME]
PREFIX_MAPPING = {AMENITIES: 1, APPLIANCES: 2, PARKING: 3}
RENAMED_COLUMNS = {
    "Children_are_welcome": CHILDREN_WELCOME,
    "Pets_allowed": PETS_ALLOWED,
    "Utility_payments": UTILITY_PAYMENTS,
    "New_construction": NEW_CONSTRUCTION,
    "Floors_in_the_building": FLOORS,
    "Number_of_rooms": ROOMS,
    "Number_of_bathrooms": BATHROOMS,
    "Furniture": FURNISHED,
    "Construction_type": CONSTRUCTION,
    "Datetime": DATE,
    "amenities": AMENITIES,
    "appliances": APPLIANCES,
    "parking": PARKING
}