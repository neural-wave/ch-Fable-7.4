# t3_surrender_value, r1-search

Round 1 of the surrender value. Holes: the rounding by system, per fund or once, the cross rate, the day a surrender or death claim makes a policy worth 0.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t3_surrender_value/r1-search/S1 | {'rounding': ('down', 'half_up'), 'summed': 'each', 'valuation': 'exact', 'ended': 'on'} | 4800 / 5009 | 1094 / 1144 |
| t3_surrender_value/r1-search/S2 | {'rounding': ('down', 'half_up'), 'summed': 'each', 'valuation': 'exact', 'ended': 'after'} | 4800 / 5009 | 1094 / 1144 |
| t3_surrender_value/r1-search/S3 | {'rounding': ('down', 'half_up'), 'summed': 'each', 'valuation': 'exact', 'ended': 'units'} | 4800 / 5009 | 1094 / 1144 |
| t3_surrender_value/r1-search/S4 | {'rounding': 'half_up', 'summed': 'each', 'valuation': 'exact', 'ended': 'on'} | 4537 / 5009 | 1030 / 1144 |
| t3_surrender_value/r1-search/S5 | {'rounding': 'half_up', 'summed': 'each', 'valuation': 'exact', 'ended': 'after'} | 4537 / 5009 | 1030 / 1144 |
| t3_surrender_value/r1-search/S6 | {'rounding': 'half_up', 'summed': 'each', 'valuation': 'exact', 'ended': 'units'} | 4537 / 5009 | 1030 / 1144 |
| t3_surrender_value/r1-search/S7 | {'rounding': ('down', 'half_up'), 'summed': 'each', 'valuation': 'rate', 'ended': 'on'} | 4184 / 5009 | 950 / 1144 |
| t3_surrender_value/r1-search/S8 | {'rounding': ('down', 'half_up'), 'summed': 'each', 'valuation': 'rate', 'ended': 'after'} | 4184 / 5009 | 950 / 1144 |
| t3_surrender_value/r1-search/S9 | {'rounding': ('down', 'half_up'), 'summed': 'each', 'valuation': 'rate', 'ended': 'units'} | 4184 / 5009 | 950 / 1144 |
| t3_surrender_value/r1-search/S10 | {'rounding': 'half_up', 'summed': 'each', 'valuation': 'rate', 'ended': 'on'} | 3973 / 5009 | 903 / 1144 |
| t3_surrender_value/r1-search/S11 | {'rounding': 'half_up', 'summed': 'each', 'valuation': 'rate', 'ended': 'after'} | 3973 / 5009 | 903 / 1144 |
| t3_surrender_value/r1-search/S12 | {'rounding': 'half_up', 'summed': 'each', 'valuation': 'rate', 'ended': 'units'} | 3973 / 5009 | 903 / 1144 |
| t3_surrender_value/r1-search/S13 | {'rounding': ('down', 'half_up'), 'summed': 'once', 'valuation': 'exact', 'ended': 'on'} | 3209 / 5009 | 735 / 1144 |
| t3_surrender_value/r1-search/S14 | {'rounding': ('down', 'half_up'), 'summed': 'once', 'valuation': 'exact', 'ended': 'after'} | 3209 / 5009 | 735 / 1144 |
| t3_surrender_value/r1-search/S15 | {'rounding': ('down', 'half_up'), 'summed': 'once', 'valuation': 'exact', 'ended': 'units'} | 3209 / 5009 | 735 / 1144 |
| t3_surrender_value/r1-search/S16 | {'rounding': 'half_up', 'summed': 'once', 'valuation': 'exact', 'ended': 'on'} | 3179 / 5009 | 732 / 1144 |
| t3_surrender_value/r1-search/S17 | {'rounding': 'half_up', 'summed': 'once', 'valuation': 'exact', 'ended': 'after'} | 3179 / 5009 | 732 / 1144 |
| t3_surrender_value/r1-search/S18 | {'rounding': 'half_up', 'summed': 'once', 'valuation': 'exact', 'ended': 'units'} | 3179 / 5009 | 732 / 1144 |
| t3_surrender_value/r1-search/S19 | {'rounding': ('down', 'half_up'), 'summed': 'once', 'valuation': 'rate', 'ended': 'on'} | 3026 / 5009 | 684 / 1144 |
| t3_surrender_value/r1-search/S20 | {'rounding': ('down', 'half_up'), 'summed': 'once', 'valuation': 'rate', 'ended': 'after'} | 3026 / 5009 | 684 / 1144 |
| t3_surrender_value/r1-search/S21 | {'rounding': ('down', 'half_up'), 'summed': 'once', 'valuation': 'rate', 'ended': 'units'} | 3026 / 5009 | 684 / 1144 |
| t3_surrender_value/r1-search/S22 | {'rounding': 'half_up', 'summed': 'once', 'valuation': 'rate', 'ended': 'on'} | 3010 / 5009 | 682 / 1144 |
| t3_surrender_value/r1-search/S23 | {'rounding': 'half_up', 'summed': 'once', 'valuation': 'rate', 'ended': 'after'} | 3010 / 5009 | 682 / 1144 |
| t3_surrender_value/r1-search/S24 | {'rounding': 'half_up', 'summed': 'once', 'valuation': 'rate', 'ended': 'units'} | 3010 / 5009 | 682 / 1144 |
| t3_surrender_value/r1-search/S25 | {'rounding': 'down', 'summed': 'once', 'valuation': 'exact', 'ended': 'on'} | 2684 / 5009 | 613 / 1144 |
| t3_surrender_value/r1-search/S26 | {'rounding': 'down', 'summed': 'once', 'valuation': 'exact', 'ended': 'after'} | 2684 / 5009 | 613 / 1144 |
| t3_surrender_value/r1-search/S27 | {'rounding': 'down', 'summed': 'once', 'valuation': 'exact', 'ended': 'units'} | 2684 / 5009 | 613 / 1144 |
| t3_surrender_value/r1-search/S28 | {'rounding': 'down', 'summed': 'once', 'valuation': 'rate', 'ended': 'on'} | 2494 / 5009 | 570 / 1144 |
| t3_surrender_value/r1-search/S29 | {'rounding': 'down', 'summed': 'once', 'valuation': 'rate', 'ended': 'after'} | 2494 / 5009 | 570 / 1144 |
| t3_surrender_value/r1-search/S30 | {'rounding': 'down', 'summed': 'once', 'valuation': 'rate', 'ended': 'units'} | 2494 / 5009 | 570 / 1144 |
| t3_surrender_value/r1-search/S31 | {'rounding': 'down', 'summed': 'each', 'valuation': 'exact', 'ended': 'on'} | 1880 / 5009 | 415 / 1144 |
| t3_surrender_value/r1-search/S32 | {'rounding': 'down', 'summed': 'each', 'valuation': 'exact', 'ended': 'after'} | 1880 / 5009 | 415 / 1144 |
| t3_surrender_value/r1-search/S33 | {'rounding': 'down', 'summed': 'each', 'valuation': 'exact', 'ended': 'units'} | 1880 / 5009 | 415 / 1144 |
| t3_surrender_value/r1-search/S34 | {'rounding': 'down', 'summed': 'each', 'valuation': 'rate', 'ended': 'on'} | 1790 / 5009 | 389 / 1144 |
| t3_surrender_value/r1-search/S35 | {'rounding': 'down', 'summed': 'each', 'valuation': 'rate', 'ended': 'after'} | 1790 / 5009 | 389 / 1144 |
| t3_surrender_value/r1-search/S36 | {'rounding': 'down', 'summed': 'each', 'valuation': 'rate', 'ended': 'units'} | 1790 / 5009 | 389 / 1144 |
