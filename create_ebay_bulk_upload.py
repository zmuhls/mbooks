#!/usr/bin/env python3
"""
Generate comprehensive eBay bulk upload CSV from book listing metadata
Maps all metadata fields to appropriate eBay inventory API categories
"""

import json
import csv
import os
from pathlib import Path
from datetime import datetime

# eBay category IDs for books
EBAY_CATEGORY = {
    "id": "377",  # Antiquarian & Collectible
    "path": "Books & Magazines > Books & Book Sets > Antiquarian & Collectible"
}

# Condition mapping to eBay standard condition codes
CONDITION_MAPPING = {
    "NEW": "New",
    "LIKE_NEW": "Like New",
    "VERY_GOOD": "Very Good",
    "GOOD": "Good",
    "ACCEPTABLE": "Acceptable",
    "FOR_PARTS_OR_NOT_WORKING": "For parts or not working"
}


def load_metadata_files(base_path):
    """Load all metadata.json files from listing directories"""
    listings = {}

    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path):
            metadata_file = os.path.join(item_path, "metadata.json")
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        listings[item] = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"Error loading {metadata_file}: {e}")

    return listings


def generate_listing_title(metadata):
    """Generate optimized eBay listing title from metadata"""
    basic = metadata.get("basic_info", {})
    edition = metadata.get("edition_details", {})
    physical = metadata.get("physical_details", {})

    title_parts = []

    # Main title
    if basic.get("title"):
        title_parts.append(basic["title"])

    # Author or Editor
    if basic.get("author"):
        author = basic["author"]
        if isinstance(author, list):
            author = author[0]
        title_parts.append(f"by {author}")
    elif basic.get("editor"):
        editor = basic["editor"]
        if isinstance(editor, list):
            editor = editor[0]
        title_parts.append(f"Editor: {editor}")

    # Edition info
    if edition.get("is_signed") and edition.get("signed_by"):
        signed_by = edition["signed_by"]
        if isinstance(signed_by, list):
            signed_by = ", ".join(signed_by)
        title_parts.append(f"SIGNED by {signed_by}")
    elif edition.get("is_signed"):
        title_parts.append("SIGNED Edition")

    if edition.get("is_limited_edition"):
        edition_desc = edition.get("edition_description", "Limited Edition")
        title_parts.append(f"- {edition_desc}")

    # Format info
    if physical.get("format"):
        title_parts.append(physical["format"])

    full_title = " ".join(title_parts)

    # Truncate to eBay's 80-character limit
    if len(full_title) > 80:
        full_title = full_title[:77] + "..."

    return full_title


