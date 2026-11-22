# First Boot Concept Playground

This optional browser sketch preserves the HTML concept supplied by the creator on 2026-11-01. The primary project remains the custom Windows C++ AI-BS game engine and its native SDK, persistence and creator tools.

Open `first_boot_playground.html` directly in your browser, or use **Open Concept Playground (browser)** in the native AI-BS Game Engine Build workspace. The native button launches the local file through the operating system's default browser. It does not embed a browser or introduce a browser dependency into the C++ engine.

The page uses the supplied Three.js r128 script from `https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js`. Internet access and a WebGL-capable browser are required for the scene. A visible fallback explains when the renderer cannot load. No local server or package installation is required for this sketch.

The supplied scene includes motherboard traces, a GPU landmark, memory towers, movement, equipment/vehicle catalogs, garage tuning and drafted gate choices. Use W/A/S/D or the arrow keys to move; toolbar buttons open the concept menus. These are exploratory interactions, not the implemented native game's mechanics.

All displayed loads, temperatures, coolant rates, masses and diagnostic outcomes are simulated concept values. This page does not read real hardware telemetry, use native checkpoints, or persist Adam's memory. Reloading resets the sketch. The dialogue is authored game dialogue, not historical quotation. Equipment values and named encounters remain concept proposals rather than final balance or new source-story facts.

Changes to the supplied HTML are limited to the visible concept-status notice, renderer-load/error fallback and positioning the existing HUD below that notice. The original gameplay script and pinned CDN version are retained. The renderer is loaded after the explanatory notice so an offline failure still leaves a readable page.

Verification: extracted inline JavaScript is checked with `node --check`; native tests verify the button label, resolved local path, enabled/disabled state and signal connection without launching a browser. These checks do not claim browser/WebGL rendering or native save interoperability.
