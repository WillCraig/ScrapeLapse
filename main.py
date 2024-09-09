import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import cv2
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def download_image(img_url: str, save_dir: str) -> None:
    """
    Downloads a single image and saves it to the specified directory.
    """
    try:
        img_data = requests.get(img_url).content
        img_filename = os.path.join(save_dir, os.path.basename(img_url))

        with open(img_filename, 'wb') as img_file:
            img_file.write(img_data)

        print(f"Downloaded {img_filename}")
    except Exception as e:
        print(f"Failed to download {img_url}: {e}")


def download_images(url: str, save_dir: str, max_workers: int = 10) -> None:
    """
    Scrapes image URLs from the provided webpage and downloads them in parallel.
    """
    # Create directory if it doesn't exist
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Send a request to the website
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all <a> tags that link to .jpg images
    image_links = soup.find_all('a', href=lambda href: href and href.endswith('.jpg'))

    # Create a list of image URLs
    image_urls: List[str] = [os.path.join(url, img_tag.get('href')) for img_tag in image_links]

    # Download images using a thread pool for parallel downloads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda img_url: download_image(img_url, save_dir), image_urls)

    print("All images downloaded.")


def create_timelapse(image_folder: str, output_video: str, fps: int = 30) -> None:
    """
    Creates a time-lapse video from images in the specified folder.
    """
    # Get a sorted list of images
    images: List[str] = [img for img in os.listdir(image_folder) if img.endswith(".jpg")]
    images.sort()

    if not images:
        print("No images found.")
        return

    # Get the frame size from the first image
    first_image_path: str = os.path.join(image_folder, images[0])
    frame = cv2.imread(first_image_path)
    height, width, layers = frame.shape

    # Initialize the video writer
    video = cv2.VideoWriter(output_video, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    # Write images to the video
    for image in images:
        img_path: str = os.path.join(image_folder, image)
        frame = cv2.imread(img_path)
        video.write(frame)

    video.release()
    print(f"Video saved as {output_video}")


def main(url: str, save_dir: str, output_video: str, max_workers: int = 10, fps: int = 30) -> None:
    """
    Main function to download images and create a time-lapse video.
    """
    # Download images
    download_images(url, save_dir, max_workers)

    # Create a time-lapse video
    create_timelapse(save_dir, output_video, fps)


if __name__ == "__main__":
    # Load URL from the .env file, defaulting to https://www.apple.com if not present
    url: str = os.getenv('TARGET_URL', 'https://www.apple.com')

    current_date = datetime.now().strftime("%Y_%m_%d")

    # Settings
    save_dir: str = f"images_copy_{current_date}"
    output_video: str =f"expv_timelapse_{current_date}.mp4"
    max_workers: int = 10
    fps: int = 30

    # Run the main process with the provided settings
    main(url, save_dir, output_video, max_workers, fps)
