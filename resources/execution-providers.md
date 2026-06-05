# Execution Providers

## `cuda`

- Prefer when: an NVIDIA GPU is available and the task is performance-sensitive
- Strengths: best default speed on this machine, broad support
- Tradeoff: requires GPU-compatible runtime and drivers
- Fallback: use `cpu` if CUDA is unavailable or unstable

## `tensorrt`

- Prefer when: the machine reports TensorRT support and the user wants maximum throughput
- Strengths: can outperform plain CUDA on tuned workloads
- Tradeoff: more environment sensitivity and model compatibility risk
- Fallback: use `cuda` first, then `cpu`

## `cpu`

- Prefer when: GPU providers are unavailable, broken, or the task is small
- Strengths: widest compatibility, predictable fallback
- Tradeoff: slowest option for video-heavy workflows
- Fallback role: safe baseline for diagnostics and recovery

## Default selection policy

- First choice: `cuda`
- Second choice: `tensorrt` only when explicitly requested or benchmarked
- Final fallback: `cpu`
