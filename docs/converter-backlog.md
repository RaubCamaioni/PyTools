# Converter tool backlog

Date: 2026-10-20. Companion to `tools/converters/` (103 tools live on pywebtools.com as of
this date). This file lists the converter tools that popular sites offer and we have **not**
built, with what each one does and what it would take.

## How the list was made

Census of the tool catalogues on Convertio, CloudConvert, Zamzar, Online-Convert, AConvert,
FreeConvert, iLovePDF, iLoveIMG, Smallpdf, PDF24, TinyWow, ezgif, 10015.io, Browserling,
IT-Tools, CodeBeautify, RapidTables, unitconverters.net and epochconverter.com, then ranked
with Google Trends (US, 12 months, "pdf to word" = 100 as the anchor):

| search term | relative interest | status |
|---|---|---|
| youtube to mp3 | 191 | impossible (no network, legal) |
| remove background | 126 | backlog, tier 3 |
| pdf to word | 100 | **live** |
| word to pdf | 100 | **live** (approximation, see tier 3) |
| image to text (OCR) | 56 | backlog, tier 2 |
| jpg to pdf | 52 | live |
| mp4 to mp3 | 33 | live |
| pdf to excel | 32 | **live** |
| heic to jpg | 30 | live |
| video to gif | 27 | live |
| compress pdf | 18 | live |
| png to jpg, webp to png | 13-15 | live |
| epub to pdf, mp3 to wav, svg to png, docx to pdf | 6-11 | live except svg to png (tier 2) |
| unit converter | 6 | live |
| stl to obj, xml to json, ttf to woff | 0-2 | xml to json live; rest backlog |

Paid data would sharpen this: one month of Ahrefs/Semrush "top pages" for the sites above
gives per-tool traffic; Google Keyword Planner (free with an Ads account) gives volumes.

## Built since this list was written

Batches three and four turned most of the tier-1 rows below into live tools (the site now
has 245 converters). Rows that mention one of these are done; the notes are kept for the
reasoning behind each one.

- **PDF**: pdf_crop, pdf_n_up, pdf_rasterize, pdf_repair, pdf_reorder, pdf_redact,
  pdf_compare, comic_archive_converter (cbz ↔ pdf), pdf_page_size (resize, blank pages,
  pad to even), pdf_form_fields (list, fill, flatten), pdf_bookmarks (export, import,
  generate from headings, remove)
- **Office**: markdown_to_pptx, html_to_docx, rtf_to_text, eml_to_text,
  contacts_calendar_to_csv, csv_to_contacts_calendar, opendocument_to_text, csv_split,
  excel_merge, excel_to_html (+xml), docx_merge, docx_find_replace, document_word_counter,
  document_metadata (read/strip), csv_merge
- **Image**: image_caption, image_frame, image_filters, image_pixelate_region,
  image_collage, image_split, image_palette, image_compare, image_upscale,
  image_bulk_resize, image_histogram, color_blindness_simulator, color_palette_generator,
  gradient_generator, qr_code_styled, qr_code_with_logo, barcode_generator,
  favicon_generator, blur_faces
- **GIF, video, audio**: gif_add_text, gif_editor, gif_from_images, video_rotate_flip,
  video_speed (incl. reverse), video_mute, video_merge, video_to_webp, video_trim,
  audio_adjust, audio_merge, audio_trim, audio_visualizer, tone_generator, audio_tags,
  audio_silence_trim, audio_compress, media_info
- **Fonts, 3D**: font_converter, mesh_converter
- **Data and developer**: csv_sql_query, csv_tools, json_diff, json_query,
  json_schema_validator, json_to_types, json_flatten, json_merge, xml_formatter,
  sql_formatter, web_code_formatter, python_formatter, html_minifier, svg_optimizer,
  cron_explainer, chmod_calculator, docker_run_to_compose, hmac_generator,
  password_hasher, totp_generator, ssh_key_generator, certificate_decoder,
  file_encryptor, jwt_generator, password_strength, passphrase_generator,
  encoding_converter, nato_alphabet, ascii_banner, list_operations, text_extractor,
  text_cleanup, text_wrap, find_replace, text_transform, readability_score, hex_dump,
  line_tools, timestamp_decoder, calendar_generator, sun_moon_calculator,
  number_validator, phone_number_parser, user_agent_parser, web_reference_lookup,
  random_data_generator, random_picker, math_evaluator, percent_calculator,
  tip_split_calculator, loan_calculator, compound_interest_calculator,
  electrical_calculator, force_torque_converter, frequency_converter,
  data_rate_converter, random_number_generator, id_generator, cidr_tools,
  mac_address_formatter, email_normalizer, dotenv_json_converter, markdown_toc,
  html_table_converter, bbcode_to_html, file_type_detector

