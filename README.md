## PyTools
PyTools is a web hosting platform for python scripts.  
The entrypoint arguments and return values are automatically  
converter to a web compatable format.   

## Uploading Scripts
Only individual python files (.py) are currently supported.  
The entrypoint function must be the same name as the uploaded file.  

To upload a script, log into the webpage by clicking login (top right).  
Then go to profile (top right), click upload code, browse to file and upload.  

All entrypoint arguments are converted to equivalent web form values.  
The currently supported arguments are: str, int, float, literal, Path   
Unsupported types can be represented as strings and parsed inside the entrypoint function.  

Path arguments are converted to file upload form items.  
Path returns are converted to file download links.  

## Script Tags
Add tags to the top of the script.  
Filter by tags using the homepage search bar.  

## Example Script
``` python
# text, converter

from pathlib import Path

def lower_case_text(input: Path) -> Path:
  output = Path("output.txt")  
  
  with open(input, 'r') as f:
    text = f.read()

  with open(output, 'w') as f:
    f.write(text.lower())
  
  return output
```

## Converter Tools
`tools/converters/` holds the converter scripts published on the site (text and
encoding, data formats, units, colour/time/network, image, PDF, Office documents,
media, subtitles, archives). They follow the rules above; a few extra constraints
that the upload parser enforces are worth knowing when writing new ones:

- form inputs are single-line, so multi-line content is taken as a `Path` upload
- `Literal` option values may only contain letters, digits, `_` and `.` (no hyphens),
  and the function receives them as strings
- numeric arguments should carry a default, the form submits every field
- tags on line 1 are plain alphanumeric words
- every line must be 120 characters or shorter (the upload is rejected otherwise); `black -l 120` gets there

The sandbox image (`sandbox/pyproject.toml`) provides numpy, scipy, pandas,
opencv (headless, 4.x), av, pymupdf (+pymupdf4llm), cadquery, ezdxf, Pillow (+HEIF),
PyYAML, qrcode, openpyxl, python-docx, python-pptx, pdf2docx, mammoth, ebooklib, rawpy,
markdown, tzdata, num2words, xmltodict, tomli-w, py7zr, cryptography, bcrypt,
cron-descriptor, croniter, jmespath, jsonschema, sqlparse, jsbeautifier, cssbeautifier,
rcssmin, rjsmin, black, python-stdnum, phonenumbers, faker, python-barcode, mutagen,
fonttools, brotli, trimesh (+networkx), striprtf, pyzipper, pyfiglet, zxcvbn, astral,
ua-parser and scour.

Docstrings and comments are wrapped at 88 columns so the code view reads comfortably;
only code lines go out to 120.

Converter ideas that are not built yet, and why, are kept in
`docs/converter-backlog.md`.

## Demo Website
The application is hosted at https://pywebtools.com.  
Currently hosted under Linode server, lowest resources.  
Heavy load scripts will take longer to return.  
Website responsiveness will be impacted by multiple clients.  

## Building Instructions
Required Secrets:
``` bash
GOOGLE_CLIENT_ID=<google_client_id_url>
GOOGLE_CLIENT_SECRET=<google_client_secret>
GOOGLE_REDIRECT_URI=<redirect_fastapi_auth_endpoint>
SESSION_SECRET=<session_secret>
ROOT_PATH=localhost
DATABASE=/data/database.db
SANDBOX=/venvs/sandbox/
```

## Dvelopment

## Roadmap
Usability:  
- error message return as toast  

User Page:  
- update user attributes  
- update tool attributes  
- allow image upload with code (hard to make safe), generate image from stl?  

Tool Page:  
- up vote / down vote  
- report  
- GPT malicious code check (infinite while loops, ect)  
- split donation button (dontation split between web hoster and tool writer)  
- Remix of query parameters for specific tasks

Admin Page:  
- banning users  
- tool statistics  

CadQuery:  
- embedded VTK model renderer  
- show model in index.html  

Index Page:  
- improve search/index capabilites  
- organize by up/down vote  
- show votes on item  
- add catagories button to index page

## Debugging Nested Cgroups
Keywords delegation slice, cgroup, systemd  
```bash
# enable delegation for users
# /etc/systemd/system/user@.service.d/delegate.conf 
[Service]
Delegate=cpu cpuset io memory pids
```

Check for cgroup.subtree_control permissions.  
This shows the specific user permissions.  
Ensure permissions are allowed through the tree.  
Check if podman nesting works in root vs non-root.
```bash
cat /sys/fs/cgroup/user.slice/user-1000.slice/cgroup.subtree_control
```

## Setup Tailwind
Download latest binary from: https://github.com/tailwindlabs/tailwindcss/releases  
``` bash
wget https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.17/tailwindcss-linux-x64
chmod +x tailwindcss-linux-x64
sudo mv tailwindcss-linux-x64 /usr/local/bin/tailwindcss
tailwindcss --output ./server/src/app/static/styles.css --watch
```

## Rootless Podman in Podman
``` bash
https://www.redhat.com/en/blog/podman-inside-container
podman run --security-opt label=disable --user podman --device /dev/fuse quay.io/podman/stable podman run alpine echo hello
```

## Front End Development
The front end can be developed without having a functional isolate binary.  
The backend is fastapi.  
The frontend is htmx and hyperscript.  