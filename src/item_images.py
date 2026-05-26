from __future__ import annotations

from src.models import CollectionItem, ItemImage


def image_sort_key(image: ItemImage) -> tuple[int, int]:
    fallback = image.id or 0
    return (image.sort_order if image.sort_order is not None else fallback, fallback)


def ordered_images(item: CollectionItem) -> list[ItemImage]:
    return sorted(item.images, key=image_sort_key)


def assign_image_order(images: list[ItemImage]) -> None:
    for index, image in enumerate(images, start=1):
        image.sort_order = index
        image.is_cover = index == 1


def normalize_image_order(item: CollectionItem) -> None:
    assign_image_order(ordered_images(item))


def move_image(item: CollectionItem, image_id: int, delta: int) -> bool:
    images = ordered_images(item)
    current = next((index for index, image in enumerate(images) if image.id == image_id), None)
    if current is None:
        return False

    target = current + delta
    if target < 0 or target >= len(images):
        return False

    images[current], images[target] = images[target], images[current]
    assign_image_order(images)
    return True
