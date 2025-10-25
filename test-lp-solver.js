import { solve_lp, SolverResult } from './lp-solver.js';
import {
    TestRunner,
    assertEquals,
    assertNotNull,
    assertGreaterThan,
    assertLessThan,
    assertAlmostEqual,
    assertTrue
} from './test-framework.js';

export async function runTests() {
    const runner = new TestRunner();
    const test = (name, fn) => runner.test(name, fn);
    
    // Test: simple optimization
    await test('simple optimization', async () => {
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
        
        assertTrue(result.is_optimal(), 'Result should be optimal');
        assertEquals(result.status, 'Optimal', 'Status should be Optimal');
        
        // Check that x + y = 10 (within tolerance)
        const total = (result.variable_values["x"] || 0) + (result.variable_values["y"] || 0);
        assertAlmostEqual(total, 10, 0.01, 'x + y should equal 10');
        
        // Check objective value is 10
        const obj_value = Object.values(result.variable_values).reduce((a, b) => a + b, 0);
        assertAlmostEqual(obj_value, 10, 0.01, 'Objective value should be 10');
        
        return 'Simple optimization works';
    });
    
    // Test: variable extraction
    await test('variable extraction', async () => {
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
        
        assertTrue(result.is_optimal(), 'Result should be optimal');
        assertTrue('a' in result.variable_values, 'Variable a should be in result');
        assertTrue('b' in result.variable_values, 'Variable b should be in result');
        
        // Check constraints are satisfied
        const a = result.variable_values["a"];
        const b = result.variable_values["b"];
        assertTrue(a >= 2 - 0.01, 'a >= 2');
        assertTrue(a + b >= 5 - 0.01, 'a + b >= 5');
        
        return 'Variable extraction works';
    });
    
    // Test: multiple variables
    await test('multiple variables', async () => {
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
        
        assertTrue(result.is_optimal(), 'Result should be optimal');
        
        // Check all variables are in result
        assertTrue('x1' in result.variable_values, 'x1 should be in result');
        assertTrue('x2' in result.variable_values, 'x2 should be in result');
        assertTrue('x3' in result.variable_values, 'x3 should be in result');
        
        // Check constraints
        const x1 = result.variable_values["x1"];
        const x2 = result.variable_values["x2"];
        const x3 = result.variable_values["x3"];
        
        assertTrue(x1 >= 3 - 0.01, 'x1 >= 3');
        assertTrue(x2 >= 4 - 0.01, 'x2 >= 4');
        assertTrue(x3 >= 5 - 0.01, 'x3 >= 5');
        assertTrue(x1 + x2 + x3 >= 15 - 0.01, 'x1 + x2 + x3 >= 15');
        
        // Since constraints force x1>=3, x2>=4, x3>=5, and x1+x2+x3>=15
        // The sum is at least 12, so we need at least 3 more
        // Optimal should be x1=3, x2=4, x3=8 (or similar)
        assertAlmostEqual(x1 + x2 + x3, 15, 0.01, 'Sum should be 15');
        
        return 'Multiple variables work';
    });
    
    // Test: infeasible problem
    await test('infeasible problem', async () => {
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
        
        assertTrue(!result.is_optimal(), 'Result should not be optimal');
        assertEquals(result.status, 'Infeasible', 'Status should be Infeasible');
        
        return 'Infeasible problem detected';
    });
    
    // Test: zero variables
    await test('zero variables', async () => {
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
        
        assertTrue(result.is_optimal(), 'Result should be optimal');
        
        // x should be 5, y should be 0 (since it's expensive and not required)
        const x = result.variable_values["x"] || 0;
        const y = result.variable_values["y"] || 0;
        
        assertAlmostEqual(x, 5, 0.01, 'x should be 5');
        assertAlmostEqual(y, 0, 0.01, 'y should be 0');
        
        return 'Zero variables handled correctly';
    });
    
    // Test: solver result attributes
    await test('solver result attributes', async () => {
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
        assertNotNull(result.status, 'Result has status');
        assertNotNull(result.variable_values, 'Result has variable_values');
        assertTrue(typeof result.is_optimal === 'function', 'Result has is_optimal method');
        
        // Check types
        assertTrue(typeof result.variable_values === 'object', 'variable_values is object');
        
        // Check functionality
        assertEquals(result.is_optimal(), result.status === 'Optimal', 
            'is_optimal() matches status');
        
        return 'SolverResult attributes work';
    });
    
    // Test: maximization with equality and bounds
    await test('maximization with equality and bounds', async () => {
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
        
        assertTrue(result.is_optimal(), 'Result should be optimal');
        
        // Extract variable values
        const x1 = result.variable_values["x1"] || 0;
        const x2 = result.variable_values["x2"] || 0;
        const x3 = result.variable_values["x3"] || 0;
        const x4 = result.variable_values["x4"] || 0;
        
        assertAlmostEqual(x1, 17.5, 0.01, 'x1 should be 17.5');
        assertAlmostEqual(x2, 1.0, 0.01, 'x2 should be 1.0');
        assertAlmostEqual(x3, 16.5, 0.01, 'x3 should be 16.5');
        assertAlmostEqual(x4, 2.0, 0.01, 'x4 should be 2.0');
        
        return 'Maximization with equality and bounds works';
    });
    
    return runner;
}

