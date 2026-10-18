"""Plain-language labels of features, conditions and constants, from what the extract says about itself.

Nothing here is invented: every word comes from the data dictionary or from the rule.
- NRDICT gives what a column is (`PH_FREQ` -> "premium frequency"), sometimes with its codes inline
  ("version status (C=current, S=superseded)");
- NRCODE gives what a code means: the domain of a column is its abbreviation (`PH_FREQ` -> FREQ) or the alias of
  its table followed by the start of it (`PR_STATE` -> PRSTAT); `M` of FREQ -> "monthly";
- SCHEMA.md gives the positions of fixed-width codes (`RK_TARKEY[6]` -> "premium type": `E` single);
- the frame names say how a feature was read: `@PR_RCVDT` on the money received date, `[6]` the 6th character,
  `weekday(...)`, `previous(...)`, `<task>__<column>` a value of another task;
- the candidate gives the computation: a ratio 0.02 on PR_AMTRC -> "2 % of the amount received".
Where the extract says nothing, the label is the code itself and `known` is False. Subjects carry no article:
statements and questions add "the".
"""
import calendar
import dataclasses
import functools
import re
from decimal import Decimal, InvalidOperation

from . import paths, schema

WEEKDAYS = {str(i + 1): name for i, name in enumerate(calendar.day_name)}  # 1 = Monday, like dsl.weekday
MONTHS = {str(i): calendar.month_name[i] for i in range(1, 13)}
ROUNDING = {"ROUND_HALF_UP": "rounded half up", "ROUND_HALF_EVEN": "rounded half to even",
            "ROUND_HALF_DOWN": "rounded half down", "ROUND_DOWN": "rounded towards zero",
            "ROUND_UP": "rounded away from zero", "ROUND_FLOOR": "rounded down", "ROUND_CEILING": "rounded up"}
INLINE_CODES = re.compile(r"\s*\(([^()]*=[^()]*)\)")
CALENDAR = {"weekday": ("weekday", "day of the week of the {date}"), "day": ("number", "day of the month of the {date}"),
            "month": ("month", "month of the {date}"), "year": ("number", "year of the {date}"),
            "month_end": ("flag", "{date} is the last day of its month")}


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def words(name):
    """`policy_value` -> "policy value"."""
    return re.sub(r"_+", " ", name).strip()


@functools.cache
def code_table():
    """{domain: {code: text}} of NRCODE (the English text, else the other one), empty without the table."""
    from . import store
    if not paths.LEGACY.exists() or "NRCODE" not in store.tables():
        return {}
    found = {}
    for row in store.load("NRCODE").iter_rows(named=True):
        text = row.get("CD_TXTEN") or row.get("CD_TXTDE")
        if row["CD_DOMAIN"] and row["CD_CODE"] is not None and text:
            found.setdefault(row["CD_DOMAIN"], {})[str(row["CD_CODE"])] = text
    return found


@functools.cache
def code_positions():
    """{column: {position: (meaning, {value: text})}} from the position tables of SCHEMA.md.

    A table follows a line such as "The tariff key `RK_TARKEY` looks like `FXU03LB`:" and its rows read
    "| 6 | premium type | `L` regular, `E` single |"; a range "4-5" gives every position in it.
    """
    path = paths.REPO / "SCHEMA.md"
    if not path.exists():
        return {}
    found, current = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.search(r"`(\w+)` looks like", line)
        if m:
            current = m.group(1)
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if current and len(cells) >= 3 and re.fullmatch(r"\d+(-\d+)?", cells[0]):
            first, _, last = cells[0].partition("-")
            values = {} if re.search(r"`\s*to\s*`", cells[2]) else {  # "`01` to `04`" is a range, not a meaning
                k: v.strip() for k, v in re.findall(r"`([^`]+)`\s+([^,`(]+)", cells[2])}
            for pos in range(int(first), int(last or first) + 1):
                found.setdefault(current, {})[pos] = (cells[1], values)
        elif current and line.strip() and not line.startswith("|") and current in found:
            current = None  # the table is over
    return found


