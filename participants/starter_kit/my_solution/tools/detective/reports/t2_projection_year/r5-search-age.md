# t2_projection_year, r5-search-age

After r4: 8 of the 29 wrong policies have an impossible birth date (31 April, 30 February: profile check undecodable), which decoded to null, and 18 start on the 1st exactly six months after a birthday on day 2 to 12 (r4/T1 PS_BIRTH day <= 12.5): the nearest age is decided by days there. Holes: how an impossible day is read, and nearest-age conventions counted in days.

| Finding | Holes | Right (80 %) | Right (held out) |
| --- | --- | --- | --- |
| t2_projection_year/r5-search-age/S1 | {'age': 'nearest', 'impossible': 'clamp'} | 63604 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-age/S2 | {'age': 'nearest', 'impossible': 'roll'} | 63604 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-age/S3 | {'age': 'months', 'impossible': 'clamp'} | 63604 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-age/S4 | {'age': 'months', 'impossible': 'roll'} | 63604 / 64021 | 14835 / 15019 |
| t2_projection_year/r5-search-age/S5 | {'age': 'nearest_days365.25', 'impossible': 'clamp'} | 63469 / 64021 | 14768 / 15019 |
| t2_projection_year/r5-search-age/S6 | {'age': 'nearest_days365.25', 'impossible': 'roll'} | 63469 / 64021 | 14768 / 15019 |
| t2_projection_year/r5-search-age/S7 | {'age': 'nearest_days365', 'impossible': 'clamp'} | 62686 / 64021 | 14735 / 15019 |
| t2_projection_year/r5-search-age/S8 | {'age': 'nearest_days365', 'impossible': 'roll'} | 62686 / 64021 | 14735 / 15019 |
