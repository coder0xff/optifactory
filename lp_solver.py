"""LP solver abstraction layer.

This module provides an abstraction for solving LP problems from text format.
In Python, uses the mip package. When porting to JavaScript, replace with HiGHS.
"""

import os
import tempfile

from mip import Model, OptimizationStatus as MipStatus


# Solver status constants - abstracted from mip
class SolverStatus:
    """Optimization status constants."""
    OPTIMAL = "OPTIMAL"
    INFEASIBLE = "INFEASIBLE"
    UNBOUNDED = "UNBOUNDED"
    FEASIBLE = "FEASIBLE"
    LOADED = "LOADED"
    ERROR = "ERROR"


class SolverResult:
    """Result from LP solver.
    
    Attributes:
        status: optimization status (SolverStatus constant)
        variable_values: dict mapping variable name to solution value
    """
    def __init__(self, status: str, variable_values: dict[str, float]):
        self.status = status
        self.variable_values = variable_values
    
    def is_optimal(self) -> bool:
        """Check if optimization succeeded."""
        return self.status == SolverStatus.OPTIMAL


def solve_lp(lp_text: str) -> SolverResult:
    """Solve LP problem from CPLEX LP format text.
    
    Precondition:
        lp_text is valid CPLEX LP format
    
    Postcondition:
        returns SolverResult with optimization status and variable values
    
    Args:
        lp_text: LP problem in CPLEX LP format
    
    Returns:
        SolverResult containing status and variable values
    """
    # Write LP text to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lp', delete=False) as f:
        f.write(lp_text)
        temp_lp_path = f.name
    
    try:
        # Load LP file with mip and optimize
        model = Model()
        model.verbose = 0
        model.read(temp_lp_path)
        model.optimize()
        
        # Extract variable values
        variable_values = {}
        for var in model.vars:
            if var.x is not None:
                variable_values[var.name] = var.x
        
        # Map mip status to abstracted status
        status_map = {
            MipStatus.OPTIMAL: SolverStatus.OPTIMAL,
            MipStatus.INFEASIBLE: SolverStatus.INFEASIBLE,
            MipStatus.UNBOUNDED: SolverStatus.UNBOUNDED,
            MipStatus.FEASIBLE: SolverStatus.FEASIBLE,
            MipStatus.LOADED: SolverStatus.LOADED,
        }
        status = status_map.get(model.status, SolverStatus.ERROR)
        
        return SolverResult(status, variable_values)
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_lp_path):
            os.remove(temp_lp_path)

