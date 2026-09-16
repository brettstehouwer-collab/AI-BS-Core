# Goal Description

Implement a professional "Final Draft" standard paginated view for the Screenplay Editor, replacing the continuous scrolling layout. Ensure the exact placement of screenwriting elements (Action, Dialogue, Character, etc.) matches industry standards. This ensures the output of the "Book to Script" feature is reviewed and edited in a professional, paginated, and accurate format.

## Proposed Changes

### `frontend/components/ScreenplayEditor.jsx`
#### [MODIFY] ScreenplayEditor.jsx
- **Pagination Logic:** 
  - Introduce an algorithm that dynamically calculates the height/line count of each AST block to divide the script into pages (approx. 54-55 lines per page).
  - Wrap the rendering in `<div className="screenplay-page">` elements, which are styled as `8.5in` by `11in` white paper sheets with standard 1-inch top/bottom margins and a 1.5-inch left margin.
  - Add page numbers at the top right of each page (except the title page/page 1).
- **Final Draft Element Standards (CSS & Margins):**
  - **Font:** Enforce `Courier Prime` (or `Courier New`) at exactly `12pt`.
  - **Line Height:** Enforce `12pt` with `14.4px` to `16px` line spacing (6 lines per inch).
  - **Scene Heading / Action:** `max-width: 6.0in` (60 characters), left aligned.
  - **Character:** `margin-left: 2.2in` (3.7in from paper edge, so `2.2in` from the 1.5in text boundary).
  - **Dialogue:** `margin-left: 1.0in` (2.5in from edge), `max-width: 3.5in` (35 characters).
  - **Parenthetical:** `margin-left: 1.6in` (3.1in from edge), `max-width: 2.0in` (20 characters).
  - **Transition:** `margin-left: 4.0in` (5.5in from edge).
- **Editor Mechanics:**
  - Adjust the `contentEditable` blocks so they render within their respective pages seamlessly. The editor will render the entire AST, chunked into pages, so the user can scroll down through a stack of pages (like Print Layout in Google Docs).
  - Fix focus retention and `Backspace` / `Enter` logic to ensure jumping between blocks across page boundaries works smoothly.

### `frontend/components/ScreenwritingTab.jsx`
#### [MODIFY] ScreenwritingTab.jsx
- Adjust the main container backgrounds to a darker gray (e.g., `#0a0a0a` or `#1f1f1f`) so the white screenplay pages stand out clearly.
- Update the layout toggle so the preview (if active) also reflects the exact same pagination standards.

## User Review Required

> [!IMPORTANT]
> Since we are moving from a single continuous block of text to a **page-based layout**, elements that exceed the bottom of a page will automatically "push" the next block to the next page. Splitting a single long action paragraph or a long piece of dialogue perfectly across a page boundary while typing in a web browser can be very complex.
> 
> **Proposed Approach:** For this phase, we will keep blocks intact. If a block of dialogue or action doesn't fit on the current page, the *entire block* will be pushed to the next page. Is this acceptable for now, or would you like me to implement dynamic block-splitting (which adds significant complexity to the editor)?

## Open Questions

> [!WARNING]
> Do you want the editor itself (where you type) to be paginated (like Google Docs Print Layout), or do you prefer the *Preview* pane to be paginated, while the Editor remains continuous? The plan above assumes making the **Editor** paginated, giving a true WYSIWYG (What You See Is What You Get) experience.
