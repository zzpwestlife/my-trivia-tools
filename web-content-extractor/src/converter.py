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
            
            # Post-processing: Remove excessive blank lines
            final_markdown = "\n".join([line for line in final_markdown.splitlines() if line.strip() != ""])
            
            # Ensure code blocks have language hints if possible (readability usually strips this)
            # We can't easily guess language without more complex logic.
            
            logger.info("Successfully converted HTML to Markdown.")
            return final_markdown

        except Exception as e:
            logger.error(f"Error converting to Markdown: {e}")
            raise
