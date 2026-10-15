from pathlib import Path

from PIL import Image

from workers.scripts.image.compress_image import compress_image


def test_compress_image_downscales_when_quality_is_not_enough(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.png"
    output_path = tmp_path / "output.jpg"

    image = Image.new("RGB", (1600, 1200), (120, 80, 40))
    image.save(input_path, format="PNG")

    compress_image(input_path, output_path, target_size=10_000)

    assert output_path.stat().st_size <= 10_000
    with Image.open(output_path) as output:
        assert output.size < image.size