"""Keys and relations between the Neuron tables, found in the data with Desbordante instead of written by hand.

Desbordante (https://github.com/Desbordante/desbordante-core) profiles data with published algorithms. The
steps, one module each:

1. `keys`: the documented keys of SCHEMA.md against the candidate keys that HyUCC finds.
2. `inclusions`: the inclusion dependencies between all tables (Faida exact, Spider approximate).
3. `relations`: every inclusion checked exactly; it is a relation when it can be a foreign key.
4. `graph`, `diagram`: the relations as a graph of tables and as a picture.
"""