def generate_description(metadata):
    """Generate HTML listing description from metadata"""
    basic = metadata.get("basic_info", {})
    pub = metadata.get("publication_details", {})
    edition = metadata.get("edition_details", {})
    physical = metadata.get("physical_details", {})
    condition = metadata.get("condition", {})
    notes = metadata.get("notes", "")

    html_parts = []

    # Title and creators
    html_parts.append(f"<h2>{basic.get('title', 'Unknown Title')}</h2>")

    if basic.get("author"):
        author = basic["author"]
        if isinstance(author, list):
            author = " & ".join(author)
        html_parts.append(f"<p><strong>Author:</strong> {author}</p>")

    if basic.get("editor"):
        editor = basic["editor"]
        if isinstance(editor, list):
            editor = " & ".join(editor)
        html_parts.append(f"<p><strong>Editor:</strong> {editor}</p>")

    if basic.get("illustrator"):
        html_parts.append(f"<p><strong>Illustrator:</strong> {basic['illustrator']}</p>")

    # Publication details
    html_parts.append("<h3>Publication Details</h3><ul>")
    if pub.get("publisher"):
        html_parts.append(f"<li>Publisher: {pub['publisher']}</li>")
    if pub.get("publication_year"):
        html_parts.append(f"<li>Publication Year: {pub['publication_year']}</li>")
    if pub.get("page_count"):
        html_parts.append(f"<li>Pages: {pub['page_count']}</li>")
    if pub.get("language"):
        lang = "English" if pub["language"] == "en" else pub["language"]
        html_parts.append(f"<li>Language: {lang}</li>")
    html_parts.append("</ul>")

    # Edition details
    if edition.get("edition_description"):
        html_parts.append(f"<h3>Edition Information</h3>")
        html_parts.append(f"<p>{edition['edition_description']}</p>")
        if edition.get("is_limited_edition") and edition.get("edition_size"):
            html_parts.append(f"<p>Limited to {edition['edition_size']} copies</p>")
        if edition.get("copy_identifier"):
            copy_id = edition["copy_identifier"]
            html_parts.append(f"<p>Copy: {copy_id['value']}</p>")
        if edition.get("is_signed"):
            signed_info = "<p><strong>Signed</strong>"
            if edition.get("signed_by"):
                signed_by = edition["signed_by"]
                if isinstance(signed_by, list):
                    signed_by = " & ".join(signed_by)
                signed_info += f" by {signed_by}"
            elif edition.get("signature_notes"):
                signed_info += f": {edition['signature_notes']}"
            signed_info += "</p>"
            html_parts.append(signed_info)

    # Physical details
    html_parts.append("<h3>Physical Characteristics</h3><ul>")
    if physical.get("format"):
        html_parts.append(f"<li>Format: {physical['format']}</li>")
    if physical.get("binding_type"):
        html_parts.append(f"<li>Binding: {physical['binding_type']}</li>")
    if physical.get("binding_color"):
        html_parts.append(f"<li>Binding Color: {physical['binding_color']}</li>")
    if physical.get("gilt_details"):
        html_parts.append(f"<li>Gilt Details: {physical['gilt_details']}</li>")
    if physical.get("has_dust_jacket"):
        dj_condition = physical.get("dust_jacket_condition", "Included")
        html_parts.append(f"<li>Dust Jacket: {dj_condition}</li>")
    if physical.get("has_slipcase"):
        html_parts.append(f"<li>Includes Slipcase</li>")
    html_parts.append("</ul>")

    # Condition
    if condition.get("condition_notes"):
        html_parts.append(f"<h3>Condition</h3><p>{condition['condition_notes']}</p>")

    # Additional notes
    if notes:
        html_parts.append(f"<h3>Details</h3><p>{notes}</p>")

    return "".join(html_parts)


def get_image_urls(listing_folder, metadata):
    """Generate full GitHub Pages URLs for eBay images."""
    BASE_URL = "https://zmuhls.github.io/mbooks/listings"

    images = metadata.get("images", {}).get("files", [])
    primary = metadata.get("images", {}).get("primary_image", "")

    # Primary image first
    if primary and primary in images:
        image_list = [primary] + [img for img in images if img != primary]
    else:
        image_list = images

    # Build full URLs
    full_urls = [f"{BASE_URL}/{listing_folder}/{img}" for img in image_list]

    return "|".join(full_urls)


