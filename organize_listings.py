#!/usr/bin/env python3
"""
Script to organize eBay listing photos into folders with extracted metadata
"""
import os
import shutil
import json

# Define listings with metadata extracted from images
listings = {
    "the_stand_stephen_king": {
        "title": "The Stand",
        "author": "Stephen King",
        "format": "Limited Edition with Slipcase",
        "condition": "Used",
        "notes": "Orange leather binding with dust jacket featuring sunset road scene",
        "images": ["IMG_5510.jpg", "IMG_5511.jpg"]
    },
    "the_handyman_bentley_little": {
        "title": "The Handyman",
        "author": "Bentley Little",
        "publisher": "Graveyard Editions",
        "edition": "Special Signed Edition - Limited to 500 numbered copies",
        "copy_number": "402",
        "signed_by": "Bentley Little",
        "format": "Hardcover",
        "notes": "Red leather binding with gold gilt title",
        "images": ["IMG_5513.jpg", "IMG_5516.jpg"]
    },
    "zodiac_neal_stephenson": {
        "title": "Zodiac: The Eco Thriller",
        "author": "Neal Stephenson",
        "edition": "Special Signed Edition - Limited to 500 numbered and 26 lettered copies",
        "copy_number": "118",
        "signed_by": "Neal Stephenson",
        "format": "Hardcover",
        "notes": "Brown/tan binding with skull and tentacle cover art",
        "images": ["IMG_5517.jpg", "IMG_5519.jpg"]
    },
    "in_laymons_terms": {
        "title": "In Laymon's Terms",
        "editor": "Kelly Laymon, Steve Gerlach, Richard Chizmar",
        "edition": "Special Signed Edition - Limited to 400 numbered copies",
        "copy_number": "226",
        "format": "Hardcover with slipcase",
        "signed": "Multiple contributors",
        "notes": "Black slipcase with signature page showing multiple author signatures",
        "images": ["IMG_5520.jpg", "IMG_5521.jpg"]
    },
    "october_dreams": {
        "title": "October Dreams: A Celebration of Halloween",
        "editor": "Richard Chizmar and Robert Morrish",
        "format": "Hardcover",
        "notes": "Orange/red cover with Halloween pumpkin artwork",
        "images": ["IMG_5523.jpg"]
    },
    "fearie_tales": {
        "title": "Fearie Tales",
        "editor": "Stephen Jones",
        "illustrator": "Alan Lee",
        "subtitle": "Stories of the Grimm & Gruesome",
        "format": "Hardcover with slipcase",
        "signed": "Multiple contributors",
        "edition": "Special signed edition",
        "notes": "Multiple signature pages with gothic/fantasy artwork, includes dramatic cat-like creature illustration",
        "images": ["IMG_5525.jpg", "IMG_5526.jpg", "IMG_5527.jpg", "IMG_5528.jpg", "IMG_5530.jpg"]
    },
    "first_blood_david_morrell": {
        "title": "First Blood",
        "author": "David Morrell",
        "edition": "Signed Lettered Edition - Limited to 52 copies",
        "copy_letter": "PP",
        "signed_by": "David Morrell",
        "format": "Hardcover with slipcase",
        "notes": "Black leather spine with gold gilt lettering, housed in wood-grain slipcase",
        "images": ["IMG_5531.jpg", "IMG_5532.jpg", "IMG_5533.jpg"]
    },
    "dark_delicacies": {
        "title": "Dark Delicacies: Original Tales of Terror and the Macabre",
        "editor": "Del Howison and Jeff Gelb",
        "edition": "Deluxe Signed Artist Edition - Limited to 1250 numbered copies",
        "copy_number": "16",
        "format": "Hardcover",
        "signed": "Multiple contributors including Ned Dameron and Glenn Chadbourne",
        "notes": "Red/orange artwork with signature pages featuring skulls and gothic horror imagery. Cover shows skull in bloody dinner setting.",
        "images": ["IMG_5534.jpg", "IMG_5535.jpg", "IMG_5537.jpg", "IMG_5538.jpg", "IMG_5539.jpg"]
    }
}

def create_listing_folders():
    """Create folders for each listing and organize images"""
    base_path = os.path.dirname(os.path.abspath(__file__))

    for folder_name, metadata in listings.items():
        # Create folder
        folder_path = os.path.join(base_path, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Save metadata as JSON
        metadata_file = os.path.join(folder_path, "metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Copy images to folder
        for image in metadata['images']:
            src = os.path.join(base_path, image)
            if os.path.exists(src):
                dst = os.path.join(folder_path, image)
                shutil.copy2(src, dst)
                print(f"Copied {image} to {folder_name}/")
            else:
                print(f"Warning: {image} not found")

        print(f"Created folder: {folder_name}")
        print(f"  - {len(metadata['images'])} images")
        print(f"  - Metadata saved\n")

if __name__ == "__main__":
    print("Organizing eBay listing photos...\n")
    create_listing_folders()
    print("\nDone! Created 8 listing folders with metadata.")
    print("\nNote: The following files were not included (personal photos):")
    print("  - lp_image.jpg")
    print("  - lp_image 2.jpg")
    print("  - lp_image 3.jpg")
