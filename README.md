# Satisgraphery

This directory contains JavaScript as self-contained HTML files using Vue.js 3.

## Files

### Application Files
- **index.html** (~90 lines) - Main application window with tabbed interface
- **economy_editor.html** (~40 lines) - Standalone economy view page
- **factory_editor.html** (~40 lines) - Standalone factory view page

### Shared Components (Zero Duplication)
- **styles.css** (~450 lines) - All CSS styles shared across all pages
- **controllers.js** (~380 lines) - Business logic controllers (EconomyController, FactoryController)
- **graphviz-viewer.js** (~120 lines) - Vue mixin for interactive graph viewing with zoom/pan
- **economy-view-component.js** (~170 lines) - Reusable Economy View component (UI + file I/O)
- **factory-view-component.js** (~350 lines) - Reusable Factory View component (UI + graphviz rendering)

## Architecture

The codebase follows a **zero-duplication** architecture using Vue.js components:

```
HTML Files (Application Entry Points)
├── index.html          → Uses both FactoryView + EconomyView components
├── factory_editor.html → Uses FactoryView component only
└── economy_editor.html → Uses EconomyView component only

Shared Components (Loaded via <script> tags)
├── styles.css                   → All CSS (no duplication)
├── controllers.js               → Business logic (pure, no UI/file I/O)
├── graphviz-viewer.js           → Vue mixin for zoom/pan
├── factory-view-component.js    → Factory view component (UI + rendering)
└── economy-view-component.js    → Economy view component (UI + file I/O)
```

**MVC Separation:**
- **Controllers** (controllers.js): Pure business logic - data structures, algorithms, state management
- **Views** (view components): UI rendering, user interactions, file I/O, browser APIs
- **Model**: Shared economy data between controllers

**Key Benefits:**
- ✅ **Zero duplication** - All HTML, CSS, and JavaScript is defined once
- ✅ **Component reuse** - Same components work standalone or in tabs
- ✅ **No build step** - Pure static HTML + JS loaded from CDN
- ✅ **Easy maintenance** - Change once, updates everywhere

## Framework

All editors use **Vue.js 3** loaded from CDN (unpkg.com), making them fully self-contained with no build step or server-side processing required beyond serving static HTML.

Vue components are defined as JavaScript objects with inline templates, allowing complete reusability without JSX or build tools.

## Usage

Open the main application in a web browser:

```bash
# Using Python's built-in server
python -m http.server 8000

# Then navigate to:
# http://localhost:8000/port/index.html
```

