# Multi-Actor Multi-Face Workflow

## Goal

Support a conversational agent workflow for swapping multiple roles and multiple faces across one or more target videos without forcing the user to specify every FaceFusion parameter up front.

The design principle is:

- the user describes roles, faces, and rough time ranges
- the agent builds project state
- the agent generates preview tasks first
- the agent promotes approved previews into full-resolution jobs

This avoids treating a multi-actor edit as one giant opaque run.

## Core Model

Represent each editing project as three layers:

1. cast
- who each role is
- which source assets belong to that role, such as face images or audio clips

2. shots
- which time ranges or segments exist
- which roles appear in each segment
- which operation each segment needs

3. plan
- which concrete FaceFusion tasks should run
- in what order
- with which risk level

## Project State Files

Store one project folder per editing session:

```text
<project_root>/
  cast.json
  shots.json
  plan.json
  previews/
  renders/
  manifests/
```

Recommended default root:

```text
<facefusion_root>/.multi-actor-projects/<project_id>/
```

## `cast.json` schema

```json
{
  "project_id": "movie-001",
  "target_media": [
    "D:/video/main.mp4"
  ],
  "roles": [
    {
      "role_id": "hero",
      "role_name": "Hero",
      "source_face_path": "D:/faces/hero.jpg",
      "source_audio_path": "D:/audio/hero.wav",
      "source_assets": {
        "face": "D:/faces/hero.jpg",
        "audio": "D:/audio/hero.wav"
      },
      "notes": "main male lead"
    },
    {
      "role_id": "villain",
      "role_name": "Villain",
      "source_face_path": "D:/faces/villain.jpg",
      "notes": "appears in duel scenes"
    }
  ]
}
```

Rules:

- `role_id` must be stable and machine-friendly.
- use `source_assets` to carry operation-specific inputs such as `face`, `audio`, `image`, or `video`.
- `source_face_path` remains the shorthand for the primary face asset when face swap is involved.
- if the user provides multiple candidate assets for one role, keep one active source and store alternates in `notes` or a future `variants` field.

## `shots.json` schema

```json
{
  "project_id": "movie-001",
  "shots": [
    {
      "shot_id": "s001",
      "target_path": "D:/video/main.mp4",
      "trim_start": 0.0,
      "trim_end": 12.5,
      "roles": [
        "hero"
      ],
      "operations": [
        {
          "operation_type": "face_swap",
          "roles": [
            "hero"
          ]
        },
        {
          "operation_type": "lip_sync",
          "roles": [
            "hero"
          ]
        }
      ],
      "preview_required": true,
      "risk_level": "low",
      "notes": "single close-up"
    },
    {
      "shot_id": "s002",
      "target_path": "D:/video/main.mp4",
      "trim_start": 12.5,
      "trim_end": 28.0,
      "roles": [
        "hero",
        "villain"
      ],
      "preview_required": true,
      "risk_level": "high",
      "notes": "two faces in same frame"
    }
  ]
}
```

Rules:

- each shot is a bounded time segment
- `roles` lists only the roles that must be swapped in that segment
- `operations[]` can override the default face-swap behavior and describe per-shot actions such as `lip_sync`, `face_enhance`, `background_remove`, or `frame_enhance`
- multi-role segments default to `preview_required = true`
- multi-role or crowded segments default to `risk_level = high`
- when a shot is materialized into a FaceFusion job step, any trim bounds are coerced to integer frame boundaries for CLI compatibility

## `plan.json` schema

```json
{
  "project_id": "movie-001",
  "tasks": [
    {
      "task_id": "preview-s002-hero-villain",
      "task_type": "preview",
      "shot_id": "s002",
      "operation_type": "face_swap",
      "roles": [
        "hero",
        "villain"
      ],
      "mode": "reference",
      "status": "planned",
      "output_path": "D:/project/previews/s002-preview.mp4",
      "processors": [
        "face_swapper",
        "face_enhancer"
      ],
      "execution_provider": "cuda"
    },
    {
      "task_id": "final-s002-hero-villain",
      "task_type": "final",
      "shot_id": "s002",
      "operation_type": "face_swap",
      "roles": [
        "hero",
        "villain"
      ],
      "mode": "reference",
      "status": "blocked_on_preview",
      "output_path": "D:/project/renders/s002-final.mp4",
      "processors": [
        "face_swapper",
        "face_enhancer"
      ],
      "execution_provider": "cuda"
    }
  ]
}
```

Rules:

- every high-risk shot should get a preview task before a final task
- final tasks remain blocked until preview approval
- one task may represent one shot with one or more roles if the role mapping can be kept stable
- operations that need different source asset kinds should become separate tasks
- if stability is poor, split the shot into finer-grained tasks

## Agent Conversation Flow

### Phase 1: build cast

The agent asks only for role mapping:

- how many target roles need replacement
- which source assets belong to each role
- whether any role appears only in limited scenes

Output:

- `cast.json`

### Phase 2: build shot list

The agent determines shot boundaries in one of two ways:

1. user-specified ranges
- use when the user already knows the timecodes

2. semi-automatic segmentation
- use rough scenes or candidate ranges first
- ask the user to confirm or adjust

Output:

- `shots.json`

### Phase 3: generate preview plan

The agent converts shots into preview tasks:

- single-role shots may skip preview if the user wants speed
- multi-role shots should always preview first
- long shots may be previewed with a shorter internal sample range
- lip sync usually needs one task per speaking role because it needs one source audio asset

Output:

- `plan.json`

### Phase 4: queue execution

The agent turns plan tasks into FaceFusion jobs:

