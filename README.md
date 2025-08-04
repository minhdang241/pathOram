# How to run
Make sure that you clean up 2 files `stash.json` and `name2blockid.json`. Also, cleanup 2 folders `protected_images` and `unprotected_images` if there are files existing. Then executing the following command to run the application:

## Running the application
```python3
python3 app.py
```
## Running the simulation
```python3
python3 simulation.py
```

**Note:** you should install all the required packages listed in the `requirements.txt` file.

# Project Description
A web application that allows users to store and view photos, but with a backend that uses Path ORAM to ensure the storage provider (Google Cloud Storage) cannot learn which photos are being accessed (access pattern privacy). The system will visually demonstrate this privacy by contrasting it with a naive, unprotected approach.

The system has three main components:
- **Frontend**: enable user interacts with the system
- **Backend**: runs the PathORAM logic, communicates with the GCS.
- **Storage**: GCS

# Demonstration

Providing 2 views:
- **Unprotected view**: user clicks a photo, the server log shows a single, revealing request: `GET /unprotected-bucket/my_trip.jpg`. The access pattern is leaked.
- **Protected view**: user clicks the same photo. The server logs shows a bunch of meaningless objects (e.g., GET /oram-bucket/5, PUT /oram-bucket/29, ...), revealing nothing about the photo itself. This shows that the access pattern has been hidden.
