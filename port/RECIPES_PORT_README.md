# Recipe System JavaScript Port

This directory contains a JavaScript port of the Python `recipes.py` module.

## Files

### Data Files (require manual population)
- **`recipes-data.js`** - Recipe definitions (paste `recipes.json` content)
- **`loads-data.js`** - Machine power consumption (paste `loads.json` content)
- **`fluids-data.js`** - Fluid color mappings (paste `fluids.json` content)

### Code Files
- **`recipes.js`** - Main recipe system implementation
- **`test-recipes.html`** - Test suite to verify the port

## Setup Instructions

1. Open each data file (`recipes-data.js`, `loads-data.js`, `fluids-data.js`)
2. Copy the corresponding JSON file contents from the project root
3. Paste the JSON data into the placeholder locations in each file
4. Open `test-recipes.html` in a browser to verify everything works

## API

The JavaScript port maintains the same API as the Python version:

### Constants
- `Purity.IMPURE`, `Purity.NORMAL`, `Purity.PURE` - resource node purity levels

### Functions
- `get_conveyor_rate(speed)` - conveyor belt capacity
- `get_mining_rate(mark, purity)` - miner extraction rate
- `get_water_extraction_rate()` - water extractor rate
- `get_oil_extraction_rate(purity)` - oil extractor rate
- `get_load(machine)` - machine power consumption
- `get_all_recipes()` - all recipes by name
- `get_all_recipes_by_machine()` - recipes grouped by machine
- `get_recipes_for(output, enablement_set)` - recipes producing an output
- `get_recipe_for(output, enablement_set)` - best recipe for an output
- `find_recipe_name(recipe)` - get name from Recipe object
- `get_base_parts()` - raw materials with no recipe
- `get_terminal_parts()` - end products not consumed
- `get_default_enablement_set()` - default enabled recipes
- `get_fluids()` - all fluid names
- `get_fluid_color(fluid)` - hex color for a fluid

### Classes
- `Recipe` - represents a recipe with machine, inputs, and outputs

## Testing

Open `test-recipes.html` in a web browser to run the test suite. All tests should pass if the data files are correctly populated.

## Integration

The files are loaded in `index.html` in this order:
1. `recipes-data.js`
2. `loads-data.js`
3. `fluids-data.js`
4. `recipes.js`
5. Other application files