Or just open index.html directly in your browser (file:// protocol).

The standalone editors can also be opened individually:
- http://localhost:8000/port/economy_editor.html
- http://localhost:8000/port/factory_editor.html

## Features Ported

### Main Application Window (index.html)
- ✅ Tabbed interface (Factory and Economy tabs)
- ✅ Status bar with color-coded messages (info, warning, error)
- ✅ Shared controller state (economy data shared between tabs)
- ✅ Auto-generate factory on startup
- ✅ Welcome message on load
- ✅ Integrates both editors in single application

### Economy Editor
- ✅ Filter text box with real-time filtering
- ✅ Sortable table columns (Item, Value, Locked)
- ✅ Editable value inputs
- ✅ Pinned/locked checkboxes
- ✅ Alternating row colors
- ✅ Sort direction indicators (▲/▼)
- ✅ Button UI: Reset, Rebalance, Load CSV, Save CSV
- ⚠️ Placeholder controller with mock data

### Factory Editor
- ✅ Outputs and Inputs text areas
- ✅ Recipe search filter
- ✅ Hierarchical checkbox tree (machines > recipes)
- ✅ Tristate checkboxes for parent nodes
- ✅ Three optimization weight sliders
- ✅ Design power checkbox
- ✅ Conditional power warning display
- ✅ Generate Factory button
- ✅ Copy Graphviz to Clipboard button
- ✅ **Interactive graph viewer with zoom and pan**
- ⚠️ Placeholder controller with mock data

### Graphviz Viewer
- ✅ SVG rendering using @hpcc-js/wasm
- ✅ Mouse wheel zoom (0.35x to 2.0x range, exponential 1.1^n)
- ✅ Zoom centered on mouse cursor position
- ✅ Click-and-drag panning
- ✅ Smooth zoom transitions with CSS transforms
- ✅ Zoom percentage indicator overlay
- ✅ Status bar integration showing zoom level
- ✅ Auto-reset zoom to 100% on new graph
- ✅ Grab cursor during pan operations

## Controller Placeholders

Both files include JavaScript placeholder controller classes that mirror the Python controller APIs:

### EconomyController (JavaScript)
- `get_filter_text()` / `set_filter_text(text)`
- `get_header_texts()` - returns header labels with sort indicators
- `set_sort(column)` - handles column sorting
- `set_item_value(item_name, value)`
- `set_item_pinned(item_name, is_pinned)`
- `get_economy_table_structure()` - returns filtered and sorted table data
- `reset_to_default()` - placeholder stub
- `recompute_values()` - placeholder stub
- `load_from_csv(filepath)` - placeholder stub
- `save_to_csv(filepath)` - placeholder stub

### FactoryController (JavaScript)
- `get_outputs_text()` / `set_outputs_text(text)`
- `get_inputs_text()` / `set_inputs_text(text)`
- `get_recipe_search_text()` / `set_recipe_search_text(text)`
- `get_input_costs_weight()` / `set_input_costs_weight(value)`
- `get_machine_counts_weight()` / `set_machine_counts_weight(value)`
- `get_power_consumption_weight()` / `set_power_consumption_weight(value)`
- `get_design_power()` / `set_design_power(value)`
- `set_recipe_enabled(recipe_name, enabled)`
- `on_recipe_toggled(recipe_tree_id, is_checked)`
- `get_recipe_tree_structure()` - returns hierarchical tree data
- `should_show_power_warning()` - checks if warning should display
- `get_tooltip_for_tree_id(tree_id)` - returns tooltip text
- `generate_factory_from_state()` - returns mock graphviz diagram
- `copy_graphviz_source()` - returns graphviz source for clipboard

## Implementation Notes

### Vue.js 3 Reactivity
The editors use Vue's reactivity system to automatically update the UI when data changes, similar to Tkinter's variable tracing.

### No Build Step
All code (HTML, CSS, JavaScript) is contained in single files with Vue.js loaded from CDN. This meets the requirement of being "fully self-contained, static, and requires no additional server-side processing beside the completion of an HTML GET request."

### Mock Data
The placeholder controllers include sample mock data:
- **Economy**: 13 sample items (Iron Ore, Copper Ore, Iron Ingot, etc.)
- **Factory**: 5 mock machines with 2-3 recipes each

### File Operations
CSV operations are split between view and controller:

**View Responsibilities (economy-view-component.js):**
- Trigger file picker dialog (`<input type="file">`)
- Read file content using FileReader API
- Create and download CSV files using Blob + URL.createObjectURL
- Handle file I/O errors and user feedback

**Controller Responsibilities (controllers.js):**
- Parse CSV data into economy structure
- Generate CSV data from economy state
- Validate and transform data

This separation keeps the controller pure (testable, no side effects) while the view handles all browser/file system interactions.

### Graphviz Viewer
The factory editor includes an interactive SVG viewer that renders Graphviz DOT strings using **@hpcc-js/wasm**.

**Features:**
- Real-time SVG rendering from DOT source
- Mouse wheel zoom with exponential scaling (1.1^n per notch)
- Zoom range: 35% to 200% (matches Python's -10 to 7 exponent range)
- Zoom centered on mouse cursor position
- Click-and-drag panning with grab cursor
- CSS transform-based smooth zoom (no re-rendering needed)
- Zoom percentage overlay indicator
- Status bar shows current zoom level

**Performance:**
Unlike the Python version which uses PNG rasterization and multi-threaded rendering with LRU caching, the JavaScript version uses vector SVG rendering which is:
- Lighter weight (no image caching needed)
- Resolution independent (crisp at any zoom level)
- Faster (no background threads needed)
- Simpler implementation

The @hpcc-js/wasm library is a WebAssembly port of Graphviz that runs entirely in the browser.

## Differences from Python Version

### Simplified Components
- No `CheckboxTreeview` widget - implemented custom tree with Vue
- No `SliderSpinbox` component - implemented inline with range input + value display
- No `Tooltip` component - using CSS-only tooltips and title attributes
- `GraphvizViewer` - reusable Vue mixin with zoom/pan functionality

### Missing Python-Specific Features
- Mousewheel scrolling bindings (handled natively by browser)
- Focus management and keyboard navigation
- File dialogs (require server-side or File System Access API)

### Enhanced Features
- Responsive layout using CSS Grid
- Modern styling with hover effects and transitions
- Browser-native form controls

## Next Steps for Integration

To integrate with real backend logic:

1. **Replace mock data** in controller constructors with actual data sources
2. **Implement stub methods** (reset, rebalance, CSV operations, factory generation)
3. **Add graphviz rendering** using a library like d3-graphviz or graphviz-wasm
4. **Connect to backend API** if server-side processing is needed
5. **Add error handling** and loading states
6. **Implement file operations** using File System Access API or server endpoints

## Browser Compatibility

- Tested in modern browsers (Chrome, Firefox, Edge, Safari)
- Requires ES6+ support
- Uses modern CSS features (Grid, Flexbox, CSS variables)
- Clipboard API requires HTTPS (except localhost)

