"""The feature language of step 5: what the LLM may propose, checked before anything is computed.

An expression is a call of one primitive on frame columns and constants, nested at most two levels, e.g.
`at(BR_TIER, PR_RCVDT)` or `weekday(PR_DUEDT)`. It is parsed with `ast` and only these calls, column names and
constants are accepted: no attribute access, no operators, no eval. Every primitive is computed by Polars.
"""
import ast
import datetime as dt

import polars as pl

CONVERSION = dt.date(2007, 8, 11)  # system change found by the audit (CBLBATCH -> NGBATCH)
MAX_DEPTH = 2

PRIMITIVES = {
    "at": ("value of a versioned column on a date of the grain row", ("column", "date")),
    "days": ("days from the first date to the second", ("date", "date")),
    "weekday": ("day of the week, 1 = Monday", ("date",)),
    "day": ("day of the month", ("date",)),
    "month": ("month", ("date",)),
    "year": ("year", ("date",)),
    "month_end": ("the date is the last day of its month", ("date",)),
    "age": ("completed years from birth to the date", ("date", "date")),
    "birthday_days": ("days from the date to the next birthday", ("date", "date")),
    "pos": ("character at a 1-based position of a code", ("column", "int")),
    "ratio": ("first number divided by the second", ("number", "number")),
    "diff": ("first number minus the second", ("number", "number")),
    "era": ("'before' or 'after' the system change of 2007-08-11", ("date",)),
}


class Invalid(ValueError):
    pass


def vocabulary():
    return "\n".join(f"- {name}({', '.join(args)}): {doc}" for name, (doc, args) in PRIMITIVES.items())


def parse(text, columns, full_columns=()):
    """AST of a valid expression; raises Invalid with a message the model can act on."""
    try:
        tree = ast.parse(text.strip(), mode="eval").body
    except SyntaxError as e:
        raise Invalid(f"not an expression: {e.msg}") from None
    _check(tree, set(columns), set(full_columns), 1)
    return tree


def _check(node, columns, full, depth):
    if depth > MAX_DEPTH + 1:
        raise Invalid("nested too deeply (at most two levels)")
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, str)):
        return
    if isinstance(node, ast.Name):
        if node.id not in columns and node.id not in full:
            raise Invalid(f"unknown column {node.id}")
        return
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords):
        raise Invalid("only calls of the primitives on columns and constants are allowed")
    name = node.func.id
    if name not in PRIMITIVES:
        raise Invalid(f"unknown primitive {name}; use one of {', '.join(PRIMITIVES)}")
    expected = PRIMITIVES[name][1]
    if len(node.args) != len(expected):
        raise Invalid(f"{name} takes {len(expected)} arguments: {', '.join(expected)}")
    if name == "at":
        column, date = node.args
        if not (isinstance(column, ast.Name) and isinstance(date, ast.Name)):
            raise Invalid("at(column, date) takes a column name and a date column of the grain")
        if f"{column.id}@{date.id}" not in full:
            raise Invalid(f"{column.id} is not versioned on {date.id}; versioned columns can be read on the grain dates")
        return
    for arg in node.args:
        _check(arg, columns, full, depth + 1)


def evaluate(node, df, full):
    """Polars Series of a parsed expression on the frame `df` (and the full frame for `at`)."""
    if isinstance(node, ast.Constant):
        return pl.Series([node.value] * df.height)
    if isinstance(node, ast.Name):
        return df[node.id] if node.id in df.columns else full[node.id]
    name, args = node.func.id, node.args
    if name == "at":
        return full[f"{args[0].id}@{args[1].id}"]
    if name == "pos":
        return evaluate(args[0], df, full).cast(pl.String).str.slice(int(args[1].value) - 1, 1)
    values = [evaluate(a, df, full) for a in args]
    frame = pl.DataFrame({f"a{i}": v for i, v in enumerate(values)})
    a = pl.col("a0")
    b = pl.col("a1") if len(values) > 1 else None
    expr = {
        "days": lambda: (b - a).dt.total_days(),
        "weekday": lambda: a.dt.weekday(),
        "day": lambda: a.dt.day(),
        "month": lambda: a.dt.month(),
        "year": lambda: a.dt.year(),
        "month_end": lambda: a.dt.month_end() == a,
        "age": lambda: b.dt.year() - a.dt.year() - ((b.dt.month() * 100 + b.dt.day()) < (a.dt.month() * 100 + a.dt.day())).cast(pl.Int32),
        "birthday_days": lambda: _birthday_days(a, b),
        "ratio": lambda: a.cast(pl.Float64) / b.cast(pl.Float64),
        "diff": lambda: a.cast(pl.Float64) - b.cast(pl.Float64),
        "era": lambda: pl.when(a < CONVERSION).then(pl.lit("before")).otherwise(pl.lit("after")),
    }[name]()
    return frame.select(expr.alias("v"))["v"]


def _birthday_days(birth, on):
    this_year = pl.date(on.dt.year(), birth.dt.month(), pl.min_horizontal(birth.dt.day(), 28))
    next_one = pl.when(this_year >= on).then(this_year).otherwise(this_year.dt.offset_by("1y"))
    return (next_one - on).dt.total_days()


def lineage_of(node, full_meta):
    """Lineage entry of a feature built with `at` (the same path as the precomputed column), else the DSL text."""
    if isinstance(node, ast.Call) and node.func.id == "at":
        return dict(full_meta["lineage"][f"{node.args[0].id}@{node.args[1].id}"])
    return {"dsl": ast.unparse(node)}
