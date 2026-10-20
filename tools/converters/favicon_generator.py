# image, favicon, ico, icon, generator

from pathlib import Path
from PIL import Image, ImageOps
import pillow_heif
import zipfile

pillow_heif.register_heif_opener()

SIZES = [16, 32, 48, 64, 128, 180, 192, 512]


def favicon_generator(image: Path) -> Path:
    """Build a favicon set from any image: multi-size favicon.ico plus PNGs (16 to 512
    px, including apple-touch-icon 180 and android 192/512) and a ready-to-paste HTML
    snippet, zipped.
    """
    with Image.open(image) as img:
        img = ImageOps.exif_transpose(img).convert("RGBA")
        square = ImageOps.fit(img, (max(img.size), max(img.size)), Image.LANCZOS) if img.width != img.height else img
        out = Path("favicons.zip")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            ico = Path("favicon.ico")
            square.resize((64, 64), Image.LANCZOS).save(ico, sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
            zf.write(ico)
            html = ['<link rel="icon" href="/favicon.ico" sizes="any">']
            for size in SIZES:
                name = {
                    180: "apple-touch-icon.png",
                    192: "android-chrome-192x192.png",
                    512: "android-chrome-512x512.png",
                }.get(size, f"favicon-{size}x{size}.png")
                p = Path(name)
                square.resize((size, size), Image.LANCZOS).save(p, "PNG", optimize=True)
                zf.write(p)
                if size == 180:
                    html.append('<link rel="apple-touch-icon" href="/apple-touch-icon.png">')
                elif size in (16, 32):
                    html.append(f'<link rel="icon" type="image/png" sizes="{size}x{size}" href="/{name}">')
            zf.writestr("snippet.html", "\n".join(html) + "\n")
    return out
