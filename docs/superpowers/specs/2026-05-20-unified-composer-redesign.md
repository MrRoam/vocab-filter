# Vocab Filter Unified Composer Redesign

## Goal

Refactor the first screen into a focused workbench where the user sees one content input, one level choice, and one analysis action.

## Approved Direction

Use the "workbench first" direction. The page should prioritize repeated use over long onboarding. The input should follow a Gemini-like composer model: file upload and pasted text are two ways to provide the same content, not two separate tasks.

## UI Decisions

- Keep the top bar minimal: brand, current level, about.
- Add a short first-screen prompt above the composer.
- Merge upload, text, level, and analyze controls into one visual composer.
- Keep explanations out of the UI. Use only short labels that help the user act.
- Show results below the composer after analysis.
- Preserve the existing Streamlit file uploader and text area behavior internally.

## Boundaries

- Do not change the vocabulary scoring pipeline.
- Do not introduce a new frontend framework.
- Do not add decorative explanation text to the production UI.
- Do not remove existing export or placement flows.
