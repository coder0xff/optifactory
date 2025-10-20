"""Tests for LP solver abstraction."""

from lp_solver import solve_lp, SolverStatus


def test_simple_optimization():
    """Test basic LP problem solving."""
    # Simple problem: minimize x + y subject to x + y >= 10, x >= 0, y >= 0
    # Optimal solution: x=10, y=0 or x=0, y=10 (or any point on the line)
    lp_text = """\\Problem name: 

Minimize
OBJROW:  +1.0 x  +1.0 y
Subject To
constraint1:  +1.0 x  +1.0 y >= 10
Bounds
Integers
x y 
End"""
    
    result = solve_lp(lp_text)
    
    assert result.is_optimal()
    assert result.status == SolverStatus.OPTIMAL
    
    # Check that x + y = 10 (within tolerance)
    total = result.variable_values.get("x", 0) + result.variable_values.get("y", 0)
    assert abs(total - 10) < 0.01
    
    # Check objective value is 10
    assert abs(sum(result.variable_values.values()) - 10) < 0.01


def test_variable_extraction():
    """Test that variable values are correctly extracted."""
    # Problem with specific expected solution
    lp_text = """\\Problem name: 

Minimize
OBJROW:  +2.0 a  +3.0 b
Subject To
constraint1:  +1.0 a  +1.0 b >= 5
constraint2:  +1.0 a >= 2
Bounds
Integers
a b 
End"""
    
    result = solve_lp(lp_text)
    
    assert result.is_optimal()
    assert "a" in result.variable_values
    assert "b" in result.variable_values
    
    # Check constraints are satisfied
    a = result.variable_values["a"]
    b = result.variable_values["b"]
    assert a >= 2 - 0.01  # Allow small tolerance
    assert a + b >= 5 - 0.01


def test_multiple_variables():
    """Test LP with multiple variables."""
    lp_text = """\\Problem name: 

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
End"""
    
    result = solve_lp(lp_text)
    
    assert result.is_optimal()
    
    # Check all variables are in result
    assert "x1" in result.variable_values
    assert "x2" in result.variable_values
    assert "x3" in result.variable_values
    
    # Check constraints
    x1 = result.variable_values["x1"]
    x2 = result.variable_values["x2"]
    x3 = result.variable_values["x3"]
    
    assert x1 >= 3 - 0.01
    assert x2 >= 4 - 0.01
    assert x3 >= 5 - 0.01
    assert x1 + x2 + x3 >= 15 - 0.01
    
    # Since constraints force x1>=3, x2>=4, x3>=5, and x1+x2+x3>=15
    # The sum is at least 12, so we need at least 3 more
    # Optimal should be x1=3, x2=4, x3=8 (or similar)
    assert abs((x1 + x2 + x3) - 15) < 0.01


def test_infeasible_problem():
    """Test that infeasible problems are detected."""
    # Infeasible: x + y >= 10 and x + y <= 5
    lp_text = """\\Problem name: 

Minimize
OBJROW:  +1.0 x  +1.0 y
Subject To
c1:  +1.0 x  +1.0 y >= 10
c2:  -1.0 x  -1.0 y >= -5
Bounds
Integers
x y 
End"""
    
    result = solve_lp(lp_text)
    
    assert not result.is_optimal()
    assert result.status == SolverStatus.INFEASIBLE


def test_zero_variables():
    """Test that variables with zero values are included."""
    # Problem where one variable should be zero
    lp_text = """\\Problem name: 

Minimize
OBJROW:  +1.0 x  +100.0 y
Subject To
c1:  +1.0 x >= 5
Bounds
Integers
x y 
End"""
    
    result = solve_lp(lp_text)
    
    assert result.is_optimal()
    
    # x should be 5, y should be 0 (since it's expensive and not required)
    x = result.variable_values.get("x", 0)
    y = result.variable_values.get("y", 0)
    
    assert abs(x - 5) < 0.01
    assert abs(y - 0) < 0.01


def test_solver_result_attributes():
    """Test SolverResult attributes and methods."""
    lp_text = """\\Problem name: 

Minimize
OBJROW:  +1.0 x
Subject To
c1:  +1.0 x >= 1
Bounds
Integers
x 
End"""
    
    result = solve_lp(lp_text)
    
    # Check that result has expected attributes
    assert hasattr(result, "status")
    assert hasattr(result, "variable_values")
    assert hasattr(result, "is_optimal")
    
    # Check types
    assert isinstance(result.variable_values, dict)
    assert callable(result.is_optimal)
    
    # Check functionality
    assert result.is_optimal() == (result.status == SolverStatus.OPTIMAL)


def test_maximization_with_equality_and_bounds():
    """Test maximization problem with equality constraint and variable bounds."""
    lp_text = """\\Problem name: 

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
End"""
    
    result = solve_lp(lp_text)
    
    assert result.is_optimal()
    
    # Extract variable values
    x1 = result.variable_values.get("x1", 0)
    x2 = result.variable_values.get("x2", 0)
    x3 = result.variable_values.get("x3", 0)
    x4 = result.variable_values.get("x4", 0)
    
    assert abs(x1 - 17.5) < 0.01
    assert abs(x2 - 1.0) < 0.01
    assert abs(x3 - 16.5) < 0.01
    assert abs(x4 - 2.0) < 0.01
    
