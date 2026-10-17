# 012 · t4_annual_statement · from the story to the rule

**Step:** story → sketch → findings → holes → search. **LLM:** Claude Code.

## Input

The task text of t4:

> a statement has six columns. The charges are exactly the ones that Neuron takes from the policy in the fund
> accounting of t3, so t3 and t4 are best solved together.
> premiums: premiums received in the year (money date); entry charges: entry charges on the premiums invested in
> the year (trade date); admin fees, management fees, risk charges: deducted in the year; total charges: entry +
> admin + management + risk. From the start year to the year the policy ends by surrender or death, at the latest
> 2025.

What t3 gives (`011-t3-runs-story.md`): every premium and charge booking of the simulation, right.

## Prompt

Write the statement from the simulated bookings. Holes: the trade date that puts the entry charge of a premium in
a year (of its first or last premium booking), the date of the first year (start or application).

## Output

`statement.py`: the paid premium items by the year of the money date; the entry charge of a premium as the premium
less what its premium bookings invested; the ADM, AMC and RSK bookings by the year of the run.

- `t4_annual_statement/r1`: 34089 / 34145 right. `r1-search`: the holes tie (27682 / 27726)
- after r1: 36 statements have entry charges moved between two years (2012/2013, 2018/2019), always in pairs that
  cancel. Their premiums were received at the end of December and bought in funds on two trade dates, one in each
  year (2012-12-31 and 2013-01-02): the 20 % fund traded in 2013 carries 20 % of the 17.00 entry charge (3.40)
  into 2013. `r2-search-entry`: **S1** each premium booking carries its share of the entry charge, by the amount
  it invested, into the year of its trade date: 27710 / 27726, held out 6415 / 6419
- `r2.md`: the 20 statements left have admin fees off by whole francs (**r2/T1–T3** EX_TARGET =
  t4_annual_statement.admin_fees): 16 are listed in NREXCP. Hand edits, for t5

`check.py`: t4_annual_statement 34125 / 34145, the 20 hand edits.
