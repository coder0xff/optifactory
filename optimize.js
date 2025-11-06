/**
 * LP optimization module for Satisfactory factory design.
 * 
 * This module generates and solves LP problems to find optimal recipes
 * that meet production requirements while minimizing costs.
 */

import {
    get_all_recipes_by_machine,
    get_all_recipes,
    get_base_parts,
    get_default_enablement_set,
    normalize_material_names,
    normalize_input_array
} from './recipes.js';
import { get_default_economy } from './economy.js';
import { solve_lp, SolverResult } from './lp-solver.js';

// ============================================================================
// Logger
// ============================================================================

const _LOGGER = {
    info: (...args) => console.log('[optimize]', ...args),
    debug: (...args) => console.debug('[optimize]', ...args),
    warn: (...args) => console.warn('[optimize]', ...args),
    error: (...args) => console.error('[optimize]', ...args)
};

// ============================================================================
// Constants
// ============================================================================

// Variable type constant for LP generation
const INTEGER = "INTEGER";

// ============================================================================
// Classes
// ============================================================================

/**
 * Variable metadata for LP model.
 */
class Variable {
    /**
     * @param {string} name - variable name
     * @param {string} var_type - INTEGER or CONTINUOUS
     * @param {number} lb - lower bound (default 0)
     */
    constructor(name, var_type, lb = 0) {
        this.name = name;
        this.var_type = var_type;
        this.lb = lb;
    }
}

/**
 * Linear expression holding variable-coefficient pairs and a constant.
 */
class LinExpr {
    /**
     * @param {Array<[Variable, number]>} terms - list of [Variable, coefficient] pairs
     * @param {number} constant - constant offset in the expression
     */
    constructor(terms = null, constant = 0) {
        this.terms = terms !== null ? terms : [];
        this.constant = constant;
    }
    
    /**
     * Multiply all terms and constant by scalar.
     * @param {number} scalar - scalar to multiply by
     * @returns {LinExpr} new linear expression
     */
    mul(scalar) {
        const new_terms = this.terms.map(([var_obj, coef]) => [var_obj, coef * scalar]);
        return new LinExpr(new_terms, this.constant * scalar);
    }
    
    /**
     * Add another linear expression to this one.
     * @param {LinExpr} other - expression to add
     * @returns {LinExpr} new linear expression
     */
    add(other) {
        const new_terms = this.terms.concat(other.terms);
        const new_constant = this.constant + other.constant;
        return new LinExpr(new_terms, new_constant);
    }
    
    /**
     * Subtract another linear expression from this one.
     * @param {LinExpr} other - expression to subtract
     * @returns {LinExpr} new linear expression
     */
    sub(other) {
        return this.add(other.mul(-1));
    }
    
    /**
     * Create constraint: this expression >= rhs.
     * @param {number} rhs - right-hand side value
     * @returns {Constraint} new constraint
     */
    greater_or_equal(rhs) {
        return new Constraint(this, rhs);
    }
}

/**
 * Constraint: expr >= rhs.
 */
class Constraint {
    /**
     * @param {LinExpr} expr - LinExpr on left side
     * @param {number} rhs - right-hand side value
     */
    constructor(expr, rhs) {
        this.expr = expr;
        this.rhs = rhs;
    }
}

/**
 * Builder for generating CPLEX LP format text.
 * 
 * Tracks variables, constraints, and objective function.
 * Generates LP format text via to_lp_text().
 */
class LPBuilder {
    constructor() {
        this.variables = [];
        this.constraints = [];
        this.constraint_names = [];
        this.objective = null;
    }
    
    /**
     * Create new variable and return LinExpr representing it.
     * @param {string} name - variable name
     * @param {string} var_type - INTEGER or CONTINUOUS
     * @param {number} lb - lower bound (default 0)
     * @returns {LinExpr} linear expression representing the variable
     */
    add_var(name, var_type, lb = 0) {
        const var_obj = new Variable(name, var_type, lb);
        this.variables.push(var_obj);
        return new LinExpr([[var_obj, 1.0]], 0);
    }
    
