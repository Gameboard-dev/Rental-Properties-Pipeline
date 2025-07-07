from typing import List, Union, Tuple
from sqlalchemy import Column, ForeignKey, inspect
from sqlalchemy.orm import DeclarativeBase, Mapper
from sqlalchemy.types import TypeEngine

class Base(DeclarativeBase):

    __abstract__ = True

    @classmethod
    def table_columns(
        cls,
        exclude: set[str] = set(),
        typed: bool = False
    ) -> List[Union[Tuple[str, TypeEngine], str]]:
        """
        Returns column names (and optionally types) for a mapped class,
        excluding specified column names.
        """
        map: Mapper = inspect(cls)
        cols: list[Column] = [col for col in map.columns if col.name not in exclude]
        
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

