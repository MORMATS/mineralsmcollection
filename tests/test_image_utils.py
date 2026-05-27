from io import BytesIO

from PIL import Image

from src import image_utils


class FakeUpload:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getbuffer(self):
        return memoryview(self._data)


def make_image_bytes(fmt: str = "JPEG", size: tuple[int, int] = (20, 20)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color="white").save(buffer, format=fmt)
    return buffer.getvalue()


def test_save_uploaded_images_validates_and_converts_to_webp(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(image_utils, "UPLOAD_DIR", upload_dir)

    paths = image_utils.save_uploaded_images(
        "MIN-0001",
        [FakeUpload("specimen.jpg", make_image_bytes())],
    )

    assert len(paths) == 1
    assert paths[0].endswith(".webp")
    saved_path = upload_dir.parent / paths[0]
    with Image.open(saved_path) as saved:
        assert saved.format == "WEBP"
        assert saved.width <= image_utils.THUMBNAIL_SIZE[0]
        assert saved.height <= image_utils.THUMBNAIL_SIZE[1]


def test_save_uploaded_images_rejects_corrupt_file(monkeypatch, tmp_path):
    monkeypatch.setattr(image_utils, "UPLOAD_DIR", tmp_path / "uploads")

    try:
        image_utils.save_uploaded_images("MIN-0001", [FakeUpload("not-image.jpg", b"bad")])
    except image_utils.ImageUploadError as exc:
        assert "no es una imagen valida" in str(exc)
    else:
        raise AssertionError("Expected corrupt file to be rejected")


def test_delete_uploaded_images_rejects_paths_outside_upload_root(monkeypatch, tmp_path):
    monkeypatch.setattr(image_utils, "UPLOAD_DIR", tmp_path / "uploads")
    outside_file = tmp_path / "outside.webp"
    outside_file.write_bytes(b"fake image")

    deleted_count, failures = image_utils.delete_uploaded_images([str(outside_file)])

    assert deleted_count == 0
    assert failures
    assert outside_file.exists()
