from PIL import Image

from src.ui import image_height_ratio, max_image_height_ratio, shared_image_frame_ratio


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


def test_shared_image_frame_ratio_uses_middle_size_instead_of_outlier(tmp_path):
    normal_a = tmp_path / "normal-a.webp"
    normal_b = tmp_path / "normal-b.webp"
    very_tall = tmp_path / "very-tall.webp"
    Image.new("RGB", (100, 100), color="white").save(normal_a)
    Image.new("RGB", (120, 120), color="white").save(normal_b)
    Image.new("RGB", (50, 200), color="white").save(very_tall)

    assert shared_image_frame_ratio([normal_a, normal_b, very_tall]) == 1.0


def test_shared_image_frame_ratio_clamps_extreme_single_images(tmp_path):
    very_wide = tmp_path / "very-wide.webp"
    very_tall = tmp_path / "very-tall.webp"
    Image.new("RGB", (400, 100), color="white").save(very_wide)
    Image.new("RGB", (100, 400), color="white").save(very_tall)

    assert shared_image_frame_ratio([very_wide]) == 0.75
    assert shared_image_frame_ratio([very_tall]) == 1.35
