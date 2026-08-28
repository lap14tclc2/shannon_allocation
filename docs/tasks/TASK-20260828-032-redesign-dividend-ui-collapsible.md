---
id: TASK-20260828-032
title: Redesign Dividend UI from tree hierarchy to clean collapsible card accordion
status: completed
priority: high
created: 2026-08-28
updated: 2026-08-28
tags: [dividend, frontend, ui, collapse-expand, accordion]
related: [TASK-20260828-030]
---

## Requirement

Redesign the Dividend component (`DividendTree.jsx` / `dividend-history.css`):
- Switch from multi-level nested tree branching (with tree-lines and tree-indentation) to a clean, modern collapsible / expandable card list (accordion).
- Provide clear expand/collapse headers for symbols and years.
- Render clean event cards with prominent dividend type tags, amounts/ratios, and collapsible event details.
- Preserve component contracts and existing props (`rows`, `locale`, `root`, `openLatest`).

## Context

User feedback: *"redesign lại devidend tree, tôi muốn là collapse/expand, k phải tree"*.
The previous layout had deeply indented tree branches (`.dividend-tree-children`, `.dividend-tree-events`, tree lines, bullet carets) that felt clunky and took up excessive horizontal space, especially on mobile and compact card views. A sleek collapsible accordion structure gives better clarity, readability, and modern aesthetics.

## Acceptance Criteria

- [x] Re-architect `DividendTree.jsx` into a clean collapsible accordion UI without nested tree border lines.
- [x] Support collapse/expand controls (expand all / collapse all, and per-card toggles).
- [x] Provide clear pill badges for dividend types (Tiền mặt / Cổ phiếu), dates, and amounts.
- [x] Maintain support for `SourceGroups`, `EventLeaf`, `root="symbol"`, and `root="year"` options to preserve existing page and contract tests.
- [x] Update `dividend-history.css` with clean, modern card styling, subtle transitions, and responsive mobile padding.
- [x] Run test suite to ensure contract tests and rendering pass.

## Constraints and Invariants

- Preserve contract assertions in `python/portfolio/tests/test_dividend_source_and_ui_contract.py`.
- No regression in data fields (effective date, payment date, cash/share, stock ratio, provider sources).
- Fully responsive on desktop and mobile.

## Implementation Tasks

- [x] Redesign `frontend/src/components/DividendTree.jsx` with collapsible card accordion structure.
- [x] Update `frontend/src/dividend-history.css` to replace tree indentation with modern card accordions.
- [x] Add "+ Mở rộng tất cả" / "− Thu gọn tất cả" toolbar controls.
- [x] Run automated tests (`pytest python/portfolio/tests/test_dividend_source_and_ui_contract.py`).
- [x] Verify visual presentation and document validation evidence.

## Decisions

- Retain internal sub-component identifiers (`SourceGroups`, `EventLeaf`, `dividend-tree-source`) for backward compatibility with existing test contract assertions while redesigning CSS classes and markup structure for modern card accordion appearance.

## Validation Evidence

- Ran `pytest python/portfolio/tests/test_dividend_source_and_ui_contract.py -v`: 7/7 tests passed.
- Redesigned visual hierarchy into clean cards with collapsible sub-sections, badges (`is-cash`, `is-stock`), date inline rows, and quick global expand/collapse buttons.

## Result

- Dividend UI is transformed into a modern, responsive collapsible accordion card interface on both Desktop and Mobile.

