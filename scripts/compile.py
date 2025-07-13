import logging
import re
import numpy as np
import pandas as pd
from sqlalchemy import Compiled, Insert, Table
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects.postgresql import insert
from database import ROW_INDEX, LINKAGE_MAP, LISTING, PROPERTY
from database.base import Base
from database.address import *
from database.currency import *
from database.property import *
from database.feature import *
from scripts.address.lookup import administrative_pairs, row_values
from scripts.process import PREFIX_MAPPING
from scripts.csv_columns import *
from settings import SQL_PATH, engine

COMPILE_LIST = [PROVINCE, TOWN, RENOVATION, CONSTRUCTION, CURRENCY, EXCHANGE_RATE, ADMINISTRATIVE_UNIT, LISTING, ADDRESS, PROPERTY, AMENITIES, PROPERTY_AMENITIES, APPLIANCES, PROPERTY_APPLIANCES, PARKING, PROPERTY_PARKING]

def build_upserts(df: pd.DataFrame) -> dict[str, list[dict[str, str]]]:

    upserts = {}

    upserts[PROVINCE] = row_values(df[PROVINCE], 'name')

    upserts[TOWN] = row_values(df[TOWN], 'name')

    upserts[RENOVATION] = row_values(df[RENOVATION], 'type')

    upserts[CONSTRUCTION] = row_values(df[CONSTRUCTION], 'type')

    upserts[CURRENCY] = row_values(df[CURRENCY], 'code')

    upserts[ADMINISTRATIVE_UNIT] = administrative_pairs(df)

    upserts[EXCHANGE_RATE] = ExchangeRate.database_entries()

    # *PROPERTY Prerequisites
    upserts[LISTING] = df[LISTING_DB_COLUMNS].to_dict(orient='records')

    upserts[ADDRESS] = df[ADDRESS_DB_COLUMNS].to_dict(orient='records')
    #*

    df_property = df.copy().assign(**{ADDRESS: df[ROW_INDEX], LISTING: df[ROW_INDEX]})
    upserts[PROPERTY] = df_property[PROPERTY_DB_COLUMNS].to_dict(orient='records')

    # *PROPERTY POSTREQUISITES
    for name in [AMENITIES, APPLIANCES, PARKING]:

        id = PREFIX_MAPPING[name]
        prefix = f'{id}_'

        mask: pd.DataFrame = df.filter(regex=f'^{prefix}')

        choices: list[str] = [col[len(prefix):] for col in mask.columns]
        upserts[name] = row_values(choices, 'type')

        linkage = LINKAGE_MAP[name] # Property is a prerequisite
        upserts[linkage] = compile_linkage_values(df, name, prefix, list(mask.columns))
    #*

    return upserts
    

def compile_linkage_values(df: pd.DataFrame, name: str, prefix: str, columns: list[str]) -> list[dict[str, str]]:
    ''' Acquires the corresponding Amenities / Appliances / Parking linkage for each Property index '''

    if df[columns].sum(axis=1).eq(0).all():
        return []

    linkage_column = f'{PROPERTY}_{ROW_INDEX}'

    melted: pd.DataFrame = (
        df[columns + [ROW_INDEX]]
        .rename(columns={ROW_INDEX: linkage_column})
        .melt(id_vars=linkage_column) # column 'type' assigned
        .assign(type=lambda df_: df_['variable'].str.replace(prefix, '', regex=False))
        .rename(columns={'type': f"{name}_type"})
        .drop(columns='variable')
    )

    """ Example

    Melted:
        property_id    variable             value
        101            Air Conditioner     1
        101            Internet            0
        101            Parking Space       1
    
    """

    matched = melted[melted['value'] == 1].drop(columns=['value'])

    return matched.to_dict(orient='records')


def apply_inserts_formatting(compiled_sql: str) -> str:
    """
    Formats a bulk SQL INSERT by:
    - Adding a newline before VALUES
    - Indenting each value tuple onto its own line
    """
    formatted = re.sub(r"\bVALUES\s*\(", "VALUES\n  (", compiled_sql)
    formatted = re.sub(r"\),\s*\(", "),\n  (", formatted)
    return formatted + ";\n"


def compile_sql(datasets: list[pd.DataFrame]) -> str:
    ''' Takes a cleaned and parsed DataFrame and compiles SQL inserts for a PostgreSQL database '''

    df: pd.DataFrame = pd.concat([*datasets], ignore_index=True)

    df = df.replace({pd.NA: None, np.nan: None, "": None}) # Replaces various 'None' placeholders with 'None' which SQL Alchemy will compile as NULL

    df[ROW_INDEX] = df.index # Primary / Foreign of Properties / Listings
    
    sql: list[str] = []

    upserts: dict[str, list[dict[str, str]]] = build_upserts(df)

    for table_name, row_values in upserts.items():

        if table_name not in COMPILE_LIST:
            continue

        create: Compiled = CreateTable(Base.metadata.tables[table_name], if_not_exists=True).compile(engine)
        sql.append(str(create).rstrip() + ";\n")

        if not row_values:
            logging.warning(f"No row values for table '{table_name}', skipping.")
            continue

        columns: list[str] = list(row_values[0].keys())
        index = columns

        if table_name in [PROPERTY, LISTING, ADDRESS]:
            index = [ROW_INDEX]

        if table_name == EXCHANGE_RATE:
            index = [CURRENCY, DATE]

        table: Table = Base.metadata.tables[table_name]

        logging.info(f"Parsing '{table.name}'")

        clause: Insert = insert(table).values(row_values)

        excluded = clause.excluded

        primary_key = [key.name for key in table.primary_key.columns]
        set_columns = [col for col in columns if col not in primary_key]

        if set_columns:
            clause = clause.on_conflict_do_update(
                index_elements=index,
                set_={col: getattr(excluded, col) for col in set_columns}
            )
        else:
            clause = clause.on_conflict_do_nothing(index_elements=index)

        compiled_inserts: str = str(clause.compile(dialect=engine.dialect, compile_kwargs={"literal_binds": True}))
        compiled_inserts: str = apply_inserts_formatting(compiled_inserts)
        sql.append(compiled_inserts)

    return '\n'.join(sql)



if __name__ == "__main__":

    # python -m scripts.compile
    from scripts.load import load

    training, testing, addresses = load()
    sql: str = compile_sql([training, testing])
    
    with open(SQL_PATH, "w", encoding="utf-8") as file: 
        file.write(sql)




