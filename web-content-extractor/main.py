
import click
import os
import sys
import time
import random
from src.fetcher import Fetcher
from src.parser import Parser
from src.converter import Converter
from src.asset_manager import AssetManager
from src.logger import setup_logger, logger

def sanitize_filename(name):
    """
    Sanitizes a string to be safe for filenames.
    """
    # Allow alphanumeric, spaces, hyphens, underscores, and Chinese characters (if filesystem supports)
    # But for safety, let's just replace problematic chars
    import re
    # Remove chars that are not allowed in filenames
    safe_name = re.sub(r'[\\/*?:"<>|]', "", name)
    # Collapse multiple spaces
    safe_name = re.sub(r'\s+', " ", safe_name).strip()
    return safe_name

def process_single_article(url, output_dir, file_prefix="", fetcher=None):
    """
    Extracts a single article.
    Returns the relative path of the saved markdown file, or None if failed.
    """
    try:
        # Initialize components for this article
        if not fetcher:
            fetcher = Fetcher(headless=True)
            
        # Assets should be in output_dir/assets
        asset_manager = AssetManager(output_dir)
        parser = Parser(asset_manager)
        converter = Converter()

        # Step 1: Fetch HTML
        html_content = fetcher.fetch(url)

        # Step 2: Parse and process (download images)
        title, processed_html = parser.parse_and_process(html_content, base_url=url)
        
        if not title:
            title = "Untitled Article"
        
        safe_title = sanitize_filename(title)
        if not safe_title:
            safe_title = "article"

        # Step 3: Convert to Markdown
        markdown_content = converter.convert(processed_html, title)

        # Step 4: Save to file
        filename = f"{file_prefix}{safe_title}.md"
        output_file = os.path.join(output_dir, filename)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.success(f"Successfully saved: {filename}")
        return filename, title

    except Exception as e:
        logger.error(f"Failed to process article {url}: {e}")
        return None, None

def process_album(album_url, base_output_dir):
    """
    Process a WeChat Album URL.
    """
    logger.info(f"Starting Album Extraction for: {album_url}")
    
    fetcher = Fetcher(headless=True)
    parser = Parser(None) # No asset manager needed for list parsing
    
    try:
        # 1. Fetch Album Page
        album_html = fetcher.fetch(album_url)
        
        # 2. Parse Album
        album_title, articles = parser.parse_album_list(album_html)
        safe_album_title = sanitize_filename(album_title)
        
        logger.info(f"Album: {album_title}")
        logger.info(f"Found {len(articles)} articles.")
        
        # 3. Create Album Directory
        album_dir = os.path.join(base_output_dir, safe_album_title)
        if not os.path.exists(album_dir):
            os.makedirs(album_dir)
            logger.info(f"Created album directory: {album_dir}")
        
        # 4. Process Articles
        processed_articles = []
        
        for i, article in enumerate(articles):
            title = article['title']
            url = article['url']
            date = article.get('date', '')
            
            logger.info(f"Processing [{i+1}/{len(articles)}]: {title}")
            
            # Add delay
            if i > 0:
                sleep_time = random.uniform(3, 8)
                logger.info(f"Waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            
            # Process
            file_prefix = f"{i+1:02d}_"
            filename, saved_title = process_single_article(url, album_dir, file_prefix, fetcher)
            
            if filename:
                processed_articles.append({
                    'title': saved_title or title,
                    'url': url,
                    'file': filename,
                    'date': date
                })
            else:
                logger.warning(f"Skipping failed article: {title}")
        
        # 5. Generate Index
        index_content = f"# {album_title}\n\n"
        index_content += f"**Source URL**: {album_url}\n\n"
        index_content += f"**Total Articles**: {len(articles)}\n\n"
        index_content += "---\n\n"
        
        for art in processed_articles:
            date_str = f" ({art['date']})" if art['date'] else ""
            # Escape brackets in title for markdown link if necessary, but usually fine
            link_title = art['title'].replace('[', '\[').replace(']', '\]')
            index_content += f"- [{link_title}](./{art['file']}){date_str}\n"
            
        index_file = os.path.join(album_dir, "README.md") # Use README.md as index
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)
            
        logger.success(f"Album processing complete. Index saved to {index_file}")

    except Exception as e:
        logger.critical(f"Album processing failed: {e}")
        sys.exit(1)

@click.command()
@click.argument('url')
@click.option('--output', '-o', default='output', help='Output directory for the markdown file and assets.')
@click.option('--debug', is_flag=True, help='Enable debug logging.')
def main(url, output, debug):
    """
    Extracts web content from URL and converts it to Markdown.
    Supports single articles and WeChat Albums (batch download).
    """
    setup_logger(debug)

    if not os.path.exists(output):
        os.makedirs(output)

    if "appmsgalbum" in url:
        process_album(url, output)
    else:
        logger.info(f"Starting single article extraction for: {url}")
        process_single_article(url, output)

if __name__ == '__main__':
    main()
