# Multi-Agent Test Automation Pipeline

A **reusable, plug-and-play** automation framework that takes Jira acceptance criteria all the way through to test results — with zero manual test writing.

```
Jira AC  →  LLM Test Cases  →  BDD (.feature + steps + POM)  →  GitLab CI  →  Test Management
```

---

## What's New in this version

| Feature | Detail |
|---------|--------|
| **Cucumber / BDD** | Tests are generated as Gherkin `.feature` files + step definitions instead of raw `describe/it` or `test()` blocks |
| **Self-healing locators** | POM methods accept a prioritised list of CSS selectors; if the primary selector fails the framework automatically tries fallbacks and logs the miss |
| **Single-framework choice** | Each team picks **one** framework — `cypress` or `playwright` — instead of generating both |

---

## How It Works

| # | Agent | What it does |
|---|-------|-------------|
| 1 | **Jira Reader** | Fetches stories by JQL and extracts acceptance criteria |
| 2 | **Test Case Generator** | Uses an LLM (GPT-4o / Claude) to generate positive, negative & edge-case test scenarios |
| 3 | **Cypress _or_ Playwright Implementer** | Generates Cucumber `.feature` + step definitions + self-healing POM class |
| 4 | **GitLab Uploader** | Commits generated tests, triggers CI pipeline, optionally creates a Merge Request |
| 5 | **Results Uploader** | Downloads JUnit artifacts and uploads results to Xray / Zephyr Scale / qTest |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 20+
- Access to: Jira Cloud, an LLM API (OpenAI / Anthropic / Azure OpenAI), GitLab, and a test management tool

### 2. Clone & Install

```bash
git clone https://github.com/your-org/apitestproject.git
cd apitestproject

# Python dependencies
pip install -r requirements.txt

# Node dependencies
npm install
# If using Playwright, also install browsers:
npx playwright install --with-deps
```

### 3. Configure

```bash
cp .env.example .env   # fill in your credentials
```

Edit `config/config.yaml` — the three key choices for each team:

```yaml
test_generation:
  framework: "cypress"     # ← "cypress" OR "playwright"
  bdd: true                # ← true = Cucumber .feature + steps
  self_healing: true       # ← true = multi-selector fallback in POM
  language: "typescript"
```

### 4. Run the Pipeline

```bash
# Use the framework set in config.yaml
python main.py

# Or override on the command line
python main.py --framework playwright
```

---

## BDD / Cucumber

When `bdd: true`, the pipeline generates three files per Jira ticket:

### Cypress (via `@badeball/cypress-cucumber-preprocessor`)

| File | Location |
|------|----------|
| Feature file | `cypress/e2e/<TICKET>.feature` |
| Step definitions | `cypress/support/step_definitions/<TICKET>.steps.ts` |
| Page Object Model | `cypress/pages/<TicketPage>.ts` |

### Playwright (via `playwright-bdd`)

| File | Location |
|------|----------|
| Feature file | `playwright/features/<TICKET>.feature` |
| Step definitions | `playwright/steps/<TICKET>.steps.ts` |
| Page Object Model | `playwright/pages/<TicketPage>.ts` |

**Example generated feature:**

```gherkin
Feature: PROJ-123 — Auto-generated tests

  @PROJ123_TC_1 @positive @jira-PROJ-123
  Scenario: PROJ123_TC_1: User can log in with valid credentials
    Given I am on the login page
    When I submit valid username and password
    Then I should be redirected to the dashboard
```

---

## Self-Healing Locators

When `self_healing: true`, every POM method receives an ordered array of CSS selectors loaded from a **locator registry** JSON file.

```
cypress/support/locator_registry.json    (Cypress)
playwright/support/locator_registry.json (Playwright)
```

The pipeline seeds the registry with three placeholder selectors per action (`data-testid`, `id`, `aria-label`). Teams replace the placeholders with real selectors from their application.

**How it works at runtime:**

1. Try selector `[0]` (primary)
2. If not found within 2 s → try selector `[1]`, log a warning
3. Continue until a selector succeeds or all are exhausted

```typescript
// Generated POM (Playwright example)
async performPROJ123TC1(): Promise<void> {
  const el = await findElement(this.page,
    PROJ123Page_Locators['PROJ123TC1'] ?? []);
  // TODO: interact with el
}
```

```typescript
// Generated POM (Cypress example)
performPROJ123TC1(): void {
  const el = selfHeal(PROJ123Page_Locators['PROJ123TC1'] ?? []);
  // TODO: interact with el
}
```

---

## Team Onboarding (3 steps)

1. **`config/config.yaml`** — set `framework`, `bdd`, `self_healing`, Jira project key, GitLab namespace
2. **`.env`** — fill in API tokens
3. **Run** `python main.py`

The locator registry is auto-seeded with placeholder selectors. Teams update `locator_registry.json` with real selectors as they fill in the `// TODO` comments.

---

## Project Structure

