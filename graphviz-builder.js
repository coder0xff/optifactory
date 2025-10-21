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
        const escapeFunc = this._getEscapeFunc();
        for (const [key, value] of Object.entries(this.graphAttrs)) {
            // Escape and quote string values
            const formattedValue = typeof value === 'string' ? `"${escapeFunc(value)}"` : value;
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
        const escapeFunc = this._getEscapeFunc();
        if (node.label !== undefined) {
            attrs.push(`label="${escapeFunc(node.label)}"`);
        }
        if (node.shape) attrs.push(`shape=${node.shape}`);
        if (node.style) attrs.push(`style=${node.style}`);
        if (node.fillcolor) attrs.push(`fillcolor=${node.fillcolor}`);
        if (node.color) attrs.push(`color=${node.color}`);
        
        const attrStr = attrs.length > 0 ? ` [${attrs.join(', ')}]` : '';
        const quotedId = this._getQuoteIdFunc()(node.id);
        return `${indent}${quotedId}${attrStr}\n`;
    }

    _formatEdge(edge, indent) {
        const attrs = [];
        const escapeFunc = this._getEscapeFunc();
        if (edge.label !== undefined) {
            // Escape and quote string labels
            const formattedLabel = typeof edge.label === 'string' ? `"${escapeFunc(edge.label)}"` : edge.label;
            attrs.push(`label=${formattedLabel}`);
        }
        if (edge.color) attrs.push(`color="${edge.color}"`);
        if (edge.style) attrs.push(`style="${edge.style}"`);
        if (edge.penwidth) attrs.push(`penwidth="${edge.penwidth}"`);
        
        const attrStr = attrs.length > 0 ? ` [${attrs.join(', ')}]` : '';
        const quoteFunc = this._getQuoteIdFunc();
        return `${indent}${quoteFunc(edge.from)} -> ${quoteFunc(edge.to)}${attrStr}\n`;
    }

    /**
     * Get the quoting function from root Digraph.
     * Traverse up parent chain to find the root Digraph's _quoteId method.
     */
    _getQuoteIdFunc() {
        let current = this;
        while (current.parent) {
            current = current.parent;
        }
        return current._quoteId.bind(current);
    }

    /**
     * Get the escape function from root Digraph.
     * Traverse up parent chain to find the root Digraph's _escapeString method.
     */
    _getEscapeFunc() {
        let current = this;
        while (current.parent) {
            current = current.parent;
        }
        return current._escapeString.bind(current);
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
     * Quote a node ID if it contains spaces or special characters.
     * @param {string} id - node identifier
     * @returns {string} quoted ID if needed, otherwise original ID
     */
    _quoteId(id) {
        // Quote if ID contains spaces, special chars, or starts with a digit
        if (/[\s\-:]/.test(id) || /^\d/.test(id)) {
            return `"${id.replace(/"/g, '\\"')}"`;
        }
        return id;
    }

    /**
     * Escape special characters in string values for DOT output.
     * @param {string} str - string to escape
     * @returns {string} escaped string
     */
    _escapeString(str) {
        return str.replace(/\\/g, '\\\\')
                  .replace(/"/g, '\\"')
                  .replace(/\n/g, '\\n')
                  .replace(/\r/g, '\\r')
                  .replace(/\t/g, '\\t');
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
        // Quote the name if it contains spaces or special characters
        const quotedName = /[\s"]/.test(this.name) ? `"${this.name.replace(/"/g, '\\"')}"` : this.name;
        let output = `digraph ${quotedName} {\n`;
        
        // Add graph attributes
        for (const [key, value] of Object.entries(this.graphAttrs)) {
            output += `  ${key}=${value}\n`;
        }
        
        // Add nodes
        for (const node of this.nodes) {
            const attrs = [];
            // Handle label - always include it if defined (even if empty string)
            // Graphviz uses node ID as label if label attribute is missing
            if (node.label !== undefined) {
                attrs.push(`label="${this._escapeString(node.label)}"`);
            }
            if (node.shape) attrs.push(`shape=${node.shape}`);
            if (node.style) attrs.push(`style=${node.style}`);
            if (node.fillcolor) attrs.push(`fillcolor=${node.fillcolor}`);
            if (node.color) attrs.push(`color=${node.color}`);
            
            const attrStr = attrs.length > 0 ? ` [${attrs.join(', ')}]` : '';
            output += `  ${this._quoteId(node.id)}${attrStr}\n`;
        }
        
        // Add subgraphs
        for (const sub of this.subgraphs) {
            output += sub._toDot('  ');
        }
        
        // Add edges
        for (const edge of this.edges) {
            const attrs = [];
            if (edge.label !== undefined) {
                // Escape and quote string labels
                const formattedLabel = typeof edge.label === 'string' ? `"${this._escapeString(edge.label)}"` : edge.label;
                attrs.push(`label=${formattedLabel}`);
            }
            if (edge.color) attrs.push(`color="${edge.color}"`);
            if (edge.style) attrs.push(`style="${edge.style}"`);
            if (edge.penwidth) attrs.push(`penwidth="${edge.penwidth}"`);
            
            const attrStr = attrs.length > 0 ? ` [${attrs.join(', ')}]` : '';
            output += `  ${this._quoteId(edge.from)} -> ${this._quoteId(edge.to)}${attrStr}\n`;
        }
        
        output += "}\n";
        return output;
    }
}

export { Digraph, Subgraph };