def description(column):
    """(what a legacy column is, the codes written inline in its description), (None, {}) if NRDICT does not say."""
    if not (paths.LEGACY / "NRDICT.csv").exists():
        return None, {}
    spec = schema.find(column)
    if spec is None or not spec.desc:
        return None, {}
    inline = {}
    for group in INLINE_CODES.findall(spec.desc):
        for part in group.split(","):
            if "=" in part:
                code, text = (p.strip() for p in part.split("=", 1))
                inline[code] = text
    return INLINE_CODES.sub("", spec.desc).strip(), inline


def domain_of(column):
    """The NRCODE domain of a column: its table alias followed by the start of its abbreviation (PR_STATE ->
    PRSTAT), else its abbreviation (PH_STATE -> STATE)."""
    if "_" not in column:
        return None
    alias, abbreviation = column.split("_", 1)
    domains = code_table()
    own = next((d for d in sorted(domains) if d.startswith(alias) and len(d) > len(alias)
                and abbreviation.startswith(d[len(alias):])), None)
    return own or (abbreviation if abbreviation in domains else None)


@dataclasses.dataclass
class Feature:
    """A feature of the frame in words: `subject` names it (no article), `value(v)` says what a value means."""
    name: str
    subject: str
    codes: dict
    known: bool
    kind: str = "code"  # code, weekday, month, flag, number
    base: str = ""  # what the column is, without position or date: the code texts that repeat it are cut

    def value(self, v):
        v = str(v)
        text = {"weekday": WEEKDAYS, "month": MONTHS}.get(self.kind, self.codes).get(v)
        if text is None:
            return number(v)
        if self.base and text.lower().startswith(self.base.lower() + " "):
            return text[len(self.base) + 1:]  # "broker tier A" of the broker tier -> "A"
        return text

    def explained(self, v):
        """The value says what it is: a meaning in the extract, a day, a month, or a number (a rate, a count)."""
        return (self.kind in ("weekday", "month", "flag", "number") or str(v) in self.codes
                or re.fullmatch(r"-?\d+(\.\d+)?", str(v)) is not None)

    def is_(self, v, negate=False):
        """Statement of a condition: "the premium frequency is monthly", "the policy state is not premium holiday"."""
        if self.kind == "flag":
            holds = (str(v).lower() in ("true", "1")) != negate
            return f"the {self.subject}" if holds else f"the {self.subject.replace(' is ', ' is not ', 1)}"
        article = "a " if self.kind == "weekday" else ""
        return f"the {self.subject} {'is not' if negate else 'is'} {article}{self.value(v)}"

    def question(self, v):
        """Question of a split: "Is the premium frequency monthly?"."""
        if self.kind == "flag":
            return f"Is the {self.subject.replace(' is ', ' ', 1)}?"
        article = "a " if self.kind == "weekday" else ""
        return f"Is the {self.subject} {article}{self.value(v)}?"


def feature(name, task=None):
    """The words of one frame column, a calendar expression of the DSL, or another task's value."""
    m = re.fullmatch(r"(\w+)\((\w+)\)", name)
    if m and m.group(1) in CALENDAR:
        kind, template = CALENDAR[m.group(1)]
        inner = feature(m.group(2), task)
        return Feature(name, template.format(date=inner.subject), {}, inner.known, kind)
    if m and m.group(1) == "previous":
        inner = feature(m.group(2), task)
        return Feature(name, f"previous {inner.subject} of the same policy", {}, inner.known, "number")
    if "__" in name:
        other, column = name.split("__", 1)
        return Feature(name, f"{words(column)} of {other}", {}, True, "number")
    m = re.fullmatch(r"([A-Z]{2}_[A-Z0-9]+)(_RAW)?(?:@(\w+?))?(?:\[(\d+)\])?", name)
    if not m:
        meaning = target_meaning(task, name)
        return Feature(name, meaning or words(name), {}, True, "number")
    base, raw, anchor, position = m.groups()
    desc, inline = description(base)
    subject, codes = desc or base, dict(inline)
    domain = domain_of(base)
    if domain:
        codes.update(code_table().get(domain, {}))
    if raw:
        subject = f"{subject} as stored"
    if position:
        pos = int(position)
        layout = code_positions().get(base, {}).get(pos)
        if layout:
            subject, codes = f"{layout[0]} ({ordinal(pos)} character of the {subject})", dict(layout[1])
        else:
            subject, codes = f"{ordinal(pos)} character of the {subject}", {}
    if anchor:
        subject = f"{subject} on the {date_words(anchor, task)}"
    return Feature(name, subject, codes, desc is not None, base=desc or "")


