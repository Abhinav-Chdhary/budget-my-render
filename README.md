# Budget My Render

An open-source Blender add-on for making render-time trade-offs visible and reproducible.

The add-on captures current Cycles settings and can run a sample-count matrix, saving each image and its elapsed render time in one JSON report.

## Install the development add-on

1. Open Blender and switch to the **Scripting** workspace.
2. Open `addon/budget_my_render.py` in Blender's Text Editor.
3. Click **Run Script**.
4. In the 3D Viewport, press `N` and open the **Render Budget** tab.
5. Select **Cycles** in Render Properties.
6. Enter comma-separated **Max samples** values, such as `16, 64, 256, 1024`.
7. Click **Run Sample Benchmark**. Blender renders each value serially; its normal UI will be unavailable while each render is running.

If the current `.blend` file has been saved, each run is written to a sibling `reports/benchmark-<timestamp>/` folder. That folder contains one image per sample count and `benchmark.json` with the timings and captured settings. For an unsaved file, it is written to Blender's temporary directory.

The runner restores the scene's original max-samples value and render output path when it finishes or a render errors. It does not change adaptive sampling, denoising, resolution, device, or any other quality setting: hold those constant for a fair comparison.

## Estimate render time

The **Estimate final render** panel runs two opt-in pilot renders of the current scene and local machine, then estimates the time for the selected target max-samples value. It does not save pilot images, but it does use the same CPU or GPU resources as a normal Cycles render while the pilots run.

The default pilots are 16 and 64 samples. Their timings are fitted to a simple linear model that includes setup time, and the sidebar displays both an estimate and an uncertainty range. With adaptive sampling enabled, the selected target is a maximum rather than a fixed sample count, so the add-on marks the estimate as low confidence and widens the range.

Each estimate is recorded as `reports/estimate-<timestamp>/estimate.json`. The estimate is scene- and machine-specific; rerun it after material scene, engine, device, resolution, or render-setting changes.

## Development target

Use Blender 4.2 or later. The add-on uses only Blender's bundled Python API and has no external dependencies.

## First benchmark

Follow [the fixture instructions](fixtures/README.md), capture settings at each configuration, and keep the rendered output alongside the JSON report. Do not compare times from different machines as if they were directly equivalent.

## Roadmap

1. Capture current settings as a stable JSON record. **Done**
2. Render a selected configuration matrix and measure elapsed time. **Done**
3. Estimate a selected target from two opt-in pilot renders. **Done**
4. Compare output against a high-sample reference.
5. Learn from ordinary completed renders and recommend configurations for a chosen time budget.
6. Evaluate new adaptive-sampling policies against the baseline.

## License

[MIT](LICENSE)
