import logging
import re
import pandas as pd
from typing import List
from sqlalchemy import Compiled, Insert, insert, Table
from sqlalchemy.schema import CreateTable
from scripts.process import FEATURE_PREFIXES
from settings import engine
from database.base import Base
from database.address import *
from database.currency import *
from database.property import *

TABLES = [
    Province.__tablename__, 
    AdministrativeDivision.__tablename__, 
    Town.__tablename__, 
    Address.__tablename__, 
    Amenity.__tablename__,
    Appliance.__tablename__,
    Parking.__tablename__,
    Renovation.__tablename__,
    Construction.__tablename__,
    Currency.__tablename__,
    ExchangeRate.__tablename__,
    Listing.__tablename__,
    Property.__tablename__,
    Property_Amenities.__tablename__,
    Property_Appliances.__tablename__,
    Property_Parking.__tablename__,
    ]

def unique_administrative_pairs(df: pd.DataFrame) -> pd.Series:
    ''' Assumes every district in the data has a corresponding province and returns all unique pairs '''
    unique_pairs: pd.DataFrame = df[[ADMINISTRATIVE_UNIT, PROVINCE]].dropna().drop_duplicates()
    entries: pd.Series = unique_pairs.apply(
        lambda row: {
            'name': row['Administrative'],
            'province': row['Province']
        } if row['Administrative'] != '' and row['Province'] != '' else None,
        axis=1
    )
    return entries.dropna()


def compile_upserts(
    table: Table,
    row_values: list[dict],
    primary_key: list[str],
    columns: list[str]
) -> str:
    ''' Runs SQL compilation for ON CONFLICT DO UPDATE statements '''
    logging.debug(f"Running SQL compilation for {table.name}")
    stmt: Insert = insert(table).values(row_values)
    stmt = stmt.on_conflict_do_update(
        index_elements=primary_key,
        set_={col: getattr(stmt.excluded, col) for col in columns}
    )
    parsed: str = str(stmt.compile(dialect=engine.dialect, compile_kwargs={"literal_binds": True}))
    parsed = re.sub(r"\bVALUES\s*\(", "VALUES\n  (", parsed)
    parsed = re.sub(r"\),\s*\(", r"),\n  (", parsed) + ";\n"
    return parsed


def create_tables():
    sql: list[str] = []
    tables = [(name, Base.metadata.tables[name]) for name in TABLES]

    for name, table in tables:
        compiled: Compiled = CreateTable(table, if_not_exists=True).compile(engine)
        string: str = str(compiled).rstrip()
        sql.append(string + ";\n")

    return '\n'.join(sql)


def reference_value_inserts(df: pd.DataFrame):
    
    sql: list[str] = []
    upserts: dict[str, list[dict[str, str]]] = {} # (entries) dict[table_name, list[dict[table_column, column_value]]]

    columns = ['Province', 'Administrative', 'Town', 'Renovation', 'Construction', 'Feature']

    for i, csv_column in enumerate(columns):

        table_name: str
        
        if csv_column == 'Administrative':
            table_name = 'administrative_division'
            upserts[table_name] = unique_administrative_pairs(df)
            
        elif csv_column == 'Feature':
            for table_name, id in FEATURE_PREFIXES.items():
                prefix = f'{id}_' # '1_' '2_' '3_'
                mask = df.filter(regex=f'^{prefix}')
                columns = [col[len(prefix):] for col in mask.columns]
                if not columns: print(f"{table_name} has no columns")
                upserts[table_name] = [{'type': v} for v in columns]

        else: # 'Province', 'Town' // 'Renovation', 'Construction'
            table_name = csv_column.lower()
            column = 'name' if i < 3 else ('type' if i != 6 else 'code') # ternary condition
            unique = df[csv_column].dropna()
            unique = unique[unique.astype(str).str.strip() != ''].unique() # Filters away literal empty strings.
            #print(unique)
            upserts[table_name] = [{column: v} for v in unique]


    for table_name, row_values in upserts.items():
        columns: list[str] = row_values[0].keys()
        primary_key: list[str]
        
        if table_name == 'exchange_rate':
            primary_key = ['date', 'currency']
        else:
            primary_key = columns

        table = Base.metadata.tables[table_name]
        compiled_sql: str = compile_upserts(
                table, 
                row_values, 
                primary_key=primary_key, 
                columns=columns)
        sql.append(compiled_sql)

    return '\n'.join(sql)



def properties_values(df: pd.DataFrame):
    ''' 
    Builds SQL entries related to specific properties
    - listing
    - address
    - property
    '''
    sql: list[str] = []

    listings = df[['id', 'Date', 'Price', 'Duration', 'Currency']].to_dict(orient='records')
    addresses = df[['id'] + ADDRESS_COLUMNS].to_dict(orient='records')
    properties = df[['id'] + [col for col in PROPERTY_COLUMNS if col in df.columns]].to_dict(orient='records')

    '''
    Note: 'address' contains addresses linked to 'specific' properties and cross-referenced with foreign keys.
    '''

    entries: dict[str, list[dict[str, str]]] = {
        'listing': listings,
        'address': addresses,
        'property': properties,
    }

    for table_name, row_values in entries.items():
        compiled_sql = compile_upserts(
            table = Base.metadata.tables[table_name],
            row_values = row_values,
            primary_key = ['id'],
            columns = row_values[0].keys()
        )
        sql.append(compiled_sql)

    return '\n'.join(sql)


def property_feature_linkages(df: pd.DataFrame, prefix: str) -> list[dict[str, str]]:

    columns = [col for col in df.columns if col.startswith(prefix)]

    if df[columns].sum(axis=1).eq(0).all():
        return []

    melted = (
        df[columns + ['id']]
        .rename(columns={'id': 'property_id'})
        .melt(id_vars='property_id')
        .assign(type=lambda df_: df_['variable'].str.replace(prefix, '', regex=False)) # assign 'type' column.
        .drop(columns='variable')
    )

    """
    Melted:
        property_id    variable             value
        101            Air Conditioner     1
        101            Internet            0
        101            Parking Space       1
    """

    matched = melted[melted['value'] == 1].drop(columns=['value'])

    return matched.to_dict(orient='records')


def linkage_table_values(df: pd.DataFrame):
    '''
    Compiles entries in linking tables which model many-to-one relationships.
    <br> The following linking tables are assumed to be used:
    - property_amenities
    - property_appliances
    - property_parking
    '''
    sql: list[str] = []

    for name, id in FEATURE_PREFIXES.items():
        table: Table = Base.metadata.tables[name]
        #print(f"Found Table: {table.name}")
        prefix = f'{id}_'
        row_values: list[dict[str,str]] = property_feature_linkages(df, prefix)
        if not row_values: 
            print(f"{table.name} has no valid attributes in DataFrame.")
            continue
        #print(f"row_values: {row_values}")
        columns = primary_key = ['property_id', 'type']
        sql_entry = compile_upserts(
            table,
            row_values,
            primary_key,
            columns
        )
        sql.append(sql_entry)
    
    return '\n'.join(sql)


def compile_sql_entries(datasets: List[pd.DataFrame]) -> str:
    df: pd.DataFrame = pd.concat([*datasets], ignore_index=True) # Remember to ignore the index so index acts as a unique row index
    df['id'] = df.index

    sql: str = ""
    sql += create_tables()
    sql += reference_value_inserts(df)
    sql += properties_values(df)
    sql += linkage_table_values(df)

    return sql


