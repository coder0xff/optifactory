#!/usr/bin/env node

/**
 * Test runner for all test modules
 * Usage: node run-tests.js
 */

import { runTests as runRecipesTests } from './test-recipes.js';
import { runTests as runBalancerTests } from './test-balancer.js';
import { runTests as runParsingUtilsTests } from './test-parsing-utils.js';
import { runTests as runGraphvizBuilderTests } from './test-graphviz-builder.js';
import { runTests as runEconomyTests } from './test-economy.js';
import { runTests as runEconomyControllerTests } from './test-economy-controller.js';
import { runTests as runFactoryControllerTests } from './test-factory-controller.js';
import { runTests as runLpSolverTests } from './test-lp-solver.js';
import { runTests as runFactoryTests } from './test-factory.js';
import { runTests as runOptimizeTests } from './test-optimize.js';

async function main() {
    console.log('Running Optifactory Test Suite\n');
    
    const allResults = [];
    
    // Run recipe tests
    console.log('Running test-recipes.js...');
    const recipesRunner = await runRecipesTests();
    const recipesResults = await recipesRunner.printResults();
    allResults.push({ name: 'test-recipes.js', ...recipesResults });
    
    // Run balancer tests
    console.log('Running test-balancer.js...');
    const balancerRunner = await runBalancerTests();
    const balancerResults = await balancerRunner.printResults();
    allResults.push({ name: 'test-balancer.js', ...balancerResults });
    
    // Run parsing utils tests
    console.log('Running test-parsing-utils.js...');
    const parsingUtilsRunner = await runParsingUtilsTests();
    const parsingUtilsResults = await parsingUtilsRunner.printResults();
    allResults.push({ name: 'test-parsing-utils.js', ...parsingUtilsResults });
    
    // Run graphviz builder tests
    console.log('Running test-graphviz-builder.js...');
    const graphvizBuilderRunner = await runGraphvizBuilderTests();
    const graphvizBuilderResults = await graphvizBuilderRunner.printResults();
    allResults.push({ name: 'test-graphviz-builder.js', ...graphvizBuilderResults });
    
    // Run economy tests
    console.log('Running test-economy.js...');
    const economyRunner = await runEconomyTests();
    const economyResults = await economyRunner.printResults();
    allResults.push({ name: 'test-economy.js', ...economyResults });
    
    // Run economy controller tests
    console.log('Running test-economy-controller.js...');
    const economyControllerRunner = await runEconomyControllerTests();
    const economyControllerResults = await economyControllerRunner.printResults();
    allResults.push({ name: 'test-economy-controller.js', ...economyControllerResults });
    
    // Run factory controller tests
    console.log('Running test-factory-controller.js...');
    const factoryControllerRunner = await runFactoryControllerTests();
    const factoryControllerResults = await factoryControllerRunner.printResults();
    allResults.push({ name: 'test-factory-controller.js', ...factoryControllerResults });

    console.log('Running test-lp-solver.js...');
    const lpSolverRunner = await runLpSolverTests();
    const lpSolverResults = await lpSolverRunner.printResults();
    allResults.push({ name: 'test-lp-solver.js', ...lpSolverResults });

    console.log('Running test-factory.js...');
    const factoryRunner = await runFactoryTests();
    const factoryResults = await factoryRunner.printResults();
    allResults.push({ name: 'test-factory.js', ...factoryResults });

    console.log('Running test-optimize.js...');
    const optimizeRunner = await runOptimizeTests();
    const optimizeResults = await optimizeRunner.printResults();
    allResults.push({ name: 'test-optimize.js', ...optimizeResults });
    
    // Overall summary
    const totalPass = allResults.reduce((sum, r) => sum + r.passCount, 0);
    const totalFail = allResults.reduce((sum, r) => sum + r.failCount, 0);
    const totalTests = totalPass + totalFail;
    
    console.log('\n' + '='.repeat(70));
    console.log('OVERALL SUMMARY');
    console.log('='.repeat(70));
    console.log(`Total: ${totalTests} tests, ${totalPass} passed, ${totalFail} failed`);
    console.log('='.repeat(70) + '\n');
    
    // Exit with error code if any tests failed
    if (totalFail > 0) {
        process.exit(1);
    }
}

main().catch(err => {
    console.error('Fatal error running tests:', err);
    process.exit(1);
});

