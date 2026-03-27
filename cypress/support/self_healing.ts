/**
 * Cypress Self-Healing Locator Support
 *
 * Provides a custom `selfHeal()` helper that tries a prioritised list of
 * CSS/XPath selectors and returns the first one that finds an element.
 * When a fallback selector is used, the miss is logged so the team knows
 * to update the primary selector.
 *
 * Usage in a Page Object:
 *   import { selfHeal } from '../support/self_healing';
 *
 *   perform() {
 *     selfHeal(["[data-testid='btn']", "#btn", "button.submit"])
 *       .click();
 *   }
 *
 * Import in cypress/support/e2e.ts:
 *   import './self_healing';
 */

/**
 * Tries each selector in order and returns the first Cypress chainable that
 * finds at least one DOM element.
 *
 * @param selectors - Ordered list of CSS selectors (most specific first).
 * @param options   - Optional Cypress get() options forwarded to every attempt.
 */
export function selfHeal(
  selectors: string[],
  options?: Partial<Cypress.Loggable & Cypress.Timeoutable>,
): Cypress.Chainable<JQuery<HTMLElement>> {
  if (!selectors || selectors.length === 0) {
    throw new Error('[Self-Healing] No selectors provided.');
  }

  const tryNext = (index: number): Cypress.Chainable<JQuery<HTMLElement>> => {
    if (index >= selectors.length) {
      throw new Error(
        `[Self-Healing] All selectors exhausted. Tried: ${selectors.join(' | ')}`,
      );
    }

    const selector = selectors[index];

    return cy.get('body').then(($body) => {
      if ($body.find(selector).length > 0) {
        if (index > 0) {
          Cypress.log({
            name: 'Self-Healing',
            message: `Primary selector failed. Using fallback [${index}]: ${selector}`,
            consoleProps: () => ({ selectors, usedIndex: index }),
          });
        }
        return cy.get(selector, options);
      }

      Cypress.log({
        name: 'Self-Healing',
        message: `Selector [${index}] not found: ${selector}`,
        consoleProps: () => ({ selectors, failedIndex: index }),
      });
      return tryNext(index + 1);
    });
  };

  return tryNext(0);
}