def date_words(anchor, task=None):
    """The name of a date of the grain row or of the target: "money received date", "valuation date"."""
    desc = description(anchor)[0] if re.fullmatch(r"[A-Z]{2}_\w+", anchor) else None
    return desc or target_meaning(task, anchor) or words(anchor)


def target_meaning(task, column):
    """The meaning a task definition gives to one of its target columns, if any."""
    if not task:
        return None
    from . import taskdef
    definition = (taskdef.find(task) or {}).get("task", {})
    for item in definition.get("keys", []) + definition.get("values", []):
        if item.get("name") == column and item.get("meaning"):
            return item["meaning"]
    return None


def condition(clause, task=None, negate=False):
    """[feature, op, value] -> statement, e.g. ["PH_FREQ", "=", "M"] -> "the premium frequency is monthly"."""
    name, op, value = clause
    return feature(name, task).is_(value, negate=(op != "=") != negate)


def number(text):
    """A decimal without the zeros past the cents: "0.020000" -> "0.02", "61100.00" stays; other text as it is."""
    if re.fullmatch(r"-?\d+\.\d+", text):
        d = Decimal(text).normalize()
        return format(d.quantize(Decimal("0.01")) if d.as_tuple().exponent > -2 else d, "f")
    return text


def percent(c):
    """0.02 -> "2 %", 0.005 -> "0.5 %", 0.985 -> "98.5 %"."""
    return f"{format((Decimal(str(c)) * 100).normalize(), 'f')} %"


def constant(relation, c, task=None):
    """What the constant of a branch does: "2 % of the amount received", "3 months after the previous due date"."""
    kind, x = relation["kind"], relation.get("input")
    subject = feature(x, task).subject if x else None
    try:
        d = Decimal(str(c))
    except InvalidOperation:
        return str(c)  # a lookup: its own words
    if kind == "ratio":
        return f"the {subject} itself" if d == 1 else f"{percent(d)} of the {subject}"
    if kind == "diff":
        return f"the {subject} {'plus' if d >= 0 else 'minus'} {format(abs(d).normalize(), 'f')}"
    if kind in ("days", "months"):
        n = int(d)
        unit = kind[:-1] if abs(n) == 1 else kind
        return f"{abs(n)} {unit} {'after' if n >= 0 else 'before'} the {subject}"
    return f"always {format(d.normalize(), 'f')}"


def computation(candidate, task=None):
    """The last step of a candidate: "amount = the amount received × the rate of the branch, rounded half up"."""
    relation = candidate["relation"]
    value = candidate.get("value") or "value"
    target = target_meaning(task, value) or words(value)
    x = feature(relation["input"], task).subject if relation.get("input") else None
    where = lookup_words(candidate, task) if candidate.get("lookup") else "the constant of the branch"
    kind = relation["kind"]
    if kind == "ratio":
        return f"{target} = the {x} × {where}, {ROUNDING.get(candidate.get('rounding', 'ROUND_HALF_UP'), 'rounded')}"
    if kind == "diff":
        return f"{target} = the {x} + {where}"
    if kind in ("days", "months"):
        return f"{target} = the {x} + {where}, in {kind}"
    return f"{target} = {where}"


def lookup_words(candidate, task=None):
    """ "the commission rate of commission rates (NRCOMR) for the broker tier on ... and the premium type (...)"."""
    from .freeze import titles
    lk = candidate["lookup"]
    try:
        title = titles().get(lk["table"], lk["table"])
        column = schema.column(lk["table"], lk["column"]).desc
    except (OSError, StopIteration, KeyError):
        title, column = lk["table"], lk["column"]
    keys = " and the ".join(feature(f, task).subject for f in lk["keys"].values())
    return f"the {column} of {title} ({lk['table']}) for the {keys}"


def path(clauses, task=None):
    """A path of conditions as one sentence."""
    return "; ".join(condition(c, task) for c in clauses) or "every row"
