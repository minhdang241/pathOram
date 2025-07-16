from flask import Flask, render_template, redirect, url_for
from placeholder_oram import PathORAM # Assuming this is the correct import for your class

app = Flask(__name__)
oram = PathORAM() # Initialize your ORAM instance

@app.route('/')
def home():
    # Fetch logs for both protected and unprotected views
    # from your PathORAM instance to pass to the single index.html template
    protected_logs = oram.get_logs("PROTECTED")
    unprotected_logs = oram.get_logs("UNPROTECTED")
    return render_template('index.html',
                           protected_logs=protected_logs,
                           unprotected_logs=unprotected_logs)

@app.route('/access/<view_type>/<int:block_id>')
def access(view_type, block_id):
    if view_type.lower() == "protected":
        # Clear previous protected logs *before* making the new access calls
        # This ensures that only the new set of calls for this access are shown.
        oram.clear_logs("PROTECTED")

        # Simulate ORAM access with multiple internal API calls
        # The number of internal calls should be handled by your PathORAM's access method
        # or you can loop here to simulate multiple external calls to PathORAM's access.
        # Given your previous app.py, PathORAM.access itself might handle multiple calls.
        # If oram.access("PROTECTED", block_id) already generates multiple internal logs,
        # then a single call here is sufficient.
        # If it only generates one internal log, and you want more, loop it.
        # For demonstrating multiple logs per click in protected view:
        num_simulated_oram_ops = 5 # You can make this random, e.g., random.randint(3, 7)
        for _ in range(num_simulated_oram_ops):
            oram.access("PROTECTED", block_id) # Call your ORAM's access method multiple times
                                               # or let its internal logic create multiple logs per call.

    elif view_type.lower() == "unprotected":
        # Clear previous unprotected logs *before* making the new access call
        # This ensures only the single new API call is shown.
        oram.clear_logs("UNPROTECTED")
        # Unprotected: Just one access call to your ORAM
        oram.access("UNPROTECTED", block_id)
    else:
        # Handle invalid view_type, e.g., return an error or redirect home
        pass # For now, just continue

    # After performing the access, redirect back to the home page to refresh logs
    return redirect(url_for('home'))

@app.route('/clear_logs/<view_type>')
def clear_logs(view_type):
    # Clear logs for the specified view type using your ORAM's method
    oram.clear_logs(view_type.upper())
    # Redirect back to the home page to show cleared logs
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
