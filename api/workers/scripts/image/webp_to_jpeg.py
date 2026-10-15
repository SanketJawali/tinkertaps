import argparse
from pathlib import Path

try:
    from .format_convertor import convert_image
except ImportError:
    from format_convertor import convert_image


def webp_to_jpeg(input_path: Path, output_path: Path) -> None:
    convert_image(input_path, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a WebP image to JPEG.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        webp_to_jpeg(args.input, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()