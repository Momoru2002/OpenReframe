from PIL import Image


def portrait_to_landscape(image: Image.Image):
    target_ratio = 16 / 9

    width = image.width
    height = image.height

    new_width = int(height * target_ratio)

    if new_width <= width:
        return image

    canvas = Image.new(
        "RGB",
        (new_width, height),
        (0, 0, 0)
    )

    offset_x = (new_width - width) // 2

    canvas.paste(
        image,
        (offset_x, 0)
    )

    return canvas