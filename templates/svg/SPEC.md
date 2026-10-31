# Animated Sidebar SVG Specification

## Overview

`templates/svg/` contains standalone animated SVG icons for the Subreply sidebar (`templates/sidebar.html`). When a sidebar link is selected (`.sidebar a.on`) or has active notifications (`.sidebar a.red`), Jinja2 conditionally includes the corresponding animated SVG via `{% include "svg/<id>.svg" %}` (resolved through `FileSystemLoader(['templates'])` in `app/jinja.py`).

## File Naming & Heroicons Synchronization

1. **Path ID Mapping**: Every animated SVG filename in `templates/svg/` matches the exact `<path id="...">` attribute from `templates/sidebar.html` (`templates/svg/<id>.svg`).
2. **Heroicons Upstream Updates**: New versions of static icons in `templates/sidebar.html` will be fetched automatically based on their `<path id="...">` identifiers from [heroicons.com](https://heroicons.com) (24x24 outline set).
3. **Regeneration Requirement**: Whenever new versions of static icons are fetched from `heroicons.com` and updated in `templates/sidebar.html`, the corresponding animated SVG files in `templates/svg/` **must** be updated or regenerated from the new Heroicons `<path d="...">` geometry so their resting frame (`t = 0` and `t = 0.5..1.0`) matches the static icon exactly.

## Theme & Styling Constraints

- **CSS-Only Colors**: Animated SVGs must **never** define `stroke`, `fill`, or color values on `<svg>`, `<path>`, `<animate>`, or `<animateTransform>` elements. All colors are inherited strictly from the CSS theme in `static/style.sass` (`var(--black)` by default, `var(--white)` when `.sidebar a.on`, and `var(--alert)` when `.sidebar a.red`, adapting automatically to light and dark color schemes).
- **`<path>`-Only Geometry**: Because `static/style.sass` scopes stroke and fill rules to `svg path` and `.sidebar a.on svg path`, all graphical shapes inside each animated SVG must use `<path>` elements (never `<circle>`, `<rect>`, `<line>`, or `<polyline>`).
- **Root SVG Attributes**:
  ```xml
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" overflow="visible">
  ```
  `overflow="visible"` prevents spring overshoots from clipping against the `24x24` viewBox while staying within the `.sidebar svg` `2px` padding box.
- **Preserved Primary ID**: The primary `<path>` in each animated SVG retains `id="<icon-id>"` matching its filename.

## Timing, Loop & Spring Physics

All animations use native SVG SMIL (`<animate>` and `<animateTransform>`) with cubic-bezier spline interpolation (`calcMode="spline"`):

- **Total Cycle Duration (`dur`)**: `1.6s` (`repeatCount="indefinite"`).
- **Equal Active & Pause Duration**:
  - **Active Animation Phase (`0.0 -> 0.5`, `0.8s`)**: Multi-keyframe damped spring motion with a fast initial impulse, primary overshoot, opposite rebound (undershoot), micro-settle, and return to exact resting coordinates at `keyTimes = 0.5`.
  - **Pause Phase (`0.5 -> 1.0`, `0.8s`)**: Holds the exact static resting state for `0.8s`—the same duration as the active animation itself.
- **Canonical Spring Keyframe Profile**:
  - `keyTimes`: `0;0.14;0.28;0.4;0.5;1` (staggered sub-paths vary peak/rebound times within `0..0.5` while always settling by `0.5` and holding through `1`).
  - `keySplines`: `0.2 0.8 0.2 1;0.4 0 0.2 1;0.4 0 0.2 1;0.4 0 0.2 1;0 0 1 1`
    - Segment 1 (`0.2 0.8 0.2 1`): Snappy impulse out to peak spring overshoot.
    - Segments 2–4 (`0.4 0 0.2 1`): Smooth harmonic rebound and damped settle back to rest.
    - Segment 5 (`0 0 1 1`): Stationary pause for the second half of the cycle.

## Per-Icon Motion Specifications

Each of the 18 sidebar icons has a distinct motion tailored to its visual metaphor:

| Filename (`templates/svg/`) | Sidebar Item | Motion Description |
| :--- | :--- | :--- |
| `bolt.svg` | Feed | **Electric Strike**: High-voltage radial stretch (`1.14x` / `1.18y`) and counter-clockwise snap (`-12deg` around `12, 12`), rebounding (`0.93x`, `+6deg`) before settling. |
| `bars-arrow-up.svg` | Following | **Ascending Sort Cascade**: Upward arrow launches (`dy = -2.75`) with spring rebound while the three horizontal bars ripple in width from bottom (`y = 13.5`) to top (`y = 4.5`). |
| `bars-arrow-down.svg` | Followers | **Incoming Drop & Wave**: Downward arrow drops (`dy = +2.75`) and rebounds while the three horizontal bars dip vertically in a top-to-bottom impact wave. |
| `at-symbol.svg` | Mentions | **Spiral Wind-Up & Pulse**: Outer `@` tail whips counter-clockwise (`-22deg` -> `+9deg` around `12, 12`) while the inner loop (`r = 4.5`) pulses outward (`r = 5.35`) and rebounds. |
| `chat-bubble-bottom-center-text.svg` | Messages (Thread) | **Bubble Hop & Typewriter Lines**: Center-tailed bubble pops upward (`dy = -1.5`) while the two text lines retract and spring-extend left-to-right with staggered overshoot. |
| `chat-bubble-left-ellipsis.svg` | Messages (Empty Thread) | **Mexican-Wave Typing Dots**: The three ellipsis dots (`x = 8.25, 12, 15.75`) jump vertically (`dy = -2.4`) in a staggered left-to-right wave inside a gently shifting bubble. |
| `chat-bubble-left.svg` | Messages (List) | **Tail-Anchored Wag**: Pivoting around its bottom-left tail tip (`8.25, 21`), the chat bubble flicks upward (`-11deg`), rebounds (`+5deg`, `-2deg`), and settles. |
| `arrow-uturn-left.svg` | Replies | **Slingshot U-Turn Snapback**: Left chevron and U-turn arch lunge leftward (`dx = -2`) as the top stem stretches (`x = 1..15`), then recoil right (`+1.2`) and settle. |
| `bookmark.svg` | Saved | **Ribbon Pull & Notch Snap**: Anchored at the top bar, the ribbon stretches down (`y = 22.8`) then snaps upward (`y = 19.6`) as the center V-notch deepens (`y = 15.6`) and settles. |
| `user-circle.svg` | Profile | **Portrait Nod & Follow-Through**: Inside the static outer ring, the avatar head bobs upward (`dy = -1.8`) followed by a delayed elastic rise of the shoulder arc. |
| `adjustments-horizontal.svg` | Options | **Opposing Fader Sliders**: The three circular knobs (`y = 6, 12, 18`) slide horizontally in alternating directions (`+5.5`, `-5.5`, `+4.5`) while their left/right track segments morph in lockstep. |
| `information-circle.svg` | About | **Inquisitive "i" Hop**: Inside the circle, the top dot launches upward (`dy = -2.4`) ahead of the lower stem (`dy = -1.3`), rebounding in a playful two-part bounce. |
| `lock-closed.svg` | Login | **Shackle Pop & Padlock Jiggle**: The top U-shackle pops upward (`dy = -2.4`) and clasps back down, triggering a rotational jiggle (`-7deg` -> `+5deg` around `12, 16`) of the lock body. |
| `receipt-refund.svg` | Recover | **Receipt Feed & Refund Rewind**: The jagged receipt slips downward (`dy = +1.2`) while the inner refund arrow springs leftward (`dx = -1.8`) to emphasize reversal. |
| `clipboard-document-check.svg` | Register | **Clip Press & Checkmark Draw-Pop**: The top clipboard clip lifts (`dy = -1.2`) while the checkmark draws via `stroke-dashoffset` and pops outward in scale before settling. |
| `users.svg` | People | **Alternating Duet Bounce**: The foreground user hops upward first (`t = 0.12`, `dy = -1.8`), followed by the background user hopping up-right (`t = 0.18`, `dx = +0.4, dy = -2.1`). |
| `arrow-trending-up.svg` | Trending | **Bullish Breakout Surge**: The zig-zag trend line surges diagonally up-right (`+1.5, -1.5`) while the arrowhead leads with a larger spring lunge (`+2.1, -2.1`). |
| `globe-alt.svg` | Discover | **3D Longitude Spin & Axial Tilt**: Inner meridian curves morph asymmetrically (`rx = 4.5 -> 6.6 / 2.1 -> 3.3 / 5.7`) to simulate 3D longitudinal rotation while the globe tilts (`+12deg` -> `-5deg`). |