```
apitestproject/
├── agents/
│   ├── base.py                    # Base class and config loader
│   ├── coordinator.py             # Orchestrator (single-framework)
│   ├── jira_reader.py             # Agent 1: Jira reader
│   ├── test_case_generator.py     # Agent 2: LLM test case generator
│   ├── cypress_implementer.py     # Agent 3a: Cypress (BDD or classic)
│   ├── playwright_implementer.py  # Agent 3b: Playwright (BDD or classic)
│   ├── self_healing.py            # Locator registry + seed utility
│   ├── gitlab_uploader.py         # Agent 4: GitLab push + pipeline
│   └── results_uploader.py        # Agent 5: Results → test management
│
├── templates/
│   ├── cypress_feature.j2         # Cucumber .feature template (Cypress)
│   ├── cypress_steps.j2           # Cypress step definitions template
│   ├── cypress_pom.j2             # Cypress POM (with self-healing)
│   ├── cypress_spec.j2            # Cypress classic spec template
│   ├── playwright_feature.j2      # Cucumber .feature template (Playwright)
│   ├── playwright_steps.j2        # Playwright step definitions template
│   ├── playwright_pom.j2          # Playwright POM (with self-healing)
│   └── playwright_spec.j2         # Playwright classic spec template
│
├── cypress/
│   ├── e2e/                       # Generated .feature files
│   ├── pages/                     # Generated POM classes
│   ├── support/
│   │   ├── e2e.ts                 # Global support (imports self_healing)
│   │   ├── self_healing.ts        # selfHeal() custom helper
│   │   ├── locator_registry.json  # Team-managed selector registry
│   │   └── step_definitions/      # Generated step definitions
│
├── playwright/
│   ├── features/                  # Generated .feature files
│   ├── steps/                     # Generated step definitions
│   ├── pages/                     # Generated POM classes
│   └── support/
│       ├── self_healing.ts        # findElement() helper
│       └── locator_registry.json  # Team-managed selector registry
│
├── config/config.yaml             # ← Only file teams need to change
├── .env.example
├── .gitignore
├── .gitlab-ci.yml                 # Single-framework CI (TEST_FRAMEWORK variable)
├── cypress.config.ts              # Cypress + Cucumber preprocessor config
├── playwright.config.ts           # Playwright + playwright-bdd config
├── package.json
├── requirements.txt
├── tsconfig.json
└── main.py                        # Entry point (--framework flag)
```

---

## CI Pipeline

Set the `TEST_FRAMEWORK` CI/CD variable in GitLab (**Settings → CI/CD → Variables**) to `cypress` or `playwright`. Only the matching job runs.

| Stage | Job | Runs when |
|-------|-----|-----------|
| `install` | `install-deps` | Always |
| `test` | `cypress-tests` | `TEST_FRAMEWORK == "cypress"` |
| `test` | `playwright-tests` | `TEST_FRAMEWORK == "playwright"` |
| `report` | `test-results` | Always (collects whichever ran) |

For Playwright the CI script runs `npx bddgen` before `npx playwright test` to compile `.feature` files into runnable test cases.

---

## Supported Test Management Tools

| Tool | Config value |
|------|-------------|
| Xray (Jira plugin) | `xray` |
| Zephyr Scale | `zephyr_scale` |
| qTest | `qtest` |
| None / manual | `none` |

---

## Security Notes

- **Never commit `.env`** — it is in `.gitignore`
- All secrets are read from environment variables
- Set GitLab CI tokens as **protected/masked** CI/CD variables

A **reusable, plug-and-play** automation framework that takes Jira acceptance criteria all the way through to test results — with zero manual test writing.

```
Jira AC  →  Test Cases  →  Cypress + Playwright (POM)  →  GitLab CI  →  Test Management
```

---

## How It Works

| # | Agent | What it does |
|---|-------|-------------|
| 1 | **Jira Reader** | Fetches stories by JQL and extracts acceptance criteria |
| 2 | **Test Case Generator** | Uses an LLM (GPT-4o / Claude) to generate positive, negative & edge-case test scenarios |
| 3 | **Cypress Implementer** | Generates `*.cy.ts` spec files and Page Object Model classes |
| 4 | **Playwright Implementer** | Generates `*.spec.ts` spec files and Page Object Model classes |
| 5 | **GitLab Uploader** | Commits generated tests, triggers CI pipeline, optionally creates a Merge Request |
| 6 | **Results Uploader** | Downloads JUnit artifacts and uploads results to Xray / Zephyr Scale / qTest |

Agents 3 and 4 run **in parallel** for faster throughput.

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 20+
- Access to: Jira Cloud, an LLM API (OpenAI / Anthropic / Azure OpenAI), GitLab, and a test management tool

### 2. Clone & Install

```bash
git clone https://github.com/your-org/apitestproject.git
cd apitestproject

# Python dependencies
pip install -r requirements.txt

# Node dependencies (for generated test execution)
npm install
npx playwright install --with-deps
```

### 3. Configure

```bash
# Copy the example env file and fill in your credentials
cp .env.example .env
```

Edit `.env` with your tokens:

```env
JIRA_EMAIL=you@yourorg.com
JIRA_API_TOKEN=your-jira-token
OPENAI_API_KEY=sk-...
GITLAB_TOKEN=glpat-...
XRAY_CLIENT_ID=...
XRAY_CLIENT_SECRET=...
```

