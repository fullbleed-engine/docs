"""PNG encoding changes are acceptable; changed pixels, geometry or modes are not."""
import io
from pathlib import Path
import struct
import unittest

from PIL import Image, UnidentifiedImageError
from PIL.PngImagePlugin import PngInfo
from verify_component_kits import compare_png_pixels

BASELINE = Path(__file__).resolve().parents[1] / "docs/assets/component-kits/default-1.png"


def encode(image, **options):
    out = io.BytesIO()
    image.save(out, format="PNG", **options)
    return out.getvalue()


class PngGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = BASELINE.read_bytes()

    def test_different_compression_preserves_every_pixel(self):
        with Image.open(io.BytesIO(self.original)) as image:
            encoded = encode(image, compress_level=0)
        self.assertNotEqual(encoded, self.original)
        result = compare_png_pixels(encoded, self.original)
        self.assertFalse(result["encoding_equal"])
        self.assertEqual(result["mode"], "RGB")

    def test_one_changed_channel_in_one_pixel_fails(self):
        with Image.open(io.BytesIO(self.original)) as image:
            changed = image.copy()
        red, green, blue = changed.getpixel((0, 0))
        changed.putpixel((0, 0), (red ^ 1, green, blue))
        with self.assertRaisesRegex(AssertionError, "PNG pixels differ"):
            compare_png_pixels(encode(changed), self.original)

    def test_changed_dimensions_fail(self):
        with Image.open(io.BytesIO(self.original)) as image:
            changed = image.crop((0, 0, image.width - 1, image.height))
        with self.assertRaises(AssertionError):
            compare_png_pixels(encode(changed), self.original)

    def test_changed_mode_fails_even_with_opaque_alpha(self):
        with Image.open(io.BytesIO(self.original)) as image:
            changed = image.convert("RGBA")
        with self.assertRaises(AssertionError):
            compare_png_pixels(encode(changed), self.original)

    def test_invalid_png_fails(self):
        with self.assertRaises(UnidentifiedImageError):
            compare_png_pixels(b"invalid image", self.original)

    def test_changed_gamma_metadata_fails(self):
        metadata = PngInfo()
        metadata.add(b"gAMA", struct.pack(">I", 45455))
        with Image.open(io.BytesIO(self.original)) as image:
            changed = encode(image, pnginfo=metadata)
        with self.assertRaisesRegex(AssertionError, "PNG metadata differs"):
            compare_png_pixels(changed, self.original)

    def test_another_image_format_fails(self):
        stream = io.BytesIO()
        with Image.open(io.BytesIO(self.original)) as image:
            image.save(stream, format="TIFF")
        with self.assertRaises(AssertionError):
            compare_png_pixels(stream.getvalue(), self.original)


if __name__ == "__main__":
    unittest.main()