- create one drafted job per project or per target file
- create one step per preview/final task
- group low-risk steps and isolate high-risk ones

Output:

- FaceFusion job queue plus updated task statuses

### Phase 5: approval loop

After preview output:

- if role mapping is correct, mark preview approved
- if faces are swapped incorrectly, adjust the shot plan rather than rerunning the entire project
- regenerate only the affected task or shot

## Task Generation Strategy

## Low-risk shots

Characteristics:

- single visible face
- stable framing
- little occlusion

Default execution:

- `face_swapper`
- optional `face_enhancer`
- standard `cuda`
- preview optional

## Medium-risk shots

Characteristics:

- multiple cuts
- partial occlusion
- moderate motion

Default execution:

- preview first
- `face_swapper`
- optional `face_enhancer`
- reference-oriented face selection when available

## High-risk shots

Characteristics:

- multiple faces in the same frame
- rapid motion
- occlusion
- crowd scenes

Default execution:

- mandatory preview
- reference mode
- explicit shot-specific notes
- isolate in separate tasks
- never bundle many high-risk shots into one blind full render

## Face Selection Strategy

For multi-role same-frame work, prefer reference-based selection.

Default policy:

- use `face-selector-mode = reference`
- create a reference binding for each role from a stable frame
- keep role-to-reference binding per shot
- do not rely on simple ordering alone for crowded or moving scenes

Fallback policy:

- if one shot is too unstable, split it into smaller sub-shots
- if two roles repeatedly cross or occlude each other, isolate the problematic range into its own task

## Recommended New MCP Tools

These sit above the existing low-level FaceFusion tools.

### `facefusion_define_cast`

Purpose:

- create or update `cast.json`

Input:

- `project_id`
- `target_media[]`
- `roles[]`

Output:

- normalized cast state

### `facefusion_plan_shots`

Purpose:

- create or update `shots.json`

Input:

- `project_id`
- `target_path`
- `shots[]` or `time_ranges[]`
- `auto_preview_policy?`

Output:

- normalized shot list

### `facefusion_build_multi_actor_plan`

Purpose:

- generate `plan.json`

Input:

- `project_id`
- `preview_mode`
- `quality_profile`

Output:

- task plan
- preview vs final split
- risk annotations

### `facefusion_materialize_multi_actor_jobs`

Purpose:

- turn `plan.json` into FaceFusion jobs and steps

Input:

- `project_id`
- `job_strategy`

Output:

- `job_id`
- created step list

## Job Strategy

Recommended default:

- one FaceFusion job per project timeline
- one step per shot task

Alternative:

- one FaceFusion job per target file
- one step per shot

Avoid:

- one single full-length command with all roles mixed together and no shot boundaries

## Preview Strategy

Preview output should be cheap and fast.

Defaults:

- shorter trim range when possible
- lower output quality
- same processors as final where possible
- same role mapping logic as final

The preview must validate identity mapping, not cinematic quality.

## Operation Profiles

Supported high-level operation types:

- `face_swap`
- `lip_sync`
- `face_enhance`
- `background_remove`
- `frame_enhance`
- `frame_colorize`
- `expression_restore`
- `face_edit`
- `age_modify`

Rules of thumb:

- `face_swap` uses role face assets and supports multi-role reference workflows.
- `lip_sync` uses role audio assets and should usually stay one speaking role per task.
- `background_remove`, `frame_enhance`, and `frame_colorize` can run without source assets.
- processor-specific flags can stay attached to the operation instead of leaking into the whole project.

## Approval And Retry Loop

Preview-first workflows need an explicit approval loop so the agent can promote only the right tasks.

Recommended status flow:

- `planned` -> ready to materialize
- `materialized` -> added to a FaceFusion job
- `approved` -> preview looked correct and matching final tasks may proceed
- `rejected` -> preview had identity issues and should not promote final tasks
- `blocked_on_preview` -> final task is waiting for preview approval
- `blocked_on_revision` -> final task is waiting for the user or agent to revise the shot
- `materialize_failed` -> the task could not be added to a FaceFusion job
- `failed` -> execution failed after materialization

Recommended tools:

### `facefusion_approve_preview`

Purpose:

- mark a preview task approved or rejected
- unlock matching final tasks when approved
- keep matching final tasks blocked when revision is needed

Input:

- `project_id`
- `task_id?`
- `shot_id?`
- `approved`
- `approval_notes?`

Output:

- updated preview task status
- affected final task statuses
- persisted `plan.json` path

### `facefusion_retry_failed_task`

Purpose:

- reset a failed or rejected task back into a runnable state
- optionally materialize the retry into a dedicated FaceFusion job

Input:

- `project_id`
- `task_id`
- `materialize_immediately?`

Output:

- updated task status
- retry count
- optional materialization result

Policy:

- retry only the affected task
- keep approved previews intact
- if the failure came from incorrect identity mapping, reject the preview first and rebuild only the impacted shot

## Failure Recovery

If a preview fails:

- do not invalidate the whole project
- mark only that task as failed
- attach failure notes to the shot or task
- reroute through troubleshooting
- use `facefusion_retry_failed_task` only after the task or shot has been revised

If a final render fails:

- preserve approved previews
- retry only failed tasks
- prefer retrying one task into a dedicated retry job instead of mutating the whole queue

## Acceptance Criteria

A multi-actor workflow is successful when:

- the user can describe roles conversationally instead of writing full CLI commands
- the agent can produce stable `cast`, `shot`, and `plan` state
- multi-role shots are previewed before final render
- failures cause local retries, not whole-project restarts
- the same project can be resumed later from stored state
