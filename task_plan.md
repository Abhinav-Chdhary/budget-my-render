# Task Plan: Budget My Render Bootstrap

## Goal

Develop a trustworthy in-Blender render-time estimate that does not require artists to manually run benchmark matrices.

## Phases

- [x] Phase 1: Create repository metadata and project plan.
- [x] Phase 2: Implement the first Blender add-on feature.
- [x] Phase 3: Add documentation and a reproducible fixture.
- [x] Phase 4: Verify the package structure and hand off installation steps.
- [x] Phase 5: Add a safe automatic sample-benchmark operator.
- [x] Phase 6: Verify the report format and update documentation.
- [x] Phase 7: Define the prediction approach from the first recorded benchmark.
- [x] Phase 8: Implement an on-demand pilot-render estimator.
- [x] Phase 9: Reuse a valid pilot calibration when only target sample count changes.

## Key Questions

1. Can the first feature work in a normal Blender installation without external dependencies?
2. Does the repository make the future benchmark runner easy to add?
3. Can the runner restore every modified scene setting even when a render fails?
4. How can an estimate be useful before a final render without pretending that settings alone describe scene complexity?

## Decisions Made

- [Packaging]: Begin with a conventional single-file Blender add-on for broad Blender-version compatibility.
- [First feature]: Report the active Cycles configuration and write a JSON snapshot beside the `.blend` file (or Blender's temporary directory).
- [Benchmark behavior]: Render comma-separated sample counts sequentially and restore the original sample count and output path in a `finally` block.
- [Prediction approach]: Start with an opt-in, low-sample pilot render on the current scene and local machine; extrapolate to the artist's target samples, report an uncertainty range, and learn from completed normal renders.
- [Calibration reuse]: Keep the fitted setup cost and per-sample rate in the active scene. Recalculate instantly for a new target when a fingerprint of the core render settings still matches.

## Errors Encountered

- Blender 5.2.0 LTS crashes during headless startup while initialising its Metal GPU backend in this environment, before the add-on loads. The add-on passed standalone Python syntax compilation; verify its Blender UI panel in the normal desktop app.
- The estimator helper test initially used exact floating-point equality; rerun it using a numeric tolerance. A follow-up expected value was rounded incorrectly (74.950 instead of 74.947 seconds); correct the test fixture.

## Status

**Complete** — changing only target samples recalculates instantly; tracked core settings trigger a recalibration prompt.
