# Budget My Render

An open-source Blender add-on that estimates how long the current Cycles render will take.

## Install the Blender Extension

Download a validated `budget_my_render-<version>.zip` release. In Blender 4.2
or later, open **Edit → Preferences → Get Extensions**, use the menu in the
upper-right, choose **Install from Disk**, select the ZIP, and enable **Budget
My Render**. In the 3D Viewport, press `N` and open the **Render Budget** tab.

The extension requests Blender's **files** permission only to write local JSON
estimate reports. It has no network or external Python dependencies. Reports
are written next to the saved `.blend` in `reports/`, or to the system temporary
directory when the file has not been saved. They are never uploaded by the
extension.

## Run the development script

1. Open Blender and switch to the **Scripting** workspace.
2. Open `addon/budget_my_render.py` in Blender's Text Editor.
3. Click **Run Script**.
4. In the 3D Viewport, press `N` and open the **Render Budget** tab.
5. Select **Cycles** in Render Properties and set its normal **Max Samples** value.
6. Click **Estimate render time**.

## Estimate render time

The panel has one action: **Estimate render time**. It runs two opt-in 16- and 64-sample pilot renders of the current scene and local machine, then estimates the time for the **Max Samples** value already selected in Cycles. It does not save pilot images, but it does use the same CPU or GPU resources as a normal Cycles render while the pilots run.

The default pilots are 16 and 64 samples. Their timings are fitted to a simple linear model that includes setup time, and the sidebar displays both an estimate and an uncertainty range. With adaptive sampling enabled, the selected target is a maximum rather than a fixed sample count, so the add-on marks the estimate as low confidence and widens the range.

Pilot renders use Blender's normal render operator. They replace the current
**Render Result** and invoke normal render handlers, so save or disable any
workflow automation that reacts to completed renders before estimating.

Each estimate is recorded as `reports/estimate-<timestamp>/estimate.json`. The estimate is scene- and machine-specific; rerun it after material scene, engine, device, resolution, or render-setting changes.

Changing only Cycles' **Max Samples** value does not run pilots again. The sidebar immediately recalculates from the existing calibration. Core settings such as resolution, device, adaptive sampling, denoising, and ray-bounce limits invalidate that calibration and show a recalibration prompt.

## Development target

Use Blender 4.2 or later. The add-on uses only Blender's bundled Python API and has no external dependencies.

## Build a distributable extension

The extension source is [`addon/`](addon/), containing the required
`blender_manifest.toml` and `__init__.py`. To build and validate a distributable
ZIP, run:

```bash
BLENDER_BIN=/path/to/blender ./scripts/build_extension.sh
```

The ZIP is placed in `dist/`. See [the release checklist](docs/RELEASING.md)
for clean-profile testing and publication steps.

## Roadmap

1. Estimate the current Cycles Max Samples value from two opt-in pilot renders. **Done**
2. Compare output against a high-sample reference.
3. Learn from ordinary completed renders and recommend configurations for a chosen time budget.
4. Evaluate new adaptive-sampling policies against the baseline.

## License

[MIT](LICENSE)
