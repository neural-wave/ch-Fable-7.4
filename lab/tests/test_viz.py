"""`lab viz`: the atlas opens offline and every chart can be painted in both themes."""
import json
import re

import polars as pl
import pytest

from neuronlab import viz


@pytest.fixture(scope="module")
def page():
    return viz.atlas().read_text(encoding="utf-8")


def test_the_atlas_opens_without_a_network(page):
    import base64
    import gzip
    assert not re.search(r'<(script|link|img)[^>]+(src|href)="(https?:)?//', page)
    packed = re.search(r'<script type="application/octet-stream" id="plotly-gzip">([^<]+)</script>', page).group(1)
    assert "plotly.js v" in gzip.decompress(base64.b64decode(packed)).decode("utf-8")[:2000]
    assert len(page) < 4_000_000
    for view in ("index", "rules", "policy", "story"):
        assert f'data-view="{view}"' in page


def test_every_chart_is_valid_and_uses_known_colors(page):
    specs = re.findall(r'<script type="application/json" data-chart="[^"]+">(.*?)</script>', page, re.S)
    assert specs
    tokens = set(viz.THEMES["light"]) & set(viz.THEMES["dark"])
    for spec in specs:
        fig = json.loads(spec)
        assert "data" in fig and "layout" in fig
        used = set(re.findall(r'"@([a-z0-9-]+)"', spec))
        assert used <= tokens, used - tokens


def test_where_axis_bins():
    import datetime as dt
    days = pl.DataFrame({"w": [dt.date(2000 + i % 20, 1 + i % 12, 1) for i in range(100)]})
    assert viz.binned(days, "w")[1] == "date"
    small = pl.DataFrame({"w": list(range(1, 32)) * 3})
    binned, kind = viz.binned(small, "w")
    assert kind == "number" and binned["bin"].n_unique() == 31
    wide = pl.DataFrame({"w": [float(i) for i in range(1000)]})
    assert viz.binned(wide, "w")[0]["bin"].n_unique() == viz.BINS
    codes = pl.DataFrame({"w": ["LS", "UB", "LS"]})
    assert viz.binned(codes, "w")[1] == "category"


def test_bars_stay_thin():
    assert viz.bar_gap(2) > 0.9 and viz.bar_gap(40) == 0.15