    /**
     * Add constraint with given name.
     * @param {Constraint} constraint - constraint to add
     * @param {string} name - constraint name
     */
    add_constraint(constraint, name) {
        this.constraints.push(constraint);
        this.constraint_names.push(name);
    }
    
    /**
     * Set objective function to minimize.
     * @param {LinExpr} expr - objective expression
     */
    set_objective(expr) {
        this.objective = expr;
    }
    
    /**
     * Consolidate duplicate variables by summing their coefficients.
     * @param {Array<[Variable, number]>} terms - list of [Variable, coefficient] pairs
     * @returns {Object<string, [Variable, number]>} dict mapping var name -> [Variable, coefficient]
     */
    _consolidate_terms(terms) {
        const consolidated = {};
        for (const [var_obj, coef] of terms) {
            if (var_obj.name in consolidated) {
                const [_, existing_coef] = consolidated[var_obj.name];
                consolidated[var_obj.name] = [var_obj, existing_coef + coef];
            } else {
                consolidated[var_obj.name] = [var_obj, coef];
            }
        }
        return consolidated;
    }
    
    /**
     * Format expression terms into lines respecting line length limit.
     * @param {string} label - label for the expression
     * @param {Object<string, [Variable, number]>} terms_dict - consolidated terms
     * @param {number} constant - constant value (default 0)
     * @param {number} max_line_len - maximum line length (default 500)
     * @returns {Array<string>} array of formatted lines
     */
    _format_expression_line(label, terms_dict, constant = 0, max_line_len = 500) {
        const lines = [];
        let current_line = label;
        
        for (const [var_obj, coef] of Object.values(terms_dict)) {
            if (Math.abs(coef) > 1e-10) {  // skip near-zero coefficients
                let term;
                if (coef >= 0) {
                    term = `  +${coef} ${var_obj.name}`;
                } else {
                    term = `  ${coef} ${var_obj.name}`;
                }
                
                // check if adding this term would exceed line length
                if (current_line.length + term.length > max_line_len && current_line !== label) {
                    lines.push(current_line);
                    current_line = " " + term;  // continuation lines start with space
                } else {
                    current_line += term;
                }
            }
        }
        
        // add constant if non-zero
        if (Math.abs(constant) > 1e-10) {
            let term;
            if (constant >= 0) {
                term = `  +${constant}`;
            } else {
                term = `  ${constant}`;
            }
            if (current_line.length + term.length > max_line_len && current_line !== label) {
                lines.push(current_line);
                current_line = " " + term;
            } else {
                current_line += term;
            }
        }
        
        if (current_line) {
            lines.push(current_line);
        }
        
        return lines;
    }
    
