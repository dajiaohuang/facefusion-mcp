# FaceFusion Processors

## Primary processors

### `face_swapper`
- Best for: direct face replacement in images or videos
- Common pairings: `face_enhancer`, `frame_enhancer`
- Cost profile: medium to high, depends on source size and target duration
- Avoid when: the user wants expression editing or background removal rather than identity transfer

### `face_enhancer`
- Best for: restoring or sharpening swapped faces
- Common pairings: `face_swapper`
- Cost profile: medium
- Avoid when: the user only wants global frame enhancement

### `background_remover`
- Best for: cutouts, alpha-style exports, subject isolation
- Common pairings: none, or downstream editing outside FaceFusion
- Cost profile: medium to high on large video batches
- Avoid when: the user mainly wants face manipulation

### `frame_enhancer`
- Best for: global frame upscaling and cleanup
- Common pairings: `face_swapper`, `face_enhancer`
- Cost profile: high on video
- Avoid when: the user only needs local face restoration

### `frame_colorizer`
- Best for: recoloring grayscale or archival footage
- Common pairings: `frame_enhancer`
- Cost profile: medium to high
- Avoid when: the source is already color

### `lip_syncer`
- Best for: syncing a target face to audio
- Common pairings: `face_swapper`, `face_enhancer`
- Cost profile: high
- Avoid when: there is no audio-driven talking-head goal

### `face_editor`
- Best for: pose, gaze, mouth, and expression adjustments
- Common pairings: `expression_restorer`
- Cost profile: medium to high
- Avoid when: the user only wants a standard swap

### `expression_restorer`
- Best for: recovering target-face expression after other manipulations
- Common pairings: `face_swapper`, `face_editor`
- Cost profile: medium
- Avoid when: no visible expression drift exists

### `deep_swapper`
- Best for: pre-trained identity-specific swaps
- Common pairings: `face_enhancer`
- Cost profile: high storage and model cost
- Avoid when: the user wants a general-purpose swapper with arbitrary source images

### `age_modifier`
- Best for: aging or de-aging a face
- Common pairings: `face_enhancer`
- Cost profile: medium
- Avoid when: the task is identity transfer or restoration rather than age transformation

## Common processor combinations

- Standard swap: `face_swapper` + optional `face_enhancer`
- Higher quality video: `face_swapper` + `face_enhancer` + `frame_enhancer`
- Talking head sync: `lip_syncer` + optional `face_enhancer`
- Portrait cleanup: `face_enhancer` only
- Cutout workflow: `background_remover`
