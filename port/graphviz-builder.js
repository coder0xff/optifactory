/**
 * Simple Graphviz DOT language builder
 * Generates DOT strings for directed graphs without external dependencies
 */

/**
 * Subgraph class for creating graph clusters and subgraphs
 */
class Subgraph {
    constructor(name, parent = null) {
        this.name = name;
        this.parent = parent;
        this.nodes = [];
        this.edges = [];
        this.subgraphs = [];
        this.graphAttrs = {};
    }

    /**
     * Add a node to this subgraph.
     * @param {string} id - node identifier
     * @param {string} label - node label (can be empty string)
     * @param {Object} attrs - node attributes
     */
    node(id, label, attrs = {}) {
        this.nodes.push({ id, label, ...attrs });
    }

    /**
     * Add an edge to this subgraph.
     * @param {string} fromId - source node ID
     * @param {string} toId - target node ID
     * @param {Object} attrs - edge attributes
     */
    edge(fromId, toId, attrs = {}) {
        this.edges.push({ from: fromId, to: toId, ...attrs });
    }

    /**
     * Set subgraph attributes.
     * @param {Object|string} keyOrAttrs - attribute key or object of attributes
     * @param {*} value - attribute value (if first param is string)
     */
    attr(keyOrAttrs, value) {
        if (typeof keyOrAttrs === 'string') {
            this.graphAttrs[keyOrAttrs] = value;
        } else {
            Object.assign(this.graphAttrs, keyOrAttrs);
        }
    }

    /**
     * Create a nested subgraph.
     * @param {string} name - subgraph name
     * @param {Function} callback - function to build subgraph content
     * @returns {Subgraph} the created subgraph
     */
    subgraph(name, callback) {
        const sub = new Subgraph(name, this);
        this.subgraphs.push(sub);
        if (callback) {
            callback(sub);
        }
        return sub;
    }

    /**
     * Generate DOT string for this subgraph.
     * @param {string} indent - indentation string
     * @returns {string} DOT representation
     */
    _toDot(indent = '  ') {
        let output = `${indent}subgraph ${this.name} {\n`;
        const innerIndent = indent + '  ';
        
        // Add subgraph attributes
        for (const [key, value] of Object.entries(this.graphAttrs)) {
            // Quote string values
            const formattedValue = typeof value === 'string' ? `"${value}"` : value;
            output += `${innerIndent}${key}=${formattedValue}\n`;
        }
        
        // Add nodes
        for (const node of this.nodes) {
            output += this._formatNode(node, innerIndent);
        }
        
        // Add nested subgraphs
        for (const sub of this.subgraphs) {
            output += sub._toDot(innerIndent);
        }
        
        // Add edges
        for (const edge of this.edges) {
            output += this._formatEdge(edge, innerIndent);
        }
        
        output += `${indent}}\n`;
        return output;
    }

    _formatNode(node, indent) {
        const attrs = [];
        if (node.label !== undefined && node.label !== '') {
            attrs.push(`label="${node.label}"`);
        }
        if (node.shape) attrs.push(`shape=${node.shape}`);
        if (node.style) attrs.push(`style=${node.style}`);
        if (node.fillcolor) attrs.push(`fillcolor=${node.fillcolor}`);
        if (node.color) attrs.push(`color=${node.color}`);
        
        const attrStr = attrs.length > 0 ? ` [${attrs.join(', ')}]` : '';
        return `${indent}${node.id}${attrStr}\n`;
    }

    _formatEdge(edge, indent) {
        const attrs = [];
        if (edge.label !== undefined) {
            // Quote string labels
            const formattedLabel = typeof edge.label === 'string' ? `"${edge.label}"` : edge.label;
            attrs.push(`label=${formattedLabel}`);
        }
        if (edge.color) attrs.push(`color="${edge.color}"`);
        if (edge.style) attrs.push(`style="${edge.style}"`);
        if (edge.penwidth) attrs.push(`penwidth="${edge.penwidth}"`);
        
        const attrStr = attrs.length > 0 ? ` [${attrs.join(', ')}]` : '';
        return `${indent}${edge.from} -> ${edge.to}${attrStr}\n`;
    }
}

