from PIL import Image

from src.ui import image_height_ratio, max_image_height_ratio


def test_image_height_ratio_reads_image_dimensions(tmp_path):
    image_path = tmp_path / "wide.webp"
    Image.new("RGB", (40, 20), color="white").save(image_path)

    assert image_height_ratio(image_path) == 0.5


def test_max_image_height_ratio_uses_tallest_rendered_image(tmp_path):
    wide_path = tmp_path / "wide.webp"
    tall_path = tmp_path / "tall.webp"
    Image.new("RGB", (100, 50), color="white").save(wide_path)
    Image.new("RGB", (50, 100), color="white").save(tall_path)

    assert max_image_height_ratio([wide_path, tall_path]) == 2.0