Still open from tier 1: pptx rendering (needs LibreOffice), MOBI output, pdf metadata
stripping, code_to_image, font_info, mesh_info, dxf_to_svg, svg_to_dxf, gcode_preview,
step_to_stl, meta-tag generators. Tiers 2 and 3 are unchanged.

## Site constraint: upload → output only

The site deliberately stays a simple form: upload a file / type values, get a result. Tools
marked **interactive** below need a canvas, a live preview, drag and drop, drawing, or a
multi-step flow, and are out of scope until the page model changes. Everything else fits the
current model and can be added as a single `.py` file.

## Tier 1 — fits the current model, pip packages only

### PDF
| tool | what it does | notes |
|---|---|---|
| pdf_crop | trim margins / crop every page to a box | pymupdf `set_cropbox`; needs numbers, not a visual crop |
| pdf_pages_per_sheet | N-up: 2/4/6 pages per sheet, booklet imposition | pymupdf `show_pdf_page` |
| pdf_grayscale | convert a colour PDF to black and white | rasterise pages or recolour via pymupdf |
| pdf_flatten | rasterise pages so forms/annotations become fixed content | pymupdf |
| pdf_repair | re-save a damaged PDF, rebuild xref | pymupdf open + save with `garbage=4` |
| pdf_strip_metadata | remove author/title/producer/XMP | pymupdf `set_metadata({})`, `del_xml_metadata` |
| pdf_reorder_pages | new page order from a list like 3,1,2 | pymupdf `select` |
| pdf_redact_text | black out every occurrence of a search term | pymupdf `add_redact_annot` + `apply_redactions`; visual redaction is **interactive** |
| pdf_compare | diff text of two PDFs (unified diff / side by side) | difflib on `get_text` |
| pdf_to_cbz / cbz_to_pdf | comic archives | pymupdf + zipfile |
| pdf_page_size | resize pages to A4/Letter, scale content | pymupdf |
| pdf_form_fields_to_json | dump form field names/values; fill from JSON | pymupdf widgets; visual filling is **interactive** |
| pdf_add_blank_pages / pdf_duplicate_pages | layout helpers | pymupdf |
| pdf_bookmarks | export TOC to text, import from text | pymupdf `get_toc`/`set_toc` |

### Office and documents
| tool | what it does | notes |
|---|---|---|
| markdown_to_pptx | headings → slides, bullets → body | python-pptx |
| pptx_to_pdf / pptx_to_images | render slides | needs LibreOffice (tier 3); python-pptx cannot render |
| html_to_docx | HTML page → Word | html2text → existing text_to_docx, or `htmldocx` |
| rtf_to_text | Rich Text → plain text/Markdown | `striprtf` (tiny) |
| eml_to_pdf / eml_to_text, msg_to_text | email files → readable document | stdlib `email`; `.msg` needs `extract-msg` |
| ics_to_csv, vcf_to_csv | calendar / contacts to spreadsheet | stdlib parsing or `icalendar`, `vobject` |
| odt_ods_odp_to_* | OpenDocument conversions | `odfpy`; fidelity limited without LibreOffice |
| excel_split / csv_split | split a big sheet into N files or by column value | openpyxl / csv |
| excel_merge | combine several workbooks/CSVs | openpyxl |
| excel_to_html / excel_to_xml / xml_to_excel | table format shuffles | openpyxl + stdlib |
| docx_merge, docx_to_text_batch | combine Word files | python-docx (page breaks only) |
| mobi/azw3 output | EPUB → MOBI/AZW3 | needs `kindlegen`/calibre, not available; EPUB → PDF/TXT is live |

### Image
| tool | what it does | notes |
|---|---|---|
| image_add_text / meme_generator | caption with top/bottom text | Pillow; font must be in the image (`fonts-dejavu-core`); placement by numbers, visual placement is **interactive** |
| image_border, image_rounded_corners, image_circle_crop | framing effects | Pillow |
| image_filters | sepia, invert, grayscale, posterize, blur, sharpen, vintage | Pillow ImageOps/ImageFilter |
| image_pixelate_region / blur_region | blur a rectangle given by numbers | Pillow; visual selection is **interactive** |
| image_collage / image_combine | grid or side-by-side from a zip | Pillow |
| image_split | cut into N×M tiles (zip) | Pillow |
| image_color_palette / image_average_color | dominant colours, hex list | Pillow quantize |
| image_compare / image_diff | highlight differences between two images | Pillow ImageChops |
| image_upscale | 2×/4× Lanczos (not AI) | Pillow; AI upscalers are tier 3 |
| heic_to_jpg (dedicated) | thin wrapper over image_format_converter for discoverability | tags already cover "heic" |
| svg_to_png / svg_to_pdf | rasterise SVG | tier 2 (cairo) |
| png_to_svg | vectorise bitmap | tier 2 (potrace) |
| barcode_generator | EAN/UPC/Code128 PNG/SVG | `python-barcode` |
| code_to_image | syntax-highlighted screenshot of a snippet | `pygments` + Pillow |
| ico_to_png, cur/ani tools | icon formats | Pillow reads ICO |
| avif support | AVIF in/out | Pillow ≥11.2 wheels include libavif; verify in the image |
| image_to_text (OCR) | tier 2 | tesseract |
| remove_background, upscale_ai, colorize, restore, unblur, object removal | tier 3 / not feasible in 30 s CPU | models |
| photo editor, crop by drag, draw, annotate, photo censor brush, collage builder | **interactive** | — |

