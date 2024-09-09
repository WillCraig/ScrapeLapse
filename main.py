import os
from datetime import datetime
import time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import cv2
from typing import List
import csv
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def download_image(img_url: str, save_dir: str) -> None:
    """
    Downloads a single image and saves it to the specified directory.

    Args:
        img_url (str): The URL of the image to download.
        save_dir (str): The directory where the image will be saved.
    """
    try:
        img_data = requests.get(img_url).content
        img_filename = os.path.join(save_dir, os.path.basename(img_url))

        with open(img_filename, 'wb') as img_file:
            img_file.write(img_data)

        print(f"Downloaded {img_filename}")
    except Exception as e:
        print(f"Failed to download {img_url}: {e}")


def download_images(url: str, save_dir: str, max_workers: int = 10) -> int:
    """
    Scrapes image URLs from the provided webpage and downloads only new ones in parallel.

    Args:
        url (str): The URL of the webpage to scrape for images.
        save_dir (str): The directory where the images will be saved.
        max_workers (int): The maximum number of threads to use for parallel downloads.

    Returns:
        int: The number of images downloaded.
    """
    # Create directory if it doesn't exist
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # List of already downloaded files
    downloaded_images = set(os.listdir(save_dir))

    # Send a request to the website
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all <a> tags that link to .jpg images
    image_links = soup.find_all('a', href=lambda href: href and href.endswith('.jpg'))

    # Create a list of image URLs and filter out already downloaded images
    image_urls: List[str] = [
        os.path.join(url, img_tag.get('href')) for img_tag in image_links
        if os.path.basename(img_tag.get('href')) not in downloaded_images
    ]

    if not image_urls:
        print("No new images to download.")
        return 0

    # Download images using a thread pool for parallel downloads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda img_url: download_image(img_url, save_dir), image_urls)

    print("New images downloaded.")
    return len(image_urls)


def create_timelapse(image_folder: str, output_video: str, fps: int = 30) -> None:
    """
    Creates a time-lapse video from images in the specified folder.

    Args:
        image_folder (str): The folder containing the images.
        output_video (str): The output video file path.
        fps (int): The frames per second for the video.
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


def log_time_data(date_time: str, num_images: int, total_time: float, save_dir: str) -> None:
    """
    Logs the time, date, number of images, and total execution time to a CSV file.

    Args:
        date_time (str): The date and time of the execution.
        num_images (int): The number of images downloaded.
        total_time (float): The total time taken for execution in seconds.
        save_dir (str): The directory where the log CSV will be saved.
    """
    log_file = os.path.join(save_dir, 'time_log.csv')
    fieldnames = ['date_time', 'num_images', 'total_time', 'speed_per_image']

    # Calculate speed (time per image)
    speed_per_image = total_time / num_images if num_images > 0 else 0

    # Append to the CSV file
    with open(log_file, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Write headers only if the file is new
        if file.tell() == 0:
            writer.writeheader()

        # Write the log entry
        writer.writerow({
            'date_time': date_time,
            'num_images': num_images,
            'total_time': total_time,
            'speed_per_image': speed_per_image
        })


def main(url: str, save_dir: str, output_video: str, max_workers: int = 10, fps: int = 30) -> None:
    """
    Main function to download images and create a time-lapse video.

    Args:
        url (str): The URL of the webpage to scrape for images.
        save_dir (str): The directory where the images will be saved.
        output_video (str): The output video file path.
        max_workers (int): The maximum number of threads to use for parallel downloads.
        fps (int): The frames per second for the video.
    """
    # Track start time
    start_time = time.time()

    # Download images and track the number of images
    num_images = download_images(url, save_dir, max_workers)

    # Create a time-lapse video
    create_timelapse(save_dir, output_video, fps)

    # Track end time and calculate total execution time
    end_time = time.time()
    total_time = end_time - start_time

    # Log the time and speed data
    current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_time_data(current_date_time, num_images, total_time, save_dir)


if __name__ == "__main__":
    # Load URL from the .env file, defaulting to https://www.apple.com if not present
    url: str = os.getenv('TARGET_URL', 'https://www.apple.com')

    current_date = datetime.now().strftime("%Y_%m_%d")

    # Settings
    save_dir: str = f"images_export"
    output_video: str = f"expv_timelapse_{current_date}.mp4"
    max_workers: int = 10
    fps: int = 30

    # Run the main process with the provided settings
    main(url, save_dir, output_video, max_workers, fps)
