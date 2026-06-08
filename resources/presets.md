# FaceFusion MCP Presets

These presets are MCP-side default bundles. They do not replace raw FaceFusion flags, but they give the agent stable starting points for common tasks.

## Available presets

### `fast_preview_swap`
- Use for: quick preview swaps
- Defaults:
  - processors: `face_swapper`
  - memory: `strict`
  - video preset: `veryfast`

### `balanced_face_swap`
- Use for: most normal face swap jobs
- Defaults:
  - processors: `face_swapper`, `face_enhancer`
  - memory: `moderate`
  - selector mode: `one`

### `quality_face_swap`
- Use for: final higher-quality renders
- Defaults:
  - processors: `face_swapper`, `face_enhancer`, `frame_enhancer`
  - memory: `tolerant`
  - selector mode: `reference`

### `multi_face_reference`
- Use for: multi-face and same-frame role swaps
- Defaults:
  - processors: `face_swapper`, `face_enhancer`
  - selector mode: `reference`
  - mask types: `box`, `occlusion`, `region`

### `lip_sync_clean`
- Use for: speaking-face lip sync
- Defaults:
  - processors: `lip_syncer`, `face_enhancer`
  - mask focus: `mouth`

### `portrait_enhance`
- Use for: portrait restoration only
- Defaults:
  - processors: `face_enhancer`

### `frame_restore`
- Use for: whole-frame cleanup and upscale
- Defaults:
  - processors: `frame_enhancer`

### `background_cutout`
- Use for: subject isolation and cutouts
- Defaults:
  - processors: `background_remover`

### `archive_colorize`
- Use for: grayscale or archival footage
- Defaults:
  - processors: `frame_colorizer`, `frame_enhancer`

### `face_debug_overlay`
- Use for: detection and mask debugging
- Defaults:
  - processors: `face_debugger`
  - log level: `debug`

## Usage rule

- Pass `preset` into:
  - `facefusion_run_job`
  - `facefusion_launch_ui`
  - `facefusion_batch_run`
  - `facefusion_benchmark`
- Explicit request fields override the preset defaults.
- Use `facefusion_list_presets` to inspect the exact merged preset definitions.
