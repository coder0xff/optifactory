#!/usr/bin/env node

/**
 * Debug helper - runs a single test module
 * Usage: node debug-test.js test-factory-controller
 */

const moduleName = process.argv[2] || 'test-factory-controller';
const modulePath = `./${moduleName}.js`;

console.log(`Debugging ${modulePath}...\n`);

import(modulePath)
    .then(module => module.runTests())
    .then(runner => runner.printResults())
    .catch(err => {
        console.error('Error:', err);
        process.exit(1);
    });

