# Cycles Accuracy Study

Run `run_accuracy_study.py` from Blender's **Scripting** workspace. It creates
temporary interior, glossy, transparent, volume, and curve-hair fixtures and
measures the same 16/64-sample linear model used by the add-on against a
256-sample reference. It renders no image files and removes its temporary
scenes when complete.

The default `REPEATS = 2` produces ten measurements. Change `REPEATS`,
`REFERENCE_SAMPLES`, or `RESOLUTION` at the top of the script only when the
study report records those changes alongside its data.

Save the current `.blend` before running; the raw JSON is then written next to
it. For an unsaved file, Blender's temporary directory is used instead.

Analyse the raw report with ordinary Python:

```bash
python3 benchmarks/analyze_accuracy.py /path/to/accuracy-study-*.json
```

The generated summary reports mean, median, P90, and maximum absolute error,
plus a conservative non-adaptive uncertainty-range recommendation.
