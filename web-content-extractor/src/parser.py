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

    def parse_album_list(self, html: str) -> tuple[str, list]:
        """
        Parses a WeChat Album page to extract the album title and article list.
        Returns: (album_title, list_of_articles)
        Each article is a dict: {'title': str, 'url': str, 'date': str}
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Extract Album Title
        album_title_elem = soup.find(class_="album__label-title")
        if album_title_elem:
            album_title = album_title_elem.get_text(strip=True)
        else:
            album_title = soup.title.string if soup.title else "Unknown Album"
            
        logger.info(f"Parsed Album Title: {album_title}")

        # 2. Extract Articles
        articles = []
        # Find all list items
        items = soup.find_all(class_="album__list-item")
        
        for i, item in enumerate(items):
            # Extract Title
            # Try specific classes first
            title_elem = item.find(class_="album__item-title") or item.find(class_="js_album_item_title")
            if title_elem:
                title = title_elem.get_text(strip=True)
            else:
                # Fallback: look for any link text
                link_elem = item.find("a")
                title = link_elem.get_text(strip=True) if link_elem else f"Article {i+1}"
            
            # Fix duplication issue (e.g. "TitleTitle") if it occurs commonly
            # Simple heuristic: if the string is exactly repeated twice, cut it in half
            # But let's verify if that's actually the case. 
            # In the analysis output: "从Prompt...①从Prompt...①"
            # It seems the text is indeed duplicated.
            # Let's try to find if there is a data attribute or just take the first child's text?
            # Or use regex to check if string is composed of two identical halves
            if len(title) > 0 and len(title) % 2 == 0:
                mid = len(title) // 2
                if title[:mid] == title[mid:]:
                    title = title[:mid]
            
            # Extract URL
            url = item.get('data-link')
            if not url:
                a_tag = item.find('a')
                if a_tag:
                    url = a_tag.get('href')
            
            # Ensure URL is absolute
            if url and not url.startswith('http'):
                # WeChat links are usually absolute, but just in case
                pass
            
            # Extract Date (Create Time)
            # Usually in .album__item-info -> .album__item-content-other -> span
            date = ""
            date_elem = item.find(class_="album__item-content-other")
            if date_elem:
                # usually matches "2024年1月1日" or similar
                date = date_elem.get_text(strip=True)
            
            if title and url:
                articles.append({
                    'title': title,
                    'url': url,
                    'date': date
                })
        
        logger.info(f"Found {len(articles)} articles in album.")
        return album_title, articles

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

    def _preprocess_wechat(self, html_content: str) -> str:
        """
        Specific preprocessing for WeChat articles.
        - Fix lazy loading images (data-src -> src)
        - Clean up manual bullets (•) in list items to avoid double bullets in markdown
        - Clean up WeChat specific headers/sections
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Fix lazy loaded images
        for img in soup.find_all('img'):
            if 'data-src' in img.attrs:
                img['src'] = img['data-src']
        
        # Clean up list items that contain manual bullets
        # WeChat often uses <li><section><span>• </span>...</section></li>
        for li in soup.find_all('li'):
            # Unwrap section and p tags inside li to avoid nested list issues in markdownify
            for tag in li.find_all(['section', 'p']):
                tag.unwrap()
                
            # Check for bullet characters at the start of the text content
            text = li.get_text()
            if text.strip().startswith('•') or text.strip().startswith('·'):
                # We need to find the text node containing the bullet and remove it
                # Recursively search for the first text node
                def remove_bullet(element):
                    if element.string and (element.string.strip().startswith('•') or element.string.strip().startswith('·')):
                        element.string.replace_with(element.string.strip().lstrip('•').lstrip('·').strip())
                        return True
                    if hasattr(element, 'children'):
                        for child in element.children:
                            if remove_bullet(child):
                                return True
                    return False
                
                remove_bullet(li)

        # Auto-link URLs in text
        # Find text nodes that look like URLs and wrap them in <a> tags
        import re
        url_pattern = re.compile(r'(https?://[^\s<>"]+|www\.[^\s<>"]+)')
        
        # Iterate over all text nodes (simplified approach: just find all strings)
        # We need to be careful not to break existing links
        # A safer way is to find text nodes that are NOT inside <a> tags
        for text_node in soup.find_all(string=True):
            if text_node.parent.name == 'a' or text_node.parent.name == 'script' or text_node.parent.name == 'style':
                continue
            
            if url_pattern.search(text_node):
                # We found a URL in text. We need to replace this text node with a sequence of nodes
                # (text, a, text, ...)
                # However, modifying the tree while iterating is tricky.
                # Let's try a simple regex replacement if the text node is just text
                # But converting text node to HTML is hard with BS4 string replacement
                # So we might skip this complex logic for now and rely on post-processing or just let it be.
                # Actually, markdownify might not auto-link plain text.
                # Let's try to wrap it in <> which markdownify might respect or convert to autolink.
                # Or just leave it, standard markdown viewers often auto-link.
                # But the user complained about "messy layout". Long URLs are messy.
                # Converting to [Link](url) makes it cleaner if we truncate the text?
                # No, just standard <url> is fine.
                pass 
                # Decided to skip auto-linking logic in BS4 for now to avoid breaking HTML structure
                # unless we are sure.
                
        # Clean up "扩展方案" style headers
        # Convert <h2 ...><span>扩展方案</span></h2> to clean <h2>扩展方案</h2>
        # Actually markdownify handles h2 fine, but we might want to strip styles
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            # Remove inline styles that might cause issues (though readability usually strips them, let's be safe)
            if 'style' in tag.attrs:
                del tag['style']
            # Clean up inner spans
            for span in tag.find_all('span'):
                span.unwrap()

        # Remove empty paragraphs or sections that just contain spacing
        for p in soup.find_all(['p', 'section']):
            if not p.get_text(strip=True) and not p.find('img'):
                p.decompose()

        return str(soup)

    def parse_and_process(self, html_content: str, base_url: str) -> str:
        """
        Parses the HTML content, extracts the main article, processes images,
        and returns the cleaned HTML string ready for Markdown conversion.
        """
        try:
            # Special handling for X.com
            if "x.com" in base_url or "twitter.com" in base_url:
                return self._parse_x_com(html_content, base_url)

            # Preprocess HTML for specific sites
            if "mp.weixin.qq.com" in base_url:
                logger.info("Detected WeChat article, applying WeChat-specific extraction...")
                # Special handling for WeChat: directly extract #js_content to avoid Readability issues
                soup = BeautifulSoup(html_content, 'html.parser')
                content_div = soup.find(id="js_content")
                if content_div:
                    # Fix lazy loaded images in content_div
                    for img in content_div.find_all('img'):
                        if 'data-src' in img.attrs:
                            img['src'] = img['data-src']
                            # Remove data-src to avoid confusion
                            del img['data-src']
                            
                    # Clean up list items that contain manual bullets
                    for li in content_div.find_all('li'):
                        # Unwrap section and p tags inside li
                        for tag in li.find_all(['section', 'p']):
                            tag.unwrap()
                            
                        # Check for bullet characters at the start of the text content
                        text = li.get_text()
                        if text.strip().startswith('•') or text.strip().startswith('·'):
                            def remove_bullet(element):
                                if element.string and (element.string.strip().startswith('•') or element.string.strip().startswith('·')):
                                    element.string.replace_with(element.string.strip().lstrip('•').lstrip('·').strip())
                                    return True
                                if hasattr(element, 'children'):
                                    for child in element.children:
                                        if remove_bullet(child):
                                            return True
                                return False
                            remove_bullet(li)

                    # Remove empty paragraphs or sections
                    for p in content_div.find_all(['p', 'section']):
                        if not p.get_text(strip=True) and not p.find('img'):
                            p.decompose()

                    # Extract title separately as #js_content doesn't have it
                    # WeChat title is usually in #activity-name
                    title_elem = soup.find(id="activity-name")
                    title = title_elem.get_text(strip=True) if title_elem else soup.title.string

                    # Use content_div as our source
                    soup = BeautifulSoup(str(content_div), 'html.parser')
                    # Skip Readability entirely for WeChat
                    cleaned_html = str(soup)
                    
                    # Process images using the standard logic below
                    # (we need to re-find images in the new soup)
                    images = soup.find_all('img')
                    logger.info(f"Found {len(images)} images in WeChat content.")
                    
                    for img in images:
                        src = img.get('src')
                        if src:
                            new_src = self.asset_manager.download_image(src, base_url)
                            img['src'] = new_src
                            # Remove unnecessary attributes
                            for attr in ['width', 'height', 'style', 'class', 'data-type', 'data-ratio']:
                                if attr in img.attrs: del img[attr]
                    
                    return title, str(soup)
                
                else:
                    logger.warning("Could not find #js_content, falling back to standard Readability...")
                    # Fallthrough to standard logic if #js_content is missing

            # Initialize Readability Document
            doc = Document(html_content)
            
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
