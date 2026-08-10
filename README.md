# Budget My Render

An open-source Blender add-on for making render-time trade-offs visible and reproducible.

The first milestone captures the current Cycles render settings as JSON. The next milestone will render a small configuration matrix and report a time-versus-quality curve.

## Install the development add-on

1. Open Blender and switch to the **Scripting** workspace.
2. Open `addon/budget_my_render.py` in Blender's Text Editor.
3. Click **Run Script**.
4. In the 3D Viewport, press `N` and open the **Render Budget** tab.
5. Select **Cycles** in Render Properties, then click **Capture Settings Snapshot**.

If the current `.blend` file has been saved, the report is written to a sibling `reports/` folder. For an unsaved file, it is written to Blender's temporary directory.

## Development target

Use Blender 4.2 or later. The add-on uses only Blender's bundled Python API and has no external dependencies.

## First benchmark

Follow [the fixture instructions](fixtures/README.md), capture settings at each configuration, and keep the rendered output alongside the JSON report. Do not compare times from different machines as if they were directly equivalent.

## Roadmap

1. Capture current settings as a stable JSON record. **Done**
2. Render a selected configuration matrix and measure elapsed time.
3. Compare output against a high-sample reference.
4. Recommend configurations for a chosen time budget.
5. Evaluate new adaptive-sampling policies against the baseline.

## License

[MIT](LICENSE)
