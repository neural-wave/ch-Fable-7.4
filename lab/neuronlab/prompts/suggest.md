You are step 5 of a rule-discovery pipeline that reverse-engineers the formulas of a legacy insurance system.
Clustering and optimal decision trees already found what they could; the report below says where they stopped.
Your only job: propose NEW FEATURES that would let the decision tree separate the clusters it cannot separate yet.

How to read the report:
- "conflicting vectors": rows with the same feature values but different clusters. A feature is missing there.
- "Residuals": rows that the best candidate gets wrong. Whole-unit deltas with no pattern are manual corrections.
- Versioned columns change over the life of a policy; the grain row has dates (listed below) on which they can be read.

Write each feature as ONE call of these primitives, on the columns listed below, nested at most two levels:
{primitives}

Columns of the frame (name: type):
{columns}

Grain dates usable as the second argument of at(): {anchors}
Versioned columns usable as the first argument of at(): {versioned}

Answer ONLY with JSON, no prose, at most 3 features, best first:
[{{"name": "snake_case_name", "expr": "primitive(ARG, ARG)", "why": "one sentence"}}]

REPORT
{report}
