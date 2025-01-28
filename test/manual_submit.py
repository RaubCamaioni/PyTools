import requests
from pathlib import Path

# url = "http://127.0.0.1:8080/tool/3"
# data = {
#     "mounts": "[[10,10],[10,10]]",
#     "angle": "60",
#     "screw_size": "2.4",
#     "edge_padding": "5",
#     "padding": "10",
#     "thickness": "3",
# }
# response = requests.post(url, data=data)

url = "http://127.0.0.1:8080/tool/1"
data = {"hash": "sha256"}
file_path = str(Path("test_file.txt").absolute())
with open(file_path, "r") as file:
    files = {"file": file}
    response = requests.post(url, data=data, files=files)


if response.status_code == 200:
    print(response.json())
else:
    print(f"Error submitting form: {response.status_code}")
