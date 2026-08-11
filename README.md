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

## Development target

Use Blender 4.2 or later. The add-on uses only Blender's bundled Python API and has no external dependencies.

## First benchmark

Follow [the fixture instructions](fixtures/README.md), capture settings at each configuration, and keep the rendered output alongside the JSON report. Do not compare times from different machines as if they were directly equivalent.

## Roadmap

1. Capture current settings as a stable JSON record. **Done**
2. Render a selected configuration matrix and measure elapsed time. **Done**
3. Compare output against a high-sample reference.
4. Recommend configurations for a chosen time budget.
5. Evaluate new adaptive-sampling policies against the baseline.

## License

[MIT](LICENSE)
