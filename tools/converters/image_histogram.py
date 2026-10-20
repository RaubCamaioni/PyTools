# image, histogram, exposure, brightness, analysis

from pathlib import Path
from PIL import Image, ImageDraw, ImageOps, ImageStat
import pillow_heif

pillow_heif.register_heif_opener()


def image_histogram(image: Path) -> dict:
    """Draw the RGB and luminance histogram of a photo and report exposure statistics:
    mean brightness, contrast, clipped shadows and highlights, and whether it looks
    under- or over-exposed.
    """
    with Image.open(image) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")
    img.thumbnail((1200, 1200))
    gray = ImageOps.grayscale(img)
    hist = img.histogram()
    lum = gray.histogram()
    total = img.width * img.height
    width, height = 512, 220
    chart = Image.new("RGB", (width, height + 20), "white")
    draw = ImageDraw.Draw(chart)
    peak = max(max(hist), 1)
    for channel, color in ((0, (220, 40, 40)), (1, (40, 170, 60)), (2, (40, 80, 220))):
        values = hist[channel * 256 : (channel + 1) * 256]
        for x, v in enumerate(values):
            bar = int(v / peak * height)
            draw.line((x * 2, height - bar, x * 2, height), fill=color)
    for x, v in enumerate(lum):
        bar = int(v / max(max(lum), 1) * height)
        draw.point((x * 2 + 1, height - bar), fill="black")
    draw.text((4, height + 2), "0 shadows", fill="black")
    draw.text((width - 90, height + 2), "highlights 255", fill="black")
    out = image.with_name(f"{image.stem}_histogram.png")
    chart.save(out)
    stat = ImageStat.Stat(gray)
    mean, stddev = stat.mean[0], stat.stddev[0]
    shadows = sum(lum[:8]) / total * 100
    highlights = sum(lum[248:]) / total * 100
    verdict = "looks under-exposed" if mean < 70 else "looks over-exposed" if mean > 190 else "exposure looks balanced"
    if shadows > 5:
        verdict += "; shadows are clipped"
    if highlights > 5:
        verdict += "; highlights are blown out"
    return {
        "file": out,
        "mean_brightness_0_255": round(mean, 1),
        "contrast_stddev": round(stddev, 1),
        "clipped_shadows_percent": round(shadows, 2),
        "clipped_highlights_percent": round(highlights, 2),
        "channel_means_rgb": [round(m, 1) for m in ImageStat.Stat(img).mean],
        "verdict": verdict,
    }
