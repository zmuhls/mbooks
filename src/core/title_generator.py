"""Centralized title and description generation for eBay listings.

This module consolidates title generation logic that was previously duplicated
across exporter.py, listing.py, and other scripts. All eBay title/description
generation should go through this module.
"""

from typing import Dict, Any, List, Optional, Union


class TitleGenerator:
    """Generate eBay-optimized titles and descriptions."""

    MAX_TITLE_LENGTH = 80
    TRUNCATION_SUFFIX = "..."

    @classmethod
    def generate_title(
        cls,
        metadata: Dict[str, Any],
        max_length: int = MAX_TITLE_LENGTH,
        include_slipcase: bool = False
    ) -> str:
        """Generate eBay-optimized title from metadata.

        Args:
            metadata: Book metadata dict (can be nested or flat structure)
            max_length: Maximum title length (eBay limit is 80)
            include_slipcase: Whether to include slipcase tag

        Returns:
            Title string, truncated if necessary
        """
        # Handle both nested (metadata.json) and flat (Listing dataclass) structures
        basic = metadata.get('basic_info', metadata)
        edition = metadata.get('edition_details', metadata)
        physical = metadata.get('physical_details', metadata)

        # Start with title
        title_text = basic.get('title', 'Book')
        parts = [title_text]

        # Add creator (author or editor)
        creator = cls._get_creator(basic)
        if creator:
            # Take first author only, truncate at comma
            first_creator = creator.split(',')[0].strip()
            parts.append(f"by {first_creator}")

        # Add special edition markers
        if edition.get('is_signed'):
            parts.append('SIGNED')

        if edition.get('is_limited_edition'):
            parts.append('Limited Ed')

        if include_slipcase and physical.get('has_slipcase'):
            parts.append('w/Slipcase')

        # Join and truncate
        full_title = ' '.join(parts)
        return cls._truncate(full_title, max_length)

    @classmethod
    def generate_description(
        cls,
        metadata: Dict[str, Any],
        format: str = 'html'
    ) -> str:
        """Generate eBay listing description.

        Args:
            metadata: Book metadata dict
            format: Output format ('html' or 'text')

        Returns:
            Description string
        """
        basic = metadata.get('basic_info', metadata)
        edition = metadata.get('edition_details', metadata)
        physical = metadata.get('physical_details', metadata)
        condition = metadata.get('condition', metadata)
        publication = metadata.get('publication_details', metadata)
        notes = metadata.get('notes', '')

        if format == 'html':
            return cls._generate_html_description(
                basic, edition, physical, condition, publication, notes
            )
        else:
            return cls._generate_text_description(
                basic, edition, physical, condition, publication, notes
            )

    @classmethod
    def get_special_attributes(cls, metadata: Dict[str, Any]) -> List[str]:
        """Get list of special attributes for eBay listing.

        Args:
            metadata: Book metadata dict

        Returns:
            List of attribute strings
        """
        edition = metadata.get('edition_details', metadata)
        physical = metadata.get('physical_details', metadata)

        attrs = []
        if edition.get('is_signed'):
            attrs.append('Signed')
        if edition.get('is_limited_edition'):
            attrs.append('Limited Edition')
        if physical.get('has_dust_jacket'):
            attrs.append('Dust Jacket')
        if physical.get('has_slipcase'):
            attrs.append('Slipcase')
        if physical.get('binding_type') == 'Leather':
            attrs.append('Leather Bound')

        return attrs

    @classmethod
    def get_title_length_status(cls, title: str) -> Dict[str, Any]:
        """Get title length status for UI display.

        Args:
            title: The title string

        Returns:
            Dict with length info and color status
        """
        length = len(title)
        if length <= 70:
            status = 'good'
            color = 'green'
        elif length <= 77:
            status = 'warning'
            color = 'yellow'
        else:
            status = 'danger'
            color = 'red'

        return {
            'length': length,
            'max': cls.MAX_TITLE_LENGTH,
            'remaining': cls.MAX_TITLE_LENGTH - length,
            'status': status,
            'color': color,
            'is_valid': length <= cls.MAX_TITLE_LENGTH
        }

    # Private helper methods

    @classmethod
    def _get_creator(cls, basic: Dict[str, Any]) -> Optional[str]:
        """Extract creator string from basic info."""
        author = basic.get('author')
        editor = basic.get('editor')

        creator = author or editor
        if creator is None:
            return None

        # Handle list of authors/editors
        if isinstance(creator, list):
            return ', '.join(str(c) for c in creator)
        return str(creator)

    @classmethod
    def _truncate(cls, text: str, max_length: int) -> str:
        """Truncate text to max length with suffix."""
        if len(text) <= max_length:
            return text
        suffix_len = len(cls.TRUNCATION_SUFFIX)
        return text[:max_length - suffix_len] + cls.TRUNCATION_SUFFIX

    @classmethod
    def _generate_html_description(
        cls,
        basic: Dict,
        edition: Dict,
        physical: Dict,
        condition: Dict,
        publication: Dict,
        notes: str
    ) -> str:
        """Generate comprehensive HTML formatted description for eBay.

        Creates a well-structured HTML description with clear sections
        for all book metadata, optimized for eBay's listing display.
        """
        html_parts = []

        # ===== HEADER SECTION =====
        title = basic.get('title', '')
        subtitle = basic.get('subtitle', '')
        if title:
            html_parts.append(f'<h2 style="color:#333;margin-bottom:5px;">{title}</h2>')
            if subtitle:
                html_parts.append(f'<p style="color:#666;font-style:italic;margin-top:0;">{subtitle}</p>')

        # ===== CREATOR INFO =====
        creator = cls._get_creator(basic)
        if creator:
            label = 'Author' if basic.get('author') else 'Editor'
            html_parts.append(f'<p><strong>{label}:</strong> {creator}</p>')

        illustrator = basic.get('illustrator')
        if illustrator:
            html_parts.append(f'<p><strong>Illustrator:</strong> {illustrator}</p>')

        contributors = basic.get('contributors', [])
        if contributors:
            if isinstance(contributors, list):
                contributors = ', '.join(contributors)
            html_parts.append(f'<p><strong>Contributors:</strong> {contributors}</p>')

        html_parts.append('<hr style="border:1px solid #ddd;margin:15px 0;">')

        # ===== EDITION DETAILS SECTION =====
        has_edition_info = any([
            edition.get('edition_description'),
            edition.get('is_signed'),
            edition.get('is_limited_edition')
        ])

        if has_edition_info:
            html_parts.append('<h3 style="color:#444;">Edition Details</h3>')

            edition_desc = edition.get('edition_description')
            if edition_desc:
                html_parts.append(f'<p><strong>Edition:</strong> {edition_desc}</p>')

            # Signed info with details
            if edition.get('is_signed'):
                signed_by = edition.get('signed_by', 'the author')
                sig_notes = edition.get('signature_notes', '')
                html_parts.append(f'<p><strong>SIGNED</strong> by {signed_by}</p>')
                if sig_notes:
                    html_parts.append(f'<p style="margin-left:20px;color:#555;"><em>{sig_notes}</em></p>')

            # Limited edition info
            if edition.get('is_limited_edition'):
                edition_size = edition.get('edition_size')
                copy_id = edition.get('copy_identifier', {})
                copy_number = edition.get('copy_number') or copy_id.get('value')
                copy_type = copy_id.get('type', 'numbered')

                if edition_size and copy_number:
                    if copy_type == 'lettered':
                        html_parts.append(f'<p><strong>Limited Edition:</strong> Letter {copy_number} of {edition_size} lettered copies</p>')
                    else:
                        html_parts.append(f'<p><strong>Limited Edition:</strong> Copy #{copy_number} of {edition_size}</p>')
                elif edition_size:
                    html_parts.append(f'<p><strong>Limited Edition:</strong> Limited to {edition_size} copies</p>')
                else:
                    html_parts.append('<p><strong>Limited Edition</strong></p>')

            html_parts.append('<hr style="border:1px solid #ddd;margin:15px 0;">')

        # ===== PUBLICATION DETAILS SECTION =====
        has_pub_info = any([
            publication.get('publisher'),
            publication.get('publication_year'),
            publication.get('isbn_13') or publication.get('isbn_10')
        ])

        if has_pub_info:
            html_parts.append('<h3 style="color:#444;">Publication Details</h3>')
            html_parts.append('<table style="border-collapse:collapse;width:100%;max-width:400px;">')

            publisher = publication.get('publisher')
            if publisher:
                html_parts.append(f'<tr><td style="padding:3px 10px 3px 0;"><strong>Publisher:</strong></td><td>{publisher}</td></tr>')

            year = publication.get('publication_year')
            if year:
                html_parts.append(f'<tr><td style="padding:3px 10px 3px 0;"><strong>Year:</strong></td><td>{year}</td></tr>')

            orig_year = publication.get('original_publication_year')
            if orig_year and orig_year != year:
                html_parts.append(f'<tr><td style="padding:3px 10px 3px 0;"><strong>Original Publication:</strong></td><td>{orig_year}</td></tr>')

            isbn = publication.get('isbn_13') or publication.get('isbn_10')
            if isbn:
                html_parts.append(f'<tr><td style="padding:3px 10px 3px 0;"><strong>ISBN:</strong></td><td>{isbn}</td></tr>')

            pages = publication.get('page_count')
            if pages:
                html_parts.append(f'<tr><td style="padding:3px 10px 3px 0;"><strong>Pages:</strong></td><td>{pages}</td></tr>')

            language = publication.get('language', 'en')
            if language and language != 'en':
                html_parts.append(f'<tr><td style="padding:3px 10px 3px 0;"><strong>Language:</strong></td><td>{language.upper()}</td></tr>')

            html_parts.append('</table>')
            html_parts.append('<hr style="border:1px solid #ddd;margin:15px 0;">')

        # ===== PHYSICAL DETAILS SECTION =====
        html_parts.append('<h3 style="color:#444;">Physical Description</h3>')
        html_parts.append('<table style="border-collapse:collapse;width:100%;max-width:400px;">')

        book_format = physical.get('format', 'Hardcover')
        html_parts.append(f'<tr><td style="padding:3px 10px 3px 0;"><strong>Format:</strong></td><td>{book_format}</td></tr>')

        binding = physical.get('binding_type')
        if binding:
            binding_info = binding
            binding_color = physical.get('binding_color')
            if binding_color:
                binding_info += f' ({binding_color})'
            html_parts.append(f'<tr><td style="padding:3px 10px 3px 0;"><strong>Binding:</strong></td><td>{binding_info}</td></tr>')

        gilt = physical.get('gilt_details')
        if gilt:
            html_parts.append(f'<tr><td style="padding:3px 10px 3px 0;"><strong>Gilt:</strong></td><td>{gilt}</td></tr>')

        html_parts.append('</table>')

        # Extras (slipcase, dust jacket)
        extras = []
        if physical.get('has_dust_jacket'):
            dj_cond = physical.get('dust_jacket_condition')
            if dj_cond:
                extras.append(f'Dust jacket ({dj_cond})')
            else:
                extras.append('Dust jacket included')

        if physical.get('has_slipcase'):
            sc_cond = physical.get('slipcase_condition')
            if sc_cond:
                extras.append(f'Slipcase ({sc_cond})')
            else:
                extras.append('Slipcase included')

        if extras:
            html_parts.append(f'<p style="margin-top:10px;"><strong>Includes:</strong> {", ".join(extras)}</p>')

        html_parts.append('<hr style="border:1px solid #ddd;margin:15px 0;">')

        # ===== CONDITION SECTION =====
        html_parts.append('<h3 style="color:#444;">Condition</h3>')

        grade = condition.get('overall_grade')
        if grade:
            grade_display = grade.replace('_', ' ').title()
            # Color code condition
            grade_colors = {
                'New': '#2e7d32',
                'Like New': '#388e3c',
                'Very Good': '#689f38',
                'Good': '#afb42b',
                'Acceptable': '#fbc02d'
            }
            color = grade_colors.get(grade_display, '#666')
            html_parts.append(f'<p><strong>Overall Grade:</strong> <span style="color:{color};font-weight:bold;">{grade_display}</span></p>')

        book_cond = condition.get('book_condition')
        if book_cond:
            html_parts.append(f'<p>{book_cond}</p>')

        defects = condition.get('defects', [])
        if defects:
            html_parts.append('<p><strong>Notes:</strong></p>')
            html_parts.append('<ul style="margin:5px 0;padding-left:20px;">')
            for defect in defects:
                html_parts.append(f'<li>{defect}</li>')
            html_parts.append('</ul>')

        special_features = condition.get('special_features', [])
        if special_features:
            html_parts.append('<p><strong>Special Features:</strong></p>')
            html_parts.append('<ul style="margin:5px 0;padding-left:20px;">')
            for feature in special_features:
                html_parts.append(f'<li>{feature}</li>')
            html_parts.append('</ul>')

        cond_notes = condition.get('condition_notes')
        if cond_notes:
            html_parts.append(f'<p style="color:#555;"><em>{cond_notes}</em></p>')

        # ===== ADDITIONAL NOTES =====
        if notes:
            html_parts.append('<hr style="border:1px solid #ddd;margin:15px 0;">')
            html_parts.append(f'<p>{notes}</p>')

        # ===== FOOTER =====
        html_parts.append('<hr style="border:1px solid #ddd;margin:15px 0;">')
        html_parts.append('<p style="color:#888;font-size:0.9em;">Please see photos for detailed condition assessment. Feel free to message with any questions.</p>')

        return '\n'.join(html_parts)

    @classmethod
    def _generate_text_description(
        cls,
        basic: Dict,
        edition: Dict,
        physical: Dict,
        condition: Dict,
        publication: Dict,
        notes: str
    ) -> str:
        """Generate comprehensive plain text description."""
        lines = []

        # Title and creator
        title = basic.get('title', '')
        if title:
            lines.append(title.upper())
            subtitle = basic.get('subtitle')
            if subtitle:
                lines.append(subtitle)
            lines.append('')

        creator = cls._get_creator(basic)
        if creator:
            label = 'Author' if basic.get('author') else 'Editor'
            lines.append(f"{label}: {creator}")

        illustrator = basic.get('illustrator')
        if illustrator:
            lines.append(f"Illustrator: {illustrator}")

        lines.append('')

        # Edition info
        edition_desc = edition.get('edition_description')
        if edition_desc:
            lines.append(f"Edition: {edition_desc}")

        if edition.get('is_signed'):
            signed_by = edition.get('signed_by', 'the author')
            lines.append(f"SIGNED by {signed_by}")

        if edition.get('is_limited_edition'):
            edition_size = edition.get('edition_size')
            copy_id = edition.get('copy_identifier', {})
            copy_number = edition.get('copy_number') or copy_id.get('value')
            if edition_size and copy_number:
                lines.append(f"Limited Edition: Copy #{copy_number} of {edition_size}")
            elif edition_size:
                lines.append(f"Limited Edition: {edition_size} copies")

        # Publication details
        publisher = publication.get('publisher')
        year = publication.get('publication_year')
        if publisher or year:
            lines.append('')
            if publisher:
                lines.append(f"Publisher: {publisher}")
            if year:
                lines.append(f"Year: {year}")

        isbn = publication.get('isbn_13') or publication.get('isbn_10')
        if isbn:
            lines.append(f"ISBN: {isbn}")

        # Physical details
        lines.append('')
        book_format = physical.get('format', 'Hardcover')
        lines.append(f"Format: {book_format}")

        binding = physical.get('binding_type')
        if binding:
            lines.append(f"Binding: {binding}")

        if physical.get('has_dust_jacket'):
            lines.append("Includes dust jacket")
        if physical.get('has_slipcase'):
            lines.append("Includes slipcase")

        # Condition
        lines.append('')
        grade = condition.get('overall_grade')
        if grade:
            lines.append(f"Condition: {grade.replace('_', ' ').title()}")

        book_cond = condition.get('book_condition')
        if book_cond:
            lines.append(book_cond)

        defects = condition.get('defects', [])
        for defect in defects:
            lines.append(f"- {defect}")

        # Notes
        if notes:
            lines.append('')
            lines.append(notes)

        lines.append('')
        lines.append("Please see photos for detailed condition. Questions welcome.")

        return '\n'.join(lines)


# Convenience functions for direct import
def generate_title(metadata: Dict[str, Any], **kwargs) -> str:
    """Generate eBay title from metadata."""
    return TitleGenerator.generate_title(metadata, **kwargs)


def generate_description(metadata: Dict[str, Any], **kwargs) -> str:
    """Generate eBay description from metadata."""
    return TitleGenerator.generate_description(metadata, **kwargs)


def get_special_attributes(metadata: Dict[str, Any]) -> List[str]:
    """Get special attributes list from metadata."""
    return TitleGenerator.get_special_attributes(metadata)