def create_csv(output_file):
    """Create comprehensive eBay bulk upload CSV"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    listings = load_metadata_files(base_path)

    if not listings:
        print("No listings found!")
        return

    # Define CSV columns for eBay bulk upload
    fieldnames = [
        "Action",  # Add, Replace, Delete
        "Item ID",
        "Item Title",
        "Item Description",
        "Item Category",
        "Item Format",
        "Item Condition",
        "Item Type",
        "Listing Format",  # FixedPrice, Auction
        "Item Location",
        "Item Quantity",
        "Item Start Price",
        "Item Reserve Price",
        "Item Duration",
        "Item Currency",
        "Item Location City",
        "Item Location State",
        "Item Location Country",
        "Item Location Postal Code",
        "Format: Format",
        "Language",
        "Author",
        "Publisher",
        "Publication Year",
        "ISBN-10",
        "ISBN-13",
        "Edition",
        "Signed",
        "Limited Edition",
        "Special Attributes",
        "Physical Condition Notes",
        "Binding Type",
        "Binding Color",
        "Has Dust Jacket",
        "Has Slipcase",
        "Gallery Image URLs",
        "Payment Methods",
        "Return Days",
        "Return Accepted",
        "Restocking Fee",
        "Shipping Type",
        "Flat Shipping Rate",
        "Free Shipping",
        "Shipping Policy ID",
        "Payment Policy ID",
        "Return Policy ID",
        "Internal Notes",
        "Data Source"
    ]

    rows = []

    for listing_id, metadata in sorted(listings.items()):
        basic = metadata.get("basic_info", {})
        pub = metadata.get("publication_details", {})
        edition = metadata.get("edition_details", {})
        physical = metadata.get("physical_details", {})
        condition = metadata.get("condition", {})
        pricing = metadata.get("pricing", {})
        ebay_data = metadata.get("ebay_listing_data", {})
        images = metadata.get("images", {})

        # Handle author field
        author = ""
        if basic.get("author"):
            author_val = basic["author"]
            author = author_val if isinstance(author_val, str) else (", ".join(author_val) if author_val else "")
        elif basic.get("editor"):
            editor_val = basic["editor"]
            author = editor_val if isinstance(editor_val, str) else (", ".join(editor_val) if editor_val else "")

        # Handle special attributes
        special_attrs = []
        if edition.get("is_signed"):
            special_attrs.append("Signed")
        if edition.get("is_limited_edition"):
            special_attrs.append("Limited Edition")
        if physical.get("has_dust_jacket"):
            special_attrs.append("Dust Jacket")
        if physical.get("has_slipcase"):
            special_attrs.append("Slipcase")

        # Handle genre
        genre = ""
        if pub.get("genre"):
            genre_val = pub["genre"]
            genre = genre_val if isinstance(genre_val, str) else (", ".join(genre_val) if genre_val else "")

        # Create row
        row = {
            "Action": "Add",
            "Item ID": "",  # Leave empty for new items
            "Item Title": generate_listing_title(metadata),
            "Item Description": generate_description(metadata),
            "Item Category": EBAY_CATEGORY["id"],
            "Item Format": physical.get("format", ""),
            "Item Condition": CONDITION_MAPPING.get(condition.get("overall_grade"), "Used"),
            "Item Type": "Book",
            "Listing Format": "FixedPrice",
            "Item Location": "United States",
            "Item Quantity": "1",
            "Item Start Price": "",  # User to fill in
            "Item Reserve Price": "",
            "Item Duration": "30",  # 30 days
            "Item Currency": "USD",
            "Item Location City": "",
            "Item Location State": "",
            "Item Location Country": "United States",
            "Item Location Postal Code": "",
            "Format: Format": physical.get("format", ""),
            "Language": "English" if pub.get("language") == "en" else pub.get("language", ""),
            "Author": author,
            "Publisher": pub.get("publisher", ""),
            "Publication Year": str(pub.get("publication_year", "")) if pub.get("publication_year") else "",
            "ISBN-10": pub.get("isbn_10", ""),
            "ISBN-13": pub.get("isbn_13", ""),
            "Edition": edition.get("edition_description", ""),
            "Signed": "Yes" if edition.get("is_signed") else "No",
            "Limited Edition": "Yes" if edition.get("is_limited_edition") else "No",
            "Special Attributes": "; ".join(special_attrs) if special_attrs else "",
            "Physical Condition Notes": condition.get("condition_notes", metadata.get("notes", "")),
            "Binding Type": physical.get("binding_type", ""),
            "Binding Color": physical.get("binding_color", ""),
            "Has Dust Jacket": "Yes" if physical.get("has_dust_jacket") else "No",
            "Has Slipcase": "Yes" if physical.get("has_slipcase") else "No",
            "Gallery Image URLs": get_image_urls(listing_id, metadata),
            "Payment Methods": "PayPal, CreditCard",
            "Return Days": "14",
            "Return Accepted": "Yes",
            "Restocking Fee": "",
            "Shipping Type": "Flat",
            "Flat Shipping Rate": "",  # User to fill in
            "Free Shipping": "No",
            "Shipping Policy ID": ebay_data.get("policies", {}).get("fulfillment_policy_id", ""),
            "Payment Policy ID": ebay_data.get("policies", {}).get("payment_policy_id", ""),
            "Return Policy ID": ebay_data.get("policies", {}).get("return_policy_id", ""),
            "Internal Notes": metadata.get("internal_notes", ""),
            "Data Source": "; ".join(metadata.get("data_sources", {}).get("manual_entry", []))
        }

        rows.append(row)

    # Write CSV file
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Created eBay bulk upload CSV: {output_file}")
    print(f"✓ Total listings: {len(rows)}")
    print(f"✓ Fields: {len(fieldnames)}")
    print("\nFirst few columns created:")
    for field in fieldnames[:10]:
        print(f"  - {field}")
    print("  ...")


if __name__ == "__main__":
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "ebay_bulk_upload.csv"
    )
    create_csv(output_path)
