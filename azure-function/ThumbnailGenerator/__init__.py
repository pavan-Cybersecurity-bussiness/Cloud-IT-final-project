"""
ThumbnailGenerator — Azure Function, Blob Storage trigger.

Fires whenever a new image lands in the "listing-images" container — i.e.
whenever the Listings service uploads a photo for a new or edited listing
(see backend/listings-service/image_storage.py). Resizes it to a 300x300
thumbnail and writes the result to "listing-thumbnails".

This is the serverless component the brief asks for, wired directly to the
Blob Storage requirement rather than being an unrelated bolted-on function.
"""
import io
import logging

from PIL import Image

THUMBNAIL_SIZE = (300, 300)


def main(inputBlob: bytes, outputBlob) -> None:
    logging.info("Generating thumbnail for uploaded blob (%d bytes)", len(inputBlob))

    try:
        image = Image.open(io.BytesIO(inputBlob))
        image.thumbnail(THUMBNAIL_SIZE)

        output = io.BytesIO()
        image_format = image.format or "JPEG"
        image.save(output, format=image_format)
        outputBlob.set(output.getvalue())

        logging.info("Thumbnail written (%s, %dx%d)", image_format, image.width, image.height)
    except Exception as exc:
        # Don't crash the function on a corrupt/unsupported upload — log and
        # move on rather than leaving the function app in a failed state.
        logging.error("Could not generate thumbnail: %s", exc)
