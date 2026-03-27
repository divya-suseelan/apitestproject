import { defineConfig } from 'cypress';
import { addCucumberPreprocessorPlugin } from '@badeball/cypress-cucumber-preprocessor';
import { createEsbuildPlugin } from '@badeball/cypress-cucumber-preprocessor/esbuild';
import createBundler from '@bahmutov/cypress-esbuild-bundler';

export default defineConfig({
  e2e: {
    baseUrl: process.env.BASE_URL || 'http://localhost:3000',
    specPattern: 'cypress/e2e/**/*.{cy.ts,cy.js,feature}',
    supportFile: 'cypress/support/e2e.ts',
    screenshotsFolder: 'cypress/screenshots',
    videosFolder: 'cypress/videos',

    async setupNodeEvents(on, config) {
      // Required for @badeball/cypress-cucumber-preprocessor
      await addCucumberPreprocessorPlugin(on, config);

      on(
        'file:preprocessor',
        createBundler({
          plugins: [createEsbuildPlugin(config)],
        }),
      );

      return config;
    },

    reporter: 'junit',
    reporterOptions: {
      mochaFile: 'output/cypress-results/results-[hash].xml',
      toConsole: true,
    },
  },
});
