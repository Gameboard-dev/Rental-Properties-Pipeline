from enum import Enum
from functools import lru_cache
from settings import logging
from graphviz import Digraph
from collections import defaultdict
from sqlalchemy import MetaData, Table
from sqlalchemy.orm import Mapper
from database.address import *
from database.currency import *
from database.property import *
from database.feature import *
from database.base import Base

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

metadata = Base.metadata

LAYOUT_CONFIG = {
    "rankdir": "LR",
    "splines": "true",
    "overlap": "false",
    "ranksep": "1.3",
    "nodesep": "0.8",
}

COLOR_SCHEMA = {
    "Strong Entity": "#e6f2ff",
    "Weak Entity": "#ffe6e6",
    "Associative Entity": "#f1e78d"
}

PK_ICON = "🔑"
FK_ICON = "🔗"

class EntityType(Enum):
    STRONG = "Strong Entity"
    WEAK = "Weak Entity"
    ASSOCIATIVE = "Associative Entity"
    INHERITED = "Inherited Entity"

RENDERED_TABLES = set()

# ─────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────

def build_html_table(rows: list[str], heading: str = None, bgcolor: str = None) -> str:
    """ Constructs and returns a table as a Graphviz html label """
    bgcolor = f' BGCOLOR="{bgcolor}"' if bgcolor else ""
    rows = "\n".join(rows)
    table_contents = f"{heading}\n{rows}" if heading else rows
    return f"""<
    <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0"{bgcolor}>
        {table_contents}
    </TABLE>>"""

def entity_categorization(table: Table) -> EntityType:
    ''' Classifies an entity as weak, strong or associative, by foreign and primary keys '''
    pk_cols = {col.name for col in table.primary_key.columns}
    fk_cols = {fk.parent.name for fk in table.foreign_keys}
    if (model := sqlalchemy_model(table.name)) and inherits(model):
        return EntityType.INHERITED
    elif pk_cols == fk_cols and len(pk_cols) > 1:
        return EntityType.ASSOCIATIVE
    elif pk_cols & fk_cols and len(pk_cols) > 1:
        return EntityType.WEAK
    else:
        return EntityType.STRONG

def color_code(type_name: str):
    ''' Assigns a color code to an entity based on the entity type '''
    return COLOR_SCHEMA[type_name]

def html_syntax_name(name: str) -> str:
    ''' Converts a string name with spaces into Graphvis compatible syntax '''
    return name.replace(" ", "_").replace("-", "_")

def build_html_columns(col: Column, pk: set, fk: set) -> str:

    icons = []
    if col.name in pk:
        icons.append(PK_ICON)
    if col.name in fk:
        icons.append(FK_ICON)

    left_port = html_syntax_name(col.name) + "_LEFT"
    right_port = html_syntax_name(col.name) + "_RIGHT"

    def port_cell(p):
        """Generates Graphviz HTML for a table cell PORT """
        return f'<TD PORT="{p}" WIDTH="5" HEIGHT="10" ALIGN="CENTER" VALIGN="MIDDLE">&nbsp;</TD>'

    return (
        "<TR>"
        + port_cell(left_port)
        + f'<TD ALIGN="LEFT" VALIGN="MIDDLE">{" ".join(icons)} {col.name}</TD>'
        + f'<TD ALIGN="LEFT" VALIGN="MIDDLE">{col.type}</TD>'
        + port_cell(right_port)
        + "</TR>"
    )


def inherits(cls) -> bool:
    """ Check whether any of the class's superclasses are subclasses of Base, excluding Base itself """
    return any(issubclass(superclass, Base) and superclass is not Base for superclass in cls.__bases__)


@lru_cache(maxsize=None)
def sqlalchemy_model(table_name: str) -> type | None:
    ''' Maps a table_name to a model class when called initially and caches the results '''
    for mapper in Base.registry.mappers:
        table : Table = mapper.local_table
        if isinstance(mapper, Mapper) and table.name == table_name:
            #logging.debug(f"Mapped table: {table.name} == {table_name}")
            return mapper.class_
    return None


# ─────────────────────────────────────────────────────────────
# DIAGRAM CONSTRUCTION
# ─────────────────────────────────────────────────────────────

def add_table_node(graph: Digraph, table: Table):
    """Adds a table node to a Digraph with a HTML-style label representing its structure """

    # Skip rendering if already rendered
    if table.name in RENDERED_TABLES: 
        return

    RENDERED_TABLES.add(table.name)

    # Identify the primary and foreign keys
    pk = {col.name for col in table.primary_key.columns}
    fk = {fk.parent.name for fk in table.foreign_keys}

    # Classify as strong, weak, association entity
    entity_type: EntityType = entity_categorization(table)

    # Build the table heading across the columns/cells
    columns = 4
    heading = (
        f'<TR><TD COLSPAN="{columns}" BGCOLOR="lightgray" ALIGN="CENTER" CELLPADDING="4">'
        f'<FONT POINT-SIZE="16"><B>{table.name.replace("_", " ").title()}</B></FONT></TD></TR>'
    )

    # Generate full HTML label with rows for each column and color coded by the entity type
    label = build_html_table(
        rows=[build_html_columns(col, pk, fk) for col in table.columns],
        heading=heading,
        bgcolor=color_code(entity_type.value)
    )

    # Add the label node to the graph
    graph.node(table.name, label=label, shape='plaintext')


