# Web Content Extraction Tool Implementation Plan

## Overview
- **Objective**: Develop a Python-based CLI tool to extract content from dynamic websites (specifically targeting SPA sites like X.com), parse the main content, download associated images locally, and save the result as Markdown.
- **Scope**: 
  - CLI interface for URL input.
  - Headless browser automation for dynamic content rendering.
  - Smart content extraction (removing navigation, ads, etc.).
  - Asset management (image downloading and link rewriting).
  - Markdown file generation.
- **Success Criteria**: 
  - Successfully extracts content from a given URL (including X.com posts/threads).
  - Generates a clean Markdown file in the `output` directory.
  - Downloads images to `output/assets` and correctly links them in the Markdown.
  - Handles dynamic loading (scrolling/waiting) effectively.

## Architecture Overview
- **System Design**: Modular Python application with distinct layers for Fetching, Parsing, and Converting.
- **Key Components**:
  - **Fetcher (Playwright)**: Handles browser automation, JavaScript execution, and dynamic content loading.
  - **Parser (Readability)**: Extracts the primary article content from the raw HTML.
  - **Converter (Markdownify)**: Converts HTML to Markdown format.
  - **Asset Manager**: Downloads images and rewrites image sources.
  - **CLI (Click/Argparse)**: User interface for arguments and options.
- **Technology Stack**: 
  - Python 3.9+
  - `playwright`: For robust dynamic content fetching.
  - `readability-lxml`: For reliable content extraction.
  - `markdownify`: For flexible HTML to Markdown conversion.
  - `beautifulsoup4`: For DOM manipulation (specifically for image tag processing).
  - `requests`: For downloading image assets.

## Architectural Decisions

### Decision 1: Browser Automation Engine
- **Context**: Need to scrape dynamic Single Page Applications (SPAs) like X.com which rely heavily on JavaScript.
- **Options Considered**: `requests` + `BeautifulSoup`, `Selenium`, `Playwright`.
- **Decision**: **Playwright**.
- **Rationale**: Faster and more reliable than Selenium; handles modern web features and waiting conditions (network idle, element visibility) better than static requests.
- **Consequences**: Requires browser binary installation (`playwright install`), slightly heavier setup than pure HTTP libraries.

### Decision 2: Content Extraction Strategy
- **Context**: Need to isolate the "main content" from headers, footers, and sidebars.
- **Options Considered**: Custom CSS selectors per site, `readability-lxml`, `trafilatura`.
- **Decision**: **`readability-lxml`**.
- **Rationale**: Proven, robust port of the Firefox Reader View algorithm. It provides a generic solution that works on most article-based sites without per-site maintenance.
- **Consequences**: May occasionally miss content on very non-standard layouts, but offers the best general-purpose baseline.

### Decision 3: Asset Handling
- **Context**: Images need to be stored locally for offline viewing of the Markdown.
- **Decision**: **Download and Rewrite**.
- **Rationale**: Markdown files should be self-contained regarding assets. 
- **Consequences**: Need to parse HTML `<img>` tags, download files, generate unique filenames (hash-based), and rewrite the `src` attribute before conversion to Markdown.

## Implementation Phases

### Phase 1: Setup & Infrastructure
**Objective**: Initialize project structure and install dependencies.
**Dependencies**: None.

#### Tasks
1.  **[TASK-001]**: Project Initialization
    -   **Description**: Create project directory structure (`src/`, `output/`, `tests/`) and `requirements.txt`.
    -   **Complexity**: Low
    -   **Estimated Effort**: 30 mins
    -   **Dependencies**: None
    -   **Assignee Role**: Developer
    -   **Acceptance Criteria**: Folder structure exists; virtual environment created; dependencies installed.
    -   **Files/Scope**: `requirements.txt`, `README.md`, directory structure.

2.  **[TASK-002]**: CLI Skeleton
    -   **Description**: Implement basic CLI entry point using `argparse` or `click` that accepts a URL and output directory.
    -   **Complexity**: Low
    -   **Estimated Effort**: 1 hour
    -   **Dependencies**: TASK-001
    -   **Assignee Role**: Developer
    -   **Acceptance Criteria**: Script runs and prints the provided URL.
    -   **Files/Scope**: `src/main.py`

