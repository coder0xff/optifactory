/**
 * Simple test framework for browser-based testing
 */

// Common CSS styles for test pages
export const TEST_STYLES = `
    body {
        font-family: monospace;
        padding: 20px;
        max-width: 1200px;
        margin: 0 auto;
    }
    .test-section {
        margin: 20px 0;
        padding: 10px;
        border: 1px solid #ccc;
        background: #f5f5f5;
    }
    .test-section h3 {
        margin-top: 0;
    }
    .pass {
        color: green;
    }
    .fail {
        color: red;
    }
    pre {
        background: white;
        padding: 10px;
        overflow-x: auto;
        border: 1px solid #ddd;
    }
`;

/**
 * Test runner class
 */
export class TestRunner {
    constructor() {
        this.results = [];
        this.graphvizInstance = null;
        this.testPromises = [];
    }

    /**
     * Initialize graphviz for rendering (optional)
     */
    async initGraphviz() {
        try {
            const { Graphviz } = await import('https://cdn.jsdelivr.net/npm/@hpcc-js/wasm-graphviz@1.13.0/+esm');
            this.graphvizInstance = await Graphviz.load();
        } catch (e) {
            console.warn('Failed to load graphviz:', e);
        }
    }

    /**
     * Run a test (supports both sync and async functions)
     * Can be called with or without await
     * @param {string} name - Test name
     * @param {Function} fn - Test function that returns a result message or {message, graph, html}
     */
    test(name, fn) {
        const promise = (async () => {
            try {
                const result = await fn();
                if (result) {
                    // Check if result is an object with message and graph
                    if (typeof result === 'object' && result.message) {
                        this.results.push({ 
                            name, 
                            status: 'pass', 
                            message: result.message,
                            graph: result.graph,
                            html: result.html
                        });
                    } else {
                        this.results.push({ name, status: 'pass', message: result });
                    }
                } else {
                    this.results.push({ name, status: 'fail', message: 'Test returned false' });
                }
            } catch (e) {
                this.results.push({ name, status: 'fail', message: e.message, error: e });
            }
        })();
        
        this.testPromises.push(promise);
        return promise;
    }

    /**
     * Display results to a container element
     * Waits for all queued tests to complete before displaying
     * @param {string} containerId - ID of the container element
     */
    async displayResults(containerId = 'results') {
        // Wait for all tests to complete
        await Promise.all(this.testPromises);
        
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container element #${containerId} not found`);
            return;
        }

        let passCount = 0;
        let failCount = 0;

        // Create summary
        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'test-section';
        summaryDiv.style.cssText = 'font-size: 1.2em; padding: 20px; background: #ddd;';
        container.appendChild(summaryDiv);

        // Display each result
        for (const result of this.results) {
            const section = document.createElement('div');
            section.className = 'test-section';

            const statusClass = result.status === 'pass' ? 'pass' : 'fail';
            if (result.status === 'pass') {
                passCount++;
            } else {
                failCount++;
            }

            // Build graph display if available
            let graphDisplay = '';
            if (result.graph && result.graph.source) {
                const svgContainerId = `svg-${Math.random().toString(36).substr(2, 9)}`;
                graphDisplay = `
                    <details ${this.graphvizInstance ? 'open' : ''}>
                        <summary style="cursor: pointer; margin-top: 10px; font-weight: bold;">
                            View Generated Graph
                        </summary>
                        <div id="${svgContainerId}" style="margin-top: 10px; border: 1px solid #ddd; padding: 10px; background: white; overflow: auto;"></div>
                        <details style="margin-top: 10px;">
                            <summary style="cursor: pointer; font-weight: bold;">
                                View DOT Source
                            </summary>
                            <pre style="margin-top: 5px;">${this.escapeHtml(result.graph.source)}</pre>
                        </details>
                    </details>
                `;

                section.innerHTML = `
                    <h3 class="${statusClass}">${result.status.toUpperCase()}: ${result.name}</h3>
                    <pre>${result.message}</pre>
                    ${result.error ? `<pre style="color: red;">${result.error.stack}</pre>` : ''}
                    ${graphDisplay}
                    ${result.html ? result.html : ''}
                `;

                container.appendChild(section);

                // Render graph if graphviz is available
                if (this.graphvizInstance) {
                    try {
                        const svg = await this.graphvizInstance.layout(result.graph.source, 'svg', 'dot');
                        const svgContainer = document.getElementById(svgContainerId);
                        if (svgContainer) {
                            svgContainer.innerHTML = svg;
                        }
                    } catch (e) {
                        const svgContainer = document.getElementById(svgContainerId);
                        if (svgContainer) {
                            svgContainer.innerHTML = `<pre style="color: red;">Failed to render: ${e.message}</pre>`;
                        }
                    }
                }
            } else {
                section.innerHTML = `
                    <h3 class="${statusClass}">${result.status.toUpperCase()}: ${result.name}</h3>
                    <pre>${result.message}</pre>
                    ${result.error ? `<pre style="color: red;">${result.error.stack}</pre>` : ''}
                    ${result.html ? result.html : ''}
                `;

                container.appendChild(section);
            }
        }

