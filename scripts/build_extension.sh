#!/usr/bin/env bash

# Build and validate the exact Blender Extension ZIP that will be distributed.
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
extension_source="$repository_root/addon"
distribution_directory="$repository_root/dist"
blender_binary="${BLENDER_BIN:-blender}"
extension_version="$(sed -nE 's/^version = "([^"]+)"$/\1/p' "$extension_source/blender_manifest.toml")"

if [[ -z "$extension_version" ]]; then
  printf 'Could not read the extension version from blender_manifest.toml.\n' >&2
  exit 1
fi

if ! command -v "$blender_binary" >/dev/null 2>&1; then
  printf 'Blender executable not found: %s\n' "$blender_binary" >&2
  printf 'Set BLENDER_BIN to the Blender executable, then run this script again.\n' >&2
  exit 127
fi

mkdir -p "$distribution_directory"
package_path="$distribution_directory/budget_my_render-$extension_version.zip"
# Never validate a previous release artifact when the build command failed to
# produce a new one for this source revision.
rm -f "$package_path"

"$blender_binary" --command extension validate "$extension_source"
"$blender_binary" --command extension build \
  --source-dir "$extension_source" \
  --output-filepath "$package_path"

if [[ ! -f "$package_path" ]]; then
  printf 'Blender reported success but no Budget My Render ZIP was created.\n' >&2
  exit 1
fi

"$blender_binary" --command extension validate "$package_path"
printf 'Validated extension package: %s\n' "$package_path"
