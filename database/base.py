
from typing import Callable, List, Self, Type, Union
from sqlalchemy.orm import Mapper, DeclarativeBase, DeclarativeMeta
from sqlalchemy import Column, ForeignKey, Table, inspect
from typing import Tuple 
from sqlalchemy.types import TypeEngine

class Base(DeclarativeBase):

    __abstract__ = True
    
    @classmethod
    def columns(
        cls: type[Self],
        exclude: Union[str, List[str]] = '',
        typified: bool = False
    ) -> List[Union[str, Tuple[str, TypeEngine]]]:
        """ Returns column names for the mapped class, optionally including types. """
        excluded = {exclude} if isinstance(exclude, str) else set(exclude or [])
        mapper: Mapper = inspect(cls)
        columns = mapper.columns

        values: Callable[[Column], Union[str, tuple[str, TypeEngine]]] = (
            (lambda col: (col.name, col.type)) if typified else (lambda col: col.name)
        )

        return [values(col) for col in columns if col.name not in excluded]


    @staticmethod
    def add_foreign_key(
        datatype: TypeEngine,
        ref: str,
        *, # Marks the beginning of keyword-only arguments.
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
    
    @staticmethod
    def map_table(model: Type[DeclarativeMeta]) -> Table:
        '''
        If the class is not mapped to an SQLAlchemy Table a `TypeError` is raised. Otherwise the mapped Table is returned.
        '''
        mapper: Mapper = inspect(model)
        if table := mapper.mapped_table is None:
            raise TypeError(f"{model.__name__} is not mapped as a Table.")
        return table




