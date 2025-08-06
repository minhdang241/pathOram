from __future__ import annotations

import base64
import logging
import time
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for

from photo_manager import PhotoManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = Flask(__name__)
photo_manager = PhotoManager(is_local=False)
app.secret_key = "7832"

protected_log_store = []
unprotected_log_store = []
protected_image_url = None
unprotected_image_url = None
protected_latency = None
unprotected_latency = None

benchmark_records = {
    "upload_protected": [],
    "upload_unprotected": [],
    "download_protected": [],
    "download_unprotected": [],
}


@app.route("/")
def home():
    # Fetch logs for both protected and unprotected views
    # from your PathORAM instance to pass to the single index.html template
    return render_template(
        "index.html",
        protected_logs=protected_log_store,
        protected_image_url=protected_image_url,
        protected_latency=protected_latency,
        protected_image_ids=photo_manager.list_photo_ids(use_oram=True),
        unprotected_logs=unprotected_log_store,
        unprotected_image_url=unprotected_image_url,
        unprotected_latency=unprotected_latency,
        unprotected_image_ids=photo_manager.list_photo_ids(),
    )


@app.route("/access/<view_type>/<path:photo_id>")
def access(view_type: str, photo_id: str):
    global protected_log_store, unprotected_log_store
    global protected_image_url, unprotected_image_url
    global protected_latency, unprotected_latency
    global benchmark_records
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
        data, logs = photo_manager.download_photo(photo_id, use_oram=True)
        image_url = f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"
        end_time = time.time()
        latency = end_time - start_time
        size_kb_protected = len(data) / 1024
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        protected_log_store.extend(logs)
        protected_image_url = image_url
        protected_latency = latency
        benchmark_records["download_protected"].append(
            {
                "filename": photo_id,
                "latency": latency,
                "size_kb": size_kb_protected,
                "timestamp": timestamp,
            }
        )

        return render_template(
            "index.html",
            protected_logs=protected_log_store,
            unprotected_logs=unprotected_log_store,
            protected_image_url=protected_image_url,
            protected_latency=protected_latency,
            protected_image_ids=photo_manager.list_photo_ids(use_oram=True),
            unprotected_image_url=unprotected_image_url,
            unprotected_latency=unprotected_latency,
            unprotected_image_ids=photo_manager.list_photo_ids(),
        )

    elif view_type.lower() == "unprotected":
        # Clear previous unprotected logs *before* making the new access call
        # This ensures only the single new API call is shown.
        # oram.clear_logs("UNPROTECTED")
        # Unprotected: Just one access call to your ORAM
        # oram.access("UNPROTECTED", block_id)

        start_time = time.time()
        data, logs = photo_manager.download_photo(photo_id)
        image_url = f"data:image/jpeg;base64,{base64.b64encode(data).decode('utf-8')}"
        end_time = time.time()
        latency = end_time - start_time
        size_kb_unprotected = len(data) / 1024
        unprotected_log_store.extend(logs)
        unprotected_image_url = image_url
        unprotected_latency = latency
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        benchmark_records["download_unprotected"].append(
            {
                "filename": photo_id,
                "latency": latency,
                "size_kb": size_kb_unprotected,
                "timestamp": timestamp,
            }
        )
        return render_template(
            "index.html",
            protected_logs=protected_log_store,
            unprotected_logs=unprotected_log_store,
            protected_image_url=protected_image_url,
            protected_image_ids=photo_manager.list_photo_ids(use_oram=True),
            unprotected_image_url=unprotected_image_url,
            protected_latency=protected_latency,
            unprotected_latency=unprotected_latency,
            unprotected_image_ids=photo_manager.list_photo_ids(),
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
        start_time = time.time()
        logs = photo_manager.upload_photo(filename, data, use_oram=False)
        latency = time.time() - start_time
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        size_kb = len(data) / 1024
        unprotected_log_store.extend(logs)
        benchmark_records["upload_unprotected"].append(
            {
                "filename": filename,
                "latency": latency,
                "size_kb": size_kb,
                "timestamp": timestamp,
            }
        )

    return redirect(url_for("home"))


@app.route("/upload/protected", methods=["POST"])
def upload_protected():
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
        start_time = time.time()
        logs = photo_manager.upload_photo(
            filename, data, use_oram=True
        )  # FIXED: use_oram=True
        latency = time.time() - start_time
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        size_kb = len(data) / 1024
        protected_log_store.extend(logs)
        benchmark_records["upload_protected"].append(
            {
                "filename": filename,
                "latency": latency,
                "size_kb": size_kb,
                "timestamp": timestamp,
            }
        )

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


@app.route("/benchmark")
def benchmark():
    return render_template("benchmark.html", records=benchmark_records)


@app.route("/clear_benchmark", methods=["POST"])
def clear_benchmark():
    global benchmark_records
    for key in benchmark_records:
        benchmark_records[key].clear()
    flash("Benchmark records cleared.")
    return redirect(url_for("benchmark"))


if __name__ == "__main__":
    app.run(debug=True)
