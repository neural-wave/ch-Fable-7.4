# Starter kit

`submission.py` is the file we call. It already has one function per task, all returning empty results, so you
can fill them in one by one. List the packages you use in `requirements.txt`.

To score your code against the train targets:

```
python check.py
python check.py --tasks t0_commission
python check.py --submission ../my_solution
```

`scoring.py` is the scoring we use for the evaluation. Note that the train targets still
contain the values that were corrected by hand (that is task t5), so even a perfect set of rules stays a little
below 100 % locally. The official evaluation does not score those rows.

What to hand in: the folder `my_solution` with `submission.py` and your helper modules, `requirements.txt`, all your tools and visualizations you
built, and a short `README.md` about your approach and the rules you found. Your code has to
calculate everything from the files in `legacy_dir`. The only exception is t5, which gets `targets_dir` with the
target files of the policies to check. Reading the target files anywhere else or putting values into the submission is
not allowed.
