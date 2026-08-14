# Cycles Accuracy Study — 2026-08-15

## Scope

The controlled study ran the add-on's two-point 16/64-sample linear model
against 256-sample Cycles references. It used ten total measurements: two
repeats each of locally generated interior, glossy, transparent, volume, and
curve-hair fixtures. Adaptive sampling and denoising were disabled.

Environment: Blender 5.2.0 LTS on macOS 15.7.3 arm64 at 512 × 512.

## Results

| Metric | Absolute percentage error |
| --- | ---: |
| Mean | 2.85% |
| Median | 2.27% |
| P90 | 6.67% |
| Maximum | 8.31% |

The interior fixture was the worst observed case (8.31%). No systematic
over- or under-prediction appeared across the ten runs.

## Decision

Keep the current ±25% non-adaptive artist-facing range. The study strongly
supports it as conservative for this environment, but ten runs on one device
and one target sample count are insufficient to narrow a public guarantee.

## Next evidence

- Repeat with a 1024-sample reference to verify longer extrapolation.
- Add another hardware class, ideally CPU and a non-Apple GPU.
- Run the same matrix with adaptive sampling enabled; retain a separate wider
  policy for that mode until measured evidence supports a change.
