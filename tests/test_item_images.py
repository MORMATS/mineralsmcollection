from types import SimpleNamespace

from src.item_images import assign_image_order, ordered_images


def test_ordered_images_falls_back_to_id_without_sort_order():
    item = SimpleNamespace(
        images=[
            SimpleNamespace(id=3),
            SimpleNamespace(id=1),
            SimpleNamespace(id=2),
        ]
    )

    assert [image.id for image in ordered_images(item)] == [1, 2, 3]


def test_assign_image_order_tolerates_images_without_sort_order():
    images = [
        SimpleNamespace(id=1, is_cover=False),
        SimpleNamespace(id=2, is_cover=True),
    ]

    assign_image_order(images)

    assert images[0].is_cover is True
    assert images[1].is_cover is False
