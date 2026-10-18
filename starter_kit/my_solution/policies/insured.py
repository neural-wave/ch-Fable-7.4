"""The insured person of a policy (NRRISK, NRPERS) and the ages the mortality table is read with."""
from neuron import add_months, age, day, policy_years

from .codes import is_smoker

SEX_OF_TARIFF = {"M": "1", "W": "2"}  # RK_TARKEY[2]; any other tariff takes the sex of the person


class Insured:
    """The person of a risk with the mortality table of the tariffs.

    A tariff for men or women (RK_TARKEY[2]) sets the sex of the mortality table; a unisex tariff takes the sex
    of the person.
    """

    def __init__(self, risk, person, mortality):
        self.risk, self.mortality, self.smoker = risk, mortality, is_smoker(person)
        self.birth = person["PS_BIRTH"] or day(person["PS_BIRTH_RAW"], month_end=True)  # 31 September: 30 September
        self.sex = SEX_OF_TARIFF.get(risk["RK_TARKEY"][2], person["PS_SEX"])

    def entry_age(self, start, cobol):
        """The age on `start`: COBOL takes days / 365, rounded; Neuron NG the age at the nearest birthday."""
        if cobol:
            return ((start - self.birth).days + 182) // 365
        return age(self.birth, add_months(start, 6))

    def policy_year_age(self, start, day_, cobol):
        """The age of the mortality table in the policy year of `day_`.

        Offers of the COBOL version add the completed policy years to the entry age; Neuron NG takes the age at
        the nearest birthday on the last policy anniversary.
        """
        years = policy_years(start, day_)
        if cobol:
            return self.entry_age(start, cobol=True) + years
        return self.entry_age(add_months(start, 12 * years), cobol=False)
