import click
import os
import sys
from src.fetcher import Fetcher
from src.parser import Parser
from src.converter import Converter
from src.asset_manager import AssetManager
from src.logger import setup_logger, logger

@click.command()
@click.argument('url')
@click.option('--output', '-o', default='output', help='Output directory for the markdown file and assets.')
@click.option('--debug', is_flag=True, help='Enable debug logging.')
def main(url, output, debug):
    """
    Extracts web content from URL and converts it to Markdown.
    """
    setup_logger(debug)
    logger.info(f"Starting extraction for: {url}")

    try:
        # Create output directory
        if not os.path.exists(output):
            os.makedirs(output)
        
        # Initialize components
        fetcher = Fetcher(headless=True)
        asset_manager = AssetManager(output)
        parser = Parser(asset_manager)
        converter = Converter()

        # Step 1: Fetch HTML
        html_content = fetcher.fetch(url)

        # Step 2: Parse and process (download images)
        title, processed_html = parser.parse_and_process(html_content, base_url=url)
        
        if not title:
            title = "Untitled Article"
        
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
        if not safe_title:
            safe_title = "article"

        # Step 3: Convert to Markdown
        markdown_content = converter.convert(processed_html, title)

        # Step 4: Save to file
        output_file = os.path.join(output, f"{safe_title}.md")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.success(f"Successfully saved Markdown to: {output_file}")
        logger.info(f"Assets saved in: {os.path.join(output, 'assets')}")

    except Exception as e:
        logger.critical(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
