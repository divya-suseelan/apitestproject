# Multi-Agent Test Automation Pipeline

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
