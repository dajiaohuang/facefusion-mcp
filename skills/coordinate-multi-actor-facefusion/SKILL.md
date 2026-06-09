---
name: coordinate-multi-actor-facefusion
description: Coordinate a conversational multi-actor FaceFusion project through the FaceFusion MCP plugin. Use when the user wants to swap multiple roles or multiple faces across one or more videos, map source faces to named roles, define shot ranges, approve previews before final renders, or retry only the affected shot instead of rerunning the entire project.
---

# Coordinate Multi-Actor Facefusion

Use this skill as the top-level router for multi-role FaceFusion projects. It should decide which phase-specific skill to use next, keep the whole project coherent, and prevent the conversation from jumping into the wrong phase.

## Workflow

1. Start by reading `../../resources/multi-actor-workflow.md`.
2. If environment readiness is unknown, call `facefusion_health_check`.
3. Decide which phase the project is currently in:
   - draft cast and shots
   - review references and bind roles
   - refine plan and preview lifecycle
4. Delegate the detailed workflow to the matching phase skill:
   - `../draft-facefusion-cast-and-shots/SKILL.md`
   - `../review-facefusion-references/SKILL.md`
   - `../refine-facefusion-plan/SKILL.md`
5. After each phase action, summarize the updated project state and either move to the next phase or stay in the current phase if details are still missing.
6. Before any preview or final swap execution, require one dedicated confirmation turn that shows the full planned configuration back to the user.

## Conversation Rules

- Keep the conversation in one phase at a time.
- Ask only the minimum blocking question for the current phase.
- Do not mix initial draft collection, reference review, and preview approval into one long turn unless the user already provided nearly everything.
- Treat `default_ui_mode` as a routing preference, not a hard requirement.
- Always produce an initial draft state before trying to collect every possible detail.
- After merge decisions and source bindings are known, do not jump straight into execution. First return the full settings for confirmation.

## Tool Rules

- Stay in the multi-actor tool family unless the user abandons the project workflow.
- Use this skill to choose the next phase skill, not to duplicate all phase-specific instructions inline.
- If the user asks for a high-level project status, summarize `cast.json`, `shots.json`, `references.json`, and `plan.json` state rather than diving into one tool call immediately.
- Before materializing or running jobs, prefer `facefusion_review_multi_actor_configuration` so the user can approve the full configuration explicitly.

## References

- `../../resources/multi-actor-workflow.md`
- `../../resources/parameter-mapping.md`
- `references/conversation-patterns.md`
