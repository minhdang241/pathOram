from flask import Flask, render_template, redirect, url_for
from placeholder_oram import PathORAM

app = Flask(__name__)
oram = PathORAM()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/protected')
def protected_view():
    logs = oram.get_logs("PROTECTED")
    return render_template('protected.html', logs=logs)

@app.route('/unprotected')
def unprotected_view():
    logs = oram.get_logs("UNPROTECTED")
    return render_template('unprotected.html', logs=logs)

@app.route('/access/<view>/<int:block_id>')
def access(view, block_id):
    if view.lower() == "protected":
        # Simulate recursive ORAM access with multiple path accesses
        for _ in range(5):  # You can adjust this number as needed
            oram.access("PROTECTED", block_id)
    else:
        # Unprotected: Just one access
        oram.access("UNPROTECTED", block_id)

    return redirect(url_for(f'{view.lower()}_view'))

@app.route('/clear_logs/<view>')
def clear_logs(view):
    oram.clear_logs(view.upper())
    return redirect(url_for(f'{view.lower()}_view'))

if __name__ == "__main__":
    app.run(debug=True)
