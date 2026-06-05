# Multi-Actor Conversation Patterns

## Goal

Drive a complex FaceFusion project by gathering only the next missing piece of information.

## Phase Order

1. Cast
2. Shots
3. Plan
4. Preview approval
5. Retry or final promotion

Do not ask ahead for details that belong to later phases unless the user already volunteered them.

## Phase 1: Cast

Ask for:

- the role names
- the source face file for each role
- the target media file or files

Good prompt shape:

- "List each role you want replaced and the face image that should represent it."

Completion signal:

- every role has a stable `role_id`
- every role has one active `source_face_path`

## Phase 2: Shots

Ask for:

- which time ranges or segments need swaps
- which roles appear in each segment
- which operation each segment needs, such as face swap, lip sync, enhancement, or background removal
- whether any segment is crowded or risky

Good prompt shape:

- "Give me the time ranges and which roles appear in each one; rough ranges are fine for the first pass."

Completion signal:

- each shot has `shot_id`, target path, and either default face-swap behavior or explicit `operations[]`

## Phase 3: Plan

Default policy:

- single-role stable shots can move faster
- multi-role shots should preview first
- crowded same-frame shots should stay isolated
- lip sync should usually bind one role to one source audio asset per task
- global processors like background removal or frame enhancement can stay role-free

What to tell the user:

- preview tasks will be created before final tasks for risky shots
- final tasks stay blocked until preview approval

## Phase 4: Preview Approval

When preview outputs exist:

- summarize preview task ids and their matching final tasks
- ask whether each preview is approved or rejected
- call `facefusion_approve_preview`

Good prompt shape:

- "Preview `preview-s002` is ready. Should I approve it and unlock `final-s002`, or keep it blocked for revision?"

## Phase 5: Retry

Use `facefusion_retry_failed_task` when:

- one task failed to materialize
- one preview was rejected and is ready for a targeted retry
- one final render failed but the surrounding plan is still valid

Good prompt shape:

- "Only `preview-s002` needs another pass. I can retry just that task instead of rebuilding the whole queue."

## User Experience Rules

- Prefer concise summaries over raw JSON dumps.
- Reflect the current project state after each tool call.
- If the user is unsure about exact timecodes, help them build shots first instead of blocking on precision.
- If the user gives enough structure in one message, skip straight to the next missing phase.
