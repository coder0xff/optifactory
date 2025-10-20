# Test Framework

This directory contains a common test framework (`test-framework.js`) used by all test HTML files.

## Files

- **test-framework.js** - Common test infrastructure with:
  - `TestRunner` class for managing and displaying test results
  - Standard assertion functions (assertEquals, assertNotNull, assertTrue, etc.)
  - Graphviz rendering support for visual graph display
  - Consistent styling across all test pages

- **test-balancer.html** - Tests for the balancer system
- **test-recipes.html** - Tests for the recipe system  
- **test-economy.html** - Tests for the economy system
- **test-graphviz-builder.html** - Tests for the graphviz builder with visual graph rendering

## Usage

All test files follow the same pattern:

```javascript
import { TestRunner, injectTestStyles, assertEquals, ... } from './test-framework.js';

// Inject common styles
injectTestStyles();

// Create test runner
const runner = new TestRunner();

// Optionally initialize graphviz for rendering
await runner.initGraphviz();

// Convenience wrapper
const test = (name, fn) => runner.test(name, fn);

// Run tests
test('Test name', () => {
    assertEquals(actual, expected, 'Description');
    return 'Test passed message';
});

// For tests that generate graphs
test('Graph test', () => {
    const graph = new Digraph();
    // ... build graph ...
    return { message: 'Description', graph: graph };
});

// For tests that generate custom HTML content
test('Table test', () => {
    const tableHtml = '<table><tr><td>Data</td></tr></table>';
    return { message: 'Description', html: tableHtml };
});

// Display results
runner.displayResults();
```

## Available Assertions

- `assertEquals(actual, expected, message)` - Deep equality check
- `assertNotEquals(actual, expected, message)` - Deep inequality check
- `assertNotNull(value, message)` - Null/undefined check
- `assertNull(value, message)` - Checks for null/undefined
- `assertTrue(value, message)` - Boolean true check
- `assertFalse(value, message)` - Boolean false check
- `assertGreaterThan(value, threshold, message)` - Numeric comparison
- `assertLessThan(value, threshold, message)` - Numeric comparison
- `assertGreaterThanOrEqual(value, threshold, message)` - Numeric comparison
- `assertLessThanOrEqual(value, threshold, message)` - Numeric comparison
- `assertAlmostEqual(actual, expected, tolerance, message)` - Floating point comparison
- `assertInstanceOf(value, constructor, message)` - Type check
- `assertContains(haystack, needle, message)` - String/array contains
- `assertNotContains(haystack, needle, message)` - String/array doesn't contain
- `assertThrows(fn, message)` - Function throws error

## Graph Rendering

When `TestRunner.initGraphviz()` is called, tests can return graph objects and they will be:
1. Rendered as SVG diagrams using @hpcc-js/wasm-graphviz
2. Display the DOT source code in a collapsible section
3. Shown in an expandable "View Generated Graph" section

This is currently used by `test-graphviz-builder.html` to visually verify graph generation.

## Custom HTML Content

Tests can return custom HTML to be displayed in the results. This is useful for:
- Displaying tables of computed values
- Showing formatted output
- Adding interactive elements

Simply return an object with `message` and `html` properties:

```javascript
test('Custom output', () => {
    const html = '<div style="color: blue;">Custom content</div>';
    return { 
        message: 'Test passed with custom output',
        html: html 
    };
});
```

This is currently used by `test-economy.html` to display a table of all computed item values.

