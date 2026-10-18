"""The story for a lay reader (S3): no word of the trade, every term in bold explained in the glossary, both
languages complete. The checks run on a sample story, so they do not need the artifacts; the real story.json is
checked too when `lab viz story` has written it."""
import json
import re

import pytest

from neuronlab import paths, story
from neuronlab import story_text as T

SAMPLE = {
    "policy": {"id": "BL10000042", "applied": "2004-03-01", "begin": "2004-04-01", "end": "2034-04-01", "years": 30,
               "age": 34, "premium": "250.00", "currency": "CHF", "cover": "C", "sum_insured": "50000.00",
               "growth": "0.040000", "maturity": "180000.00", "start_year": 2004, "last_year": 2025, "age_now": 55},
    "totals": {"due": 261, "paid": 259, "odd": 1, "entry": "1300.00", "admin": "1300.00", "management": "6000.00",
               "risk": "2000.00", "charges": "10600.00", "market": "-4600.00", "risk_first_year": 2005,
               "risk_first": "60.00", "risk_last": "144.00"},
    "due": {"due": "2026-12-08", "collected": "2026-12-09", "holiday": [12, 8], "day": 8},
    "hundred": {"due": "2025-12-08", "received": "2025-12-10", "delay": 2, "traded": "2025-12-11", "amount": "250.00",
                "entry": "2.00", "entry_agreed": False, "net": "98.00", "commission": "1.50", "funds": 2,
                "share": "88.20", "split": ["88.20", "9.80"], "units": "0.5123", "price": "191.29"},
    "charges": {"month": "2025-12-08", "admin": "5.00", "management": "40.00", "risk": "12.00", "management_rate": "0.012"},
    "value": {"months": ["2025-11-30", "2025-12-31"], "value": [39000.0, 40000.0], "paid": [55000.0, 55250.0],
              "projected": 60000.0},
    "change": {"date": "2007-08-11", "old_months": 40, "first_year": 1990},
    "statement": {"year": 2025, "due": 12, "paid": 12, "premiums": "3000.00", "entry_charges": "59.98", "admin_fees": "60.00",
                  "management_fees": "480.00", "risk_charges": "144.00", "total_charges": "744.00"},
    "surrender": {"date": "2025-12-31", "value": "40000.00", "surrender": "39200.00"},
    "rules": {"rows": 284203, "exact": 284150, "policies": 3019,
              "examples": [{"task": "t0_commission", "card": "tier-on-money-date", "broken": 1430, "of": 225858}]},
    "corrections": {"wrong": 53, "example": {"policy": "BL10000237", "due_nr": 41, "neuron": "18.40", "rules": "8.40",
                                             "gap": "10.00"}},
}


def stories():
    found = [("sample", SAMPLE)]
    path = paths.RUNS / "story.json"
    if path.exists():
        found.append(("built", json.loads(path.read_text(encoding="utf-8"))))
    return found


@pytest.mark.parametrize("name,data", stories(), ids=[n for n, _ in stories()])
def test_no_word_of_the_trade(name, data):
    for lang, text in story.text_of(data).items():
        for word in T.BANNED:  # whole words; a word ending in "_" or a blank is a prefix (t0_, lab )
            end = r"(?![A-Za-z0-9])" if word.strip()[-1].isalnum() else ""
            assert not re.search(r"(?<![A-Za-z0-9])" + re.escape(word.strip()) + end, text, re.I), (lang, word)
        assert "{" not in text and "}" not in text, lang  # every placeholder was filled


def bold_terms(lang):
    texts = [c["body"][lang] for c in T.CHAPTERS] + [T.NEURON[lang]]
    return {t for text in texts for t in re.findall(r"<strong>([^<{]+)</strong>", text)}


@pytest.mark.parametrize("lang", T.LANGUAGES)
def test_every_term_in_bold_is_in_the_glossary(lang):
    glossary = {term[lang].lower() for term, _ in T.GLOSSARY}
    unexplained = {t for t in bold_terms(lang) if t.lower() not in glossary}
    assert not unexplained
    assert len(bold_terms(lang)) >= 15


def test_both_languages_have_every_text():
    for chapter in T.CHAPTERS:
        assert set(chapter["title"]) == set(chapter["body"]) == set(T.LANGUAGES)
    for term, text in T.GLOSSARY:
        assert set(term) == set(text) == set(T.LANGUAGES)
    for table in (T.COVER, T.SURRENDER, T.RULE_EXAMPLES, T.FIGURES, T.HOLIDAYS):
        for entry in table.values():
            assert set(entry) == set(T.LANGUAGES)


@pytest.mark.parametrize("text,expected", [
    ("Il 8 agosto", "L'8 agosto"), ("dal 11 maggio", "dall'11 maggio"), ("circa il 1% del valore", "circa l'1% del valore"),
    ("dal 1° agosto 1998", "dal 1° agosto 1998"), ("il 18 marzo", "il 18 marzo"), ("A agosto erano", "Ad agosto erano"),
    ("qui il 8 del mese", "qui l'8 del mese"),
])
def test_italian_elisions(text, expected):
    assert story.italian(text) == expected


def test_swiss_numbers():
    nbsp = " "  # dates and amounts do not break across lines
    assert story.money("1234.5", "en") == f"CHF{nbsp}1,234.50" and story.money("1234.5", "it") == f"CHF{nbsp}1'234.50"
    assert story.date("2007-08-11", "it") == f"11{nbsp}agosto{nbsp}2007" and story.percent("0.025", "en") == "2.5%"
