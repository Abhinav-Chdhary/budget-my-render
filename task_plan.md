# Task Plan: Budget My Render Accuracy Study

## Goal

Generate reproducible representative Cycles fixtures, measure pilot-model error on the user's real hardware, and produce evidence for the next release's uncertainty ranges.

## Phases

- [x] Phase 1: Define the controlled measurement protocol and fixture coverage.
- [x] Phase 2: Implement the Blender fixture-and-measurement runner.
- [x] Phase 3: Implement offline report analysis and regression tests.
- [x] Phase 4: Run the study in desktop Blender and interpret the evidence.

## Key Questions

1. What error distribution does the two-point model show across representative Cycles workloads?
2. Are the current fixed uncertainty ranges wide enough, or should they be changed by workload/confidence?
3. How does adaptive sampling alter estimator accuracy?

## Decisions Made

- [Protocol]: Use 16- and 64-sample pilots, then compare their linear prediction to measured 256-sample references with adaptive sampling disabled.
- [Fixtures]: Generate interior, glossy, transparent, volume, and curve-hair scenes locally so the study is reproducible without redistributing third-party assets.
- [Evidence]: Keep raw timing JSON and calculate aggregate error separately in ordinary Python.
- [Range]: Retain the existing ±25% non-adaptive range. The first ten-run study has a 6.67% P90 and 8.31% maximum error, but it represents one hardware/Blender configuration and one target sample count.

## Errors Encountered

- Blender command mode crashes during Metal startup in this environment, so the measurement runner must be executed in the user's normal desktop Blender session.

## Status

**Initial study complete** — the measured data supports the existing conservative range. Further devices, 1024-sample references, and adaptive-sampling runs are the next evidence set.

---

# Historical Task Plan: Budget My Render Release Hardening

## Goal

Produce a validated Blender 4.2+ extension package that safely scopes calibration to compatible scene, software, and machine state, with automated regression tests and a user-run desktop validation checklist.

## Phases

- [x] Phase 1: Audit release blockers and define conservative correctness rules.
- [x] Phase 2: Harden calibration identity, reporting, and failure handling.
- [x] Phase 3: Convert the development script into an extension package with a manifest.
- [x] Phase 4: Add automated tests and validate the built artifact.
- [x] Phase 5: Prepare the desktop-Blender validation matrix and release handoff.
- [x] Phase 6: Publish the tested extension ZIP through a GitHub Release.

## Key Questions

1. Can a stored calibration be safely reused only when the scene, hardware, and render configuration are compatible?
2. Does the generated ZIP validate and install as a Blender Extension without external dependencies?
3. Which remaining tests must run in desktop Blender on the user's hardware?

## Decisions Made

- [Calibration]: Prefer conservative invalidation over silently reusing a potentially stale estimate.
- [Packaging]: Target the Blender Extension format introduced in Blender 4.2; retain no duplicate legacy package.
- [Testing]: Unit-test pure logic outside Blender and reserve real rendering/UI acceptance tests for desktop Blender.

## Errors Encountered

- Blender 5.2.0 LTS crashes during headless startup while initialising the Metal backend; no headless render/UI acceptance test is available in this environment.
- The Blender executable is not installed or on `PATH`, so the automated build script correctly stopped with exit code 127 before it could create or validate the distributable ZIP. Run it with `BLENDER_BIN` pointing to a desktop Blender executable.
- A verification shell snippet initially used zsh's reserved `status` variable; rerunning it with `build_result` completed normally. No repository files were affected.
- Blender is available at `/Applications/Blender.app`, but its command-mode extension validation crashes during startup with the known Metal fault. The Computer Use environment is not approved to operate Blender's desktop UI, so the final Install-from-Disk check must be completed locally by the user.
- The first manual 0.5.0 installation exposed Blender 5.2 returning a `bytes` build-platform field; fingerprint JSON serialization crashed while drawing the panel. Version 0.5.1 normalizes non-JSON Blender values and has a regression test for this case.

## Status

**Complete** — version 0.5.1 was installed through Blender's normal Install-from-Disk flow, ran an estimate successfully, and was published as a public GitHub Release.

---

# Historical Task Plan: Budget My Render Bootstrap

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
- [x] Phase 10: Reduce the artist-facing panel to the single estimate action.

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
- [Artist UI]: Use Cycles' own Max Samples field as the target, hide calibration inputs, and expose only the estimate/refresh action.

## Errors Encountered

- Blender 5.2.0 LTS crashes during headless startup while initialising its Metal GPU backend in this environment, before the add-on loads. The add-on passed standalone Python syntax compilation; verify its Blender UI panel in the normal desktop app.
- The estimator helper test initially used exact floating-point equality; rerun it using a numeric tolerance. A follow-up expected value was rounded incorrectly (74.950 instead of 74.947 seconds); correct the test fixture.

## Status

**Complete** — the panel has one action and uses Cycles' native Max Samples as its target.
