#!/venv/bin/python3

'''
File for testing read from GCS. Make sure to pip install requirements before running.
Recommended to be run in a venv.
Requires valid GCS credentials.
'''

from GoogleStorageClient import GoogleStorageClient
from PIL import Image
from io import BytesIO
import os

# set key credentials file path
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r'comp6453-credentials.json'

storageClient = GoogleStorageClient()
# Retrieves file as a stream of bytes
file = storageClient.read("spongebob.jpeg", False)


# Testing that image opens
try:
  img = Image.open(BytesIO(file))
  img.show()
except Exception:
  print("Error Displaying")