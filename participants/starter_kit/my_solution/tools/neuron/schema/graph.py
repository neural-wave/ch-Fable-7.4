"""The relations as a graph: tables as nodes, relations as edges from the child table to the parent table.

Two simplifications keep the picture readable:

- A key domain that several tables share with exactly the same values (e.g. the funds) becomes one hub node
  that the tables point to, instead of an edge between every pair of them.
- A one-column relation implied by a two-column relation of the same table is left out.

The edges are built as a table first (`relation_edges`): every edge has a `kind` ("member", "name", "data",
"approx") and a `label`, and `diagram` draws them by kind.
"""
import networkx as nx
import polars as pl

from neuron.load import tables
from neuron.schema.keys import abbreviation
from neuron.schema.relations import distinct_values

CHILD, PARENT = ["table", "columns"], ["ref_table", "ref_columns"]
EDGES = {"source": pl.String, "target": pl.String, "kind": pl.String, "label": pl.String}


def hubs(found: pl.DataFrame) -> dict[tuple[str, str], str]:
    """{(table, columns): hub name} for columns with exactly the same values in several tables.

    Such columns include each other: they are linked by INDs in both directions. The hub is named after the
    keys of its columns, e.g. "FNDID".
    """
    links = nx.DiGraph(((r["table"], r["columns"]), (r["ref_table"], r["ref_columns"]))
                       for r in found.iter_rows(named=True))
    same_values = links.to_undirected(reciprocal=True)
    same_values.remove_nodes_from(list(nx.isolates(same_values)))
    names = {}
    for component in nx.connected_components(same_values):
        name = "/".join(sorted({abbreviation(col) for _, cols in component for col in cols.split(", ")}))
        names.update(dict.fromkeys(component, name))
    return names


def hub_members(hub: dict[tuple[str, str], str], side: list[str], name: str) -> pl.DataFrame:
    """The members of the hubs as a table with the columns `side` (child or parent) and the hub as `name`."""
    rows = [dict(zip([*side, name], [*member, hub_name], strict=True)) for member, hub_name in hub.items()]
    return pl.DataFrame(rows, schema=dict.fromkeys([*side, name], pl.String))


def paired_columns(found: pl.DataFrame) -> pl.DataFrame:
    """table and columns of every single column that takes part in a two-column relation.

    A one-column relation of such a column says less than the pair, e.g. `PR_POLNR` alone next to
    `PR_POLNR, PR_EVTNR` -> NREVNT.
    """
    pairs = found.filter(pl.col("arity").gt(1))
    return pairs.select("table", pl.col("columns").str.split(", ")).explode("columns").unique(maintain_order=True)


def business_keys(columns: str) -> pl.Expr:
    """The business keys of the columns in `columns`: "PR_POLNR, PR_EVTNR" -> "POLNR+EVTNR"."""
    return pl.col(columns).str.replace_all(r"\b[A-Z0-9]+_", "").str.replace_all(", ", "+")


def edge_attributes(to_hub: pl.Expr) -> dict[str, pl.Expr]:
    """Kind and label of a relation edge.

    The kind is "approx" for an approximate IND (some values missing), else "name" for the same key name in both
    tables, else "data" for a link found from the values only. The label is the key; when the names differ and
    the target is a table, it shows both keys ("MORTTB -> TABID").
    """
    kind = pl.when(pl.col("error").gt(0)).then(pl.lit("approx")).when("same_name").then(pl.lit("name"))
    both_keys = pl.format("{} -> {}", business_keys("columns"), business_keys("ref_columns"))
    label = pl.when(pl.any_horizontal("same_name", to_hub)).then(business_keys("columns")).otherwise(both_keys)
    return {"kind": kind.otherwise(pl.lit("data")), "label": label}


def relation_edges(found: pl.DataFrame, hub: dict[tuple[str, str], str]) -> pl.DataFrame:
    """One row per drawn relation: source table, target (the parent table or its hub), kind and label.

    Relations with both ends in the same hub (the hub shows them) and implied one-column relations are left out.
    """
    linked = (found.join(paired_columns(found), on=CHILD, how="anti", maintain_order="left")
              .join(hub_members(hub, CHILD, "child_hub"), on=CHILD, how="left", maintain_order="left")
              .join(hub_members(hub, PARENT, "parent_hub"), on=PARENT, how="left", maintain_order="left"))
    drawn = linked.filter(pl.col("child_hub").eq(pl.col("parent_hub")).fill_null(False).not_())
    to_hub = pl.col("parent_hub").is_not_null()
    return drawn.select(source="table", target=pl.coalesce("parent_hub", "ref_table"), **edge_attributes(to_hub))


def merged_edges(edges: pl.DataFrame) -> pl.DataFrame:
    """One edge per pair of nodes: the kind of the first link, the labels of all links one per line."""
    labels = pl.col("label").unique(maintain_order=True).str.join("\n")
    return edges.group_by("source", "target", maintain_order=True).agg(pl.col("kind").first(), labels)


def relation_graph(found: pl.DataFrame) -> nx.DiGraph:
    """Graph of the relations in `found` (the rows of `relations()` with `relation` true).

    Every table is a node, also without relations; a hub node knows how many distinct values its domain has,
    and every member table points to it.
    """
    found = found.filter(pl.col("relation"))
    hub = hubs(found)
    graph = nx.DiGraph()
    graph.add_nodes_from(tables("NRDICT"), kind="table")
    graph.add_nodes_from((name, {"kind": "hub", "values": distinct_values(*member).height})
                         for member, name in hub.items())
    members = pl.DataFrame([[table, name, "member", ""] for (table, _), name in hub.items()], schema=EDGES,
                           orient="row")
    edges = merged_edges(pl.concat([members, relation_edges(found, hub)]))
    graph.add_edges_from((source, target, {"kind": kind, "label": label})
                         for source, target, kind, label in edges.iter_rows())
    return graph
