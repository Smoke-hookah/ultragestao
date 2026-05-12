# Frontend Rule

For any task that changes the frontend in this repository, always use the local `impeccable` skill stored at:

- `.agents/skills/impeccable`

Before editing frontend files:

1. Read `.agents/skills/impeccable/SKILL.md`.
2. Follow its required preflight and context-loading steps.
3. Apply its design, UX, and frontend quality guidance to all UI changes.

Scope:

- `frontend/src/**`
- `frontend/index.html`
- `frontend/tailwind.config.ts`
- shared frontend assets, styles, and UI components

Priority:

- Explicit user instructions override the skill.
- Existing product constraints and established UI patterns in this repo must still be preserved where applicable.
- For backend-only or non-UI tasks, the skill is not required.
