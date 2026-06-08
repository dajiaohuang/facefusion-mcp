# Multi-Actor Conversation Patterns

## Goal

Drive a complex FaceFusion project by gathering only the next missing piece of information.

The environment may prefer UI mode by default. Regardless of UI preference, generate an initial draft state after the first prompt and then keep refining it until the missing details are filled.

## Phase Order

1. Source candidates
2. Shots
3. Reference discovery and merge
4. Shot-level optional operations
5. Plan
6. Preview approval
7. Retry or final promotion

Do not ask ahead for details that belong to later phases unless the user already volunteered them.

## Phase 1: Source candidates

Ask for:

- the source face file for each known target face the user wants to swap in
- the target media file or files

Good prompt shape:

- "List the face images you want available as source candidates, and tell me the target video or videos."

Completion signal:

- every source candidate has a stable id
- every source candidate has one active `source_face_path`
- if the user gave only partial information, still produce the initial draft state and continue with follow-up questions

## Phase 2: Shots

Ask for:

- which time ranges or segments exist
- which operation each segment needs, such as face swap, lip sync, enhancement, or background removal
- whether any segment is crowded or risky
- if the user already knows exact target roles in a shot, capture them; otherwise leave roles unresolved for the next phase

Good prompt shape:

- "Give me the time ranges you want to process. Rough ranges are fine for the first pass. If you do not know the target roles yet, I can detect and group them after the shot split."

Completion signal:

- each shot has `shot_id`, target path, and either explicit `operations[]` or an unresolved placeholder for later role assignment
- if the environment is in UI mode, this is usually enough to render the first review UI

## Phase 3: Reference discovery and merge

Use `facefusion_discover_role_references` after shots exist and before final planning when target roles are not already cleanly labeled.

What to return to the user:

- how many distinct target-face clusters were detected
- which shots each cluster appears in
- which source role was prefilled for each cluster, if any
- which clusters look like they may belong to the same final role

Good prompt shape:

- "I detected 3 target-face clusters across the original footage. Cluster 1 is prefilled with `kobe`, cluster 2 with `zxf`, and cluster 3 has no source yet. Should any of these clusters be merged into one final role?"

Then ask:

- "For each merged role, keep the prefilled source face or switch to another source face?"
- "For the unfilled cluster, which source face should I use? If you have not sent it yet, send it next and I will attach it without rerunning discovery."

Completion signal:

- every final target role has one or more cluster ids
- every final target role either has a source face assigned or is explicitly marked waiting for source input
- `facefusion_apply_reference_decisions` has been called for the resolved roles
- in UI mode, render the reference review page and continue the conversation from there
- in no-UI mode, summarize the same draft state in text and keep asking merge/source questions

## Phase 4: Shot-level optional operations

Default policy:

- keep these off unless the user explicitly wants them
- common optional additions are `lip_sync`, `face_enhance`, `frame_enhance`, `background_remove`, `expression_restore`, `face_edit`, `age_modify`, and `frame_colorize`
- if the user says "apply to every shot", treat it as a batch shot-operation decision

Good prompt shape:

- "Do any of these shots also need optional pipeline steps like lip sync, face repair, frame enhancement, or background removal? By default I leave them off."

Completion signal:

- the selected extra operations are captured per shot
- `facefusion_apply_shot_operation_decisions` has been called when the user asked for any

## Phase 5: Plan

Default policy:

- single-role stable shots can move faster
- multi-role shots should preview first
- crowded same-frame shots should stay isolated
- lip sync should usually bind one role to one source audio asset per task
- global processors like background removal or frame enhancement can stay role-free

What to tell the user:

- preview tasks will be created before final tasks for risky shots
- final tasks stay blocked until preview approval

Good prompt shape:

- "I have mapped the detected clusters into final roles and can now build the preview-first execution plan."

In UI mode:

- render the plan review page after the initial plan draft
- keep asking for the missing details instead of assuming the HTML page replaces the conversation

In no-UI mode:

- summarize the draft plan in text
- continue asking follow-up questions until the plan is fully specified

## Phase 6: Preview Approval

When preview outputs exist:

- summarize preview task ids and their matching final tasks
- ask whether each preview is approved or rejected
- call `facefusion_approve_preview`

Good prompt shape:

- "Preview `preview-s002` is ready. Should I approve it and unlock `final-s002`, or keep it blocked for revision?"

## Phase 7: Retry

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
- If the user provided hints such as "use kobe and zxf on this 2-person clip", reuse those names as prefill hints during reference discovery.
- If the user is sending source images from OpenClaw or another remote agent, separate the questions clearly:
  - "Which detected target roles should merge?"
  - "Which merged roles already have a source face?"
  - "Which merged roles are still waiting for you to send a source face?"
