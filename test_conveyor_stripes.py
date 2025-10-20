"""Test conveyor and pipeline stripe generation."""

from factory import (
    _get_conveyor_mark,
    _get_conveyor_stripe_color,
    _get_pipeline_mark,
    _get_pipeline_stripe_color,
    _is_fluid,
    _get_edge_color,
)


def test_is_fluid():
    """Test fluid detection."""
    # Known fluids
    assert _is_fluid("Water") == True
    assert _is_fluid("Crude Oil") == True
    assert _is_fluid("Fuel") == True
    
    # Non-fluids
    assert _is_fluid("Iron Ore") == False
    assert _is_fluid("Iron Plate") == False
    assert _is_fluid("Copper Ingot") == False


def test_get_conveyor_mark():
    """Test conveyor mark determination based on flow rate."""
    # Mark 1: up to 60
    assert _get_conveyor_mark(30) == 1
    assert _get_conveyor_mark(60) == 1
    
    # Mark 2: up to 120
    assert _get_conveyor_mark(61) == 2
    assert _get_conveyor_mark(100) == 2
    assert _get_conveyor_mark(120) == 2
    
    # Mark 3: up to 270
    assert _get_conveyor_mark(121) == 3
    assert _get_conveyor_mark(200) == 3
    assert _get_conveyor_mark(270) == 3
    
    # Mark 4: up to 480
    assert _get_conveyor_mark(271) == 4
    assert _get_conveyor_mark(400) == 4
    assert _get_conveyor_mark(480) == 4
    
    # Above max should still return mark 4
    assert _get_conveyor_mark(500) == 4
    assert _get_conveyor_mark(1000) == 4


def test_get_pipeline_mark():
    """Test pipeline mark determination based on flow rate."""
    # Mark 1: up to 300
    assert _get_pipeline_mark(100) == 1
    assert _get_pipeline_mark(200) == 1
    assert _get_pipeline_mark(300) == 1
    
    # Mark 2: up to 600
    assert _get_pipeline_mark(301) == 2
    assert _get_pipeline_mark(450) == 2
    assert _get_pipeline_mark(600) == 2
    
    # Above max should still return mark 2
    assert _get_pipeline_mark(700) == 2
    assert _get_pipeline_mark(1000) == 2


def test_get_conveyor_stripe_color():
    """Test conveyor stripe color pattern generation."""
    # Mark 1: single black stripe
    assert _get_conveyor_stripe_color(1) == "black"
    
    # Mark 2: two black stripes separated by white
    assert _get_conveyor_stripe_color(2) == "black:white:black"
    
    # Mark 3: three black stripes
    assert _get_conveyor_stripe_color(3) == "black:white:black:white:black"
    
    # Mark 4: four black stripes
    assert _get_conveyor_stripe_color(4) == "black:white:black:white:black:white:black"


def test_get_pipeline_stripe_color():
    """Test pipeline stripe color pattern generation."""
    # Mark 1: grey:color:grey
    water_color = _get_pipeline_stripe_color(1, "Water")
    assert water_color == "grey:#7ab0d4:grey"
    
    fuel_color = _get_pipeline_stripe_color(1, "Fuel")
    assert fuel_color == "grey:#eb7d15:grey"
    
    # Mark 2: grey:color:color:grey
    water_color_mk2 = _get_pipeline_stripe_color(2, "Water")
    assert water_color_mk2 == "grey:#7ab0d4:#7ab0d4:grey"
    
    fuel_color_mk2 = _get_pipeline_stripe_color(2, "Fuel")
    assert fuel_color_mk2 == "grey:#eb7d15:#eb7d15:grey"


def test_get_edge_color():
    """Test unified edge color function."""
    # Conveyors for solids
    assert _get_edge_color("Iron Ore", 50) == "black"  # Mark 1
    assert _get_edge_color("Iron Plate", 100) == "black:white:black"  # Mark 2
    
    # Pipelines for fluids
    assert _get_edge_color("Water", 200) == "grey:#7ab0d4:grey"  # Mark 1 pipeline
    assert _get_edge_color("Fuel", 400) == "grey:#eb7d15:#eb7d15:grey"  # Mark 2 pipeline


if __name__ == "__main__":
    test_is_fluid()
    test_get_conveyor_mark()
    test_get_pipeline_mark()
    test_get_conveyor_stripe_color()
    test_get_pipeline_stripe_color()
    test_get_edge_color()
    print("All tests passed!")

