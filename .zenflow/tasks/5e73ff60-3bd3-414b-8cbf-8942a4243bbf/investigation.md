# Investigation: Cleanup playoff_dashboard.html

## Bug Summary
The `docs/playoff_dashboard.html` file is a large, monolithic file with many inline styles, manual HTML string concatenation in JavaScript, and inconsistent language (English/Russian mix). Additionally, the "Team Stats Comparison" in the modal does not match the desired design as seen in the provided reference image.

## Root Cause Analysis
- **Monolithic File**: CSS, HTML, and JS are all in one file, making it hard to maintain.
- **Inline Styles**: Many styles are applied directly in JS, which makes it difficult to change the look and feel from the CSS section.
- **Manual HTML Concatenation**: The `openModal` function builds large HTML strings, which is error-prone and hard to read.
- **Inconsistent Language**: Some UI elements use Russian text while others use English.
- **Design Mismatch**: The current "Team Stats Comparison" uses a grid of cards, while the design in `f3697471-172d-4ed6-97bb-5ebe1246541d.png` shows horizontal bars with a central label.

## Affected Components
- `docs/playoff_dashboard.html` (CSS, HTML, JS)

## Proposed Solution
1. **Move inline styles to CSS**: Identify all `style="..."` in the script and move them to the `<style>` block.
2. **Translate UI strings**: Change Russian text (e.g., "Аналитика матча") to English for consistency.
3. **Refactor "Team Stats Comparison"**: Implement the new design with horizontal bars as seen in the image.
4. **Refactor rendering logic**: Break down `openModal` into smaller, reusable rendering functions.
5. **Clean up voting logic**: Ensure consistent handling of votes between local storage and the external JSONBin service.
6. **Improve responsiveness**: Ensure the new stats comparison layout works well on mobile.
