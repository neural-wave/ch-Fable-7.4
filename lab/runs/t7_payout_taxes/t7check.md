# t7check (no targets: examples of such.pdf and consistency with NRTAXB)

## t7_tax_payout

  rows the scoring drops (wrong format): 0 of 1794
Payouts (NRTAXB, 2493 payout events): computed 680, missing 1813, not payouts 1114
  taxed or not as NRTAXB: 555 / 2493
  country of the booked taxes: 551 / 551
  remittance date exactly when something is withheld: 555 / 680
  ('BL10000004', 31) missing, NRTAXB books nothing
  ('BL10000005', 54) missing, NRTAXB books nothing
  ('BL10000006', 13) missing, NRTAXB books nothing
  ('BL10000007', 132) missing, NRTAXB books nothing
  ('BL10000007', 202) missing, NRTAXB books nothing
  ('BL10000016', 108) missing, NRTAXB books nothing
  ('BL10000021', 274) missing, NRTAXB books nothing
  ('BL10000029', 13) missing, NRTAXB books nothing
  examples of such.pdf (2 rows, a sanity check only):
  example ('BL10000086', 121): WRONG; expected ('DE', '5628.16', '1407.04', '77.38', '0.00', '2006-08-10'), computed ('DE', '11989.76', '299744.01', '1648592.05', '0.00', '2006-08-10')

## t7_tax_annual

  rows the scoring drops (wrong format): 0 of 5535
Annual (policy, year): same tax types as NRTAXB on 5508 / 6381 keys (computed 5535, booked 6381; BOC is left out)
  ('BL10000003', 2005) computed [], NRTAXB books ['VST']
  ('BL10000028', 2024) computed [], NRTAXB books ['VST']
  ('BL10000036', 2016) computed [], NRTAXB books ['BOL']
  ('BL10000052', 2003) computed [], NRTAXB books ['VST']
  ('BL10000057', 2021) computed [], NRTAXB books ['STP']
  ('BL10000074', 2020) computed [], NRTAXB books ['VST']
  ('BL10000075', 2021) computed [], NRTAXB books ['VST']
  ('BL10000076', 2010) computed [], NRTAXB books ['SOS']
  examples of such.pdf (2 rows, a sanity check only):
  example ('BL10000044', 2019): WRONG; expected ('0.00', '0.00', '0.00', '616.11', '0.00', '0.00', '0.00'), computed ('0', '0', '0', '33448.48', '0', '0', '0')
