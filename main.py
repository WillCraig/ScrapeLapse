"""
Image Scraper and Timelapse Creator

This script downloads images from a webpage and creates a timelapse video from them.
It includes parallel downloading, logging, and video creation capabilities.
Now includes an option to exclude images taken between 8 PM and 6 AM and saves images in yyyymmdd format.
"""

import os
from datetime import datetime
import time
from typing import List, Tuple
import csv

import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import cv2
from dotenv import load_dotenv


def get_image_timestamp(filename: str) -> datetime:
    """
    Extracts the timestamp from the image filename.

    Assumes that the filename includes the timestamp in the format 'YYYYMMDD_HHMMSS'.

    Args:
        filename (str): The image filename.

    Returns:
        datetime: The extracted datetime object, or None if parsing fails.
    """
    base_name = os.path.basename(filename)
    name_part, _ = os.path.splitext(base_name)
    try:
        dt = datetime.strptime(name_part, '%Y%m%d_%H%M%S')
        return dt
    except ValueError:
        # Handle cases where the format is different
        return None


def is_time_in_exclude_window(hour: int, exclude_start: int, exclude_end: int) -> bool:
    """
    Determines if a given hour is within the exclude time window.

    Args:
        hour (int): The hour to check (0-23).
        exclude_start (int): Start hour of the exclude window.
        exclude_end (int): End hour of the exclude window.

    Returns:
        bool: True if hour is within the exclude window, False otherwise.
    """
    if exclude_start < exclude_end:
        # Normal case, e.g., exclude from 6am to 8pm
        return exclude_start <= hour < exclude_end
    else:
        # Crosses midnight, e.g., exclude from 8pm to 6am
        return hour >= exclude_start or hour < exclude_end


class ImageDownloader:
    """Handles downloading images from a webpage."""

    def __init__(self, save_dir: str, max_workers: int = 10, exclude_night_photos: bool = False):
        """
        Initialize the ImageDownloader.

        Args:
            save_dir (str): Directory to save downloaded images
            max_workers (int): Maximum number of concurrent download threads
            exclude_night_photos (bool): Whether to exclude images taken between 8 PM and 6 AM
        """
        self.save_dir = save_dir
        self.max_workers = max_workers
        self.exclude_night_photos = exclude_night_photos
        self._ensure_save_dir()

    def _ensure_save_dir(self) -> None:
        """Create the save directory if it doesn't exist."""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)

    def _download_single_image(self, img_info: Tuple[str, datetime]) -> bool:
        """
        Download a single image.

        Args:
            img_info (tuple): Tuple containing (img_url, img_datetime)

        Returns:
            bool: True if download was successful, False otherwise
        """
        img_url, img_datetime = img_info
        try:
            img_data = requests.get(img_url).content
            # Create subdirectory based on date
            date_str = img_datetime.strftime('%Y%m%d')
            date_dir = os.path.join(self.save_dir, date_str)
            if not os.path.exists(date_dir):
                os.makedirs(date_dir)
            # Save image in date directory with timestamped filename
            img_filename = os.path.join(
                date_dir, img_datetime.strftime('%Y%m%d_%H%M%S') + '.jpg'
            )
            with open(img_filename, 'wb') as img_file:
                img_file.write(img_data)
            print(f"Downloaded {img_filename}")
            return True
        except Exception as e:
            print(f"Failed to download {img_url}: {e}")
            return False

    def download_images(self, url: str) -> int:
        """
        Download images from the specified URL.

        Args:
            url (str): Webpage URL to scrape for images

        Returns:
            int: Number of new images downloaded
        """
        # Get existing images
        downloaded_images = set()
        for root, _, files in os.walk(self.save_dir):
            downloaded_images.update(files)

        # Scrape webpage for image links
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        image_links = soup.find_all('a', href=lambda href: href and href.endswith('.jpg'))

        # Prepare list of images to download
        image_info_list = []
        for img_tag in image_links:
            img_href = img_tag.get('href')
            img_filename = os.path.basename(img_href)
            if img_filename in downloaded_images:
                continue

            img_datetime = get_image_timestamp(img_filename)
            if img_datetime is None:
                # Could not parse timestamp, skip the image
                print(f"Skipping image with unrecognized timestamp format: {img_filename}")
                continue

            if self.exclude_night_photos:
                img_hour = img_datetime.hour
                if is_time_in_exclude_window(img_hour, 20, 6):
                    # Image is in exclude window, skip it
                    print(f"Excluding image taken at {img_hour}:00: {img_filename}")
                    continue

            image_info_list.append((os.path.join(url, img_href), img_datetime))

        if not image_info_list:
            print("No new images to download.")
            return 0

        # Download images in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self._download_single_image, image_info_list))

        successful_downloads = sum(results)
        print(f"Downloaded {successful_downloads} new images.")
        return successful_downloads


