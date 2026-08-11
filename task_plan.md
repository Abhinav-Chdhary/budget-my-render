# Task Plan: Budget My Render Bootstrap

## Goal

Extend the Blender add-on so it can run a controlled Cycles sample benchmark and save timings, images, and settings in one JSON report.

## Phases

- [x] Phase 1: Create repository metadata and project plan.
- [x] Phase 2: Implement the first Blender add-on feature.
- [x] Phase 3: Add documentation and a reproducible fixture.
- [x] Phase 4: Verify the package structure and hand off installation steps.
- [x] Phase 5: Add a safe automatic sample-benchmark operator.
- [x] Phase 6: Verify the report format and update documentation.

## Key Questions

1. Can the first feature work in a normal Blender installation without external dependencies?
2. Does the repository make the future benchmark runner easy to add?
3. Can the runner restore every modified scene setting even when a render fails?

## Decisions Made

- [Packaging]: Begin with a conventional single-file Blender add-on for broad Blender-version compatibility.
- [First feature]: Report the active Cycles configuration and write a JSON snapshot beside the `.blend` file (or Blender's temporary directory).
- [Benchmark behavior]: Render comma-separated sample counts sequentially and restore the original sample count and output path in a `finally` block.

## Errors Encountered

- Blender 5.2.0 LTS crashes during headless startup while initialising its Metal GPU backend in this environment, before the add-on loads. The add-on passed standalone Python syntax compilation; verify its Blender UI panel in the normal desktop app.

## Status

**Complete** — benchmark runner added; it requires one normal Blender UI run because headless Blender cannot initialise Metal in this environment.
