# Desktop Blender Validation

Run this checklist with the ZIP produced by `scripts/build_extension.sh`. These
checks deliberately use a desktop Blender installation because the local
headless Metal start-up failure prevents meaningful Cycles acceptance tests in
this repository.

## Installation and safety

1. Start Blender 4.2 or later with a clean profile.
2. Install the ZIP from **Edit → Preferences → Get Extensions → Install from
   Disk** and enable **Budget My Render**.
3. Open a saved Cycles fixture. In the 3D Viewport, press `N` and verify the
   **Render Budget** tab appears.
4. Run **Estimate Render Time**. Confirm both pilot renders finish, the
   original Max Samples value is restored, and one local
   `reports/estimate-*/estimate.json` exists beside the `.blend`.
5. Inspect the report. It must use `blend_file_name`, not an absolute path;
   `network_upload` must be `false`; and its directory name must include a
   timestamp and random suffix.
6. Confirm the pilot replaces Blender's **Render Result** and triggers any
   normal render handlers expected in the test file.

## Calibration invalidation

1. After a successful estimate, change only Cycles **Max Samples**. The panel
   should immediately update its estimate without running pilot renders.
2. Change a render-relevant scene item: move the camera, edit a material, hide
   an object from render, or change a light. The panel must request
   recalibration.
3. Change the active frame or a core render setting such as resolution,
   denoising, device, or ray-bounce limit. The panel must request
   recalibration.
4. Save, close Blender, reopen the file, and enable the extension. The panel
   must request recalibration; pilot estimates do not survive a Blender
   session/cache restart.
5. Cancel a pilot render with Escape. Confirm Max Samples is restored and no
   new valid estimate appears.

## Accuracy evidence

For each fixture, run pilots at 16/64 samples, then render a reference at the
chosen target without changing the scene or render device. Record the elapsed
wall time, predicted time, and absolute percentage error.

| Fixture | Device | Adaptive | Denoise | Target samples | Predicted | Actual | Error |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| Interior | | | | | | | |
| Glossy | | | | | | | |
| Transparent | | | | | | | |
| Volume | | | | | | | |
| Hair | | | | | | | |

Use this data to replace the provisional fixed uncertainty ranges before making
an accuracy promise in release notes or store copy.
