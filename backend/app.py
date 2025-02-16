# Flask for web server
from flask import Flask, request
# CORS library to allow requests from frontend
from flask_cors import CORS
# for filepath stuff
import os

app = Flask(__name__)
CORS(app)

# audio folder won't push to github if it's empty, so create it if it doesn't exist
os.makedirs('data/audio', exist_ok=True)


# Route for handling the POST requests
@app.route('/upload', methods=['POST'])
def upload_audio():
    # Getting the audio file from the request
    audio_file = request.files['audio']
    # Save the file to the data/audio folder
    audio_file.save(os.path.join('data/audio', audio_file.filename))
    return 'File uploaded successfully'

if __name__ == '__main__':
    app.run(port=5000, debug=True)