### Phase 2: Fetcher Module (Playwright)
**Objective**: Implement the browser automation layer to retrieve raw HTML.
**Dependencies**: Phase 1.

#### Tasks
3.  **[TASK-003]**: Basic Page Fetching
    -   **Description**: Implement `Fetcher` class using Playwright to launch browser, navigate to URL, and return `content()`.
    -   **Complexity**: Medium
    -   **Estimated Effort**: 2 hours
    -   **Dependencies**: TASK-002
    -   **Assignee Role**: Developer
    -   **Acceptance Criteria**: Can fetch static HTML from a simple URL.
    -   **Files/Scope**: `src/fetcher.py`

4.  **[TASK-004]**: Dynamic Content Handling
    -   **Description**: Add logic to handle dynamic loading (scrolling to bottom, waiting for network idle). specifically for X.com/Twitter.
    -   **Complexity**: High
    -   **Estimated Effort**: 3 hours
    -   **Dependencies**: TASK-003
    -   **Assignee Role**: Developer
    -   **Acceptance Criteria**: Can successfully load a full thread or long article that requires scrolling.
    -   **Files/Scope**: `src/fetcher.py`

### Phase 3: Parser & Asset Manager
**Objective**: Extract content and handle images.
**Dependencies**: Phase 2.

#### Tasks
5.  **[TASK-005]**: Content Extraction
    -   **Description**: Implement `Parser` class using `readability-lxml` to extract the main article content from raw HTML.
    -   **Complexity**: Medium
    -   **Estimated Effort**: 2 hours
    -   **Dependencies**: TASK-003
    -   **Assignee Role**: Developer
    -   **Acceptance Criteria**: Returns clean HTML string of just the article body.
    -   **Files/Scope**: `src/parser.py`

6.  **[TASK-006]**: Image Downloading & Rewriting
    -   **Description**: Parse the *cleaned* HTML, find `<img>` tags, download images to `output/assets/`, and update `src` attributes to local paths.
    -   **Complexity**: High
    -   **Estimated Effort**: 3 hours
    -   **Dependencies**: TASK-005
    -   **Assignee Role**: Developer
    -   **Acceptance Criteria**: Images are saved to disk; HTML `src` tags point to `./assets/image.jpg`.
    -   **Files/Scope**: `src/assets.py`, `src/parser.py`

### Phase 4: Conversion & Integration
**Objective**: Convert to Markdown and save final output.
**Dependencies**: Phase 3.

#### Tasks
7.  **[TASK-007]**: Markdown Conversion
    -   **Description**: Implement `Converter` class using `markdownify` to transform the processed HTML into Markdown.
    -   **Complexity**: Low
    -   **Estimated Effort**: 1 hour
    -   **Dependencies**: TASK-006
    -   **Assignee Role**: Developer
    -   **Acceptance Criteria**: HTML tags are converted to appropriate Markdown syntax.
    -   **Files/Scope**: `src/converter.py`

8.  **[TASK-008]**: End-to-End Integration
    -   **Description**: Wire all modules together in `main.py`. Add logging and error handling.
    -   **Complexity**: Medium
    -   **Estimated Effort**: 2 hours
    -   **Dependencies**: All previous tasks
    -   **Assignee Role**: Developer
    -   **Acceptance Criteria**: Running the CLI with a URL produces a `.md` file and an `assets` folder.
    -   **Files/Scope**: `src/main.py`

## Risk Assessment
- **Technical Risks**: 
  - **Anti-Bot Measures**: X.com and others have strict anti-scraping. *Mitigation*: Use Playwright's stealth plugins (if needed) or slower human-like interactions.
  - **Layout Changes**: Readability might fail on very specific SPA layouts. *Mitigation*: Fallback to raw body dump if extraction fails.
- **Integration Risks**: 
  - **Network Timeouts**: Large images or slow sites might timeout. *Mitigation*: Implement robust retry logic and timeouts.

## Testing Strategy
- **Unit Testing**: Test individual modules (Parser, Converter) with mock HTML strings.
- **Integration Testing**: Test the full pipeline against a controlled local HTML file.
- **System Testing**: Manual testing against live sites (Wikipedia, blog post, X.com public post).
