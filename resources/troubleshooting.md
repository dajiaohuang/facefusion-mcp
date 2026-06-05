# Troubleshooting

## Missing models

- Symptom: run fails before inference starts or reports missing source/model assets
- Likely cause: required model files are absent or corrupt
- Fix: run `facefusion_download_models`, then retry the task

## CUDA unavailable

- Symptom: provider list omits `cuda`, or the task fails when `cuda` is selected
- Likely cause: runtime mismatch, driver issue, or provider not loaded
- Fix: run `facefusion_health_check`, fall back to `cpu`, and only retry `cuda` after the environment is healthy

## FFmpeg unavailable

- Symptom: video-oriented tasks fail immediately or encoding options look empty
- Likely cause: `ffmpeg` is not on `PATH`
- Fix: install or expose `ffmpeg`, then rerun `facefusion_health_check`

## Output path conflict

- Symptom: MCP tool rejects the task before launching FaceFusion
- Likely cause: the output file already exists and overwrite is disabled
- Fix: choose a new `output_path` or set `overwrite=true`

## Parameter incompatibility

- Symptom: FaceFusion exits with CLI argument errors
- Likely cause: flag combination is invalid for the chosen command or processor
- Fix: check `facefusion://reference/parameter-mapping` and reduce to a smaller valid set

## Job execution failure

- Symptom: queued or retried jobs stop with nonzero exit status
- Likely cause: bad step parameters, missing media, or provider/runtime issues
- Fix: inspect the tool result, list jobs by status, and rerun `facefusion_health_check` if the failure is environmental

## Interrupted download

- Symptom: `force-download` reports validation failures after partial progress
- Likely cause: interrupted network transfer or corrupt file
- Fix: rerun `facefusion_download_models`; FaceFusion will repair invalid downloads
