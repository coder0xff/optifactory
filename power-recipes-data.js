// Recipe data for Satisfactory
// All quantities are "per minute"

const POWER_RECIPES_DATA = {
    "Biomass Burner": {
        "Power (Leaves)": {
            "in": {
                "Leaves": 120.0
            },
            "out": {
                "MWm": 30.0
            }
        },
        "Power (Wood)": {
            "in": {
                "Wood": 18.0
            },
            "out": {
                "MWm": 30.0
            }
        },
        "Power (Biomass)": {
            "in": {
                "Solid Biofuel": 4.0
            },
            "out": {
                "MWm": 30.0
            }
        }
    },
    "Coal-Powered Generator": {
        "Coal Power": {
            "in": {
                "Coal": 15.0
            },
            "out": {
                "MWm": 75.0
            }
        }
    },
    "Fuel-Powered Generator": {
        "Power (Fuel)": {
            "in": {
                "Fuel": 20.0
            },
            "out": {
                "MWm": 250.0
            }
        },
        "Power (Liquid Biofuel)": {
            "in": {
                "Liquid Biofuel": 20.0
            },
            "out": {
                "MWm": 250.0
            }
        },
        "Power (Turbofuel)": {
            "in": {
                "Turbofuel": 7.5
            },
            "out": {
                "MWm": 250.0
            }
        },
        "Power (Rocket Fuel)": {
            "in": {
                "Rocket Fuel": 4.167
            },
            "out": {
                "MWm": 250.0
            }
        },
        "Power (Ionized Fuel)": {
            "in": {
                "Ionized Fuel": 3.0
            },
            "out": {
                "MWm": 250.0
            }
        }
    }
};

export { POWER_RECIPES_DATA };