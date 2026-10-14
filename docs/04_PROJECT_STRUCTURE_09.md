# 04_PROJECT_STRUCTURE.md

# Part 9 — Browser Project Structure

> **Purpose**
>
> The `browser/` module is responsible for all web automation in AetherOS. It provides a unified interface for interacting with websites, web applications, APIs, downloads, authentication, and browser sessions.
>
> It acts as the **web interaction layer** between AetherOS and the Internet.
>
> **Rule:** The Browser module executes web interactions only. It does not make decisions or perform AI reasoning.

---

# Browser Architecture

```text
                 Browser Agent
                       │
                       ▼
                Browser Engine
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   Playwright      Sessions      Downloads
        │              │              │
        ├──────────────┼──────────────┤
        │              │              │
 Authentication     Network       JavaScript
        │              │              │
        ▼              ▼              ▼
      Chromium      Firefox        WebKit
```

---

# Folder Structure

```text
browser/
│
├── __init__.py
│
├── core/
├── browsers/
├── contexts/
├── pages/
├── tabs/
├── navigation/
├── forms/
├── authentication/
├── cookies/
├── storage/
├── downloads/
├── uploads/
├── javascript/
├── dom/
├── network/
├── screenshots/
├── scraping/
├── pdf/
├── sessions/
├── verification/
├── automation/
├── tools/
├── wrappers/
├── utils/
│
├── manager.py
├── registry.py
├── interfaces.py
├── config.py
├── constants.py
└── exceptions.py
```

---

# Browser Philosophy

The Browser module should answer:

* Open websites
* Login
* Fill forms
* Click buttons
* Extract data
* Download files
* Upload files
* Execute JavaScript
* Capture webpages

It should **never**:

* Decide what website to visit
* Plan workflows
* Call LLMs
* Perform desktop automation

---

# 1. core/

Purpose

Central browser lifecycle.

---

Structure

```text
core/
│
├── browser.py
├── launcher.py
├── lifecycle.py
├── shutdown.py
└── health.py
```

Responsibilities

* Launch browser
* Close browser
* Restart browser
* Health monitoring

---

# 2. browsers/

Purpose

Browser implementations.

---

Structure

```text
browsers/
│
├── chromium.py
├── firefox.py
├── webkit.py
└── remote.py
```

Supported Browsers

* Chromium
* Chrome
* Edge
* Firefox
* WebKit
* Remote Browser

---

# 3. contexts/

Purpose

Browser contexts.

---

Structure

```text
contexts/
│
├── manager.py
├── isolated.py
├── persistent.py
└── incognito.py
```

Supports

* Multiple users
* Multiple sessions
* Isolated environments

---

# 4. pages/

Purpose

Current page management.

---

Structure

```text
pages/
│
├── page.py
├── history.py
├── reload.py
├── refresh.py
└── state.py
```

Capabilities

* Open
* Reload
* Back
* Forward
* Refresh

---

# 5. tabs/

Purpose

Tab management.

---

Structure

```text
tabs/
│
├── manager.py
├── create.py
├── switch.py
├── close.py
└── grouping.py
```

Supports

* Multiple tabs
* Active tab
* Background tabs
* Tab groups

---

# 6. navigation/

Purpose

Navigate websites.

---

Structure

```text
navigation/
│
├── goto.py
├── wait.py
├── redirects.py
├── history.py
└── urls.py
```

Capabilities

```python
browser.goto(url)

browser.back()

browser.forward()

browser.refresh()
```

---

# 7. forms/

Purpose

Automate forms.

---

Structure

```text
forms/
│
├── inputs.py
├── buttons.py
├── dropdowns.py
├── checkboxes.py
├── radio.py
├── uploads.py
└── validation.py
```

Supports

* Login
* Registration
* Search
* Multi-step forms

---

# 8. authentication/

Purpose

Login automation.

---

Structure

```text
authentication/
│
├── login.py
├── oauth.py
├── otp.py
├── captcha.py
└── credentials.py
```

Supports

* Username/Password
* OAuth
* Cookies
* Session Restore
* MFA (future)

---

# 9. cookies/

Purpose

Cookie management.

---

Structure

```text
cookies/
│
├── manager.py
├── import.py
├── export.py
├── cleanup.py
└── storage.py
```

---

# 10. storage/

Purpose

Browser storage.

---

Supports

* Local Storage
* Session Storage
* IndexedDB

---

Structure

```text
storage/
│
├── local.py
├── session.py
├── indexeddb.py
└── cache.py
```

---

# 11. downloads/

Purpose

File downloads.

---

Structure

```text
downloads/
│
├── manager.py
├── monitor.py
├── rename.py
├── verification.py
└── cleanup.py
```

Responsibilities

* Wait for download
* Rename
* Verify
* Move

---

# 12. uploads/

Purpose

Upload files.

---

Structure

```text
uploads/
│
├── upload.py
├── multiple.py
├── dragdrop.py
└── validation.py
```

---

# 13. javascript/

Purpose

Execute JavaScript.

---

Structure

```text
javascript/
│
├── execute.py
├── inject.py
├── evaluate.py
└── console.py
```

Example

```python
page.evaluate(js_code)
```

---

# 14. dom/

Purpose

DOM understanding.

---

Structure

```text
dom/
│
├── parser.py
├── selectors.py
├── tree.py
├── elements.py
└── inspector.py
```

Supports

