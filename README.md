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
**lower_case_text.py**
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


## Demo Website

The application is hosted at https://pywebtools.com.  
Currently hosted under Linode server, lowest resources.  
Heavy load scripts will take longer to return.  
Website responsiveness will be impacted by multiple clients.  

## Roadmap

Usability:
- error message return as toast

User Page:  
- update user attributes  
- update tool attributes  

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
