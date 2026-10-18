"""Coordinates of the diagrams of `lab serve`: decision trees, the control flow of a candidate, the join graph.

The page only draws boxes and polylines; where they go is decided here, in Python, where it is tested. Units are
CSS pixels, origins top-left. Edges are orthogonal polylines (lists of [x, y]) from the bottom of the parent to the
top of the child.
"""
NODE_W, NODE_H = 240, 88  # room for a question in plain words under the code
LEAF_W, LEAF_H = 176, 112
GAP, LEVEL = 24, 160
MARGIN = 24


def _leaves(node):
    return [node] if "leaf" in node else _leaves(node["yes"]) + _leaves(node["no"])


def _depth(node):
    return 0 if "leaf" in node else 1 + max(_depth(node["yes"]), _depth(node["no"]))


def tree(root, top=MARGIN, left=MARGIN):
    """Nodes and edges of a binary tree {split: [feature, value], yes, no} | {leaf, rows, errors}.

    Leaves sit side by side on the bottom row, in order (yes before no); each split is centred over its children.
    Node ids are paths of the branches taken: "" for the root, "y", "yn", ...
    """
    depth = _depth(root)
    nodes, edges = [], []
    counter = [0]

    def place(node, level, ident):
        """(centre x, top y) of the node, after placing its subtree."""
        if "leaf" in node:
            x = left + counter[0] * (LEAF_W + GAP)
            counter[0] += 1
            y = top + depth * LEVEL
            nodes.append({"id": ident, "kind": "leaf", "x": x, "y": y, "w": LEAF_W, "h": LEAF_H,
                          "label": str(node["leaf"]), "rows": node.get("rows"), "errors": node.get("errors")})
            return x + LEAF_W / 2, y
        children = [(ident + "y", "yes", place(node["yes"], level + 1, ident + "y")),
                    (ident + "n", "no", place(node["no"], level + 1, ident + "n"))]
        cx = (children[0][2][0] + children[1][2][0]) / 2
        y = top + level * LEVEL
        feature, value = node["split"]
        nodes.append({"id": ident, "kind": "split", "x": cx - NODE_W / 2, "y": y, "w": NODE_W, "h": NODE_H,
                      "feature": feature, "value": str(value), "label": f"{feature} = {value}"})
        for child, branch, (x2, y2) in children:
            edges.append({"from": ident, "to": child, "branch": branch, "points": _elbow(cx, y + NODE_H, x2, y2)})
        return cx, y

    place(root, 0, "")
    width = max((n["x"] + n["w"] for n in nodes), default=0) + MARGIN
    height = top + depth * LEVEL + LEAF_H + MARGIN
    return {"nodes": sorted(nodes, key=lambda n: (len(n["id"]), n["id"])), "edges": edges, "width": width,
            "height": height}


def _elbow(x1, y1, x2, y2):
    """Down from (x1, y1), across half a level below, down to (x2, y2)."""
    if abs(x1 - x2) < 0.5:
        return [[x1, y1], [x2, y2]]
    mid = y1 + (LEVEL - NODE_H) / 2
    return [[x1, y1], [x1, mid], [x2, mid], [x2, y2]]


def path_to(node_id):
    """Ids of the nodes from the root to `node_id`, e.g. "yn" -> ["", "y", "yn"]."""
    return [node_id[:i] for i in range(len(node_id) + 1)]


def flow(root, inputs_label, compute_label, result_label):
    """The control flow of a candidate: inputs, the decisions of its tree, the computation, the result.

    Every leaf (a constant) joins one bus line above the computation node.
    """
    head = NODE_H + 48
    body = tree(root, top=MARGIN + head)
    if "leaf" in root:  # a lookup or a single constant: one wide box instead of a tree
        leaf = body["nodes"][0]
        leaf.update(w=560, x=MARGIN, h=NODE_H)
        body["width"] = 560 + 2 * MARGIN
    width = max(body["width"], 720 + 2 * MARGIN)
    centre = width / 2
    shift = centre - _root_centre(body)
    for n in body["nodes"]:
        n["x"] += shift
    for e in body["edges"]:
        e["points"] = [[x + shift, y] for x, y in e["points"]]
    nodes = [{"id": "in", "kind": "io", "x": centre - 360, "y": MARGIN, "w": 720, "h": NODE_H, "label": inputs_label}]
    edges = [{"from": "in", "to": "", "branch": "", "points": [[centre, MARGIN + NODE_H], [centre, MARGIN + head]]}]
    bottom = max(n["y"] + n["h"] for n in body["nodes"])
    bus = bottom + 36
    compute_y = bus + 36
    leaves = [n for n in body["nodes"] if n["kind"] == "leaf"]
    for leaf in leaves:
        lx = leaf["x"] + leaf["w"] / 2
        edges.append({"from": leaf["id"], "to": "compute", "branch": "",
                      "points": [[lx, leaf["y"] + leaf["h"]], [lx, bus], [centre, bus], [centre, compute_y]]})
    nodes += body["nodes"]
    edges += body["edges"]
    nodes.append({"id": "compute", "kind": "step", "x": centre - 320, "y": compute_y, "w": 640, "h": NODE_H,
                  "label": compute_label})
    result_y = compute_y + NODE_H + 48
    edges.append({"from": "compute", "to": "result", "branch": "",
                  "points": [[centre, compute_y + NODE_H], [centre, result_y]]})
    nodes.append({"id": "result", "kind": "result", "x": centre - 180, "y": result_y, "w": 360, "h": 80,
                  "label": result_label})
    return {"nodes": nodes, "edges": edges, "width": width, "height": result_y + 80 + MARGIN}


