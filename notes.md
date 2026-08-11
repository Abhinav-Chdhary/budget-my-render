# Notes: Budget My Render Bootstrap

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
