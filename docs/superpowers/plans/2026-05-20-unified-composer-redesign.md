# Unified Composer Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Gemini-like unified input composer for the Vocab Filter Streamlit page.

**Architecture:** Keep the app as a single Streamlit entrypoint. Reuse the existing upload, text, level, and analyze state, but wrap them in a new semantic composer structure with scoped CSS.

**Tech Stack:** Python, Streamlit, Streamlit AppTest, Playwright CLI for rendered visual checks.

---

### Task 1: Lock The Composer Contract

**Files:**
- Modify: `tests/test_ui_state.py`

- [ ] **Step 1: Add a failing UI test**

Add a Streamlit AppTest assertion that the page renders a unified composer marker and no longer renders the old split input title marker.

- [ ] **Step 2: Run the targeted test**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_ui_state.LevelSettingsStateTest.test_analysis_renders_unified_composer`

Expected: FAIL because the current page does not emit the new composer marker.

### Task 2: Implement The Composer

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Replace the input heading markup**

Render a concise prompt and composer shell around the existing uploader, text area, level select, and analyze button.

- [ ] **Step 2: Scope composer styles**

Add `.vf-composer`, `.vf-composer-action-align`, `.vf-composer-toolbar-anchor`, and related styles. Keep touch targets at least 44px high, preserve visible focus states, and support mobile wrapping.

- [ ] **Step 3: Run the targeted test**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_ui_state.LevelSettingsStateTest.test_analysis_renders_unified_composer`

Expected: PASS.

### Task 3: Verify The Rendered Page

**Files:**
- Modify: none unless validation finds an issue.

- [ ] **Step 1: Smoke test the app**

Run: `.\.venv\Scripts\python.exe -m unittest discover tests`

Expected: all available unittest tests pass, or dependency gaps are reported.

- [ ] **Step 2: Capture desktop and mobile screenshots**

Run Playwright screenshots against `http://localhost:8501` with Edge channel at `1440x1000` and `390x844`.

Expected: The first screen shows one unified composer, no overlapping text, and the primary action remains visible on mobile.
