# Releasing Budget My Render

This repository ships a Blender Extension, not a legacy add-on ZIP. The
extension source is [`addon/`](../addon/); its `__init__.py` is the extension
entry point and delegates to `budget_my_render.py`, which remains runnable from
Blender's Text Editor for development. The package also includes its own MIT
license copy so the distributable ZIP remains self-contained.

## Before building

1. Update the version in both `addon/blender_manifest.toml` and the `bl_info`
   dictionary in `addon/budget_my_render.py`.
2. Run the automated tests and the fixture accuracy checks appropriate for the
   release:

   ```bash
   python3 -m unittest discover -s tests -v
   ```
3. Confirm `LICENSE`, this documentation, and the privacy statement in the
   main README still describe the shipped behavior.

## Build the distributable ZIP

Run this from the repository root:

```bash
BLENDER_BIN=/path/to/blender ./scripts/build_extension.sh
```

When `blender` is already on `PATH`, omit `BLENDER_BIN`. The script validates
the extension source, builds it into `dist/`, and validates the generated ZIP.
Do not upload an unvalidated archive.

For a manual equivalent:

```bash
blender --command extension validate addon
blender --command extension build --source-dir addon --output-dir dist
blender --command extension validate dist/budget_my_render-<version>.zip
```

## Clean-profile acceptance check

In a clean Blender 4.2+ profile:

1. Open **Edit → Preferences → Get Extensions**.
2. Use the menu in the upper-right and choose **Install from Disk**.
3. Select the ZIP in `dist/` and enable **Budget My Render**.
4. Open a Cycles scene, press `N` in the 3D Viewport, and check the **Render
   Budget** tab appears.
5. Run an estimate, confirm a local `reports/estimate-*/estimate.json` is
   written, and confirm that the pilots replace Blender's **Render Result** and
   invoke normal render handlers. Then disable/re-enable the extension and
   reopen the `.blend`.
6. Uninstall it. Verify the extension disappears without affecting the saved
   `.blend` or local reports.

Record the Blender version, operating system, render device, and outcome for
each supported platform.

Run the complete [desktop validation checklist](DESKTOP_VALIDATION.md),
including the calibration-invalidation and accuracy-evidence sections, before
public distribution.

## Publish

Attach the validated ZIP to a GitHub Release for direct installation, or upload
the same ZIP to Blender Extensions for review and publication. Do not alter a
ZIP after validation; rebuild and validate it again instead.
