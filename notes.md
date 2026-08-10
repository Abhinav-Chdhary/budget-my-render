# Notes: Budget My Render Bootstrap

## Sources

### Blender scripting introduction

- URL: https://docs.blender.org/manual/en/4.2/advanced/scripting/introduction.html
- Blender Python scripts can automate rendering and add UI panels/operators.
- Add-ons can be installed from Blender Preferences.

### Cycles sampling

- URL: https://docs.blender.org/manual/de/4.0/render/cycles/render_settings/sampling.html
- Sample count, adaptive sampling, and denoising are the first settings the project will record.

## Design notes

- The first add-on deliberately records settings only; it does not claim to optimise them.
- JSON is used so the upcoming benchmark runner can append measured renders without changing the reporting format.
