# Flask for web server
import json
from flask import Flask, request, jsonify, send_file, send_from_directory
# CORS library to allow requests from frontend
from flask_cors import CORS
# for filepath stuff
import os
from pydub import AudioSegment
import azure.cognitiveservices.speech as speechsdk

# Azure API keys
speech_key = "G1qZMOd4MFuiqN6jwSPcStpRPgdl3zAQM0PxfFNXFIfXMq7v2ALbJQQJ99BBACYeBjFXJ3w3AAAYACOGorwn"
service_region = "eastus"

app = Flask(__name__)
CORS(app)

# audio folder won't push to github if it's empty, so create it if it doesn't exist
os.makedirs('data/audio', exist_ok=True)
os.makedirs('data/ai_audio', exist_ok=True)

po_dict = {}


itemsFilePath = os.path.join("data", "items.json")
try:
    with open(itemsFilePath, "r") as file:
        po_dict = json.load(file)
        print("✅ PO data loaded successfully!")
except FileNotFoundError:
    print(f"❌ Error: File not found at {itemsFilePath}. Check the path.")
    po_dict = {}
except json.JSONDecodeError:
    print("❌ Error: Invalid JSON format in items.json.")
    po_dict = {}

# for checking the PO data from the dictionary manually
#print(po_dict)


def convert_audio_to_wav(input_path, output_path):
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format='wav')

def recognize_speech_from_file(audio_path):
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    result = speech_recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return "No speech could be recognized."
    elif result.reason == speechsdk.ResultReason.Canceled:
        return f"Speech recognition canceled: {result.cancellation_details.reason}"

def synthesize_speech(text, output_path):
    #Converts text to AI-generated speech using Azure Text-to-Speech.
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    
    result = synthesizer.speak_text_async(text).get()
    
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Text-to-Speech failed: {result.error_details}")



# Route for serving the React app
@app.route('/')
def serve_react():
    return send_file('static/index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_file(f'static/{path}')


# Route for handling the POST requests
@app.route('/upload', methods=['POST'])
def upload_audio():
    # Getting the audio file from the request
    audio_file = request.files['audio']

    # Save the original WebM file
    original_path = os.path.join('data/audio', 'original.webm')
    audio_file.save(original_path)
    
    # Convert WebM to WAV format that Azure likes
    wav_path = os.path.join('data/audio', 'processed.wav')
    convert_audio_to_wav(original_path, wav_path)

    # Transcribe speech
    transcript = recognize_speech_from_file(wav_path)

    # Assume the transcript is the PO number
    ai_text = f"I heard {transcript}, is that correct?"

    # Generate AI response
    ai_audio_path = os.path.join('data/ai_audio', "ai_response.wav")
    synthesize_speech(ai_text, ai_audio_path)

    return jsonify({
        "message": "File processed successfully",
        "po_number": transcript,  # Assume full transcript is the PO number
        "ai_audio": ai_audio_path
    })

@app.route('/get-ai-audio', methods=['GET'])
def get_ai_audio():
    #Sends the AI-generated speech file back to the frontend.
    ai_audio_path = os.path.join('data/ai_audio', "ai_response.wav")
    return send_file(ai_audio_path, mimetype="audio/wav")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
    
    
