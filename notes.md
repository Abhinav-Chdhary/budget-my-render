# Notes: Budget My Render Bootstrap

## Release-hardening findings (2026-08-14)

- Blender Extensions require a `blender_manifest.toml` and an `__init__.py` in the installed ZIP. The manifest must declare a semantic version, SPDX license, maintainer, type, and Blender minimum version (at least 4.2).
- Writing audit reports is filesystem access, so the extension manifest must declare a short `files` permission reason.
- A calibration is only reusable when its render settings, scene inputs, Blender/Cycles version, and machine identity are compatible. The safe release policy is to invalidate when the signature cannot establish this.
- A final clean-profile install and real render test must be executed in desktop Blender because this environment cannot start Blender headlessly with Metal.

### Sources

- Blender Extension creation: https://docs.blender.org/manual/en/4.5/advanced/extensions/getting_started.html
- Blender Extension CLI: https://docs.blender.org/manual/en/4.5/advanced/command_line/extension_arguments.html

---

## Sources

### Blender scripting introduction

- URL: https://docs.blender.org/manual/en/4.2/advanced/scripting/introduction.html
- Blender Python scripts can automate rendering and add UI panels/operators.
- Add-ons can be installed from Blender Preferences.

### Cycles sampling

- URL: https://docs.blender.org/manual/de/4.0/render/cycles/render_settings/sampling.html
- Sample count, adaptive sampling, and denoising are the first settings the project will record.

### Blender render handlers

- URL: https://docs.blender.org/api/current/genindex-R.html
- Blender exposes render lifecycle handlers, including `render_complete`, `render_cancel`, and `render_stats`.
- A later version can learn from artists' ordinary completed renders instead of requiring a separate benchmark workflow.

## Design notes

- The first add-on deliberately records settings only; it does not claim to optimise them.
- JSON is used so the upcoming benchmark runner can append measured renders without changing the reporting format.
- The benchmark runner keeps adaptive sampling and denoising unchanged. If adaptive sampling is enabled, the values in the UI and report are maximum sample caps rather than guaranteed sample counts.
- The first local Cycles measurement was nearly linear in sample count: 16/64/256 max samples measured 5.257/19.195/77.721 seconds. A two-point pilot can therefore estimate the per-sample slope for this scene and machine, but scene preparation cost requires an uncertainty range.
- From the 16- and 64-sample measurements, the fitted estimate for 256 samples is 74.947 seconds; the measured 256-sample run was 77.721 seconds. This is a useful validation example, but not a guarantee for different scenes or settings.
