# t3_booking

Grain: NRBOOK {'policy_id': 'BK_POLNR', 'booking_id': 'BK_BOOKID'} (reverse coverage 99.4%; others: )
Filter: BK_BKTYP in ['ADM', 'AMC', 'PRM', 'RSK'] (excluded rows {'DTH': 300, 'SUR': 3869, 'SWO': 4833, 'WDR': 4496, 'SWI': 4928}, errors 10581)

## amount_pc

No relation with dense clusters: a feature or a different relation is missing.
Approximate only: value / BK_EVTNR is near 0.02, 0.210616, 0.214, 0.218, 0.22214, 0.226, 0.22925, 0.232242 on 94% of the precise rows, but no center reproduces enough rows exactly. The value may be a sum of parts rounded one by one (per instalment, per month), or the input may be missing a part.

## price

No relation with dense clusters: a feature or a different relation is missing.

## units

No relation with dense clusters: a feature or a different relation is missing.
