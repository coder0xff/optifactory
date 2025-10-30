import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { assertAlmostEqual } from './test-helpers.js';
import { solve_lp, SolverResult } from '../lp-solver.js';

describe('LP Solver', () => {
    it('simple optimization', async () => {
        // Simple problem: minimize x + y subject to x + y >= 10, x >= 0, y >= 0
        // Optimal solution: x=10, y=0 or x=0, y=10 (or any point on the line)
        const lp_text = `\\Problem name: 

Minimize
OBJROW:  +1.0 x  +1.0 y
Subject To
constraint1:  +1.0 x  +1.0 y >= 10
Bounds
Integers
x y 
End`;
        
        const result = await solve_lp(lp_text);
        
        assert.ok(result.is_optimal());
        assert.strictEqual(result.status, 'Optimal');
        
        // Check that x + y = 10 (within tolerance)
        const total = (result.variable_values["x"] || 0) + (result.variable_values["y"] || 0);
        assertAlmostEqual(total, 10, 0.01);
        
        // Check objective value is 10
        const obj_value = Object.values(result.variable_values).reduce((a, b) => a + b, 0);
        assertAlmostEqual(obj_value, 10, 0.01);
    });
    
    it('variable extraction', async () => {
        // Problem with specific expected solution
        const lp_text = `\\Problem name: 

Minimize
OBJROW:  +2.0 a  +3.0 b
Subject To
constraint1:  +1.0 a  +1.0 b >= 5
constraint2:  +1.0 a >= 2
Bounds
Integers
a b 
End`;
        
        const result = await solve_lp(lp_text);
        
        assert.ok(result.is_optimal());
        assert.ok('a' in result.variable_values);
        assert.ok('b' in result.variable_values);
        
        // Check constraints are satisfied
        const a = result.variable_values["a"];
        const b = result.variable_values["b"];
        assert.ok(a >= 2 - 0.01);
        assert.ok(a + b >= 5 - 0.01);
    });
    
    it('multiple variables', async () => {
        const lp_text = `\\Problem name: 

Minimize
OBJROW:  +1.0 x1  +1.0 x2  +1.0 x3
Subject To
c1:  +1.0 x1  +1.0 x2  +1.0 x3 >= 15
c2:  +1.0 x1 >= 3
c3:  +1.0 x2 >= 4
c4:  +1.0 x3 >= 5
Bounds
Integers
x1 x2 x3 
End`;
        
        const result = await solve_lp(lp_text);
        
        assert.ok(result.is_optimal());
        
        // Check all variables are in result
        assert.ok('x1' in result.variable_values);
        assert.ok('x2' in result.variable_values);
        assert.ok('x3' in result.variable_values);
        
        // Check constraints
        const x1 = result.variable_values["x1"];
        const x2 = result.variable_values["x2"];
        const x3 = result.variable_values["x3"];
        
        assert.ok(x1 >= 3 - 0.01);
        assert.ok(x2 >= 4 - 0.01);
        assert.ok(x3 >= 5 - 0.01);
        assert.ok(x1 + x2 + x3 >= 15 - 0.01);
        
        // Since constraints force x1>=3, x2>=4, x3>=5, and x1+x2+x3>=15
        // The sum is at least 12, so we need at least 3 more
        // Optimal should be x1=3, x2=4, x3=8 (or similar)
        assertAlmostEqual(x1 + x2 + x3, 15, 0.01);
    });
    
    it('infeasible problem', async () => {
        // Infeasible: x + y >= 10 and x + y <= 5
        const lp_text = `\\Problem name: 

Minimize
OBJROW:  +1.0 x  +1.0 y
Subject To
c1:  +1.0 x  +1.0 y >= 10
c2:  -1.0 x  -1.0 y >= -5
Bounds
Integers
x y 
End`;
        
        const result = await solve_lp(lp_text);
        
        assert.ok(!result.is_optimal());
        assert.strictEqual(result.status, 'Infeasible');
    });
    
    it('zero variables', async () => {
        // Problem where one variable should be zero
        const lp_text = `\\Problem name: 

Minimize
OBJROW:  +1.0 x  +100.0 y
Subject To
c1:  +1.0 x >= 5
Bounds
Integers
x y 
End`;
        
        const result = await solve_lp(lp_text);
        
        assert.ok(result.is_optimal());
        
        // x should be 5, y should be 0 (since it's expensive and not required)
        const x = result.variable_values["x"] || 0;
        const y = result.variable_values["y"] || 0;
        
        assertAlmostEqual(x, 5, 0.01);
        assertAlmostEqual(y, 0, 0.01);
    });
    
    it('solver result attributes', async () => {
        const lp_text = `\\Problem name: 

Minimize
OBJROW:  +1.0 x
Subject To
c1:  +1.0 x >= 1
Bounds
Integers
x 
End`;
        
        const result = await solve_lp(lp_text);
        
        // Check that result has expected attributes
        assert.ok(result.status != null);
        assert.ok(result.variable_values != null);
        assert.ok(typeof result.is_optimal === 'function');
        
        // Check types
        assert.ok(typeof result.variable_values === 'object');
        
        // Check functionality
        assert.strictEqual(result.is_optimal(), result.status === 'Optimal');
    });
    
    it('maximization with equality and bounds', async () => {
        const lp_text = `\\Problem name: 

Maximize
 obj:
    x1 + 2 x2 + 4 x3 + x4
Subject To
 c1: - x1 + x2 + x3 + 10 x4 <= 20
 c2: x1 - 4 x2 + x3 <= 30
 c3: x2 - 0.5 x4 = 0
Bounds
 0 <= x1 <= 40
 2 <= x4 <= 3
End`;
        
        const result = await solve_lp(lp_text);
        
        assert.ok(result.is_optimal());
        
        // Extract variable values
        const x1 = result.variable_values["x1"] || 0;
        const x2 = result.variable_values["x2"] || 0;
        const x3 = result.variable_values["x3"] || 0;
        const x4 = result.variable_values["x4"] || 0;
        
        assertAlmostEqual(x1, 17.5, 0.01);
        assertAlmostEqual(x2, 1.0, 0.01);
        assertAlmostEqual(x3, 16.5, 0.01);
        assertAlmostEqual(x4, 2.0, 0.01);
    });
});
