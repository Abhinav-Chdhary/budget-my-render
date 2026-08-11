# Budget My Render

An open-source Blender add-on that estimates how long the current Cycles render will take.

## Install the development add-on

1. Open Blender and switch to the **Scripting** workspace.
2. Open `addon/budget_my_render.py` in Blender's Text Editor.
3. Click **Run Script**.
4. In the 3D Viewport, press `N` and open the **Render Budget** tab.
5. Select **Cycles** in Render Properties and set its normal **Max Samples** value.
6. Click **Estimate render time**.

## Estimate render time

The panel has one action: **Estimate render time**. It runs two opt-in 16- and 64-sample pilot renders of the current scene and local machine, then estimates the time for the **Max Samples** value already selected in Cycles. It does not save pilot images, but it does use the same CPU or GPU resources as a normal Cycles render while the pilots run.

The default pilots are 16 and 64 samples. Their timings are fitted to a simple linear model that includes setup time, and the sidebar displays both an estimate and an uncertainty range. With adaptive sampling enabled, the selected target is a maximum rather than a fixed sample count, so the add-on marks the estimate as low confidence and widens the range.

Each estimate is recorded as `reports/estimate-<timestamp>/estimate.json`. The estimate is scene- and machine-specific; rerun it after material scene, engine, device, resolution, or render-setting changes.

Changing only Cycles' **Max Samples** value does not run pilots again. The sidebar immediately recalculates from the existing calibration. Core settings such as resolution, device, adaptive sampling, denoising, and ray-bounce limits invalidate that calibration and show a recalibration prompt.

## Development target

Use Blender 4.2 or later. The add-on uses only Blender's bundled Python API and has no external dependencies.

## Roadmap

1. Estimate the current Cycles Max Samples value from two opt-in pilot renders. **Done**
2. Compare output against a high-sample reference.
3. Learn from ordinary completed renders and recommend configurations for a chosen time budget.
4. Evaluate new adaptive-sampling policies against the baseline.

## License

[MIT](LICENSE)
