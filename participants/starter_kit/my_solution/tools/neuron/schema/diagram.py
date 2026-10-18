"""Picture of the relation graph: tables coloured by group, key domains as grey hubs, edges styled by kind.

The groups of tables are those of the strategy document, plus the tax module that it leaves out. The picture
answers two questions at a glance: which tables hang on the policy, and which links are only approximate (the
red dotted edges point at references to rows that are missing in the export).

The texts of the picture are in Italian, like the notebooks.
"""
import collections

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

GROUPS = {
    "Polizza e persone": ["NRPOLH", "NRRISK", "NRPERS", "NRBROK"],
    "Prodotto e parametri": ["NRPROD", "NRCHRG", "NRENTC", "NRCOMR", "NRAGRE", "NRSURR", "NRWAIV", "NRILLU"],
    "Denaro e quote": ["NRPREM", "NRALLO", "NRBOOK"],
    "Mercato": ["NRFUND", "NRFPRC", "NRFXRT", "NRMORT"],
    "Eventi e metadati": ["NREVNT", "NRCODE", "NRDICT", "NREXCP"],
    "Modulo fiscale": ["NRHOLD", "NRADDR", "NRTAXR", "NRTAXB"],
}
GROUP_OF = {table: group for group, members in GROUPS.items() for table in members}
EDGE_STYLES = {  # kind: (line style, colour, legend)
    "member": ("solid", "0.6", "stessa chiave, stessi valori (hub)"),
    "name": ("solid", "tab:blue", "relazione, stesso nome di chiave"),
    "data": ("dashed", "tab:orange", "relazione trovata solo dai valori"),
    "approx": ("dotted", "tab:red", "relazione con eccezioni (IND approssimata)"),
}
ARROWS = {"member": {"arrows": False}}  # a hub membership has no direction; the relations point to the parent
DIRECTED = {"arrows": True, "arrowsize": 14}
NODE_SIZES = {"table": 2600, "hub": 700}  # in points^2, so that the arrows stop at the border of the boxes


def group_of(table: str) -> str:
    """Group of a table in `GROUPS`.

    A table of no group gets "altro", so that a new table in the export still shows up, in white.
    """
    return GROUP_OF.get(table, "altro")


def nodes_by_kind(graph: nx.DiGraph) -> dict[str, list[str]]:
    """{kind: nodes} of `graph`.

    `relation_graph` gives every node the attribute `kind`: "table" or "hub".
    """
    nodes = collections.defaultdict(list)
    for node, kind in graph.nodes(data="kind"):
        nodes[kind].append(node)
    return nodes


def edges_by_kind(graph: nx.DiGraph) -> dict[str, list[tuple[str, str]]]:
    """{kind: edges} of `graph`, with the edge kinds of `EDGE_STYLES`.

    A kind without edges gives an empty list, so every style can be drawn.
    """
    edges = collections.defaultdict(list)
    for source, target, kind in graph.edges(data="kind"):
        edges[kind].append((source, target))
    return edges


def layout(graph: nx.DiGraph) -> dict:
    """Positions {node: (x, y)} of all nodes, in the square from (0, 0) to (2, 2.3).

    The linked nodes are placed with Kamada-Kawai, which keeps related tables close together. The tables without
    any relation would end up on top of each other, so they get a row of their own below the others.
    """
    linked = [node for node in graph if graph.degree(node)]
    positions = nx.kamada_kawai_layout(graph.subgraph(linked).to_undirected(), center=(1, 1.3))
    alone = sorted(nx.isolates(graph))
    positions.update({node: (x, 0) for node, x in zip(alone, np.linspace(0.1, 1.9, len(alone)), strict=True)})
    return positions


def draw_edges(graph: nx.DiGraph, positions: dict, ax):
    """The edges of every kind in their style (`EDGE_STYLES`), and their labels.

    The node sizes are passed along although the nodes are drawn later: networkx needs them to end the arrows at
    the border of a node instead of at its centre.
    """
    sizes = [NODE_SIZES[kind] for _, kind in graph.nodes(data="kind")]
    edges = edges_by_kind(graph)
    for kind, (style, colour, _) in EDGE_STYLES.items():
        nx.draw_networkx_edges(graph, positions, edgelist=edges[kind], nodelist=list(graph), node_size=sizes,
                               style=style, edge_color=colour, width=1.4, ax=ax, **ARROWS.get(kind, DIRECTED))
    labels = {(a, b): label for a, b, label in graph.edges(data="label") if label}
    nx.draw_networkx_edge_labels(graph, positions, edge_labels=labels, font_size=7, font_color="0.25", ax=ax,
                                 bbox={"fc": "white", "ec": "none", "alpha": 0.7})


def draw_hubs(graph: nx.DiGraph, positions: dict, ax):
    """The hubs as grey dots, labelled with their key and its number of distinct values.

    The number tells the size of the key domain, e.g. how many funds the fund tables share.
    """
    hubs = nodes_by_kind(graph)["hub"]
    nx.draw_networkx_nodes(graph, positions, nodelist=hubs, node_size=NODE_SIZES["hub"], node_color="0.85", ax=ax)
    for hub in hubs:
        ax.text(*positions[hub], f'{hub}\n{graph.nodes[hub]["values"]}', ha="center", va="center", fontsize=7)


def draw_tables(graph: nx.DiGraph, positions: dict, rows: dict[str, int] | None, colours: dict, ax):
    """The tables as boxes in the colour of their group.

    With `rows` ({table: number of rows}) every box also shows the size of its table, with Swiss thousands
    separators (1'234).
    """
    for table in nodes_by_kind(graph)["table"]:
        text = f"{table}\n{rows.get(table, 0):,}".replace(",", "'") if rows else table
        box = {"boxstyle": "round,pad=0.4", "fc": colours.get(group_of(table), "white"), "ec": "0.35"}
        ax.text(*positions[table], text, ha="center", va="center", fontsize=9, family="monospace", bbox=box)


def add_legend(ax, colours: dict):
    """Legend of the group colours and of the edge styles, in the upper left corner without a frame."""
    groups = [plt.Rectangle((0, 0), 1, 1, fc=colour, ec="0.35", label=group) for group, colour in colours.items()]
    edges = [plt.Line2D([], [], ls=style, color=colour, label=text) for style, colour, text in EDGE_STYLES.values()]
    ax.legend(handles=[*groups, *edges], loc="upper left", fontsize=8, frameon=False)


def plot_relations(graph: nx.DiGraph, rows: dict[str, int] | None = None):
    """Diagram of `relation_graph`, as a matplotlib figure.

    `rows` ({table: number of rows}) adds the size of every table. The edges are drawn first, so that the
    boxes of the tables cover their ends.
    """
    positions = layout(graph)
    colours = dict(zip(GROUPS, plt.cm.Pastel1.colors, strict=False))  # 6 groups, 9 colours
    fig, ax = plt.subplots(figsize=(16, 12))
    draw_edges(graph, positions, ax)
    draw_hubs(graph, positions, ax)
    draw_tables(graph, positions, rows, colours, ax)
    add_legend(ax, colours)
    ax.axis("off")
    ax.set_title("Relazioni tra le tabelle Neuron scoperte da Desbordante (freccia: figlia -> madre)")
    return fig
