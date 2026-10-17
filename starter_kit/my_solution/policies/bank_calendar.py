"""The bank calendar of Ticino, where the direct debits are collected."""
import datetime as dt

FIXED_HOLIDAYS = {(1, 1), (1, 6), (3, 19), (5, 1), (6, 29), (8, 1), (8, 15), (11, 1), (12, 8), (12, 25), (12, 26)}
EASTER_HOLIDAYS = (1, 39, 50, 60)  # days after Easter: Easter Monday, Ascension, Whit Monday, Corpus Christi
ONE_DAY = dt.timedelta(days=1)


def easter(year):
    """Easter Sunday of a year in the Gregorian calendar.

    The anonymous Gregorian algorithm (Meeus, Astronomical Algorithms), with the letters of the book: Easter is
    the first Sunday after the ecclesiastical full moon on or after 21 March.
    """
    a, (b, c) = year % 19, divmod(year, 100)  # a: year of the 19-year lunar cycle; century, year in it
    d, e = divmod(b, 4)  # century leap years
    g = (8 * b + 13) // 25  # correction of the lunar cycle
    h = (19 * a + b - d - g + 15) % 30  # days from 21 March to the full moon, before the correction m
    i, k = divmod(c, 4)  # leap years of the century
    l = (32 + 2 * e + 2 * i - h - k) % 7  # days from the full moon to the Sunday after it
    m = (a + 11 * h + 22 * l) // 451
    month, day_ = divmod(h + l - 7 * m + 114, 31)
    return dt.date(year, month, day_ + 1)


def is_bank_holiday(day_):
    """Weekend or holiday of the Ticino calendar.

    Good Friday is a working day in Ticino; the movable holidays follow Easter.
    """
    return (day_.weekday() >= 5 or (day_.month, day_.day) in FIXED_HOLIDAYS
            or (day_ - easter(day_.year)).days in EASTER_HOLIDAYS)


def next_working_day(day_):
    """`day_` itself when the banks are open, otherwise the first working day after it."""
    while is_bank_holiday(day_):
        day_ += ONE_DAY
    return day_