/**
 * Digraph class for building directed graphs in DOT format
 */
class Digraph {
    constructor(name = 'G') {
        this.name = name;
        this.nodes = [];
        this.edges = [];
        this.subgraphs = [];
        this.graphAttrs = {};
    }

    /**
     * Add a node to the graph.
     * @param {string} id - node identifier
     * @param {string} label - node label (can be empty string)
     * @param {Object} attrs - node attributes (shape, style, fillcolor, etc.)
     */
    node(id, label, attrs = {}) {
        this.nodes.push({ id, label, ...attrs });
    }

    /**
     * Add an edge to the graph.
     * @param {string} fromId - source node ID
     * @param {string} toId - target node ID
     * @param {Object} attrs - edge attributes (label, color, penwidth, etc.)
     */
    edge(fromId, toId, attrs = {}) {
        this.edges.push({ from: fromId, to: toId, ...attrs });
    }

    /**
     * Set graph-level attributes.
     * @param {Object|string} keyOrAttrs - attribute key or object of attributes
     * @param {*} value - attribute value (if first param is string)
     */
    attr(keyOrAttrs, value) {
        if (typeof keyOrAttrs === 'string') {
            this.graphAttrs[keyOrAttrs] = value;
        } else {
            Object.assign(this.graphAttrs, keyOrAttrs);
        }
    }

    /**
     * Create a subgraph.
     * In Python, this is used with a context manager. In JS, provide a callback:
     * 
     * graph.subgraph('cluster_0', (sub) => {
     *   sub.attr({ label: 'My Cluster' });
     *   sub.node('a', 'Node A');
     * });
     * 
     * Or use it imperatively:
     * const sub = graph.subgraph('cluster_0');
     * sub.attr({ label: 'My Cluster' });
     * sub.node('a', 'Node A');
     * 
     * @param {string} name - subgraph name (use 'cluster_*' for visible clusters)
     * @param {Function} callback - optional function to build subgraph content
     * @returns {Subgraph} the created subgraph
     */
    subgraph(name, callback) {
        const sub = new Subgraph(name, this);
        this.subgraphs.push(sub);
        if (callback) {
            callback(sub);
        }
        return sub;
    }

    /**
     * Generate a DOT string representation of the graph.
     * @returns {string} DOT string representation of the graph
     */
    get source() {
        let output = `digraph ${this.name} {\n`;
        
        // Add graph attributes
        for (const [key, value] of Object.entries(this.graphAttrs)) {
            output += `  ${key}=${value}\n`;
        }
        
        // Add nodes
        for (const node of this.nodes) {
            const attrs = [];
            // Handle label separately - it can contain special characters
            if (node.label !== undefined && node.label !== '') {
                attrs.push(`label="${node.label}"`);
            }
            if (node.shape) attrs.push(`shape=${node.shape}`);
            if (node.style) attrs.push(`style=${node.style}`);
            if (node.fillcolor) attrs.push(`fillcolor=${node.fillcolor}`);
            if (node.color) attrs.push(`color=${node.color}`);
            
            const attrStr = attrs.length > 0 ? ` [${attrs.join(', ')}]` : '';
            output += `  ${node.id}${attrStr}\n`;
        }
        
        // Add subgraphs
        for (const sub of this.subgraphs) {
            output += sub._toDot('  ');
        }
        
        // Add edges
        for (const edge of this.edges) {
            const attrs = [];
            if (edge.label !== undefined) {
                // Quote string labels
                const formattedLabel = typeof edge.label === 'string' ? `"${edge.label}"` : edge.label;
                attrs.push(`label=${formattedLabel}`);
            }
            if (edge.color) attrs.push(`color="${edge.color}"`);
            if (edge.style) attrs.push(`style="${edge.style}"`);
            if (edge.penwidth) attrs.push(`penwidth="${edge.penwidth}"`);
            
            const attrStr = attrs.length > 0 ? ` [${attrs.join(', ')}]` : '';
            output += `  ${edge.from} -> ${edge.to}${attrStr}\n`;
        }
        
        output += "}\n";
        return output;
    }
}

export { Digraph, Subgraph };

