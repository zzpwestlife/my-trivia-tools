from markdownify import markdownify as md
from src.logger import logger

class Converter:
    def convert(self, html_content: str, title: str) -> str:
        """
        Converts the HTML content to Markdown.
        Adds metadata (YAML front matter or simple title) and cleans up.
        """
        try:
            # Basic conversion with GitHub Flavored Markdown
            markdown = md(html_content, heading_style="ATX", strip=['script', 'style'])
            
            # Add metadata
            final_markdown = f"# {title}\n\n{markdown}"
            
            # Post-processing: Collapse multiple blank lines into one (max 2 newlines)
            import re
            final_markdown = re.sub(r'\n{3,}', '\n\n', final_markdown)
            
            # Ensure horizontal rules have blank lines around them
            final_markdown = re.sub(r'([^\n])\n---', r'\1\n\n---', final_markdown)
            final_markdown = re.sub(r'---\n([^\n])', r'---\n\n\1', final_markdown)
            
            # Ensure code blocks have language hints if possible (readability usually strips this)
            # We can't easily guess language without more complex logic.
            
            logger.info("Successfully converted HTML to Markdown.")
            return final_markdown

        except Exception as e:
            logger.error(f"Error converting to Markdown: {e}")
            raise
