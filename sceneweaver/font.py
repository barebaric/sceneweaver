from pathlib import Path
from PIL import ImageFont
from .errors import ValidationError


def find_font(font_identifier: str, base_dir: Path) -> str:
    """
    Validates a font and returns the identifier that can be passed to
    ImageFont.
    Checks for file paths first (relative then absolute), then system fonts.
    Raises ValidationError if the font cannot be found.

    Returns the absolute path as a string if it's a file, or the original
    identifier if it's a system font.
    """
    if not font_identifier:
        raise ValidationError("Font identifier cannot be empty.")

    # 1. Check for path relative to the spec file
    potential_path = (base_dir / font_identifier).resolve()
    if potential_path.is_file():
        try:
            # Test if PIL can actually load it
            ImageFont.truetype(str(potential_path))
            return str(potential_path)
        except IOError:
            raise ValidationError(
                "Font file found but appears to be invalid or corrupted: "
                f"{potential_path}"
            )

    # 2. Check for absolute path
    abs_path = Path(font_identifier)
    if abs_path.is_absolute() and abs_path.is_file():
        try:
            ImageFont.truetype(str(abs_path))
            return str(abs_path)
        except IOError:
            raise ValidationError(
                "Font file found but appears to be invalid or corrupted: "
                f"{abs_path}"
            )

    # 3. Check for system font
    try:
        ImageFont.truetype(font_identifier)
        return font_identifier
    except IOError:
        raise ValidationError(
            f"Font '{font_identifier}' not found. It must be a path "
            f"(relative to the spec file) to a valid font file, or a "
            f"font name recognized by your system."
        )
