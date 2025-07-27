from __future__ import annotations

import base64
import time
from flask import Flask, redirect, render_template, url_for, request, flash

from photo_manager import PhotoManager

app = Flask(__name__)
photo_manager = PhotoManager(is_local=True)

protected_log_store = []
unprotected_log_store = []
protected_image_url = None
unprotected_image_url = None
protected_latency = None
unprotected_latency = None


@app.route("/")
def home():
    # Fetch logs for both protected and unprotected views
    # from your PathORAM instance to pass to the single index.html template
    image_ids = photo_manager.list_unprotected_photo_ids()
    return render_template(
        "index.html",
        unprotected_image_ids=image_ids,
        protected_logs=protected_log_store,
        unprotected_logs=unprotected_log_store,
        protected_image_url=protected_image_url,
        unprotected_image_url=unprotected_image_url,
        protected_latency=protected_latency,
        unprotected_latency=unprotected_latency,
    )


@app.route("/access/<view_type>/<path:block_id>")
def access(view_type, block_id):
    global protected_log_store, unprotected_log_store
    global protected_image_url, unprotected_image_url
    global protected_latency, unprotected_latency
    if view_type.lower() == "protected":
        # Clear previous protected logs *before* making the new access calls
        # This ensures that only the new set of calls for this access are shown.
        # oram.clear_logs("PROTECTED")

        # Simulate ORAM access with multiple internal API calls
        # The number of internal calls should be handled by your PathORAM's access method
        # or you can loop here to simulate multiple external calls to PathORAM's access.
        # Given your previous app.py, PathORAM.access itself might handle multiple calls.
        # If oram.access("PROTECTED", block_id) already generates multiple internal logs,
        # then a single call here is sufficient.
        # If it only generates one internal log, and you want more, loop it.
        # For demonstrating multiple logs per click in protected view:
        # num_simulated_oram_ops = 5 # You can make this random, e.g., random.randint(3, 7)
        # for _ in range(num_simulated_oram_ops):
        # oram.access("PROTECTED", block_id) # Call your ORAM's access method multiple times
        # or let its internal logic create multiple logs per call.
        start_time = time.time()
        data, logs = photo_manager.download_photo(str(block_id), use_oram=True)
        image_url = f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"
        print(logs)
        end_time = time.time()
        latency = end_time - start_time
        protected_log_store.extend(logs)
        protected_image_url = image_url
        protected_latency = latency
        return render_template(
            "index.html",
            protected_logs=protected_log_store,
            unprotected_logs=unprotected_log_store,
            protected_image_url=protected_image_url,
            protected_latency=protected_latency,
            unprotected_image_url=unprotected_image_url,
            unprotected_latency=unprotected_latency
        )

    elif view_type.lower() == "unprotected":
        # Clear previous unprotected logs *before* making the new access call
        # This ensures only the single new API call is shown.
        # oram.clear_logs("UNPROTECTED")
        # Unprotected: Just one access call to your ORAM
        # oram.access("UNPROTECTED", block_id)

        start_time = time.time()
        data, logs = photo_manager.download_photo(str(block_id))
        image_url = f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"
        end_time = time.time()
        latency = end_time - start_time
        unprotected_log_store.extend(logs)
        unprotected_image_url = image_url
        unprotected_latency = latency
        return render_template(
            "index.html",
            protected_logs=protected_log_store,
            unprotected_logs=unprotected_log_store,
            protected_image_url=protected_image_url,
            unprotected_image_url=unprotected_image_url,
            protected_latency=protected_latency,
            unprotected_latency=unprotected_latency,
            unprotected_image_ids=photo_manager.list_unprotected_photo_ids(),
        )
    else:
        # Handle invalid view_type, e.g., return an error or redirect home
        pass  # For now, just continue

    # After performing the access, redirect back to the home page to refresh logs
    return redirect(url_for("home"))

@app.route("/upload/unprotected", methods=["POST"])
def upload_unprotected():
    if "photo_file" not in request.files:
        flash("No file part")
        return redirect(url_for("home"))

    file = request.files["photo_file"]
    if file.filename == "":
        flash("No selected file")
        return redirect(url_for("home"))

    if file:
        filename = file.filename
        data = file.read()
        logs = photo_manager.upload_photo(filename, data, use_oram=False)
        unprotected_log_store.extend(logs)

    return redirect(url_for("home"))

@app.route("/clear_logs/<view_type>")
def clear_logs(view_type):
    # Clear logs for the specified view type using your ORAM's method
    # oram.clear_logs(view_type.upper())
    # Redirect back to the home page to show cleared logs
    global protected_log_store, unprotected_log_store
    global protected_image_url, unprotected_image_url
    global protected_latency, unprotected_latency

    if view_type.lower() == "protected":
        protected_log_store.clear()
        protected_image_url = None
        protected_latency = None
    elif view_type.lower() == "unprotected":
        unprotected_log_store.clear()
        unprotected_image_url = None
        unprotected_latency = None
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
