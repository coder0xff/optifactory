// Recipe data for Satisfactory
// All quantities are "per minute"

const RECIPES_DATA = {
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
    "Smelter": {
        "Iron Ingot": {
            "in": {
                "Iron Ore": 30.0
            },
            "out": {
                "Iron Ingot": 30.0
            }
        },
        "Copper Ingot": {
            "in": {
                "Copper Ore": 30.0
            },
            "out": {
                "Copper Ingot": 30.0
            }
        },
        "Caterium Ingot": {
            "in": {
                "Caterium Ore": 45.0
            },
            "out": {
                "Caterium Ingot": 15.0
            }
        }
    },
    "Constructor": {
        "Iron Plate": {
            "in": {
                "Iron Ingot": 30.0
            },
            "out": {
                "Iron Plate": 20.0
            }
        },
        "Iron Rod": {
            "in": {
                "Iron Ingot": 15.0
            },
            "out": {
                "Iron Rod": 15.0
            }
        },
        "Screws": {
            "in": {
                "Iron Rod": 10.0
            },
            "out": {
                "Screws": 40.0
            }
        },
        "Copper Sheet": {
            "in": {
                "Copper Ingot": 20.0
            },
            "out": {
                "Copper Sheet": 10.0
            }
        },
        "Steel Beam": {
            "in": {
                "Steel Ingot": 60.0
            },
            "out": {
                "Steel Beam": 15.0
            }
        },
        "Steel Pipe": {
            "in": {
                "Steel Ingot": 30.0
            },
            "out": {
                "Steel Pipe": 20.0
            }
        },
        "Wire": {
            "in": {
                "Copper Ingot": 15.0
            },
            "out": {
                "Wire": 30.0
            }
        },
        "Cable": {
            "in": {
                "Wire": 60.0
            },
            "out": {
                "Cable": 30.0
            }
        },
        "Quickwire": {
            "in": {
                "Caterium Ingot": 12.0
            },
            "out": {
                "Quickwire": 60.0
            }
        },
        "Reanimated SAM": {
            "in": {
                "SAM": 120.0
            },
            "out": {
                "Reanimated SAM": 30.0
            }
        },
        "Concrete": {
            "in": {
                "Limestone": 45.0
            },
            "out": {
                "Concrete": 15.0
            }
        },
        "Quartz Crystal": {
            "in": {
                "Raw Quartz": 37.5
            },
            "out": {
                "Quartz Crystal": 22.5
            }
        },
        "Silica": {
            "in": {
                "Raw Quartz": 22.5
            },
            "out": {
                "Silica": 37.5
            }
        },
        "Biomass (Leaves)": {
            "in": {
                "Leaves": 120.0
            },
            "out": {
                "Biomass": 60.0
            }
        },
        "Biomass (Wood)": {
            "in": {
                "Wood": 60.0
            },
            "out": {
                "Biomass": 300.0
            }
        },
        "Biomass (Mycelia)": {
            "in": {
              "Mycelia": 15.0
            },
            "out": {
              "Biomass": 150.0
            }
        },
        "Biomass (Alien Protein)": {
            "in": {
                "Alien Protein": 1.0
            },
            "out": {
                "Biomass": 100.0
            }
        },
        "Solid Biofuel": {
            "in": {
                "Biomass": 120.0
            },
            "out": {
                "Solid Biofuel": 60.0
            }
        },
        "Emtpy Canister": {
            "in": {
                "Plastic": 30.0
            },
            "out": {
                "Empty Canister": 60.0
            }
        },
        "Hog Protein": {
            "in": {
                "Hog Remains": 20.0
            },
            "out": {
                "Alien Protein": 20.0
            }
        },
        "Hatcher Protein": {
            "in": {
                "Hatcher Remains": 20.0
            },
            "out": {
                "Alien Protein": 20.0
            }
        },
        "Stinger Protein": {
            "in": {
                "Stinger Remains": 20.0
            },
            "out": {
                "Alien Protein": 20.0
            }
        },
        "Spitter Protein": {
            "in": {
                "Spitter Remains": 20.0
            },
            "out": {
                "Alien Protein": 20.0
            }
        },
        "Alien DNA Capsule": {
            "in": {
                "Alien Protein": 10.0
            },
            "out": {
                "Alien DNA Capsule": 10.0
            }
        },
        "Power Shard (1)": {
            "in": {
                "Blue Power Slug": 7.5
            },
            "out": {
                "Power Shard": 7.5
            }
        },
        "Power Shard (2)": {
            "in": {
                "Yellow Power Slug": 5.0
            },
            "out": {
                "Power Shard": 10.0
            }
        },
        "Power Shard (3)": {
            "in": {
                "Purple Power Slug": 2.5
            },
            "out": {
                "Power Shard": 12.5
            }
        },
        "Iron Rebar": {
            "in": {
                "Iron Rod": 15.0
            },
            "out": {
                "Iron Rebar": 15.0
            }
        },
        "Alternate: Steel Rod": {
            "in": {
                "Steel Ingot": 12.0
            },
            "out": {
                "Iron Rod": 48.0
            }
        },
        "Alternate: Cast Screws": {
            "in": {
                "Iron Ingot": 12.5
            },
            "out": {
                "Screws": 50.0
            }
        },
        "Alternate: Steel Screws": {
            "in": {
                "Steel Beam": 5.0
            },
            "out": {
                "Screws": 260.0
            }
        },
        "Alternate: Iron Pipe": {
            "in": {
                "Iron Ingot": 100.0
            },
            "out": {
                "Steel Pipe": 25.0
            }
        },
        "Alternate: Biocoal": {
            "in": {
                "Biomass": 37.5
            },
            "out": {
                "Coal": 45.0
            }
        },
        "Alternate: Charcoal": {
            "in": {
                "Wood": 15.0
            },
            "out": {
                "Coal": 150.0
            }
        },
        "Alternate: Steel Canister": {
            "in": {
                "Steel Ingot": 40.0
            },
            "out": {
                "Empty Canister": 40.0
            }
        }
    },
    "Foundry": {
        "Steel Ingot": {
            "in": {
                "Iron Ore": 45.0,
                "Coal": 45.0
            },
            "out": {
                "Steel Ingot": 45.0
            }
        },
        "Alternate: Solid Steel Ingot": {
            "in": {
                "Iron Ingot": 40.0,
                "Coal": 40.0
            },
            "out": {
                "Steel Ingot": 60.0
            }
        },
        "Alternate: Coke Steel Ingot": {
            "in": {
                "Iron Ore": 75.0,
                "Petroleum Coke": 75.0
            },
            "out": {
                "Steel Ingot": 100.0
            }
        },
        "Alternate: Compacted Steel Ingot": {
            "in": {
                "Iron Ore": 5.0,
                "Compacted Coal": 2.5
            },
            "out": {
                "Steel Ingot": 10.0
            }
        },
        "Alternate: Steel Cast Plate": {
            "in": {
                "Iron Ingot": 15.0,
                "Steel Ingot": 15.0
            },
            "out": {
                "Iron Plate": 45.0
            }
        },
        "Alternate: Molded Beam": {
            "in": {
                "Steel Ingot": 120.0,
                "Concrete": 80.0
            },
            "out": {
                "Steel Beam": 45.0
            }
        },
        "Alternate: Molded Steel Pipe": {
            "in": {
                "Steel Ingot": 5.0,
                "Concrete": 30.0
            },
            "out": {
                "Steel Pipe": 50.0
            }
        }
    },
    "Assembler": {
        "Smart Plating": {
            "in": {
                "Reinforced Iron Plate": 2.0,
                "Rotor": 2.0
            },
            "out": {
                "Smart Plating": 2.0
            }
        },
        "Versatile Framework": {
            "in": {
                "Modular Frame": 2.5,
                "Steel Beam": 30.0
            },
            "out": {
                "Versatile Framework": 5.0
            }
        },
        "Automated Wiring": {
            "in": {
                "Stator": 2.5,
                "Cable": 50.0
            },
            "out": {
                "Automated Wiring": 2.5
            }
        },
        "Reinforced Iron Plate": {
            "in": {
                "Iron Plate": 30.0,
                "Screws": 60.0
            },
            "out": {
                "Reinforced Iron Plate": 5.0
            }
        },
        "Modular Frame": {
            "in": {
                "Reinforced Iron Plate": 3.0,
                "Iron Rod": 12.0
            },
            "out": {
                "Modular Frame": 2.0
            }
        },
        "Encased Industrial Beam": {
            "in": {
                "Steel Beam": 18.0,
                "Concrete": 36.0
            },
            "out": {
                "Encased Industrial Beam": 6.0
            }
        },
        "Circuit Board": {
            "in": {
                "Copper Sheet": 15.0,
                "Plastic": 30.0
            },
            "out": {
                "Circuit Board": 7.5
            }
        },
        "AI Limiter": {
            "in": {
                "Copper Sheet": 25.0,
                "Quickwire": 100.0
            },
            "out": {
                "AI Limiter": 5.0
            }
        },
        "Fabric": {
            "in": {
                "Mycelia": 15.0,
                "Biomass": 75.0
            },
            "out": {
                "Fabric": 15.0
            }
        },
        "Rotor": {
            "in": {
                "Iron Rod": 20.0,
                "Screws": 100.0
            },
            "out": {
                "Rotor": 4.0
            }
        },
        "Stator": {
            "in": {
                "Steel Pipe": 15.0,
                "Wire": 8.0
            },
            "out": {
                "Stator": 5.0
            }
        },
        "Motor": {
            "in": {
                "Rotor": 10.0,
                "Stator": 10.0
            },
            "out": {
                "Motor": 5.0
            }
        },
        "Black Powder": {
            "in": {
                "Coal": 15.0,
                "Sulfur": 15.0
            },
            "out": {
                "Black Powder": 30.0
            }
        },
        "Stun Rebar": {
            "in": {
                "Iron Rebar": 10.0,
                "Quickwire": 50.0
            },
            "out": {
                "Stun Rebar": 10.0
            }
        },
        "Shatter Rebar": {
            "in": {
                "Iron Rebar": 10.0,
                "Quartz Crystal": 15.0
            },
            "out": {
                "Shatter Rebar": 5.0
            }
        },
        "Nobelisk": {
            "in": {
                "Black Powder": 20.0,
                "Steel Pipe": 20.0
            },
            "out": {
                "Nobelisk": 10.0
            }
        },
        "Gas Nobelisk": {
            "in": {
                "Nobelisk": 5.0,
                "Biomass": 50.0
            },
            "out": {
                "Gas Nobelisk": 5.0
            }
        },
        "Pulse Nobelisk": {
            "in": {
                "Nobelisk": 5.0,
                "Crystal Oscillator": 1.0
            },
            "out": {
                "Pulse Nobelisk": 5.0
            }
        },
        "Rifle Ammo": {
            "in": {
                "Copper Sheet": 15.0,
                "Smokeless Powder": 10.0
            },
            "out": {
                "Rifle Ammo": 75.0
            }
        },
        "Alternate: Bolted Iron Plate": {
            "in": {
                "Iron Plate": 90.0,
                "Screws": 250.0
            },
            "out": {
                "Reinforced Iron Plate": 15.0
            }
        },
        "Alternate: Adhered Iron Plate": {
            "in": {
                "Iron Plate": 11.25,
                "Rubber": 3.75
            },
            "out": {
                "Reinforced Iron Plate": 3.75
            }
        },
        "Alternate: Bolted Frame": {
            "in": {
                "Reinforced Iron Plate": 7.5,
                "Screws": 140.0
            },
            "out": {
                "Modular Frame": 5.0
            }
        },
        "Alternate: Steeled Frame": {
            "in": {
                "Reinforced Iron Plate": 2.0,
                "Steel Pipe": 10.0
            },
            "out": {
                "Modular Frame": 3.0
            }
        },
        "Alternate: Caterium Circuit Board": {
            "in": {
                "Plastic": 12.5,
                "Quickwire": 37.5
            },
            "out": {
                "Circuit Board": 8.75
            }
        },
        "Alternate: Plastic AI Limiter": {
            "in": {
                "Quickwire": 120.0,
                "Plastic": 28.0
            },
            "out": {
                "AI Limiter": 8.0
            }
        },
        "Alternate: Compacted Coal": {
            "in": {
                "Coal": 25.0,
                "Sulfur": 25.0
            },
            "out": {
                "Compacted Coal": 25.0
            }
        },
        "Alternate: Coppor Rotor": {
            "in": {
                "Copper Sheet": 22.5,
                "Screws": 195.0
            },
            "out": {
                "Rotor": 11.25
            }
        },
        "Alternate: Steel Rotor": {
            "in": {
                "Steel Pipe": 10.0,
                "Wire": 30.0
            },
            "out": {
                "Rotor": 5.0
            }
        }        
    },
    "Manufacturer": {
        "Modular Engine": {
            "in": {
                "Motor": 2.0,
                "Rubber": 15.0,
                "Smart Plating": 2.0
            },
            "out": {
                "Modular Engine": 1.0
            }
        },
        "Adaptive Control Unit": {
            "in": {
                "Automated Wiring": 5.0,
                "Circuit Board": 5.0,
                "Heavy Modular Frame": 1.0,
                "Computer": 2.0
            },
            "out": {
                "Adaptive Control Unit": 1.0
            }
        },
        "Heavy Modular Frame": {
            "in": {
                "Modular Frame": 10.0,
                "Steel Pipe": 40.0,
                "Encased Industrial Beam": 10.0,
                "Screws": 120.0
            },
            "out": {
                "Heavy Modular Frame": 2.0
            }
        },
        "High-Speed Connector": {
            "in": {
                "Quickwire": 210.0,
                "Cable": 37.5,
                "Circuit Board": 3.75
            },
            "out": {
                "High-Speed Connector": 3.75
            }
        },
        "SAM Fluctuator": {
            "in": {
                "Reanimated SAM": 60.0,
                "Wire": 50.0,
                "Steel Pipe": 30.0
            },
            "out": {
                "SAM Fluctuator": 10.0
            }
        },
        "Computer": {
            "in": {
                "Circuit Board": 10.0,
                "Cable": 20.0,
                "Plastic": 40.0
            },
            "out": {
                "Computer": 2.5
            }
        },
        "Crystal Oscillator": {
            "in": {
                "Quartz Crystal": 18.0,
                "Cable": 14.0,
                "Reinforced Iron Plate": 2.5
            },
            "out": {
                "Crystal Oscillator": 1.0
            }
        },
        "Gas Filter": {
            "in": {
                "Fabric": 15.0,
                "Coal": 30.0,
                "Iron Plate": 15.0
            },
            "out": {
                "Gas Filter": 7.5
            }
        },
        "Alternate: Heavy Encased Frame": {
            "in": {
                "Modular Frame": 7.5,
                "Encased Industrial Beam": 9.375,
                "Steel Pipe": 33.75,
                "Concrete": 20.625
            },
            "out": {
                "Heavy Modular Frame": 2.813
            }
        },
        "Alternate: Heavy Flexible Frame": {
            "in": {
                "Modular Frame": 18.75,
                "Encased Industrial Beam": 11.25,
                "Rubber": 75.0,
                "Screws": 390.0
            },
            "out": {
                "Heavy Modular Frame": 3.75
            }
        },
        "Alternate: Silicon High-Speed Connector": {
            "in": {
                "Quickwire": 90.0,
                "Silica": 37.5,
                "Circuit Board": 3.0
            },
            "out": {
                "High-Speed Connector": 3.0
            }
        },
        "Alternate: Caterium Computer": {
            "in": {
                "Circuit Board": 15.0,
                "Quickwire": 52.5,
                "Rubber": 22.5
            },
            "out": {
                "Computer": 3.75
            }
        },
        "Alternate: Insulated Crystal Oscillator": {
            "in": {
                "Quartz Crystal": 18.75,
                "Rubber": 13.125,
                "AI Limiter": 1.875
            },
            "out": {
                "Crystal Oscillator": 1.875
            }
        }
    },
    "Refinery": {
        "Plastic": {
            "in": {
                "Crude Oil": 30.0
            },
            "out": {
                "Plastic": 20.0,
                "Heavy Oil Residue": 10.0
            }
        },
        "Residual Plastic": {
            "in": {
                "Polymer Resin": 60.0,
                "Water": 20.0
            },
            "out": {
                "Plastic": 20.0
            }
        },
        "Rubber": {
            "in": {
                "Crude Oil": 30.0
            },
            "out": {
                "Rubber": 2.0,
                "Heavy Oil Residue": 20.0
            }
        },
        "Residual Rubber": {
            "in": {
                "Polymer Resin": 40.0,
                "Water": 40.0
            },
            "out": {
                "Rubber": 20.0
            }
        },
        "Petroleum Coke": {
            "in": {
                "Heavy Oil Residue": 40.0
            },
            "out": {
                "Petroleum Coke": 120.0
            }
        },
        "Fuel": {
            "in": {
                "Crude Oil": 60.0
            },
            "out": {
                "Fuel": 40.0,
                "Polymer Resin": 30.0
            }
        },
        "Residual Fuel": {
            "in": {
                "Heavy Oil Residue": 60.0
            },
            "out": {
                "Fuel": 40.0
            }
        },
        "Liquid Biofuel": {
            "in": {
                "Solid Biofuel": 90.0,
                "Water": 45.0
            },
            "out": {
                "Liquid Biofuel": 60.0
            }
        },
        "Residual Smokeless Powder": {
            "in": {
                "Black Powder": 20.0,
                "Heavy Oil Residue": 10.0
            },
            "out": {
                "Smokeless Powder": 20.0
            }
        },
        "Alternate: Recycled Plastic": {
            "in": {
                "Rubber": 30.0,
                "Fuel": 30.0
            },
            "out": {
                "Plastic": 60.0
            }
        },
        "Alternate: Recycled Rubber": {
            "in": {
                "Plastic": 30.0,
                "Fuel": 30.0
            },
            "out": {
                "Rubber": 60.0
            }
        },
        "Alternate: Heavy Oil Residue": {
            "in": {
                "Crude Oil": 30.0
            },
            "out": {
                "Heavy Oil Residue": 40.0,
                "Polymer Resin": 20.0
            }
        },
        "Alternate: Diluted Packaged Fuel": {
            "in": {
                "Heavy Oil Residue": 30.0,
                "Packaged Water": 60.0
            },
            "out": {
                "Packaged Fuel": 60.0
            }
        },
        "Alternate: Turbo Heavy Fuel": {
            "in": {
                "Heavy Oil Residue": 37.5,
                "Compacted Coal": 30.0
            },
            "out": {
                "Turbofuel": 30.0
            }
        },
        "Alternate: Pure Iron Ingot": {
            "in": {
                "Iron Ore": 35.0,
                "Water": 20.0
            },
            "out": {
                "Iron Ingot": 65.0
            }
        },
        "Alternate: Pure Copper Ingot": {
            "in": {
                "Copper Ore": 15.0,
                "Water": 10.0
            },
            "out": {
                "Copper Ingot": 37.5
            }
        },
        "Alternate: Pure Caterium Ingot": {
            "in": {
                "Caterium Ore": 24.0,
                "Water": 24.0
            },
            "out": {
                "Caterium Ingot": 12.0
            }
        },
        "Alternate: Wet Concrete": {
            "in": {
                "Limestone": 120.0,
                "Water": 100.0
            },
            "out": {
                "Concrete": 80.0
            }
        },
        "Alternate: Steamed Copper Sheet": {
            "in": {
                "Copper Ingot": 22.5,
                "Water": 22.5
            },
            "out": {
                "Copper Sheet": 22.5
            }
        },
        "Alternate: Polyester Fabric": {
            "in": {
                "Polymer Resin": 30.0,
                "Water": 30.0
            },
            "out": {
                "Fabric": 30.0
            }
        }
    },
    "Packager": {
        "Packaged Water": {
            "in": {
                "Water": 60.0,
                "Empty Canister": 60.0
            },
            "out": {
                "Packaged Water": 60.0
            }
        },
        "Packaged Oil": {
            "in": {
                "Crude Oil": 30.0,
                "Empty Canister": 30.0
            },
            "out": {
                "Packaged Oil": 30.0
            }
        },
        "Packaged Heavy Oil Residue": {
            "in": {
                "Heavy Oil Residue": 30.0,
                "Empty Canister": 30.0
            },
            "out": {
                "Packaged Heavy Oil Residue": 30.0
            }
        },
        "Packaged Liquid Biofuel": {
            "in": {
                "Liquid Biofuel": 40.0,
                "Empty Canister": 40.0
            },
            "out": {
                "Packaged Liquid Biofuel": 40.0
            }
        },
        "Packaged Fuel": {
            "in": {
                "Fuel": 40.0,
                "Empty Canister": 40.0
            },
            "out": {
                "Packaged Fuel": 40.0
            }
        },
        "Packaged Turbofuel": {
            "in": {
                "Turbofuel": 20.0,
                "Empty Canister": 20.0
            },
            "out": {
                "Packaged Turbofuel": 20.0
            }
        },
        "Unpackage Water": {
            "in": {
                "Packaged Water": 120.0
            },
            "out": {
                "Water": 120.0,
                "Empty Canister": 120.0
            }
        },
        "Unpackage Oil": {
            "in": {
                "Packaged Oil": 60.0
            },
            "out": {
                "Crude Oil": 60.0,
                "Empty Canister": 60.0
            }
        },
        "Unpackage Heavy Oil Residue": {
            "in": {
                "Packaged Heavy Oil Residue": 20.0
            },
            "out": {
                "Heavy Oil Residue": 20.0,
                "Empty Canister": 20.0
            }
        },
        "Unpackage Liquid Biofuel": {
            "in": {
                "Packaged Liquid Biofuel": 60.0
            },
            "out": {
                "Liquid Biofuel": 60.0,
                "Empty Canister": 60.0
            }
        },
        "Unpackage Fuel": {
            "in": {
                "Packaged Fuel": 60.0
            },
            "out": {
                "Fuel": 60.0,
                "Empty Canister": 60.0
            }
        },
        "Unpackage Turbofuel": {
            "in": {
                "Packaged Turbofuel": 20.0
            },
            "out": {
                "Turbofuel": 20.0,
                "Empty Canister": 20.0
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

export { RECIPES_DATA };