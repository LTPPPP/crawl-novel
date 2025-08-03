import os
import json
import time
import requests
import re
from argparse import ArgumentParser

def fetch_books(language, limit, search_keyword):
    """Fetch books metadata from Gutendex API."""
    base_url = "https://gutendex.com/books/"
    params = {
        "language": language,
        "search": search_keyword,
        "limit": limit
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()["results"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []

def roman_numeral(n):
    """Convert an integer to a Roman numeral."""
    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    syms = [
        "M", "CM", "D", "CD",
        "C", "XC", "L", "XL",
        "X", "IX", "V", "IV",
        "I"
    ]
    roman_num = ''
    i = 0
    while n > 0:
        for _ in range(n // val[i]):
            roman_num += syms[i]
            n -= val[i]
        i += 1
    return roman_num

def download_book(book, output_dir):
    """Download book content, images, and save metadata."""
    title = book.get("title", "Unknown Title").replace("/", "-")[:10]
    author = book.get("authors", [{}])[0].get("name", "Unknown Author").replace("/", "-")
    language = book.get("languages", ["Unknown"])[0]
    download_url = book.get("formats", {}).get("text/plain") or book.get("formats", {}).get("text/html")

    if not download_url:
        print(f"No downloadable format found for {title} by {author}")
        return

    try:
        response = requests.get(download_url, timeout=10)
        response.raise_for_status()

        # Sanitize folder name to remove invalid characters
        sanitized_title = ''.join(c for c in title if c not in "<>:\"/\\|?*")
        sanitized_author = ''.join(c for c in author if c not in "<>:\"/\\|?*")

        # Create a folder for the book
        book_folder = os.path.join(output_dir, f"{sanitized_title} - {sanitized_author}")
        os.makedirs(book_folder, exist_ok=True)

        # Save book content
        file_name = f"{sanitized_title}-{sanitized_author}.html"
        file_path = os.path.join(book_folder, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(response.text)

        # Split content into chapters (assuming chapters are separated by 'Chapter' keyword)
        chapters = re.split(r'Chapter\\s+\\d+', response.text)
        for i, chapter_content in enumerate(chapters):
            chapter_folder = os.path.join(book_folder, f"Chapter_{roman_numeral(i+1)}")
            os.makedirs(chapter_folder, exist_ok=True)

            # Save chapter content
            chapter_file_path = os.path.join(chapter_folder, f"Chapter_{roman_numeral(i+1)}.txt")
            with open(chapter_file_path, "w", encoding="utf-8") as f:
                f.write(chapter_content)

        # Download images if available
        image_urls = [url for key, url in book.get("formats", {}).items() if key.startswith("image/")]
        images_folder = os.path.join(book_folder, "images")
        os.makedirs(images_folder, exist_ok=True)
        for idx, image_url in enumerate(image_urls):
            try:
                image_response = requests.get(image_url, timeout=10)
                image_response.raise_for_status()
                image_path = os.path.join(images_folder, f"image_{idx+1}.jpg")
                with open(image_path, "wb") as img_file:
                    img_file.write(image_response.content)
            except requests.exceptions.RequestException as e:
                print(f"Error downloading image {idx+1} for {title} by {author}: {e}")

        # Update metadata to include chapter structure and images
        metadata = {
            "title": title,
            "author": author,
            "language": language,
            "download_url": download_url,
            "local_file_path": file_path,
            "source": "Project Gutenberg",
            "chapters": [
                {
                    "chapter_number": roman_numeral(i+1),
                    "local_file_path": os.path.join(f"Chapter_{roman_numeral(i+1)}", f"Chapter_{roman_numeral(i+1)}.txt")
                } for i in range(len(chapters))
            ],
            "images": [
                os.path.join("images", f"image_{idx+1}.jpg") for idx in range(len(image_urls))
            ]
        }
        metadata_file = os.path.join(book_folder, "metadata.json")
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        print(f"Downloaded: {title} by {author}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {title} by {author}: {e}")

def main():
    parser = ArgumentParser(description="Crawl books from Project Gutenberg via Gutendex API.")
    parser.add_argument("--lang", type=str, default="en", help="Language filter (e.g., 'en' for English, 'vi' for Vietnamese).")
    parser.add_argument("--limit", type=int, default=10, help="Limit the number of books to fetch.")
    parser.add_argument("--search", type=str, default="", help="Search keyword for books.")
    parser.add_argument("--output", type=str, default="output", help="Output directory for downloaded books and metadata.")

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)

    # Fetch books metadata
    books = fetch_books(args.lang, args.limit, args.search)

    # Download each book
    for book in books:
        download_book(book, args.output)
        time.sleep(2)  # Sleep to avoid being blocked

if __name__ == "__main__":
    main()
