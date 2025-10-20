/**
 * LP solver abstraction layer.
 * 
 * This module provides an abstraction for solving LP problems from text format.
 * Uses the HiGHS solver via highs-js.
 */

/**
 * Result from LP solver.
 */
export class SolverResult {
    /**
     * @param {string} status - optimization status
     * @param {Object<string, number>} variable_values - dict mapping variable name to solution value
     */
    constructor(status, variable_values) {
        this.status = status;
        this.variable_values = variable_values;
    }
    
    /**
     * Check if optimization succeeded.
     * @returns {boolean}
     */
    is_optimal() {
        return this.status === 'Optimal';
    }
}

// Singleton HiGHS instance
let _highs_instance = null;

/**
 * Initialize HiGHS solver (loads the WASM module).
 * Should be called once before using solve_lp.
 * 
 * @returns {Promise<Object>} HiGHS instance
 */
export async function init_highs() {
    if (_highs_instance !== null) {
        return _highs_instance;
    }
    
    // Load HiGHS module from CDN
    _highs_instance = await Module({
        locateFile: (file) => `https://lovasoa.github.io/highs-js/${file}`
    });
    
    return _highs_instance;
}

/**
 * Solve LP problem from CPLEX LP format text.
 * Automatically initializes HiGHS if not already initialized.
 * 
 * Precondition:
 *     lp_text is valid CPLEX LP format
 *     HiGHS library is loaded (via script tag or import)
 * 
 * Postcondition:
 *     returns SolverResult with optimization status and variable values
 * 
 * @param {string} lp_text - LP problem in CPLEX LP format
 * @returns {Promise<SolverResult>} containing status and variable values
 */
export async function solve_lp(lp_text) {
    // Auto-initialize if not already done
    if (_highs_instance === null) {
        await init_highs();
    }
    
    // Solve the LP problem using HiGHS
    const solution = _highs_instance.solve(lp_text);
    
    // Extract variable values from solution
    const variable_values = {};
    if (solution.Columns) {
        for (const [var_name, var_info] of Object.entries(solution.Columns)) {
            // Include all variables, even those with zero values
            variable_values[var_name] = var_info.Primal || 0;
        }
    }
    
    return new SolverResult(solution.Status, variable_values);
}

