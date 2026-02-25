from bs4 import BeautifulSoup
from readability import Document
from src.asset_manager import AssetManager
from src.logger import logger

class Parser:
    def __init__(self, asset_manager: AssetManager):
        self.asset_manager = asset_manager

    def _replace_emojis_with_text(self, soup_element):
        """
        Replaces X.com emoji images with their alt text (unicode characters).
        """
        if not soup_element:
            return

        for img in soup_element.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            
            # X.com emojis usually have 'emoji' in src or specific classes
            # The alt tag usually contains the unicode character
            if 'emoji' in src or 'twemoji' in src:
                img.replace_with(alt if alt else "")

    def _parse_x_com(self, html: str, base_url: str) -> tuple[str, str]:
        """
        Custom parser for X.com/Twitter to bypass Readability limitations.
        Extracts the main thread/conversation.
        """
        logger.info("Using custom X.com parser (Thread Mode)...")
        soup = BeautifulSoup(html, 'html.parser')

        # 1. Title
        title = soup.title.string if soup.title else "X.com Post"
        
        combined_html = ""
        
        # Track processed images to avoid duplicates across the thread if any
        processed_img_urls = set()
        
        # Track seen text to avoid duplicates (e.g. if main tweet is repeated in reply chain)
        seen_texts = set()

        # 2. Check for Longform Article (X Article)
        # This is where the missing content usually resides for "Articles"
        article_view = soup.find('div', attrs={'data-testid': 'twitterArticleReadView'})
        if article_view:
            logger.info("Found X Article (Longform) view. Extracting...")
            
            # Pre-process emojis in the article view
            self._replace_emojis_with_text(article_view)

            # Cleanup Article View: Remove unwanted elements
            # Remove Action Bars (Like, Retweet, etc.)
            for action_bar in article_view.find_all('div', attrs={'role': 'group'}):
                action_bar.decompose()
            
            # Remove SVGs (Icons) which clutter markdown
            for svg in article_view.find_all('svg'):
                svg.decompose()
                
            # Remove Profile Images from the article view (they are usually redundant or clutter)
            for img in article_view.find_all('img'):
                src = img.get('src', '')
                if 'profile_images' in src:
                    img.decompose()
            
            # Remove "View analytics" and other footer text
            for a in article_view.find_all('a'):
                if 'analytics' in a.get('href', ''):
                    a.decompose()
            
            # Remove "Show more" buttons
            for element in article_view.find_all(string="Show more"):
                if element.parent:
                    element.parent.decompose()
                    
            # Remove "Quote" label
            for element in article_view.find_all(string="Quote"):
                if element.parent:
                    element.parent.decompose()

            # Format User Name in Article View
            user_name_div = article_view.find('div', attrs={'data-testid': 'User-Name'})
            if user_name_div:
                 # Extract text cleanly (Name @handle · Date)
                 text = user_name_div.get_text(strip=True)
                 # Replace with bold text and a line break
                 new_tag = soup.new_tag("div")
                 new_tag.attrs['class'] = 'article-author'
                 strong = soup.new_tag("strong")
                 strong.string = text
                 new_tag.append(strong)
                 new_tag.append(soup.new_tag("br"))
                 new_tag.append(soup.new_tag("br"))
                 user_name_div.replace_with(new_tag)

            # Add to processed images so we don't duplicate them if they appear in the thread
            for img in article_view.find_all('img'):
                src = img.get('src')
                if src:
                    processed_img_urls.add(src)

            combined_html += f"""
            <div class="x-article-longform">
                {article_view}
            </div>
            <hr>
            <h3>Discussion Thread</h3>
            """
        
        # 3. Find the main container (Timeline)
        # On a status page, it's usually "Timeline: Conversation"
        timeline = soup.find('div', attrs={'aria-label': 'Timeline: Conversation'})
        if not timeline:
            # Fallback to just finding articles
            articles = soup.find_all('article')
        else:
            articles = timeline.find_all('article')
            
        if not articles:
            logger.warning("No article tag found in X.com page.")
            if not article_view:
                return title, html # Fallback if neither article view nor threads found
            # If we have article view but no threads, we can proceed with what we have
        
        # 3. Iterate over articles (Tweets)
        op_handle = None
        
        for i, article in enumerate(articles):
            # Skip articles that contain other articles (nested structures/wrappers)
            if article.find('article'):
                continue

            # Extract User Name and Handle
            user_div = article.find('div', attrs={'data-testid': 'User-Name'})
            user_text = user_div.get_text(strip=True) if user_div else "Unknown User"
            
            # Try to extract handle (e.g. @koylanai) to identify OP
            # The handle is usually in a span starting with @
            handle = "unknown"
            if user_div:
                for span in user_div.find_all('span'):
                    if span.text.startswith('@'):
                        handle = span.text
                        break
            
            # Set OP handle from the first valid article
            if op_handle is None and handle != "unknown":
                op_handle = handle
                logger.info(f"Identified OP handle: {op_handle}")

            # Extract Text
            tweet_text_div = article.find('div', attrs={'data-testid': 'tweetText'})
            text_html = ""
            if tweet_text_div:
                # Replace emojis with text before converting to string
                self._replace_emojis_with_text(tweet_text_div)
                # Clean up links/spans if needed, but keeping them is usually fine for markdownify
                text_html = str(tweet_text_div)
            
            # Text Deduping
            import hashlib
            # Normalize text for deduping
            text_content = tweet_text_div.get_text(strip=True) if tweet_text_div else ""
            if text_content:
                text_hash = hashlib.md5(text_content.encode('utf-8')).hexdigest()
                if text_hash in seen_texts:
                    logger.debug("Skipping duplicate tweet text.")
                    continue
                seen_texts.add(text_hash)
            
            # Extract Images (Tweet Photos)
            images_html = ""
            photo_divs = article.find_all('div', attrs={'data-testid': 'tweetPhoto'})
            for div in photo_divs:
                img = div.find('img')
                if img and img.get('src'):
                    src = img['src']
                    # Skip emojis in photos just in case, though unlikely here
                    if 'emoji' in src:
                        continue
                        
                    if src not in processed_img_urls:
                        # Upgrade quality
                        import re
                        src = re.sub(r'name=\w+', 'name=large', src)
                        images_html += f'<figure><img src="{src}" alt="Tweet Image"></figure>'
                        processed_img_urls.add(src)

            # Extract Card Media (Link Previews / Articles)
            card_wrapper = article.find('div', attrs={'data-testid': 'card.wrapper'})
            if card_wrapper:
                imgs = card_wrapper.find_all('img')
                for img in imgs:
                    src = img.get('src')
                    if src and 'profile_images' not in src and 'emoji' not in src and src not in processed_img_urls:
                        images_html += f'<figure><img src="{src}" alt="Card Image"></figure>'
                        processed_img_urls.add(src)
            
            # Extract Video Poster (if it's a video)
            video_player = article.find('div', attrs={'data-testid': 'videoPlayer'})
            if video_player:
                 # Video poster is often in a nested video tag or style
                 # For simplicity, we might miss the video poster if it's complex, 
                 # but sometimes there is a preview image.
                 # Let's look for any img inside videoPlayer that we haven't seen
                 for img in video_player.find_all('img'):
                     src = img.get('src')
                     if src and 'emoji' not in src and src not in processed_img_urls:
                         images_html += f'<figure><img src="{src}" alt="Video Poster"></figure>'
                         processed_img_urls.add(src)

            # Skip empty tweets (promoted tweets might be empty or different structure)
            if not text_html and not images_html:
                continue

            # Build the tweet block
            # Logic: If it's the OP, make it look like part of the article.
            # If it's someone else, make it look like a comment/quote.
            
            is_op = (handle == op_handle) or (op_handle is None) # Default to true if we can't determine
            
            if is_op:
                # For OP, we want a clean flow.
                # If it's the very first tweet, maybe show the header (Title/Author is already at top of doc? No, doc title is just page title)
                # Let's show header only for the first tweet.
                
                if i == 0:
                     tweet_block = f"""
                    <div class="tweet-header">
                        <h3>{user_text} <span style="color: #666; font-size: 0.8em;">{handle}</span></h3>
                    </div>
                    <div class="tweet-content">
                        {text_html}
                    </div>
                    <div class="tweet-media">
                        {images_html}
                    </div>
                    <hr>
                    """
                else:
                    # Subsequent OP tweets - just content, maybe a small separator
                    tweet_block = f"""
                    <div class="tweet-content-continuation">
                        {text_html}
                    </div>
                    <div class="tweet-media">
                        {images_html}
                    </div>
                    <br>
                    """
            else:
                # Non-OP tweets (Replies/Comments)
                # We can style them differently or put them in a blockquote
                tweet_block = f"""
                <blockquote>
                    <strong>{user_text}</strong> ({handle}):
                    <div class="tweet-content">
                        {text_html}
                    </div>
                    <div class="tweet-media">
                        {images_html}
                    </div>
                </blockquote>
                <br>
                """
                
            combined_html += tweet_block

        # 4. Process images (downloading)
        # We create a new soup from our constructed content to use the existing image processing logic
        content_soup = BeautifulSoup(combined_html, 'html.parser')
        images = content_soup.find_all('img')
        logger.info(f"Custom parser found {len(images)} images in the thread.")
        
        for img in images:
            src = img.get('src')
            if src:
                new_src = self.asset_manager.download_image(src, base_url)
                img['src'] = new_src
                # Clean attributes
                for attr in ['width', 'height', 'style', 'class']:
                    if attr in img.attrs: del img[attr]

        return title, str(content_soup)

    def parse_and_process(self, html_content: str, base_url: str) -> str:
        """
        Parses the HTML content, extracts the main article, processes images,
        and returns the cleaned HTML string ready for Markdown conversion.
        """
        try:
            # Special handling for X.com
            if "x.com" in base_url or "twitter.com" in base_url:
                return self._parse_x_com(html_content, base_url)

            # Preprocess HTML to fix specific site issues (like X.com images)
            title = doc.title()
            summary_html = doc.summary()
            
            # If readability fails to extract meaningful content (too short), fallback to full body?
            # For now, let's stick to summary but warn if short.
            if len(summary_html) < 200:
                logger.warning("Extracted content is very short. Readability might have failed.")
            
            soup = BeautifulSoup(summary_html, 'html.parser')
            
            # Process images
            images = soup.find_all('img')
            logger.info(f"Found {len(images)} images in article content.")
            
            for img in images:
                src = img.get('src')
                if src:
                    new_src = self.asset_manager.download_image(src, base_url)
                    img['src'] = new_src
                    # Remove unnecessary attributes like width, height, style
                    if 'width' in img.attrs: del img['width']
                    if 'height' in img.attrs: del img['height']
                    if 'style' in img.attrs: del img['style']
                    if 'class' in img.attrs: del img['class']

            # Remove empty tags or unwanted elements if any (e.g., hidden ads not caught by readability)
            for tag in soup.find_all(['script', 'style', 'iframe']):
                tag.decompose()

            cleaned_html = str(soup)
            return title, cleaned_html

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            raise
