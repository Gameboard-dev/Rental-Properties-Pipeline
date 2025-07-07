import re, logging
import pandas as pd
from typing import Dict, List, Union, Tuple
from sqlalchemy import Column, ForeignKey, Insert, Table, inspect
from sqlalchemy.orm import DeclarativeBase, Mapper
from sqlalchemy.schema import CreateTable
from sqlalchemy.types import TypeEngine
from sqlalchemy.dialects.postgresql import insert
from database import ROW_INDEX, LINKAGE_MAP, LISTING, PROPERTY, TABLES
from database.address import ADDRESS_DB_COLUMNS
from database.property import LISTING_COLUMNS, PROPERTY_COLUMNS
from scripts.address.lookup import administrative_pairs, row_values
from scripts.process import PREFIX_MAPPING
from scripts.csv_columns import *
from settings import engine


class Base(DeclarativeBase):


    __abstract__ = True


    @classmethod
    def columns(
        cls,
        excluded: set[str],
        typed: bool = False
    ) -> List[Union[Tuple[str, TypeEngine], str]]:
        """
        Returns column names (and optionally types) for a mapped class,
        excluding specified column names.
        """
        map: Mapper = inspect(cls)
        cols: list[Column] = [col for col in map.columns if col.name not in excluded]
        
        return [(col.name, col.type) if typed else col.name for col in cols]


    @staticmethod
    def add_foreign_key(
        datatype: TypeEngine,
        ref: str,
        *, # Beginning of keyword-only arguments.
        ondelete: str = 'CASCADE',
        onupdate: str = 'CASCADE',
        primary_key: bool = False,
        nullable: bool = True,
        name: str = None
    ) -> Column:
        return Column(
            datatype,
            ForeignKey(ref, ondelete=ondelete, onupdate=onupdate),
            primary_key=primary_key,
            nullable=nullable,
            name=name
        )

    @classmethod
    def build_upserts(cls, df: pd.DataFrame) -> Dict[str, List[Dict[str, str]]]:

        upserts = {}

        upserts[PROVINCE] = row_values(df[PROVINCE], 'name')
        upserts[TOWN] = row_values(df[TOWN], 'name')

        upserts[RENOVATION] = row_values(df[RENOVATION], 'type')
        upserts[CONSTRUCTION] = row_values(df[CONSTRUCTION], 'type')

        upserts[CURRENCY] = row_values(df[CURRENCY], 'code')

        unique_administrative_pairs: pd.Series = administrative_pairs(df)
        upserts[ADMINISTRATIVE_UNIT] = unique_administrative_pairs.to_dict()

        for name in [AMENITIES, APPLIANCES, PARKING]:

            id = PREFIX_MAPPING[name]
            prefix = f'{id}_'

            mask: pd.DataFrame = df.filter(regex=f'^{prefix}')

            choices: list[str] = [col[len(prefix):] for col in mask.columns]
            upserts[name] = row_values(choices, 'type')

            linkage = LINKAGE_MAP[name]
            upserts[linkage] = cls.compile_linkage_values(df, prefix, mask.columns)

        # Values on the same row are linked via ther 'ROW_INDEX' value which applies here.
        upserts[LISTING] = df[LISTING_COLUMNS].to_dict(orient='records')
        upserts[ADDRESS] = df[ADDRESS_DB_COLUMNS].to_dict(orient='records')
        upserts[PROPERTY] = df[PROPERTY_COLUMNS].to_dict(orient='records')

        upserts[PROPERTY][ADDRESS] = df[ROW_INDEX]
        upserts[PROPERTY][LISTING] = df[ROW_INDEX]

        return upserts


    @classmethod
    def compile_tables(cls) -> List[str]:
        ''' Retrieves compiled SQL statements using CREATE TABLE IF NOT EXISTS '''
        return [
            str(CreateTable(cls.metadata.tables[name], if_not_exists=True).compile(engine))
            for name in TABLES
        ]
    

    def compile_linkage_values(df: pd.DataFrame, prefix: str, columns: list[str]) -> list[dict[str, str]]:
        ''' Acquires the corresponding Amenities / Appliances / Parking linkage for each Property index '''

        if df[columns].sum(axis=1).eq(0).all():
            return []

        melted: pd.DataFrame = (
            df[columns + ['id']]
            .rename(columns={'id': 'property_id'})
            .melt(id_vars='property_id')
            .assign(type=lambda df_: df_['variable'].str.replace(prefix, '', regex=False)) # assign 'type' column.
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


    @classmethod
    def format_inserts(compiled: str) -> str:
        """
        Formats a bulk SQL INSERT by:
        - Adding a newline before VALUES
        - Indenting each value tuple onto its own line
        """
        formatted = re.sub(r"\bVALUES\s*\(", "VALUES\n  (", compiled)
        formatted = re.sub(r"\),\s*\(", "),\n  (", formatted)
        return formatted + ";\n"


    @classmethod
    def compile_sql(cls, datasets: List[pd.DataFrame]) -> str:
        ''' Takes a cleaned and parsed DataFrame and compiles SQL inserts for a PostgreSQL database '''

        df: pd.DataFrame = pd.concat([*datasets], ignore_index=True)
        df[ROW_INDEX] = df.index # Primary / Foreign of Properties / Listings
        
        sql: List[str] = []

        sql += cls.compile_tables()
        upserts = cls.build_upserts(df)

        for table_name, row_values in upserts.items():

            if row_values: continue

            columns: list[str] = row_values[0].keys()
            index = columns

            table: Table = Base.metadata.tables[table_name]

            expression: Insert = insert(table).values(row_values).on_conflict_do_update( # ON CONFLICT DO UPDATE
                index_elements=index,
                set_={col: getattr(expression.excluded, col) for col in columns}
            )

            compiled_inserts: str = cls.format_inserts(str(expression.compile(dialect=engine.dialect, compile_kwargs={"literal_binds": True})))
            sql.append(compiled_inserts)

        return '\n'.join(sql)



