from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
import time
from src.logger import logger

class Fetcher:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def fetch(self, url: str) -> str:
        """
        Fetches the HTML content of the given URL using Playwright.
        Handles dynamic content by waiting for network idle and scrolling.
        """
        logger.info(f"Fetching URL: {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                # Goto page and wait for initial load
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Auto-scroll for dynamic content
                if "x.com" in url or "twitter.com" in url:
                    logger.info("Detected X/Twitter URL, applying specific wait logic...")
                    try:
                        # Wait for timeline or article
                        page.wait_for_selector('article', timeout=15000)
                        
                        # Expand content (e.g. "Show more" on long tweets)
                        self._expand_content(page)
                        
                        self._auto_scroll(page)
                        
                        # Expand again after scrolling in case new replies have show more
                        self._expand_content(page)
                        
                    except Exception as e:
                        logger.warning(f"X.com specific wait failed: {e}")
                else:
                    self._auto_scroll(page)
                
                # Wait for network to be idle (heuristics)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except PlaywrightTimeoutError:
                    logger.warning("Network idle timeout, continuing with current content")

                # DEBUG: Save full page content
                with open("debug_full_page.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                logger.info("Saved debug_full_page.html for inspection")

                content = page.content()
                logger.success(f"Successfully fetched content ({len(content)} bytes)")
                return content

            except Exception as e:
                logger.error(f"Error fetching URL: {e}")
                raise
            finally:
                browser.close()

    def _expand_content(self, page: Page):
        """
        Attempts to click 'Show more' buttons to expand long tweets or threads.
        """
        logger.debug("Checking for 'Show more' buttons...")
        try:
            # Look for buttons with text "Show more" or specific X.com testids
            # Common patterns for "Show more" on X:
            # - span with text "Show more" inside a role="button" or similar
            # - div[data-testid="tweet-text-show-more-link"]
            
            # 1. Try specific data-testid first
            show_more_buttons = page.locator('[data-testid="tweet-text-show-more-link"]')
            count = show_more_buttons.count()
            if count > 0:
                logger.info(f"Found {count} 'Show more' buttons via testid. Clicking...")
                for i in range(count):
                    try:
                        if show_more_buttons.nth(i).is_visible():
                            show_more_buttons.nth(i).click()
                            page.wait_for_timeout(500) # Wait a bit for expansion
                    except Exception as e:
                        logger.warning(f"Failed to click 'Show more' button {i}: {e}")

            # 2. Try text based search if needed (fallback)
            # Sometimes X uses different structures.
            # text_buttons = page.get_by_text("Show more", exact=True)
            # if text_buttons.count() > 0:
            #      logger.info("Found 'Show more' text buttons. Clicking...")
            #      for i in range(text_buttons.count()):
            #          try:
            #              if text_buttons.nth(i).is_visible():
            #                  text_buttons.nth(i).click()
            #                  page.wait_for_timeout(500)
            #          except Exception as e:
            #              logger.warning(f"Failed to click text button {i}: {e}")
                         
        except Exception as e:
            logger.warning(f"Error during content expansion: {e}")

    def _auto_scroll(self, page: Page):
        """
        Scrolls down the page to trigger dynamic content loading.
        """
        logger.debug("Starting auto-scroll...")
        prev_height = -1
        max_scrolls = 10  # Limit scrolls to avoid infinite loops on infinite feed
        scroll_count = 0

        while scroll_count < max_scrolls:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            try:
                page.wait_for_timeout(1000)  # Wait for content to load
            except Exception:
                break
            
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == prev_height:
                break
            prev_height = new_height
            scroll_count += 1
        
        logger.debug(f"Auto-scroll finished after {scroll_count} scrolls")
