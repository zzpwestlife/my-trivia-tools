import os
import hashlib
import requests
from urllib.parse import urljoin, urlparse
from src.logger import logger

class AssetManager:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.assets_dir = os.path.join(output_dir, "assets")
        self.os_assets_dir = os.path.abspath(self.assets_dir)
        
        if not os.path.exists(self.assets_dir):
            os.makedirs(self.assets_dir)

    def download_image(self, img_url: str, base_url: str) -> str:
        """
        Downloads an image from the given URL and saves it to the assets directory.
        Returns the relative path to the saved image for use in Markdown.
        """
        try:
            # Resolve relative URLs
            full_url = urljoin(base_url, img_url)
            
            # Generate a unique filename based on the URL hash
            url_hash = hashlib.md5(full_url.encode('utf-8')).hexdigest()
            ext = os.path.splitext(urlparse(full_url).path)[1]
            if not ext:
                ext = ".jpg"  # Default extension if none found
            
            filename = f"{url_hash}{ext}"
            filepath = os.path.join(self.assets_dir, filename)
            relative_path = f"assets/{filename}"

            # Check if already exists
            if os.path.exists(filepath):
                logger.debug(f"Image already exists: {filepath}")
                return relative_path

            logger.info(f"Downloading image: {full_url}")
            response = requests.get(full_url, stream=True, timeout=10)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            
            logger.success(f"Saved image to {filepath}")
            return relative_path

        except Exception as e:
            logger.error(f"Failed to download image {img_url}: {e}")
            return img_url  # Return original URL if download fails