Edit `config/config.yaml` to match your project:

```yaml
jira:
  base_url: "https://yourorg.atlassian.net"
  project_key: "PROJ"
  jql_filter: "project = PROJ AND sprint in openSprints() AND issuetype = Story"

llm:
  provider: "openai"
  model: "gpt-4o"

gitlab:
  base_url: "https://gitlab.com"
  namespace: "your-group/your-repo"
  create_merge_request: true

test_management:
  tool: "xray"   # or "zephyr_scale" | "qtest" | "none"
```

### 4. Run the Pipeline

```bash
python main.py
```

That's it. The pipeline will:
1. Pull stories from Jira
2. Generate test cases with an LLM
3. Write Cypress + Playwright test files with POM
4. Push to GitLab and trigger the CI pipeline
5. Wait for pipeline completion and upload results

---

## Project Structure

```
apitestproject/
├── agents/
│   ├── base.py                  # Base class and config loader
│   ├── coordinator.py           # Orchestrator — runs all agents
│   ├── jira_reader.py           # Agent 1: Jira AC reader
│   ├── test_case_generator.py   # Agent 2: LLM test case generator
│   ├── cypress_implementer.py   # Agent 3: Cypress file generator
│   ├── playwright_implementer.py# Agent 4: Playwright file generator
│   ├── gitlab_uploader.py       # Agent 5: GitLab push + pipeline trigger
│   └── results_uploader.py      # Agent 6: Results → test management
│
├── templates/
│   ├── cypress_pom.j2           # Jinja2 template: Cypress POM class
│   ├── cypress_spec.j2          # Jinja2 template: Cypress spec
│   ├── playwright_pom.j2        # Jinja2 template: Playwright POM class
│   └── playwright_spec.j2       # Jinja2 template: Playwright spec
│
├── cypress/                     # Generated Cypress tests land here
│   ├── e2e/
│   ├── pages/                   # Page Object Models
│   ├── fixtures/
│   └── support/
│
├── playwright/                  # Generated Playwright tests land here
│   ├── tests/
│   └── pages/                   # Page Object Models
│
├── config/
│   └── config.yaml              # Main configuration (team-editable)
│
├── .env.example                 # Template for secrets
├── .gitignore
├── .gitlab-ci.yml               # CI pipeline definition
├── cypress.config.json          # Cypress configuration
├── playwright.config.ts         # Playwright configuration
├── package.json                 # Node dependencies
├── requirements.txt             # Python dependencies
├── tsconfig.json                # TypeScript config
└── main.py                      # Entry point
```

---

## Reuse Across Teams

Each team only needs to:

1. **Copy** `config/config.yaml` and `.env.example` → fill in their Jira project key, GitLab namespace, and credentials
2. **Update** `BASE_URL` in `.gitlab-ci.yml` to their application URL
3. **Run** `python main.py`

No agent code needs to change between teams.

---

## Customisation

### Use a different LLM

Change `llm.provider` in `config.yaml`:

```yaml
llm:
  provider: "anthropic"
  model: "claude-3-5-sonnet-20241022"
```

### Change the test management tool

```yaml
test_management:
  tool: "zephyr_scale"   # or "qtest" or "none"
```

### Use JavaScript instead of TypeScript

```yaml
test_generation:
  language: "javascript"
```

### Customise generated test structure

Edit the Jinja2 templates in `templates/`. The templates receive these variables:

| Variable | Description |
|----------|-------------|
| `ticket_id` | Jira ticket key, e.g. `PROJ-123` |
| `page_name` | CamelCase page name derived from ticket ID |
| `test_cases` | List of `TestCase` objects |
| `language` | `"typescript"` or `"javascript"` |

Each `TestCase` has: `test_id`, `ticket_id`, `title`, `type`, `given`, `when`, `then`, `tags`.

---

## CI Pipeline

The included `.gitlab-ci.yml` runs three stages:

| Stage | Job | Description |
|-------|-----|-------------|
| `install` | `install-deps` | `npm ci` + Playwright browser install |
| `test` | `cypress-tests` | Runs all Cypress specs, publishes JUnit XML |
| `test` | `playwright-tests` | Runs all Playwright specs, publishes JUnit XML + HTML report |
| `report` | `test-results` | Aggregates all artifacts for the Results Uploader |

JUnit reports are automatically displayed in GitLab's test results tab.

---

## Security Notes

- **Never commit `.env`** — it is in `.gitignore`
- All secrets are read from environment variables, never hard-coded
- GitLab CI variables should be set as **protected/masked** CI/CD variables in the GitLab project settings

---

## Supported Test Management Tools

| Tool | Config value | Upload method |
|------|-------------|---------------|
| Xray (Jira plugin) | `xray` | Xray Cloud REST API v1 |
| Zephyr Scale | `zephyr_scale` | Zephyr Scale REST API v2 |
| qTest | `qtest` | qTest REST API v3 |
| None / manual | `none` | Results saved locally in `output/` |
