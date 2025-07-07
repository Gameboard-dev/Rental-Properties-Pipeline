import re, logging
import unicodedata

import pandas as pd
from scripts.api.translate import is_non_english_string
from scripts.csv_columns import *

ORDINAL_SUFFIX = r'(st|nd|rd|th)'
NEIGHBOURHOOD_SUFFIX = r'(?:district|micro[-\s]?district|micro|neighborhood|quarter)'

WHITESPACE_RGX = re.compile(r'_|none|\s+', flags=re.IGNORECASE)
PUNCTUATION_RGX = re.compile(r'[^\w\s]', flags=re.UNICODE)

def normalize_string(value: str) -> str:
    ''' Applies extreme string normalization. Removes accented characters / spaces / underscores / punctuation '''
    if pd.isna(value) or not isinstance(value, str):
        return ''
    # Replace underscores, 'none', and extra spaces
    value = WHITESPACE_RGX.sub(' ', value)
    # Normalize unicode and accented characters
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    # Removes punctuation
    value = PUNCTUATION_RGX.sub('', value)
    return value.strip().title()

def normalize_column(col: pd.Series) -> pd.Series:
    return col.apply(normalize_string)

ORDINAL_RGX = re.compile(rf'(\d+)-?{ORDINAL_SUFFIX}', flags=re.IGNORECASE)

def fix_ordinals(string: str) -> str:
    """Removes dashes or spaces in ordinals (e.g., '2-nd' or '3 rd' → '2nd', '3rd')."""
    return ORDINAL_RGX.sub(r'\1\2', string)

ALPHANUMERIC_CODE_RGX = re.compile(r'\b(\d{1,5})\s+([A-Za-z])\b')

def fix_alphanumeric_codes(string: str) -> str:
    """Joins digits followed by trailing letters (e.g., '123 A' → '123A')."""
    return ALPHANUMERIC_CODE_RGX.sub(r'\1\2', string)

STREET_RGX = re.compile(r'\b(st\.?|street|str|srteet|stret\.?)\b', flags=re.IGNORECASE)
HIGHWAY_RGX = re.compile(r'\b(hwy|highway)\b', flags=re.IGNORECASE)
AVENUE_RGX = re.compile(r'\b(ave|avenue|avenu)\b', flags=re.IGNORECASE)

def expand_abbreviations(name: str) -> str:
    name = STREET_RGX.sub('Street', name)
    name = HIGHWAY_RGX.sub('Highway', name)
    name = AVENUE_RGX.sub('Avenue', name)
    name = name.replace("Blok", "Block")
    return name

def integer_to_ordinal(n: int) -> str:
    """Returns an integer into its ordinal form."""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

DIGIT_NEIGHBOURHOOD_RGX = re.compile(rf'\b(\d+)[\s\-]*({NEIGHBOURHOOD_SUFFIX})\b', flags=re.IGNORECASE)

def fix_neighborhood_prefixes(string: str) -> str:
    """Applies ordinal suffixes to numeric identifiers in all neighbourhoods. (I.E. 1 Quarter becomes 1st Quarter) """
    def substitute(match: re.Match):
        num, label = match.group(1), match.group(2)
        try: return f"{integer_to_ordinal(int(num))} {label}"
        except ValueError: return match.group(0)
    return DIGIT_NEIGHBOURHOOD_RGX.sub(substitute, string)

def apply_title_casing(string: str) -> str:
    ''' Ignores ordinal patterns when title casing a string '''
    return ' '.join(word if ORDINAL_RGX.match(word) else word.capitalize() for word in string.split())

def remove_ascii(string: str) -> str:
    ''' Return "" if all characters in the string are ASCII excluding "›" delimiters '''
    if is_non_english_string(string): return ""
    else: return string

def normalize_address_parts(string: str) -> str:
    ''' Normalizes abbreviations / whitespace / punctuation (and removes non-English strings) '''
    if not isinstance(string, str):
        return ""
    try:
        string = WHITESPACE_RGX.sub(' ', string)
        string = remove_ascii(string)

        if string == "": 
            return string
        
        else:
            string = fix_ordinals(string)
            string = fix_neighborhood_prefixes(string)
            string = fix_alphanumeric_codes(string)
            string = expand_abbreviations(string)
            string = apply_title_casing(string)
            #logging.debug(f"Parsed {string} succesfully")
            return string
        
    except Exception as e:
        logging.warning(f"Error when parsing '{string}' : {e}")


