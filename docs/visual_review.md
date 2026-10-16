# Visual and interaction review

Actual screenshots under screenshots/ show the working local application with synthetic data. No generated mock screen is used.

Web viewports:1440×900,1280×720,390×844 logical pixels. Full-page captures can exceed viewport height. Installed desktop requested1366×768 outer bounds; Windows rounding/title bars and host display scaling affect content/pixel dimensions.

Required states:

1. Intake: 01-intake-1440.png.
2. Critical review: 02-critical-review-1440.png.
3. Exposure: 03-exposure-1440.png,07-exposure-1280.png,08-exposure-mobile-390.png.
4. Revision/stale: 04-stale-revision-1440.png,05-revision-diff-1440.png.
5. Receipt: 06-receipt-1440.png.
6. Installed offline report: 13-installed-desktop-offline.png.

Concrete fixes: moved comparison totals above the graph; replaced tiny mobile SVG labels with readable stock/path controls; moved inspector to a drawer at 1280; preserved full source IDs/quoted passages; retained context during structured stale/policy errors.

Agent review only. No independent five-second comprehension test occurred.

|Dimension|Internal score /5|Observation|
|---|---:|---|
|Clarity|4|Data-derived hold total and explicit fixture/uncertainty labels|
|Hierarchy|4|Incident, comparison, navy map and decision controls|
|Spacing|4|Consistent panels, drawer and mobile tabs|
|Density|3|Smaller windows require vertical scrolling|
|Feedback|4|Exact sources and actual conflict responses|
|Craft|4|Shared palette, system typography, stable positions, reduced motion|

These are review aids, not official judging or accessibility scores. Known limits: large imported event graphs may need internal scrolling/table view. At short heights, sticky decision controls can overlay content while scrolling; all rows remain reachable. Installed tests also passed Chromium device-scale overrides of1.0 and1.25 with no horizontal overflow. OS display settings were unchanged; physical OS scaling changes and independent reviewer responses remain unverified.

Keyboard controls have visible focus; stock nodes accept Enter/Space. Browser checks found no horizontal page overflow at 1280/390. This is not a formal WCAG audit.
