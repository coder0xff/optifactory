"""Controller for factory design logic - no GUI dependencies"""

import logging
from dataclasses import dataclass, field
from typing import Set, Dict, List, Tuple, Optional, Any

from factory import design_factory, Factory
from parsing_utils import parse_material_rate
from recipes import get_all_recipes_by_machine, get_recipes_for, Recipe

_LOGGER = logging.getLogger("satisgraphery")


@dataclass
class FactoryConfig:
    """Configuration for factory generation"""
    outputs: Dict[str, float]
    inputs: List[Tuple[str, float]]
    mines: List[Tuple[str, str]]  # (resource, purity)
    enabled_recipes: Set[str]
    input_costs_weight: float = 1.0
    machine_counts_weight: float = 0.0
    power_consumption_weight: float = 1.0
    design_power: bool = False


@dataclass
class ValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    warnings: List[str]
    errors: List[str]


@dataclass
class RecipeTreeNode:
    """Represents a recipe in the tree"""
    tree_id: str  # "recipe:{machine}:{recipe}"
    display_name: str
    is_enabled: bool
    is_visible: bool


@dataclass
class MachineTreeNode:
    """Represents a machine group in the tree"""
    tree_id: str  # "machine:{machine}"
    display_name: str
    recipes: List[RecipeTreeNode] = field(default_factory=list)
    check_state: str = 'unchecked'  # 'checked', 'unchecked', 'tristate'
    is_visible: bool = True


@dataclass
class RecipeTreeStructure:
    """Complete tree structure with all IDs and states"""
    machines: List[MachineTreeNode] = field(default_factory=list)


