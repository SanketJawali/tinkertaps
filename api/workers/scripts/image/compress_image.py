import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image

try:
    from .format_convertor import SUPPORTED_FORMATS
except ImportError:
    from format_convertor import SUPPORTED_FORMATS


def _save_bytes(image: Image.Image, output_format: str, quality: int) -> bytes:
    buffer = BytesIO()
    save_options = {"format": output_format, "optimize": True}
    if output_format in ("JPEG", "WEBP"):
        save_options["quality"] = quality
    image.save(buffer, **save_options)
    return buffer.getvalue()


def compress_image(
    input_path: Path,
    output_path: Path,
    target_size: int,
) -> None:
    if target_size <= 0:
        raise ValueError("target_size must be greater than zero")

    output_format = SUPPORTED_FORMATS.get(output_path.suffix.lower())
    if output_format is None:
        raise ValueError(f"Unsupported output format: {output_path.suffix}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as source_image:
        image = source_image.copy()
        if output_format == "JPEG":
            if image.mode != "RGB":
                rgba_image = image.convert("RGBA")
                background = Image.new("RGB", image.size, "white")
                background.paste(rgba_image, mask=rgba_image.getchannel("A"))
                image = background
        elif output_format == "PNG" and image.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            image = image.convert("RGBA")

        if output_format == "PNG":
            data = _save_bytes(image, output_format, 0)
            if len(data) > target_size:
                data = _save_bytes(image.quantize(colors=256), output_format, 0)
        else:
            low, high = 10, 95
            data = _save_bytes(image, output_format, low)
            while low <= high:
                quality = (low + high) // 2
                candidate = _save_bytes(image, output_format, quality)
                if len(candidate) <= target_size:
                    data = candidate
                    low = quality + 1
                else:
                    high = quality - 1

        if len(data) > target_size:
            raise ValueError(
                f"Could not compress image below {target_size} bytes; "
                f"smallest output is {len(data)} bytes"
            )

        output_path.write_bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compress an image to a target size.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("target_size", type=int, help="Maximum output size in bytes")
    args = parser.parse_args()
    try:
        compress_image(args.input, args.output, args.target_size)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
