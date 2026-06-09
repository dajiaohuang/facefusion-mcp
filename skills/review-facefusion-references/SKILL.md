---
name: review-facefusion-references
description: Review and refine detected target roles for a multi-actor FaceFusion project. Use when cast.json and shots.json already exist and you need to run reference discovery, merge target clusters, bind source faces, use the reference review UI, or continue the same work in no-UI dialogue mode.
---

# Review Facefusion References

Use this skill for the role-binding and source-binding phase after the initial draft exists.

## Workflow

1. Read `../../resources/multi-actor-workflow.md`.
2. Run `facefusion_discover_role_references`.
3. If `default_ui_mode=true`, render `manifests/reference-view.html` with `facefusion_render_reference_ui` early.
4. Ask which detected clusters should merge into one final role.
5. Ask whether each merged role should keep or change the prefilled source face.
6. If some roles are still missing source images, allow them to remain unresolved temporarily when the user plans to send them later.
7. Apply resolved decisions with `facefusion_apply_reference_decisions`.

## Conversation Rules

- Do not force manual role labeling before discovery when the footage is ambiguous.
- In UI mode, use the review page but keep the conversation going.
- In no-UI mode, summarize the same state in text and continue asking merge/source questions.
- If the user is working through OpenClaw or another remote image path, treat delayed source-image arrival as a normal partial state.

## Tool Rules

- Use `facefusion_discover_role_references` before asking merge questions.
- Use `facefusion_render_reference_ui` for visual review when available or preferred.
- Use `facefusion_apply_reference_decisions` for resolved merge/source updates.
- Do not build the final plan from this skill.

## References

- `../../resources/multi-actor-workflow.md`
- `references/reference-review-patterns.md`