class TimelapseCreator:
    """Handles creating timelapse videos from images."""

    def __init__(self, image_folder: str, fps: int = 30):
        """
        Initialize the TimelapseCreator.

        Args:
            image_folder (str): Folder containing the images
            fps (int): Frames per second for the output video
        """
        self.image_folder = image_folder
        self.fps = fps

    def create_video(self, output_path: str) -> bool:
        """
        Create a timelapse video from the images.

        Args:
            output_path (str): Path where the video will be saved

        Returns:
            bool: True if video creation was successful, False otherwise
        """
        image_files = []
        for root, _, files in os.walk(self.image_folder):
            for img in files:
                if img.endswith('.jpg'):
                    img_path = os.path.join(root, img)
                    img_timestamp = get_image_timestamp(img)
                    if img_timestamp:
                        image_files.append((img_timestamp, img_path))
                    else:
                        # Skip images without recognizable timestamp
                        continue

        if not image_files:
            print("No images found for timelapse creation.")
            return False

        # Sort images by timestamp
        image_files.sort()

        # Get dimensions from first image
        first_image = cv2.imread(image_files[0][1])
        if first_image is None:
            print("Failed to read the first image.")
            return False

        height, width, _ = first_image.shape

        # Create video writer
        try:
            video = cv2.VideoWriter(
                output_path,
                cv2.VideoWriter_fourcc(*'mp4v'),
                self.fps,
                (width, height)
            )
        except Exception as e:
            print(f"Failed to initialize video writer: {e}")
            return False

        # Add frames
        for _, image_path in image_files:
            frame = cv2.imread(image_path)
            if frame is None:
                print(f"Failed to read image: {image_path}")
                continue
            video.write(frame)

        video.release()
        print(f"Video saved as {output_path}")
        return True


class ExecutionLogger:
    """Handles logging of execution metrics."""

    def __init__(self, save_dir: str):
        """
        Initialize the ExecutionLogger.

        Args:
            save_dir (str): Directory where the log file will be saved
        """
        self.log_file = os.path.join(save_dir, 'time_log.csv')
        self.fieldnames = ['date_time', 'num_images', 'total_time', 'speed_per_image']

    def log_execution(self, date_time: str, num_images: int, total_time: float) -> None:
        """
        Log execution metrics to CSV file.

        Args:
            date_time (str): Timestamp of the execution
            num_images (int): Number of images processed
            total_time (float): Total execution time in seconds
        """
        speed_per_image = total_time / num_images if num_images > 0 else 0

        with open(self.log_file, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)

            if file.tell() == 0:
                writer.writeheader()

            writer.writerow({
                'date_time': date_time,
                'num_images': num_images,
                'total_time': total_time,
                'speed_per_image': speed_per_image
            })


def main():
    """Main execution function."""
    # Load configuration
    load_dotenv()
    url = os.getenv('TARGET_URL', 'https://www.example.com')
    current_date = datetime.now().strftime("%Y_%m_%d")

    # Configuration
    config = {
        'save_dir': 'images_export',
        'output_video': f"expv_timelapse_{current_date}.mp4",
        'max_workers': 32,
        'fps': 60,
        'exclude_night_photos': True,
        'vid_export': True
    }

    # Track execution time
    start_time = time.time()

    # Initialize components
    downloader = ImageDownloader(
        save_dir=config['save_dir'],
        max_workers=config['max_workers'],
        exclude_night_photos=config['exclude_night_photos']
    )
    timelapse = TimelapseCreator(config['save_dir'], config['fps'])
    logger = ExecutionLogger(config['save_dir'])

    # Execute pipeline
    num_images = downloader.download_images(url)

    if config['vid_export']:
        print('creating video')
        timelapse.create_video(config['output_video'])


    # Log execution metrics
    total_time = time.time() - start_time
    current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.log_execution(current_date_time, num_images, total_time)

    print(f"Total execution time: {total_time:.2f} seconds")


if __name__ == "__main__":
    main()