### GIF and video (ezgif catalogue)
| tool | what it does | notes |
|---|---|---|
| gif_add_text | caption a GIF | Pillow, font needed |
| gif_crop | crop by numbers | Pillow |
| gif_make_from_images | zip of images → GIF with delay | Pillow |
| video_rotate / video_flip / video_mirror | orientation | PyAV + Pillow (slow) or `vf` filters via PyAV graph |
| video_speed | 0.25× to 4× | PyAV, drop/duplicate frames + audio resample |
| video_reverse | play backwards | decode all frames, re-encode; cap length |
| video_mute / video_extract_audio | audio track on/off | PyAV (extract exists as video_to_audio) |
| video_merge | concatenate two clips | PyAV re-encode |
| video_to_webp / video_to_apng | animated image output | PyAV + Pillow |
| video_resize / video_crop | geometry | PyAV reformat, crop by numbers |
| video_thumbnail_grid | contact sheet (exists in video_to_frames) | — |
| video_volume / audio_volume, audio_fade, audio_normalize, audio_speed | audio processing | PyAV + numpy |
| audio_merge / audio_mix | join or overlay tracks | PyAV + numpy |
| audio_waveform_image, audio_spectrogram | visualisations | numpy + Pillow / scipy |
| tone_generator, white_noise | synthesise WAV | numpy |
| mp3_tag_editor | read/write ID3/Vorbis tags, cover art | `mutagen` |
| audio_silence_trim, stereo_to_mono, resample | utilities | PyAV + numpy |
| video cutter with timeline, trimming by preview, screen/webcam recorder | **interactive** | — |
| speech_to_text, text_to_speech, youtube/tiktok download | tier 3 / impossible | — |

### Fonts, 3D and CAD (fits the site's existing CadQuery niche)
| tool | what it does | notes |
|---|---|---|
| font_converter | TTF ↔ OTF ↔ WOFF ↔ WOFF2 | `fonttools` + `brotli` |
| font_info / font_glyph_preview | metadata, sample sheet PNG | fonttools + Pillow |
| mesh_converter | STL ↔ OBJ ↔ PLY ↔ GLB ↔ 3MF, binary/ASCII STL | `trimesh` |
| mesh_info | volume, surface, bounds, watertight check | trimesh |
| step_to_stl / step_to_obj | CAD exchange | CadQuery (already in image) |
| dxf_to_svg / dxf_to_pdf / dxf_to_png | 2-D drawings | ezdxf drawing add-on (`svg` backend, no matplotlib) |
| svg_to_dxf | paths → DXF | `svgelements` + ezdxf |
| gcode_preview | plot toolpaths | numpy + Pillow |
| dwg input | DWG → anything | needs ODA converter, not available |