class FactoryController:
    """Stateful controller for factory design - single source of truth for all application state"""
    
    def __init__(self, economy: Dict[str, float]):
        """Initialize controller with economy values
        
        Args:
            economy: dict of item names to values
        """
        self.economy = economy
        
        # Configuration text state
        self._outputs_text = "Concrete:480"
        self._inputs_text = (
            "# Leave empty to auto-detect\n"
            "# Or specify like:\n"
            "# Limestone:480\n"
            "# Limestone:480\n"
            "# Limestone:480"
        )
        self._mines_text = ""
        
        # Recipe state
        self.enabled_recipes = self._get_default_enabled_recipes()
        self._recipe_search_text = ""
        
        # Optimization weights
        self._input_costs_weight = 1.0
        self._machine_counts_weight = 0.0
        self._power_consumption_weight = 1.0
        self._design_power = False
        
        # Generated factory (result)
        self._current_factory: Optional[Factory] = None
    
    # ========== State Getters ==========
    
    def get_outputs_text(self) -> str:
        """Get outputs configuration text"""
        return self._outputs_text
    
    def get_inputs_text(self) -> str:
        """Get inputs configuration text"""
        return self._inputs_text
    
    def get_mines_text(self) -> str:
        """Get mines configuration text"""
        return self._mines_text
    
    def get_recipe_search_text(self) -> str:
        """Get recipe search filter text"""
        return self._recipe_search_text
    
    def get_input_costs_weight(self) -> float:
        """Get input costs optimization weight"""
        return self._input_costs_weight
    
    def get_machine_counts_weight(self) -> float:
        """Get machine counts optimization weight"""
        return self._machine_counts_weight
    
    def get_power_consumption_weight(self) -> float:
        """Get power consumption optimization weight"""
        return self._power_consumption_weight
    
    def get_design_power(self) -> bool:
        """Get design power flag"""
        return self._design_power
    
    def get_current_factory(self) -> Optional[Factory]:
        """Get currently generated factory"""
        return self._current_factory
    
    def get_enabled_recipes(self) -> Set[str]:
        """Get set of enabled recipe names"""
        return self.enabled_recipes.copy()
    
    def get_graphviz_source(self) -> Optional[str]:
        """Get graphviz source from current factory
        
        Returns:
            Graphviz source string, or None if no factory generated
        """
        if self._current_factory is None or self._current_factory.network is None:
            return None
        return self._current_factory.network.source
    
    def get_all_recipes_by_machine(self) -> Dict[str, Dict[str, Recipe]]:
        """Get all recipes organized by machine
        
        Returns:
            Dict of {machine_name: {recipe_name: Recipe}}
        """
        return get_all_recipes_by_machine()
    
    def get_recipe_tooltip(self, recipe_name: str) -> Optional[str]:
        """Get formatted tooltip text for a recipe
        
        Args:
            recipe_name: Name of the recipe
            
        Returns:
            Formatted tooltip string, or None if recipe not found
        """
        # Find the recipe
        all_recipes = get_all_recipes_by_machine()
        for machine_recipes in all_recipes.values():
            if recipe_name in machine_recipes:
                recipe = machine_recipes[recipe_name]
                return self.format_recipe_tooltip(recipe)
        return None
    
    # ========== State Setters ==========
    
    def set_outputs_text(self, text: str):
        """Set outputs configuration text"""
        self._outputs_text = text
    
    def set_inputs_text(self, text: str):
        """Set inputs configuration text"""
        self._inputs_text = text
    
    def set_mines_text(self, text: str):
        """Set mines configuration text"""
        self._mines_text = text
    
    def set_recipe_search_text(self, text: str):
        """Set recipe search filter text"""
        self._recipe_search_text = text
    
    def set_input_costs_weight(self, value: float):
        """Set input costs optimization weight"""
        self._input_costs_weight = value
    
    def set_machine_counts_weight(self, value: float):
        """Set machine counts optimization weight"""
        self._machine_counts_weight = value
    
    def set_power_consumption_weight(self, value: float):
        """Set power consumption optimization weight"""
        self._power_consumption_weight = value
    
    def set_design_power(self, value: bool):
        """Set design power flag"""
        self._design_power = value
    
    def set_recipe_enabled(self, recipe_name: str, enabled: bool):
        """Enable or disable a recipe
        
        Args:
            recipe_name: Name of recipe to modify
            enabled: True to enable, False to disable
        """
        if enabled:
            self.enabled_recipes.add(recipe_name)
        else:
            self.enabled_recipes.discard(recipe_name)
    
    def set_recipes_enabled(self, recipe_names: Set[str]):
        """Set the complete set of enabled recipes
        
        Args:
            recipe_names: Set of recipe names to enable (all others disabled)
        """
        self.enabled_recipes = recipe_names.copy()
    
    # ========== Derived State / Queries ==========
    
    def should_show_power_warning(self) -> bool:
        """Check if power warning should be displayed
        
        Returns:
            True if design_power is enabled but no power recipes are enabled
        """
        if not self._design_power:
            return False
        
        power_recipes = get_recipes_for("MWm", self.enabled_recipes)
        return len(power_recipes) == 0
    
    # ========== Tree ID Management ==========
    
    @staticmethod
    def _make_machine_id(machine_name: str) -> str:
        """Generate stable tree ID for machine"""
        return f"machine:{machine_name}"
    
    @staticmethod
    def _make_recipe_id(machine_name: str, recipe_name: str) -> str:
        """Generate stable tree ID for recipe"""
        return f"recipe:{machine_name}:{recipe_name}"
    
    @staticmethod
    def _parse_recipe_id(tree_id: str) -> Optional[Tuple[str, str]]:
        """Parse recipe tree ID into (machine_name, recipe_name)
        
        Args:
            tree_id: Tree ID in format "recipe:{machine}:{recipe}"
            
        Returns:
            Tuple of (machine_name, recipe_name) or None if not a recipe ID
        """
        if tree_id.startswith("recipe:"):
            parts = tree_id[7:].split(":", 1)
            if len(parts) == 2:
                return parts[0], parts[1]
        return None
    
    def _recipe_matches_search(self, recipe_name: str, recipe: Recipe, search_text: str) -> bool:
        """Check if recipe matches search text
        
        Args:
            recipe_name: Name of the recipe
            recipe: Recipe object
            search_text: Lowercase search string
            
        Returns:
            True if recipe matches search criteria
        """
        if not search_text:
            return True
        
        return (
            search_text in recipe_name.lower()
            or any(search_text in inp.lower() for inp in recipe.inputs.keys())
            or any(search_text in out.lower() for out in recipe.outputs.keys())
        )
    
    def get_recipe_tree_structure(self) -> RecipeTreeStructure:
        """Get complete tree structure with IDs, states, and visibility
        
        Returns:
            RecipeTreeStructure ready for rendering
        """
        search_text = self._recipe_search_text.lower()
        machines = []
        
        for machine_name, recipes_dict in get_all_recipes_by_machine().items():
            recipe_nodes = []
            
            for recipe_name, recipe in recipes_dict.items():
                # Determine visibility based on search
                is_visible = self._recipe_matches_search(recipe_name, recipe, search_text)
                
                recipe_node = RecipeTreeNode(
                    tree_id=self._make_recipe_id(machine_name, recipe_name),
                    display_name=recipe_name,
                    is_enabled=recipe_name in self.enabled_recipes,
                    is_visible=is_visible
                )
                recipe_nodes.append(recipe_node)
            
            # Calculate machine state from visible recipes
            visible_recipes = [r for r in recipe_nodes if r.is_visible]
            if not visible_recipes:
                check_state = 'unchecked'
                is_visible = False
            else:
                enabled_count = sum(1 for r in visible_recipes if r.is_enabled)
                if enabled_count == 0:
                    check_state = 'unchecked'
                elif enabled_count == len(visible_recipes):
                    check_state = 'checked'
                else:
                    check_state = 'tristate'
                is_visible = True
            
            machine_node = MachineTreeNode(
                tree_id=self._make_machine_id(machine_name),
                display_name=machine_name,
                recipes=recipe_nodes,
                check_state=check_state,
                is_visible=is_visible
            )
            machines.append(machine_node)
        
        return RecipeTreeStructure(machines=machines)
    
    def on_recipe_toggled(self, recipe_tree_id: str, is_checked: bool):
        """Handle recipe toggle event
        
        Args:
            recipe_tree_id: Tree ID in format "recipe:{machine}:{recipe}"
            is_checked: New checked state
        """
        parsed = self._parse_recipe_id(recipe_tree_id)
        if parsed:
            _, recipe_name = parsed
            self.set_recipe_enabled(recipe_name, is_checked)
    
    def get_tooltip_for_tree_id(self, tree_id: str) -> Optional[str]:
        """Get tooltip text for a tree ID
        
        Args:
            tree_id: Tree ID (machine or recipe format)
            
        Returns:
            Tooltip text or None
        """
        parsed = self._parse_recipe_id(tree_id)
        if parsed:
            _, recipe_name = parsed
            return self.get_recipe_tooltip(recipe_name)
        return None
    
    # ========== Actions ==========
    
    def generate_factory_from_state(self) -> object:
        """Generate factory using current controller state
        
        Returns:
            graphviz_diagram suitable for display
            
        Raises:
            ValueError: If configuration is invalid or generation fails
        """
        _LOGGER.info("Generating factory...")
        
        # Parse configuration from text state
        outputs_list = self.parse_config_text(self._outputs_text)
        inputs_list = self.parse_config_text(self._inputs_text)
        
        # Build config from current state
        config = FactoryConfig(
            outputs=dict(outputs_list),
            inputs=inputs_list,
            mines=[],  # TODO: Parse mines if needed
            enabled_recipes=self.enabled_recipes,
            input_costs_weight=self._input_costs_weight,
            machine_counts_weight=self._machine_counts_weight,
            power_consumption_weight=self._power_consumption_weight,
            design_power=self._design_power
        )
        
        # Generate and cache result
        factory = self.generate_factory(config)
        self._current_factory = factory
        
        _LOGGER.info("Factory generated successfully")
        
        # Return graphviz diagram for display
        return factory.network
    
    def copy_graphviz_source(self) -> Optional[str]:
        """Get graphviz source for copying to clipboard
        
        Returns:
            graphviz_source or None if no factory available
        """
        source = self.get_graphviz_source()
        if source is None:
            _LOGGER.info("No graph to export")
            return None
        
        _LOGGER.info("Graphviz source copied to clipboard")
        return source
    
    # ========== Static Helper Methods ==========
    
    @staticmethod
    def _get_default_enabled_recipes() -> Set[str]:
        """Get default set of enabled recipes
        
        Excludes power generation and packager recipes by default
        
        Returns:
            Set of enabled recipe names
        """
        enabled = set()
        for machine_name, recipes in get_all_recipes_by_machine().items():
            for recipe_name, recipe in recipes.items():
                if "MWm" not in recipe.outputs and machine_name != "Packager":
                    enabled.add(recipe_name)
        return enabled
    
    @staticmethod
    def parse_config_text(text: str) -> List[Tuple[str, float]]:
        """Parse configuration text into list of (material, rate) tuples
        
        Format: Material:Rate, one per line
        Lines starting with # are comments and ignored
        Empty lines are ignored
        
        Args:
            text: Multi-line configuration text
            
        Returns:
            List of (material, rate) tuples
            
        Raises:
            ValueError: If parsing fails for any line
        """
        items = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            material, rate = parse_material_rate(line)
            items.append((material, rate))
        return items
    
    @staticmethod
    def format_recipe_tooltip(recipe: Recipe) -> str:
        """Format recipe inputs/outputs for display
        
        Args:
            recipe: Recipe to format
            
        Returns:
            Formatted string with inputs and outputs
        """
        lines = []
        
        if recipe.inputs:
            lines.append("Inputs:")
            for material, rate in recipe.inputs.items():
                lines.append(f"  - {material}: {rate}/min")
        
        if recipe.outputs:
            if lines:
                lines.append("")
            lines.append("Outputs:")
            for material, rate in recipe.outputs.items():
                lines.append(f"  - {material}: {rate}/min")
        
        return "\n".join(lines)
    
    def validate_config(self, config: FactoryConfig) -> ValidationResult:
        """Validate factory configuration
        
        Args:
            config: Factory configuration to validate
            
        Returns:
            ValidationResult with any warnings or errors
        """
        warnings = []
        errors = []
        
        # Check for empty outputs
        if not config.outputs:
            errors.append("No outputs specified")
        
        # Check for power design without power recipes
        if config.design_power:
            power_recipes = get_recipes_for("MWm", config.enabled_recipes)
            if not power_recipes:
                warnings.append("Power design enabled but no power-generating recipes are enabled")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            warnings=warnings,
            errors=errors
        )
    
    def generate_factory(self, config: FactoryConfig) -> Factory:
        """Generate factory from configuration
        
        Args:
            config: Factory configuration
            
        Returns:
            Generated Factory object
            
        Raises:
            ValueError: If configuration is invalid or generation fails
        """
        # Validate first
        validation = self.validate_config(config)
        if not validation.is_valid:
            raise ValueError("; ".join(validation.errors))
        
        # Generate factory
        return design_factory(
            outputs=config.outputs,
            inputs=config.inputs,
            mines=config.mines,
            enablement_set=config.enabled_recipes,
            economy=self.economy,
            input_costs_weight=config.input_costs_weight,
            machine_counts_weight=config.machine_counts_weight,
            power_consumption_weight=config.power_consumption_weight,
            design_power=config.design_power,
        )

