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
MONTHLY_USD_PRICE = 'Monthly USD Price'
PRICE_CHANGE = 'Price Change'
DISTANCE_FROM_CENTRE = 'Distance From Centre of Yerevan'
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
EXCLUSION_ID = 'EXCLUDED_ID'
DROP_REASON = 'REASON'
PLACE = "Place"
 
AMENITIES_RANK = "Amenities_Rank"
APPLIANCES_RANK = "Appliances_Rank"
PARKING_RANK = "Parking_Rank"

PRICE_BAND = "Price Band"

ADDRESS_COLUMNS = [BUILDING, STREET, STREET_NUMBER, TOWN, BLOCK, LANE, ADMINISTRATIVE_UNIT, NEIGHBOURHOOD, PROVINCE, COUNTRY]
PREFIX_MAPPING = {
    AMENITIES: 1, 
    APPLIANCES: 2, 
    PARKING: 3
}
RENAMED = {"Children_are_welcome": CHILDREN_WELCOME,
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

PREFIX_TO_RANK_COLUMN = {
    "1_": AMENITIES_RANK,
    "2_": APPLIANCES_RANK,
    "3_": PARKING_RANK,
}