### Data and developer utilities (low search volume each, cheap to add)
| tool | what it does | notes |
|---|---|---|
| csv_sql_query | run SQL against a CSV | stdlib sqlite3 |
| csv_tools | transpose, select/reorder columns, change delimiter, add/remove header | csv |
| json_diff, json_path_query, json_schema_validate, json_to_types (TS/Python/pydantic) | JSON utilities | `jsonschema`, `jmespath` |
| json_to_sql_inserts, csv_to_sql | data loading helpers | stdlib |
| xml_formatter / xml_validate, yaml_lint | markup checks | stdlib, PyYAML |
| sql_formatter, js_beautify, python_formatter, html/css/js minify | code formatting | `sqlparse`, `jsbeautifier`, `black`, `rcssmin`/`rjsmin`/`minify-html` |
| cron_explainer / crontab_generator | human text for cron | `cron-descriptor` |
| chmod_calculator, docker_run_to_compose, htpasswd_generator | ops helpers | pure python |
| hmac_generator, bcrypt_argon2_hash, totp_generator, rsa_ssh_keygen, x509_decoder, csr_decoder, file_encrypt (AES, password) | crypto utilities | stdlib hmac, `bcrypt`, `argon2-cffi`, `pyotp`, `cryptography` |
| password_strength | zxcvbn score | `zxcvbn` |
| base32/base58/ascii85/punycode/uuencode | more encodings | stdlib + `base58` |
| nato_alphabet, ascii_banner, list_set_operations, text_extractors (emails/urls/numbers), remove_accents, text_wrap_justify, find_replace_bulk | text utilities | stdlib, `pyfiglet` |
| timestamp_family | LDAP, .NET ticks, Snowflake, ObjectId, Firebase, GPS, Julian day, ISO duration | extend epoch_converter |
| calendar_generator, sunrise_sunset, moon_phase, week_number | date helpers | stdlib, `astral` |
| iban_validator, credit_card_check, isbn_ean_validator, phone_parser, vat_check | validators | `python-stdnum`, `phonenumbers` |
| user_agent_parser, mime_lookup, http_status_lookup, mac_vendor_lookup | lookups | `ua-parser`, stdlib, offline OUI table |
| random_data_generator | fake names/JSON/CSV rows | `faker` |
| math_evaluator, percentage_calculator, roman/base (live), bcd/gray_code, binary_ops | number tools | `ast`-based safe eval |
| color_shades, color_mixer, palette_generator, gradient_css | colour helpers (text out) | colorsys |
| markdown_table_generator, csv_to_html_table, html_table_to_csv | table helpers | stdlib html.parser |
| regex_tester (live), regex_cheatsheet, string_obfuscator, numeronym | text/dev | — |
| meta_tags_generator, og_preview, sitemap/robots helpers | web text generators | pure text; URL fetching is impossible (no network) |

## Tier 2 — needs a system package in `containers/Containerfile.sandbox`

| tool | package | demand |
|---|---|---|
| image_to_text (OCR), pdf_ocr (make scans searchable), scan_to_text | `tesseract-ocr` + `tesseract-ocr-eng` (~30 MB); pymupdf has built-in tesseract support, or `pytesseract` | high (56) |
| svg_to_png / svg_to_pdf | `libcairo2` + `cairosvg` | medium (7) |
| png_to_svg (vectorise) | `potrace` | medium ("png to svg" is on ezgif's popular list) |
| rar_extract / rar_to_zip | `unrar-free` + `rarfile` | medium |
| text on images with a real font (meme, gif captions, watermark quality) | `fonts-dejavu-core` | enables several tier-1 tools |
| webp/avif animated output quality | `libwebp` already in Pillow wheels; AVIF needs Pillow ≥ 11.2 | low |

## Tier 3 — heavy; prototype on the server for the 30 s / 0.5 CPU / 1 GB limits first

| tool | approach | risk |
|---|---|---|
| remove_background | `rembg` with the small `u2netp` model (5 MB) + `onnxruntime` (~50 MB) | likely 5-20 s per image; interest 126, the single biggest gap |
| word_to_pdf / pptx_to_pdf / excel_to_pdf with real fidelity | LibreOffice headless in the sandbox image (~400 MB) | 5-10 s per file; current approximations are live |
| pdf_to_word for scanned PDFs | OCR (tier 2) then pdf2docx | — |
| speech_to_text | `faster-whisper` tiny model | probably exceeds 30 s at 0.5 CPU |
| image_upscale_ai, colorize, restore, unblur, object/text removal | Real-ESRGAN / diffusion models | not feasible under the current limits |
| text_to_speech | `piper` voices (~60 MB) | borderline; worth a try |
| image_caption / ocr for handwriting | vision models | not feasible |

## Not possible on this site

- Anything that downloads from a URL: YouTube/TikTok/Instagram/Facebook/Twitter downloaders,
  website to PDF/screenshot, "save webpage", currency rates, DNS/IP geolocation lookups. The
  sandbox has no network by design.
- AI writing/rewriting tools, chat with PDF, translation, summarisers (no model, no network).
- Device/console presets (Online-Convert's "convert for iPhone/Xbox") — marketing wrappers.
- Live tools: screen recorder, webcam, microphone test, online notepad, timers (browser-side).

## Interactive tools (out of scope while the page is upload → output)

PDF editor, annotate, draw/sign, fill forms visually, rearrange pages by drag, visual redact,
compare side by side viewer; photo editor, crop by drag, draw on image, collage builder, meme
text placement, censor brush; video timeline editor, trim with preview, multi-track mixer;
colour picker from image, chart maker, QR scanner from webcam. A later page design with a
preview step could unlock these; each would still be a plain Python entrypoint underneath.
