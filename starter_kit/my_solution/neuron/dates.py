"""Calendar arithmetic of the policies: months, ages and policy years, counted the way Neuron counts them."""
import calendar
import datetime as dt


def add_months(day_, months):
    """The same day of the month, `months` later (or earlier, when negative).

    A day that the new month lacks becomes its last day: 31 January + 1 month is 28 or 29 February, and the
    next month continues from that date, so due dates on the 31st drift to the 28th when computed one by one.
    """
    years, month = divmod(day_.month - 1 + months, 12)
    year, month = day_.year + years, month + 1
    return dt.date(year, month, min(day_.day, calendar.monthrange(year, month)[1]))


def months_between(start, end):
    """Calendar months from `start` to `end`, counted on the month numbers.

    The day is ignored: from 31 January to 1 February is one month.
    """
    return (end.year - start.year) * 12 + end.month - start.month


def age(birth, day_):
    """Completed years from `birth` to `day_`.

    Before the birthday in the year of `day_`, the comparison of (month, day) takes one year off.
    """
    return day_.year - birth.year - ((day_.month, day_.day) < (birth.month, birth.day))


def calendar_years(first_day, last_day):
    """The calendar years from the year of `first_day` to the year of `last_day`, both included."""
    return range(first_day.year, last_day.year + 1)


def policy_years(start, day_):
    """Completed policy years on `day_`.

    A year is complete on its anniversary as `add_months` computes it, so a policy that starts on 29 February
    completes a year on 28 February, one day before `age` would count it.
    """
    years = age(start, day_)
    return years + (add_months(start, 12 * (years + 1)) <= day_)