def add_tables(canvas: Digraph, metadata: MetaData):

    # Conceptual Aggregates
    groups: dict[str, list[Table]] = defaultdict(list) 

    for table in metadata.tables.values():
        if model := sqlalchemy_model(table.name):
            module = model.__module__.split('.')[-1]
            #logging.debug(f"{model.__name__} is in {module}")
            groups[module].append(table)

    cluster_heads: list[str] = []
    for module, tables in groups.items():
        with canvas.subgraph(name=f"cluster_{module}") as subgraph:
            subgraph.attr(
                label=module.capitalize(),
                labelloc='t',        # Top Position
                labeljust='c',       # Centre Position
                style='dashed',      # Border Style
                fontname='Helvetica-Bold',
                fontsize='14'        # Cluster Title
            )
            for table in tables:
                add_table_node(subgraph, table)

            if tables:
                cluster_heads.append(tables[0].name)

    # Link cluster head nodes with invisible edges to enforce vertical ordering
    for i in range(len(cluster_heads) - 1):
        canvas.edge(cluster_heads[i], cluster_heads[i + 1], style="invis")


def add_connectors(canvas: Digraph, metadata: MetaData):
    ''' Adds connecting edges using ports defined as foreign key destination and source names '''

    for table in metadata.tables.values():
        for fk in table.foreign_keys:
            
            source_col = fk.parent
            source_table = source_col.table

            destination_col = fk.column
            destination_table = destination_col.table

            cardinality = "0..*" if source_col.nullable else "1..*"

            entity: EntityType = entity_categorization(table)

            if entity == EntityType.INHERITED:
                logging.info("Inherited")
                connector_args = {
                    "arrowhead": "empty",
                    "dir": "forward",
                    "color": "grey",
                }

            else:
                connector_args = {"arrowhead": "none", "arrowtail": "none", "color": "grey", 
                                  "labelangle": "0", "labeldistance": "2", "labelfontsize": "12",
                                  "fontname": "Helvetica-Bold", "fontcolor": "black", "taillabel": "1",
                                  "headlabel": cardinality, "fontsize": "11","xlabel": "is in"}

                if entity == EntityType.WEAK:
                    connector_args.update({"arrowtail": "diamond", "dir": "both"})  # ◆

                elif entity == EntityType.ASSOCIATIVE:
                    connector_args.update({"arrowtail": "odiamond", "dir": "both"})  # ◇

            destination_port = html_syntax_name(destination_col.name) + "_RIGHT"
            source_port = html_syntax_name(source_col.name) + "_LEFT"

            canvas.edge(
                destination_table.name,
                source_table.name,
                tailport=destination_port,
                headport=source_port,
                **connector_args
            )


def build_a_html_legend(canvas: Digraph) -> None:
    """Constructs HTML-style legend for the Graphviz schema."""

    def row(text, bgcolor=None, align="LEFT", size=14, bold=False):
        font = f"<FONT POINT-SIZE='{size}'>{'<B>' if bold else ''}{text}{'</B>' if bold else ''}</FONT>"
        cell = f'<TD{" BGCOLOR=" + repr(bgcolor) if bgcolor else ""} ALIGN="{align}">{font}</TD>'
        return f"<TR>{cell}</TR>"

    rows = [
        row("Legend", size=16, bold=True),
        *[row(color_code, bgcolor=COLOR_SCHEMA[color_code], align="CENTER", bold=True) for color_code in COLOR_SCHEMA],
        row("Relationships", size=14, bold=True),
        row("♦ Composition"),
        row("◊ Association"),
        #row("▷ Inheritance"),
    ]

    with canvas.subgraph() as legend:
        legend.attr(rank='min')
        legend.node('legend', label=build_html_table(rows), shape='plaintext')


# ─────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────

def render_entity_relationship_diagram():
    canvas = Digraph(comment='UML ER Diagram', engine='dot')
    canvas.attr(**LAYOUT_CONFIG)
    add_tables(canvas, metadata)
    add_connectors(canvas, metadata)
    build_a_html_legend(canvas)
    canvas.render('UML_ER_Diagram', format='pdf', view=True)


if __name__ == '__main__':
    # python -m scripts.entity
    render_entity_relationship_diagram()