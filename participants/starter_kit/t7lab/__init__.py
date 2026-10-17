"""The t7 lab: tools that read the real tax tables to find and check the rules of t7; the submission does not use
them, and they are not part of the hand-in folder `my_solution`.

Run them from `my_solution`, with the hand-in and its tools on the path:

    NEURON_DATA=<participants> PYTHONPATH="$PWD:$PWD/tools:$PWD/.." python -B -m t7lab.t7_check

- `t7_check`: the checks to pass before an upload, run like the evaluator (time, memory, PDF examples, labels);
- `t7_labels`: the bookings of NRTAXB against what may decide them, counts only;
- `t7_variants`: how many rows each open convention changes, the size of the bet of a leaderboard probe;
- `t7_discover`, `base_split`, `tax_join`: the payouts joined with their labels, trees and base definitions.
"""
