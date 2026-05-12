# DESIGN.md

## Overview

UltraDanfeXML is a single-surface operational tool focused on one dense task: processing NF-e batches with XML lookup, optional Protheus collection, boleto separation, and export organization. The UI should feel like a reliable workbench, not a marketing site and not a generic analytics dashboard.

## Visual Theme

- Register: product
- Theme direction: restrained, workbench-like, dark neutral surface with one strong blue action color and a warm amber support accent
- Mood: controlled, efficient, low-friction, audit-friendly
- Surface strategy: layered charcoal panels with a slightly cooler shell and clearly separated task surfaces

## Color Palette

Use restrained product color. Accent is reserved for primary actions, selection, and active state.

### Core

- Background: low-glare charcoal neutral
- Foreground: soft light neutral with strong contrast
- Card: slightly lifted from background, high legibility without glossy effects
- Border: quiet, visible, never invisible

### Semantic

- Primary: operational blue for primary actions and progress
- Accent: amber for highlights, guidance, and non-error emphasis
- Success: clean green for confirmed completion
- Destructive: direct red for failure and invalid states
- Muted: neutral support layer for secondary panels and metadata

### Behavioral Rules

- No decorative gradients as the main aesthetic.
- No purple bias.
- Inactive controls stay neutral.
- Status colors must stay semantic and predictable.

## Typography

- Primary stack: system sans / Segoe UI style product typography
- One family is sufficient
- Scale should be compact and task-first
- Headings should clarify structure, not dominate the surface
- Tabular and key-like data can use monospace accents sparingly

## Layout

- Use a clear task stack with explicit sections in execution order
- Favor split layouts and section headers over endless repeated cards
- Keep related controls grouped tightly
- Reserve larger spacing only between major workflow stages
- On wide screens, let status and summary information sit beside the active task when useful

## Components

- Section shells should feel consistent, with the same border, radius, and internal rhythm
- Inputs, selects, buttons, and toggles must share one coherent size vocabulary
- Progress should be visible without taking over the page
- Empty and warning states must explain what blocks the next step
- Result and audit data should prefer structured lists/tables over decorative metric cards

## Motion

- Minimal, state-driven only
- Fast transitions, around 150-200ms
- Use motion for reveal, loading, and completion feedback
- Avoid ornamental entrance choreography

## Content Style

- Portuguese, direct, concise
- Labels should describe the exact action or dependency
- Helper text only where it removes ambiguity in a high-risk step
- Error states must say what happened and what the operator should do next

## Anti-patterns

- Nested cards as default layout
- Big hero metrics for operational steps
- Decorative gradients or glow effects
- Long explanatory paragraphs above controls
- Visual hierarchy that makes secondary chrome compete with the task