    /**
     * Generate CPLEX LP format text.
     * @returns {string} LP format text
     */
    to_lp_text() {
        const lines = [];
        lines.push("\\Problem name: ");
        lines.push("");
        lines.push("Minimize");
        
        // Objective function - consolidate and handle line breaks
        if (this.objective) {
            const consolidated = this._consolidate_terms(this.objective.terms);
            const obj_lines = this._format_expression_line("OBJROW:", consolidated, this.objective.constant);
            lines.push(...obj_lines);
        } else {
            lines.push("OBJROW:");
        }
        
        // Constraints - consolidate and handle line breaks
        lines.push("Subject To");
        for (let i = 0; i < this.constraints.length; i++) {
            const constraint = this.constraints[i];
            const name = this.constraint_names[i];
            const consolidated = this._consolidate_terms(constraint.expr.terms);
            // move constant to RHS
            const rhs = constraint.rhs - constraint.expr.constant;
            const constr_lines = this._format_expression_line(`${name}:`, consolidated);
            // add >= rhs to the last line
            if (constr_lines.length > 0) {
                constr_lines[constr_lines.length - 1] += ` >= ${rhs}`;
            } else {
                constr_lines.push(`${name}: >= ${rhs}`);
            }
            lines.push(...constr_lines);
        }
        
        // Bounds (only if non-default)
        lines.push("Bounds");
        for (const var_obj of this.variables) {
            if (var_obj.lb !== 0) {
                lines.push(`${var_obj.lb} <= ${var_obj.name}`);
            }
        }
        
        // Integer variables - handle line breaks for long lists
        lines.push("Integers");
        const int_vars = this.variables
            .filter(v => v.var_type === INTEGER)
            .map(v => v.name);
        if (int_vars.length > 0) {
            // break into multiple lines if too long
            let current_line = "";
            for (const var_name of int_vars) {
                if (current_line.length + var_name.length + 1 > 500) {
                    lines.push(current_line + " ");
                    current_line = var_name;
                } else {
                    current_line += (current_line ? " " : "") + var_name;
                }
            }
            if (current_line) {
                lines.push(current_line + " ");
            }
        }
        
        lines.push("End");
        return lines.join("\n");
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Convert a string to a safe MIP solver variable name.
 *
 * Precondition:
 *     name is a non-empty string
 *
 * Postcondition:
 *     returns a string with special characters removed or replaced
 *     colons, parentheses are removed
 *     hyphens and spaces are replaced with underscores
 *
 * @param {string} name - string to convert to safe variable name
 * @returns {string} string safe for use as MIP solver variable name
 */
function _safe_var_name(name) {
    return name
        .replace(/:/g, "")
        .replace(/\(/g, "")
        .replace(/\)/g, "")
        .replace(/-/g, "_")
        .replace(/ /g, "_");
}

// ============================================================================
// Validation Functions
// ============================================================================

/**
 * Validate inputs and set defaults for optimization parameters.
 *
 * Precondition:
 *     enablement_set is either null or a Set of recipe names
 *     economy is either null or an object mapping item names to values
 *     outputs is an object mapping material names to required amounts
 *     design_power is a boolean
 *
 * Postcondition:
 *     returns [validated_enablement_set, validated_economy, final_design_power]
 *     enablement_set is set to defaults if null
 *     economy is set to default if null
 *     design_power is true if "MWm" in outputs
 *
 * @param {Set<string>|null} enablement_set - optional set of enabled recipe names
 * @param {Object<string, number>|null} economy - optional economy object
 * @param {Object<string, number>} outputs - required outputs
 * @param {boolean} design_power - whether to design power
 * @returns {[Set<string>, Object<string, number>, boolean]} tuple of (enablement_set, economy, design_power) with defaults applied
 * @throws {Error} if enablement_set contains invalid recipe names
 */
function _validate_and_set_defaults(enablement_set, economy, outputs, design_power) {
    const final_enablement = enablement_set || get_default_enablement_set();
    const all_recipes = new Set(Object.keys(get_all_recipes()));
    const invalid_recipes = new Set([...final_enablement].filter(r => !all_recipes.has(r)));
    if (invalid_recipes.size > 0) {
        throw new Error(`Enablement set contains invalid recipes: ${Array.from(invalid_recipes).join(', ')}`);
    }

    const final_design_power = design_power || ("MWm" in outputs);
    const final_economy = economy !== null ? economy : get_default_economy();

    return [final_enablement, final_economy, final_design_power];
}

// ============================================================================
// LP Building Functions
// ============================================================================

/**
 * Build a matrix of how recipes produce/consume materials.
 *
 * Precondition:
 *     enablement_set is a Set of valid recipe names
 *
 * Postcondition:
 *     returns nested object where part_recipe_matrix[part][recipe] = amount
 *     negative amounts represent consumption (inputs)
 *     positive amounts represent production (outputs)
 *
 * @param {Set<string>} enablement_set - set of enabled recipe names
 * @returns {Object<string, Object<string, number>>} nested object mapping material -> recipe -> amount (neg=input, pos=output)
 */
function _build_part_recipe_matrix(enablement_set) {
    const part_recipe_matrix = {};

    const recipes_by_machine = get_all_recipes_by_machine();
    for (const [_machine_name, machine_recipes] of Object.entries(recipes_by_machine)) {
        for (const [recipe_name, recipe] of Object.entries(machine_recipes)) {
            if (enablement_set !== null && !enablement_set.has(recipe_name)) {
                continue;
            }
            for (const [part, amount] of Object.entries(recipe.inputs)) {
                if (!(part in part_recipe_matrix)) {
                    part_recipe_matrix[part] = {};
                }
                part_recipe_matrix[part][recipe_name] = -amount;
            }
            for (const [part, amount] of Object.entries(recipe.outputs)) {
                if (!(part in part_recipe_matrix)) {
                    part_recipe_matrix[part] = {};
                }
                part_recipe_matrix[part][recipe_name] = amount;
            }
        }
    }

    return part_recipe_matrix;
}

/**
 * Validate that all requested outputs can be produced by enabled recipes.
 *
 * Precondition:
 *     outputs is an object mapping material names to required amounts
 *     part_recipe_matrix is populated with recipe data
 *
 * Postcondition:
 *     returns undefined if all outputs are producible
 *     throws Error if any outputs are not producible
 *
 * @param {Object<string, number>} outputs - required output materials
 * @param {Object<string, Object<string, number>>} part_recipe_matrix - matrix of recipe inputs/outputs
 * @throws {Error} if any output material is not produced by enabled recipes
 */
function _validate_outputs_are_producible(outputs, part_recipe_matrix) {
    const output_keys = new Set(Object.keys(outputs));
    const matrix_keys = new Set(Object.keys(part_recipe_matrix));
    const invalid_outputs = new Set([...output_keys].filter(k => !matrix_keys.has(k)));
    if (invalid_outputs.size > 0) {
        throw new Error(`Outputs contain unrecognized parts: ${Array.from(invalid_outputs).join(', ')}`);
    }
}

/**
 * Check that optimization succeeded and raise error if not.
 *
 * Precondition:
 *     result contains optimization status
 *     design_power indicates whether power design was requested
 *     lp_text is optional LP format text to write on failure
 *
 * Postcondition:
 *     returns undefined if optimization succeeded
 *     throws Error with helpful message if optimization failed
 *
 * @param {SolverResult} result - SolverResult from optimization
 * @param {boolean} design_power - whether power design was enabled
 * @param {string} lp_text - optional LP format text for debugging on failure
 * @throws {Error} if optimization status is not OPTIMAL
 */
function _validate_optimization_succeeded(result, design_power, lp_text = null) {
    if (!result.is_optimal()) {
        // Note: In browser, we can't write files, so we'll just log
        if (lp_text) {
            _LOGGER.error("Optimization failed. LP text:", lp_text);
        }
        
        let message = `Optimization failed with status ${result.status}`;
        if (result.status === 'Infeasible') {
            message = "ERROR: Couldn't design the factory. Make sure that recipes are enabled to produce output parts and all intermediate parts from base parts.";
            if (design_power) {
                message = "ERROR: Couldn't design the factory. Make sure that recipes are enabled to produce power, output parts, and all intermediate parts from base parts..";
            }
        }
        throw new Error(message);
    }
}

/**
 * Create LP builder for generating LP format text.
 *
 * Precondition:
 *     none
 *
 * Postcondition:
 *     returns an LPBuilder instance
 *
 * @returns {LPBuilder} LPBuilder instance
 */
function _create_lp_builder() {
    return new LPBuilder();
}

/**
 * Create LP variables for each enabled recipe.
 *
 * Precondition:
 *     builder is an LPBuilder instance
 *     enablement_set is a Set of enabled recipe names
 *
 * Postcondition:
 *     returns object mapping recipe_name -> LinExpr
 *     variables are INTEGER type with lower bound 0
 *     variables are added to the builder
 *
 * @param {LPBuilder} builder - LP builder to add variables to
 * @param {Set<string>} enablement_set - set of enabled recipe names
 * @returns {Object<string, LinExpr>} object mapping recipe name -> LinExpr
 */
function _create_recipe_variables(builder, enablement_set) {
    const recipe_vars = {};
    const recipes_by_machine = get_all_recipes_by_machine();
    
    for (const [machine_name, machine_recipes] of Object.entries(recipes_by_machine)) {
        for (const recipe_name of Object.keys(machine_recipes)) {
            if (enablement_set === null || enablement_set.has(recipe_name)) {
                const var_name = _safe_var_name(`${machine_name}_${recipe_name}`);
                recipe_vars[recipe_name] = builder.add_var(var_name, INTEGER, 0);
            }
        }
    }
    
    return recipe_vars;
}

/**
 * Extract recipe counts from solver result.
 *
 * Precondition:
 *     recipe_vars contains LinExpr for each recipe
 *     result contains solved variable values
 *
 * Postcondition:
 *     returns object containing only recipes with positive counts
 *     counts are extracted from result variable values by name
 *
 * @param {Object<string, LinExpr>} recipe_vars - object mapping recipe name -> LinExpr
 * @param {SolverResult} result - SolverResult with variable values
 * @returns {Object<string, number>} object mapping recipe name -> machine count (positive values only)
 */
function _extract_recipe_counts(recipe_vars, result) {
    const output = {};
    
    for (const [recipe_name, linexpr] of Object.entries(recipe_vars)) {
        // LinExpr should have exactly one term for recipe variables
        if (linexpr.terms.length !== 1) {
            throw new Error(`Recipe variable should have exactly one term: ${recipe_name}`);
        }
        const [var_obj, coef] = linexpr.terms[0];
        if (coef !== 1.0) {
            throw new Error(`Recipe variable should have coefficient 1: ${recipe_name}`);
        }
        
        // look up variable value in result
        const value = result.variable_values[var_obj.name] || 0;
        if (value > 0) {
            output[recipe_name] = Math.round(value);
        }
    }
    
    return output;
}

/**
 * Compute total available amount of a part (production + inputs).
 *
 * Precondition:
 *     part is a material name
 *     contributors_dict maps recipe names to amounts (neg=input, pos=output)
 *     recipe_vars maps recipe names to LinExpr
 *     inputs maps material names to available input amounts
 *     design_power indicates whether power production is enabled
 *
 * Postcondition:
 *     returns LinExpr for total part availability
 *     includes recipe contributions and available inputs
 *
 * @param {string} part - material name
 * @param {Object<string, number>} contributors_dict - recipe contributions for this part
 * @param {Object<string, LinExpr>} recipe_vars - LinExpr for recipes
 * @param {Object<string, number>} inputs - available input materials
 * @param {boolean} design_power - whether power design is enabled
 * @returns {LinExpr} LinExpr for total part count
 */
function _compute_part_count(part, contributors_dict, recipe_vars, inputs, design_power) {
    const part_recipe_contributions = [];
    
    for (const [recipe_name, amount] of Object.entries(contributors_dict)) {
        // no power production when power design is disabled
        if (part === "MWm" && !design_power && amount > 0) {
            continue;
        }
        part_recipe_contributions.push(recipe_vars[recipe_name].mul(amount));
    }
    
    if (part_recipe_contributions.length === 0) {
        throw new Error("It should not be in the matrix if it has no contributors.");
    }
    
    // chain .add() to sum all contributions
    let result = part_recipe_contributions[0];
    for (let i = 1; i < part_recipe_contributions.length; i++) {
        result = result.add(part_recipe_contributions[i]);
    }
    
    // add input constant if present
    const input_amount = inputs[part] || 0;
    if (input_amount !== 0) {
        result = result.add(new LinExpr([], input_amount));
    }
    
    return result;
}

/**
 * Apply economy weight to a part cost.
 *
 * Precondition:
 *     weighted_cost is a LinExpr
 *     part is a material name
 *     economy is either null or an object of material values
 *
 * Postcondition:
 *     returns weighted_cost multiplied by economy value if available
 *     logs warning if part not in economy
 *     returns original weighted_cost if economy is null
 *
 * @param {LinExpr} weighted_cost - LinExpr to weight
 * @param {string} part - material name
 * @param {Object<string, number>|null} economy - optional economy object
 * @returns {LinExpr} weighted LinExpr
 */
function _apply_economy_weight(weighted_cost, part, economy) {
    if (economy) {
        if (part in economy) {
            return weighted_cost.mul(economy[part]);
        } else {
            _LOGGER.warn(
                `Part ${part} not found in the provided economy. Using default value of 1.`
            );
        }
    }
    return weighted_cost;
}

/**
 * Compute weighted cost for a non-output part and update power tracking.
 *
 * Precondition:
 *     part is a material name not in outputs
 *     part_count is a LinExpr for part availability
 *     base_parts is the set of base materials
 *     inputs maps material names to available input amounts
 *     design_power indicates whether power design is enabled
 *     weights are non-negative numbers
 *     economy is either null or an object of material values
 *     builder is the LPBuilder
 *     power_sum is current power tracking expression or null
 *
 * Postcondition:
 *     returns [weighted_part_cost, updated_power_sum]
 *     weighted_part_cost may be null if weight is zero
 *     adds balance constraint to builder for non-base, non-power parts
 *     parts with input quantity of 0 are allowed negative balances (can be external inputs)
 *     updates power_sum if part is "MWm" and design_power is true
 *
 * @param {string} part - material name
 * @param {LinExpr} part_count - LinExpr for part availability
 * @param {Set<string>} base_parts - set of base material names
 * @param {Object<string, number>} inputs - material -> available amount
 * @param {boolean} design_power - whether power design is enabled
 * @param {number} input_costs_weight - weight for input costs
 * @param {number} power_consumption_weight - weight for power consumption
 * @param {Object<string, number>|null} economy - optional economy object
 * @param {LPBuilder} builder - LP builder
 * @param {LinExpr|null} power_sum - current power sum tracking or null
 * @returns {[LinExpr|null, LinExpr|null]} tuple of (weighted_part_cost or null, updated_power_sum or null)
 */
function _compute_weighted_part_cost(
    part,
    part_count,
    base_parts,
    inputs,
    design_power,
    input_costs_weight,
    power_consumption_weight,
    economy,
    builder,
    power_sum
) {
    let weighted_part_cost = part_count.mul(-1);
    weighted_part_cost = _apply_economy_weight(weighted_part_cost, part, economy);

    if (part === "MWm") {
        if (design_power) {
            power_sum = power_sum !== null ? power_sum.add(part_count) : part_count;
        }
        if (power_consumption_weight > 0) {
            weighted_part_cost = weighted_part_cost.mul(power_consumption_weight);
        } else {
            weighted_part_cost = null;
        }
    } else if (base_parts.has(part) || (part in inputs && inputs[part] === 0)) {
        // allow base parts and parts with input quantity 0 to have negative balances
        if (input_costs_weight > 0) {
            weighted_part_cost = weighted_part_cost.mul(input_costs_weight);
        } else {
            weighted_part_cost = null;
        }
    } else {
        // force non-base parts and parts with input quantity > 0 to have non-negative balances
        const constraint = part_count.greater_or_equal(0);
        builder.add_constraint(constraint, _safe_var_name(`${part}_balance`));
    }

    return [weighted_part_cost, power_sum];
}

/**
 * Add material balance constraints to LP builder for all parts.
 *
 * Precondition:
 *     builder is an LPBuilder with recipe variables added
 *     part_recipe_matrix maps materials to recipe contributions
 *     recipe_vars maps recipe names to LinExpr
 *     inputs maps material names to available amounts
 *     outputs maps material names to required amounts
 *     economy is either null or an object of material values
 *     design_power indicates whether power design is enabled
 *     weights are non-negative numbers
 *     base_parts is the set of base material names
 *
 * Postcondition:
 *     material balance constraints are added to builder
 *     output constraints ensure outputs meet requirements
 *     cost constraints track input costs
 *     returns [list of cost LinExpr, power_sum expression or null]
 *
 * @param {LPBuilder} builder - LP builder
 * @param {Object<string, Object<string, number>>} part_recipe_matrix - material -> recipe -> amount
 * @param {Object<string, LinExpr>} recipe_vars - recipe -> LinExpr
 * @param {Object<string, number>} inputs - material -> available amount
 * @param {Object<string, number>} outputs - material -> required amount
 * @param {Object<string, number>|null} economy - optional economy object
 * @param {boolean} design_power - whether power design is enabled
 * @param {number} input_costs_weight - weight for input costs
 * @param {number} power_consumption_weight - weight for power consumption
 * @param {Set<string>} base_parts - set of base material names
 * @returns {[Array<LinExpr>, LinExpr|null]} tuple of (part_costs list, power_sum expression or null)
 */
function _add_material_balance_constraints(
    builder,
    part_recipe_matrix,
    recipe_vars,
    inputs,
    outputs,
    economy,
    design_power,
    input_costs_weight,
    power_consumption_weight,
    base_parts
) {
    let power_sum = null;
    const part_costs = [];
    const wastes = [];

    for (const [part, contributors_dict] of Object.entries(part_recipe_matrix)) {
        const part_count = _compute_part_count(part, contributors_dict, recipe_vars, inputs, design_power);

        if (part in outputs) {
            // add output constraint: part_count >= outputs[part]
            const constraint = part_count.sub(new LinExpr([], outputs[part])).greater_or_equal(0);
            builder.add_constraint(constraint, _safe_var_name(`${part}_output`));
            if (part === "MWm") {
                power_sum = power_sum === null ? part_count : part_count;
            }
        } else {
            // handle cost for non-output parts
            const part_cost = builder.add_var(
                _safe_var_name(`${part}_cost`), INTEGER
            );

            const waste = builder.add_var(
                _safe_var_name(`${part}_waste`), INTEGER
            );

            const [weighted_part_cost, updated_power_sum] = _compute_weighted_part_cost(
                part,
                part_count,
                base_parts,
                inputs,
                design_power,
                input_costs_weight,
                power_consumption_weight,
                economy,
                builder,
                power_sum
            );
            
            power_sum = updated_power_sum;

            if (weighted_part_cost !== null) {
                // part_cost >= weighted_part_cost  =>  part_cost - weighted_part_cost >= 0
                const constraint = part_cost.sub(weighted_part_cost).greater_or_equal(0);
                builder.add_constraint(constraint, _safe_var_name(`${part}_cost`));
                part_costs.push(part_cost);
            }

            const constraint = waste.sub(part_count).greater_or_equal(0);
            builder.add_constraint(constraint, _safe_var_name(`${part}_waste`));
            wastes.push(waste);
        }
    }

    return [part_costs, power_sum, wastes];
}

/**
 * Set optimization objective in LP builder.
 *
 * Precondition:
 *     builder has all constraints added
 *     part_costs is a list of LinExpr cost variables
 *     recipe_vars maps recipe names to LinExpr
 *     weights are non-negative numbers
 *
 * Postcondition:
 *     builder.objective is set to weighted sum of costs and machine counts
 *
 * @param {LPBuilder} builder - LP builder with constraints
 * @param {Array<LinExpr>} part_costs - list of cost LinExpr
 * @param {Object<string, LinExpr>} recipe_vars - recipe -> LinExpr
 * @param {number} input_costs_weight - weight for input costs
 * @param {number} machine_counts_weight - weight for machine counts
 */
function _set_objective(
    builder,
    part_costs,
    wastes,
    recipe_vars,
    input_costs_weight,
    machine_counts_weight,
    waste_products_weight
) {
    // sum all part costs
    let objective = new LinExpr([], 0);
    for (const cost of part_costs) {
        objective = objective.add(cost);
    }
    objective = objective.mul(input_costs_weight);
    
    // add machine counts
    let machine_sum = new LinExpr([], 0);
    for (const recipe_expr of Object.values(recipe_vars)) {
        machine_sum = machine_sum.add(recipe_expr);
    }
    objective = objective.add(machine_sum.mul(machine_counts_weight));
    
    // add wastes
    let waste_sum = new LinExpr([], 0);
    for (const waste of wastes) {
        waste_sum = waste_sum.add(waste);
    }
    objective = objective.add(waste_sum.mul(waste_products_weight));

    builder.set_objective(objective);
}

// ============================================================================
// Main API
// ============================================================================

/**
 * Optimize recipes to minimize costs while meeting output requirements.
 *
 * Precondition:
 *     inputs is an object mapping material names to available amounts
 *     outputs is an object mapping material names to required amounts
 *     enablement_set is either null or a valid Set of recipe names
 *     economy is either null or an object mapping items to values
 *     weights are non-negative numbers
 *     design_power is a boolean
 *
 * Postcondition:
 *     returns object mapping recipe names to machine counts
 *     only recipes with positive counts are included
 *     satisfies all output requirements
 *     minimizes objective function based on weights
 *
 * @param {Object<string, number>} inputs - available input materials and amounts
 * @param {Object<string, number>} outputs - required output materials and amounts
 * @param {Object} options - optional parameters
 * @param {Set<string>|null} options.enablement_set - optional set of enabled recipe names (null = default)
 * @param {Object<string, number>|null} options.economy - optional economy for valuing items (null = default)
 * @param {number} options.input_costs_weight - weight for input costs in objective
 * @param {number} options.machine_counts_weight - weight for machine counts in objective
 * @param {number} options.power_consumption_weight - weight for power consumption in objective
 * @param {number} options.waste_products_weight - weight for waste products in objective
 * @param {boolean} options.design_power - whether to design power generation (forced true if MWm in outputs)
 * @returns {Object<string, number>} object mapping recipe name -> number of machines needed
 * @throws {Error} if enablement set is invalid, outputs are unrecognized,
 *                or optimization fails (infeasible/unbounded)
 */
async function optimize_recipes(
    inputs,
    outputs,
    {
        enablement_set = null,
        economy = null,
        input_costs_weight = 1.0,
        machine_counts_weight = 0.0,
        power_consumption_weight = 0.0,
        waste_products_weight = 0.0,
        design_power = false,
        on_progress = null
    } = {}
) {
    const report_progress = (message) => {
        if (on_progress) {
            on_progress(message);
        }
    };

    // Normalize material names to canonical case
    outputs = normalize_material_names(outputs);
    inputs = normalize_material_names(inputs);

    report_progress("Validating configuration...");
    [enablement_set, economy, design_power] = _validate_and_set_defaults(
        enablement_set, economy, outputs, design_power
    );

    report_progress("Building recipe matrix...");
    const part_recipe_matrix = _build_part_recipe_matrix(enablement_set);
    _validate_outputs_are_producible(outputs, part_recipe_matrix);

    report_progress("Creating LP model...");
    const builder = _create_lp_builder();
    const recipe_vars = _create_recipe_variables(builder, enablement_set);

    report_progress("Adding constraints...");
    const [part_costs, power_sum, wastes] = _add_material_balance_constraints(
        builder,
        part_recipe_matrix,
        recipe_vars,
        inputs,
        outputs,
        economy,
        design_power,
        input_costs_weight,
        power_consumption_weight,
        get_base_parts(),
    );

    if (design_power) {
        // treat power the same as non-base parts: require non-negative balance
        if (power_sum === null) {
            throw new Error("power_sum should not be null when design_power is true");
        }
        const constraint = power_sum.greater_or_equal(0);
        builder.add_constraint(constraint, "power_balance");
    }

    report_progress("Setting objective function...");
    _set_objective(builder, part_costs, wastes, recipe_vars, input_costs_weight, machine_counts_weight, waste_products_weight);

    report_progress("Generating LP problem...");
    const lp_text = builder.to_lp_text();
    
    report_progress("Solving LP problem (this may take a while)...");
    const result = await solve_lp(lp_text);

    report_progress("Extracting solution...");
    _validate_optimization_succeeded(result, design_power, lp_text);
    return _extract_recipe_counts(recipe_vars, result);
}

// ============================================================================
// Exports
// ============================================================================

export {
    optimize_recipes
};