def _root_centre(layout):
    root = next(n for n in layout["nodes"] if n["id"] == "")
    return root["x"] + root["w"] / 2


def graph(tables, joins, box_w=208, box_h=112, gap_x=104, gap_y=96):
    """Join graph: a table above the tables that reference it (foreign key -> key points up).

    `tables` are names, `joins` are {"from": "A.col", "to": "B.col"}. The rank of a table is the longest chain of
    references below it, so referenced tables (persons, tariffs) are on top and transactions at the bottom.
    """
    plain = [j for j in joins if j.get("kind", "plain") == "plain"] or joins  # temporal joins often go both ways
    out = {t: sorted({j["to"].split(".")[0] for j in plain if j["from"].split(".")[0] == t} - {t}) for t in tables}
    out = {t: [u for u in targets if u in out] for t, targets in out.items()}
    rank = {}

    def rank_of(t, seen=()):
        if t in rank:
            return rank[t]
        if t in seen:
            return 0  # a cycle: cut it
        rank[t] = 0 if not out[t] else 1 + max(rank_of(u, seen + (t,)) for u in out[t])
        return rank[t]

    for t in tables:
        rank_of(t)
    rows = {}
    for t in sorted(tables, key=lambda t: (rank[t], t)):
        rows.setdefault(rank[t], []).append(t)
    position = {}
    for r in sorted(rows):  # order each row by the mean position of the tables it references (fewer crossings)
        def barycentre(t):
            xs = [position[u][0] for u in out[t] if u in position]
            return sum(xs) / len(xs) if xs else float("inf")
        rows[r].sort(key=lambda t: (barycentre(t), t))
        for i, t in enumerate(rows[r]):
            position[t] = (MARGIN + i * (box_w + gap_x), MARGIN + r * (box_h + gap_y))
    nodes = [{"id": t, "x": x, "y": y, "w": box_w, "h": box_h} for t, (x, y) in position.items()]
    edges, drawn = [], set()
    for j in sorted(joins, key=lambda j: j.get("kind", "plain") != "plain"):  # one line per pair, plain first
        a, b = j["from"].split(".")[0], j["to"].split(".")[0]
        if a in position and b in position and a != b and frozenset((a, b)) not in drawn:
            drawn.add(frozenset((a, b)))
            edges.append(dict(j, points=_between(position[a], position[b], box_w, box_h)))
    width = max((n["x"] + box_w for n in nodes), default=0) + MARGIN
    height = max((n["y"] + box_h for n in nodes), default=0) + MARGIN
    return {"nodes": nodes, "edges": edges, "width": width, "height": height}


def _between(a, b, w, h):
    """Segment between the borders of two boxes, from a to b."""
    (ax, ay), (bx, by) = a, b
    acx, acy, bcx, bcy = ax + w / 2, ay + h / 2, bx + w / 2, by + h / 2
    dx, dy = bcx - acx, bcy - acy
    if abs(dx) * h > abs(dy) * w:  # leaves through a side
        sx = w / 2 if dx > 0 else -w / 2
        start = [acx + sx, acy + dy * sx / dx]
        end = [bcx - sx, bcy - dy * sx / dx]
    else:
        sy = h / 2 if dy > 0 else -h / 2
        start = [acx + dx * sy / dy if dy else acx, acy + sy]
        end = [bcx - dx * sy / dy if dy else bcx, bcy - sy]
    return [[round(start[0], 1), round(start[1], 1)], [round(end[0], 1), round(end[1], 1)]]
