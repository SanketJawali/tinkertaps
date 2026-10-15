import argparse
from pathlib import Path

from PIL import Image

try:
    from .format_convertor import SUPPORTED_FORMATS
except ImportError:
    from format_convertor import SUPPORTED_FORMATS


def downsample_image(
    input_path: Path,
    output_path: Path,
    max_width: int,
    max_height: int,
) -> None:
    if max_width <= 0 or max_height <= 0:
        raise ValueError("max_width and max_height must be greater than zero")

    output_format = SUPPORTED_FORMATS.get(output_path.suffix.lower())
    if output_format is None:
        raise ValueError(f"Unsupported output format: {output_path.suffix}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as source_image:
        image = source_image.copy()
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        if output_format == "JPEG" and image.mode != "RGB":
            rgba_image = image.convert("RGBA")
            background = Image.new("RGB", image.size, "white")
            background.paste(rgba_image, mask=rgba_image.getchannel("A"))
            image = background

        image.save(output_path, format=output_format, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Downsample an image to maximum dimensions.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("max_width", type=int)
    parser.add_argument("max_height", type=int)
    args = parser.parse_args()
    try:
        downsample_image(args.input, args.output, args.max_width, args.max_height)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
