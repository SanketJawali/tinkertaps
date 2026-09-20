# image/format_convertor.py

import argparse
from pathlib import Path

from PIL import Image


SUPPORTED_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}


def convert_image(input_path: Path, output_path: Path) -> None:
    input_format = SUPPORTED_FORMATS.get(input_path.suffix.lower())
    output_format = SUPPORTED_FORMATS.get(output_path.suffix.lower())

    if input_format is None:
        raise ValueError(
            f"Unsupported input format: {input_path.suffix}"
        )

    if output_format is None:
        raise ValueError(
            f"Unsupported output format: {output_path.suffix}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as image:
        if output_format == "JPEG" and image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGB")

        image.save(output_path, format=output_format)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an image from one format to another."
    )

    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)

    args = parser.parse_args()

    try:
        convert_image(args.input, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
