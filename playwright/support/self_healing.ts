/**
 * Playwright Self-Healing Locator Support
 *
 * Provides a `findElement()` helper that tries a prioritised list of
 * CSS/XPath selectors and returns the first Locator that is attached to
 * the DOM. When a fallback selector is used, the miss is logged to the
 * console so the team knows to update the primary selector.
 *
 * Usage in a Page Object:
 *   import { findElement } from '../support/self_healing';
 *
 *   async perform(page: Page) {
 *     const el = await findElement(page, [
 *       "[data-testid='submit']",
 *       "button[type='submit']",
 *       "#submit-btn",
 *     ]);
 *     await el.click();
 *   }
 */

import { type Locator, type Page } from '@playwright/test';

/** How long (ms) to wait for an element to be attached before giving up. */
const PROBE_TIMEOUT_MS = 2_000;

/**
 * Tries each selector in order and returns the first Locator that is
 * attached to the DOM within {@link PROBE_TIMEOUT_MS}.
 *
 * @param page      - Playwright Page instance.
 * @param selectors - Ordered list of CSS / XPath selectors (most specific first).
 * @returns         The resolved Locator.
 * @throws          Error when all selectors are exhausted.
 */
export async function findElement(page: Page, selectors: string[]): Promise<Locator> {
  if (!selectors || selectors.length === 0) {
    throw new Error('[Self-Healing] No selectors provided.');
  }

  for (let i = 0; i < selectors.length; i++) {
    const selector = selectors[i];
    try {
      const locator = page.locator(selector);
      await locator.waitFor({ state: 'attached', timeout: PROBE_TIMEOUT_MS });

      if (i > 0) {
        console.warn(
          `[Self-Healing] Primary selector failed. Using fallback [${i}]: "${selector}". ` +
          `Tried: ${selectors.slice(0, i).join(' | ')}`,
        );
      }
      return locator;
    } catch {
      console.warn(`[Self-Healing] Selector [${i}] not found: "${selector}"`);
    }
  }

  throw new Error(
    `[Self-Healing] All selectors exhausted. Tried: ${selectors.join(' | ')}`,
  );
}