        // Update summary
        summaryDiv.innerHTML = `
            <strong>Test Summary:</strong> 
            <span class="pass">${passCount} passed</span>, 
            <span class="fail">${failCount} failed</span>, 
            ${passCount + failCount} total
        `;
    }

    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ====================================================================
// Assertion Functions
// ====================================================================

export function assertEquals(actual, expected, message) {
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
        throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
    }
    return message;
}

export function assertNotEquals(actual, expected, message) {
    if (JSON.stringify(actual) === JSON.stringify(expected)) {
        throw new Error(`${message}: expected not to equal ${JSON.stringify(expected)}`);
    }
    return message;
}

export function assertNotNull(value, message) {
    if (value === null || value === undefined) {
        throw new Error(`${message}: value is null or undefined`);
    }
    return message;
}

export function assertNull(value, message) {
    if (value !== null && value !== undefined) {
        throw new Error(`${message}: expected null or undefined, got ${JSON.stringify(value)}`);
    }
    return message;
}

export function assertTrue(value, message) {
    if (!value) {
        throw new Error(`${message}: value is not true`);
    }
    return message;
}

export function assertFalse(value, message) {
    if (value) {
        throw new Error(`${message}: value is not false`);
    }
    return message;
}

export function assertGreaterThan(value, threshold, message) {
    if (value <= threshold) {
        throw new Error(`${message}: ${value} is not greater than ${threshold}`);
    }
    return message;
}

export function assertLessThan(value, threshold, message) {
    if (value >= threshold) {
        throw new Error(`${message}: ${value} is not less than ${threshold}`);
    }
    return message;
}

export function assertGreaterThanOrEqual(value, threshold, message) {
    if (value < threshold) {
        throw new Error(`${message}: ${value} is not greater than or equal to ${threshold}`);
    }
    return message;
}

export function assertLessThanOrEqual(value, threshold, message) {
    if (value > threshold) {
        throw new Error(`${message}: ${value} is not less than or equal to ${threshold}`);
    }
    return message;
}

export function assertAlmostEqual(actual, expected, tolerance, message) {
    if (Math.abs(actual - expected) > tolerance) {
        throw new Error(`${message}: expected ${expected} ± ${tolerance}, got ${actual}`);
    }
    return message;
}

export function assertInstanceOf(value, constructor, message) {
    if (!(value instanceof constructor)) {
        throw new Error(`${message}: value is not an instance of ${constructor.name}`);
    }
    return message;
}

export function assertContains(haystack, needle, message) {
    if (!haystack.includes(needle)) {
        throw new Error(`${message}: "${needle}" not found in "${haystack.substring(0, 100)}..."`);
    }
    return message;
}

export function assertNotContains(haystack, needle, message) {
    if (haystack.includes(needle)) {
        throw new Error(`${message}: "${needle}" unexpectedly found`);
    }
    return message;
}

export function assertThrows(fn, message) {
    try {
        fn();
        throw new Error(`${message}: function did not throw`);
    } catch (e) {
        if (e.message.includes('function did not throw')) {
            throw e;
        }
        // Expected to throw
        return message;
    }
}

/**
 * Helper function to inject test styles into the page
 */
export function injectTestStyles() {
    const styleElement = document.createElement('style');
    styleElement.textContent = TEST_STYLES;
    document.head.appendChild(styleElement);
}