* XPath
* CSS Selectors
* Accessibility Tree

---

# 15. network/

Purpose

Network interception.

---

Structure

```text
network/
│
├── requests.py
├── responses.py
├── intercept.py
├── websocket.py
└── throttling.py
```

Capabilities

* Monitor requests
* Modify requests
* Mock APIs
* Capture responses

---

# 16. screenshots/

Purpose

Capture webpages.

---

Structure

```text
screenshots/
│
├── full.py
├── viewport.py
├── element.py
└── comparison.py
```

Supports

* Full Page
* Region
* Element Screenshot

---

# 17. scraping/

Purpose

Extract webpage data.

---

Structure

```text
scraping/
│
├── parser.py
├── extractor.py
├── cleaner.py
├── markdown.py
└── structured.py
```

Output

```json
{
  "title":"AetherOS",
  "links":[...],
  "tables":[...]
}
```

---

# 18. pdf/

Purpose

PDF generation.

---

Structure

```text
pdf/
│
├── export.py
├── printing.py
└── settings.py
```

Supports

* Save as PDF
* Print Page

---

# 19. sessions/

Purpose

Session persistence.

---

Structure

```text
sessions/
│
├── manager.py
├── save.py
├── load.py
└── restore.py
```

Allows resuming browser state.

---

# 20. verification/

Purpose

Verify browser actions.

---

Structure

```text
verification/
│
├── navigation.py
├── clicks.py
├── forms.py
├── downloads.py
└── screenshots.py
```

Confirms

* Page loaded
* Form submitted
* Download completed

---

# 21. automation/

Purpose

Reusable browser workflows.

---

Examples

```text
automation/
│
├── login.py
├── search.py
├── shopping.py
├── reporting.py
└── workflows.py
```

---

# 22. tools/

Purpose

Expose browser functionality to LLM tool calling.

---

Structure

```text
tools/
│
├── browser_tools.py
├── page_tools.py
├── navigation_tools.py
├── form_tools.py
└── download_tools.py
```

Example

```python
@tool
def open_url(url):
    ...
```

---

# 23. wrappers/

Purpose

Abstract third-party libraries.

---

Structure

```text
wrappers/
│
├── playwright_wrapper.py
├── selenium_wrapper.py
└── http_wrapper.py
```

This keeps implementation replaceable.

---

# 24. utils/

Shared helper utilities.

Examples

```text
utils/
│
├── selectors.py
├── urls.py
├── retries.py
├── timers.py
└── validators.py
```

---

# manager.py

Central browser controller.

Responsibilities

* Launch browser
* Manage sessions
* Initialize contexts
* Shutdown browser

---

# registry.py

Registers

* Browsers
* Automation workflows
* Tool wrappers
* Verification handlers

---

# interfaces.py

Example

```python
class BrowserInterface:

    open()

    close()

    goto()

    screenshot()
```

---

# config.py

Example

```yaml
browser: chromium

headless: false

timeout: 30000

downloads: ./downloads

viewport:

  width: 1920

  height: 1080
```

---

# constants.py

```python
DEFAULT_TIMEOUT = 30000

MAX_TABS = 50

DOWNLOAD_TIMEOUT = 120
```

---

# exceptions.py

Contains

```text
BrowserLaunchError

NavigationError

TimeoutError

DownloadError

AuthenticationError

ElementNotFound
```

---

# Browser Execution Flow

```text
Planner

↓

Browser Agent

↓

Browser Engine

↓

Playwright Wrapper

↓

Browser

↓

Website

↓

Verification

↓

Result
```

---

# Dependency Rules

Browser module may use

* Playwright
* Selenium
* BeautifulSoup
* lxml
* httpx

Browser module must NOT import

* Desktop Controllers
* Vision Controllers
* LLM Providers
* Core Planner
* Trading Logic

---

# Recommended Technologies

| Capability           | Technology             |
| -------------------- | ---------------------- |
| Browser Automation   | Playwright             |
| Secondary Automation | Selenium               |
| HTTP Client          | httpx                  |
| HTML Parsing         | BeautifulSoup4         |
| XML Parsing          | lxml                   |
| PDF Generation       | Playwright PDF         |
| Network Monitoring   | Playwright Network API |

---

# Future Browser Roadmap

Future capabilities include:

* Human-like browsing behavior
* Anti-bot detection avoidance
* Browser fingerprint management
* Distributed browser clusters
* Cloud browser execution
* Visual DOM understanding
* AI-assisted selector generation
* Autonomous web exploration
* Browser extension integration
* Multi-browser synchronization

---

# Summary

The `browser/` module is the web automation subsystem of AetherOS. It provides a complete abstraction over browser interaction, including navigation, forms, authentication, downloads, uploads, JavaScript execution, DOM inspection, network interception, scraping, and session management. By isolating browser automation behind stable interfaces and wrappers, AetherOS can support multiple browsers and evolve independently of the underlying automation framework while remaining reliable, scalable, and easy to maintain.

---

## Next Part

**Part 10 — `backend/`, `api/`, `database/`, and `integrations/` Project Structure**

This final section will cover:

* FastAPI backend architecture
* REST & WebSocket APIs
* Authentication
* Database layer
* ORM models
* Repositories
* Services
* External integrations
* Plugin system
* Event system
* Deployment architecture
* Complete production-ready backend design

After Part 10, the **04_PROJECT_STRUCTURE.md** document will be complete.
