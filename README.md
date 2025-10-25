# Optifactory

A web-based factory planning tool for Satisfactory. Design mathematically optimal production chains in seconds, and visualize factory networks with interactive diagrams.

## Overview

Optifactory helps you plan Satisfactory factories by:
- Computing relative item values based on recipe interconnections
- Uses industrial-grade linear programming to guarantee the best factory design for your goals (minimize costs, machines, or power)
- Designing balancer networks with splitters and mergers
- Generating interactive factory visualizations

Instead of trial-and-error, Optifactory calculates provably optimal solutions in seconds.

## Application Files

- **index.html** - Main application with tabbed interface (Factory + Economy editors)
- **economy_editor.html** - Standalone economy editor
- **factory_editor.html** - Standalone factory designer

## Architecture

The application uses a clean MVC architecture with Vue.js 3 for the UI:

```
Business Logic (Pure JavaScript)
├── economy.js              → Item value computation
├── factory.js              → Factory network design
├── recipes.js              → Satisfactory recipe data
├── balancer.js             → Splitter/merger balancing
├── optimize.js             → Linear programming optimization
├── lp-solver.js            → HiGHS LP solver interface
├── economy-controller.js   → Economy editing state management
├── factory-controller.js   → Factory design state management
├── graphviz-builder.js     → Graphviz diagram construction
└── parsing-utils.js        → Text parsing utilities

UI Components (Vue.js 3)
├── economy-editor.js       → Economy table view component
├── factory-editor.js       → Factory design view component
└── graphviz-viewer.js      → Interactive graph viewer with zoom/pan

Data Files
├── recipes-data.js         → Satisfactory recipes database
├── fluids-data.js          → Fluid colors and properties
└── loads-data.js           → Machine power consumption

Styling
└── styles.css              → All CSS styles
```

**Key Benefits:**
- ✅ **Zero duplication** - Components defined once, reused everywhere
- ✅ **No build step** - Pure static HTML + JavaScript
- ✅ **Testable** - Business logic separated from UI
- ✅ **Fast** - Runs entirely in the browser with WebAssembly

## Business Logic Components

### Economy System (`economy.js`)

Computes relative item values based on recipe interconnections using an iterative convergence algorithm.

**Key Features:**
- Separates recipes into disconnected economies using Tarjan's strongly connected components algorithm
- Iterative value convergence with adaptive temperature control
- Supports pinned values (fixed item values that don't change during computation)
- Handles cycles and complex recipe dependencies
- Exports/imports economy data as CSV

**Main Functions:**
- `compute_item_values(recipes, pinnedValues)` - compute values for all items
- `separate_economies(recipes)` - split recipes into disconnected economies
- `get_default_economy()` - get default computed values for all items
- `economy_to_csv()` / `economy_from_csv()` - serialize/deserialize economy data

**Algorithm:**
1. Collects all parts from recipes
2. Separates into strongly connected components (economies)
3. For each economy, iteratively converges values:
   - Computes instantaneous values from producers/consumers
   - Interpolates with current values using temperature
   - Adjusts temperature based on error/change trends
   - Relaxes values by processing in rank order
4. Normalizes final values to minimum of 1.0

### Factory Design System (`factory.js`)

Designs complete factory networks with machines and material routing.

**Key Features:**
- Calls linear programming optimizer to determine required machines
- Builds Graphviz visualization of entire factory network
- Creates balancer networks for material routing
- Handles fluids and solids with appropriate belt/pipe marks
- Supports mining nodes and input/output conveyors
- Generates stripe-coded edges based on flow rates

**Main Function:**
- `design_factory(outputs, inputs, mines, ...)` - design complete factory

**Process:**
1. Calculates required machines using LP optimizer
2. Builds Graphviz diagram with:
   - Input nodes (user inputs and mines)
   - Machine clusters (grouped by type/recipe)
   - Output nodes (requested outputs and byproducts)
3. Routes materials using balancer networks
4. Colors edges by conveyor/pipeline mark based on flow rate

### Balancer Networks (`balancer.js`)

Designs splitter/merger networks to route materials between sources and sinks.

**Key Features:**
- Greedy flow assignment algorithm
- Generates splitters (1→3) and mergers (3→1)
- Optimizes for minimal splitter/merger count
- Produces Graphviz diagram of balancer network

**Main Function:**
- `design_balancer(inputs, outputs)` - create balancer network

**Algorithm:**
1. Assigns flows greedily from inputs to outputs
2. Detects splitter insertion points (1 input → multiple outputs)
3. Detects merger insertion points (multiple inputs → 1 output)
4. Recursively designs sub-balancers
5. Generates Graphviz diagram with flow labels

### Linear Programming Optimization (`optimize.js`, `lp-solver.js`)

Finds optimal recipe combinations to minimize costs while meeting production requirements using mixed-integer linear programming.

**Key Features:**
- Generates LP problems in CPLEX format
- Uses HiGHS solver (WebAssembly)
- Optimizes multiple objectives:
  - Input material costs (based on economy values)
  - Machine counts
  - Power consumption
- Supports recipe enablement filtering
- Handles material balance constraints

**Main Function:**
- `optimize_recipes(inputs, outputs, options)` - find optimal recipe mix

**LP Model:**
- **Variables:** Recipe instance counts (integers)
- **Objective:** Weighted sum of input costs, machine counts, and power
- **Constraints:**
  - Material balance: production ≥ requirements
  - Non-negativity: all variables ≥ 0
  - Recipe enablement: disabled recipes forced to 0

### Recipe Database (`recipes.js`)

Contains all Satisfactory game data:
- Recipe inputs/outputs and machines
- Mining rates for different purities
- Conveyor and pipeline capacities
- Fluid colors for visualization
- Machine power consumption

**Data Organization:**
- By machine type (for UI tree structure)
- By output material (for reverse lookup)
- By recipe name (for optimization)

### Controllers (`economy-controller.js`, `factory-controller.js`)

Stateful controllers managing UI state and business logic interaction.

**EconomyController:**
- Manages economy data, pinned items, filtering, and sorting
- Provides table structure for UI rendering
- Handles CSV import/export
- Triggers recomputation with pinned values

**FactoryController:**
- Manages factory configuration (outputs, inputs, optimization weights)
- Maintains recipe enablement state
- Provides recipe tree structure for UI
- Validates configuration before generation
- Caches generated factory for export

## Usage

Open the main application in a web browser:

```bash
# Using Python's built-in server
python -m http.server 8000

# Then navigate to:
# http://localhost:8000/index.html
```

Or just open `index.html` directly in your browser (file:// protocol).

## Features

- **Economy Editor:** Compute and adjust item values, pin specific values, export/import CSV
- **Factory Designer:** Design production chains, select recipes, optimize for cost/machines/power
- **Interactive Visualization:** Zoom, pan, and explore factory network diagrams
- **Balancer Generation:** Automatic splitter/merger networks for material routing
- **No Backend Required:** Everything runs in the browser with WebAssembly

## Technical Details

**Dependencies:**
- Vue.js 3 (loaded from CDN)
- @hpcc-js/wasm (Graphviz rendering)
- HiGHS WebAssembly (LP solver)

**Browser Compatibility:**
- Modern browsers (Chrome, Firefox, Edge, Safari)
- ES6+ modules support
- WebAssembly support
- Clipboard API (requires HTTPS except on localhost)

**Performance:**
- Economy computation: ~1-2 seconds for full recipe database
- LP optimization: sub-second for typical factories
- Graphviz rendering: instant with SVG (no rasterization)
- All computation runs client-side with no server required

