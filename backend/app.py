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

# Store the last detected PO number for confirmation
last_detected_po = None

# Load PO data
po_dict = {}
itemsFilePath = os.path.join("data", "items.json")
try:
    with open(itemsFilePath, "r") as file:
        po_dict = json.load(file)
        print("✅ PO data loaded successfully!")
except FileNotFoundError:
    print(f"❌ Error: File not found at {itemsFilePath}. Check the path.")
except json.JSONDecodeError:
    print("❌ Error: Invalid JSON format in items.json.")

# File paths
WAV_PATH = os.path.join('data/audio', 'processed.wav')
ORIGINAL_PATH = os.path.join('data/audio', 'original.webm')
AI_AUDIO_PATH = os.path.join('data/ai_audio', "ai_response.wav")

def get_po_details(po_number):
    """Get formatted details of a PO number"""
    if po_number in po_dict:
        details_str = f"PO Number: {po_number}\nItems:\n"
        for item_name, details in po_dict[po_number]["items"].items():
            details_str += f"- {item_name}\n"
            details_str += f"  Item Number: {details['item_number']}\n"
            details_str += f"  Bin Location: {details['bin_location']}\n"
        
        return details_str
    else:
        print(f"❌ PO Number '{po_number}' not found.")
        return None

def convert_audio_to_wav(input_path, output_path):
    """Convert audio to WAV format compatible with Azure"""
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format='wav')

def recognize_speech_from_file(audio_path):
    """Recognize speech from audio file using Azure"""
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    result = speech_recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return "No speech could be recognized"
    elif result.reason == speechsdk.ResultReason.Canceled:
        return f"Speech recognition canceled: {result.cancellation_details.reason}"

def synthesize_speech(text, output_path):
    """Convert text to speech using Azure"""
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    
    result = synthesizer.speak_text_async(text).get()
    
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"Text-to-Speech failed: {result.error_details}")

def is_confirmation(text):
    """Check if the text is a confirmation"""
    confirmation_phrases = ['yes', 'correct', 'that is correct', 'that\'s correct', 'yeah', 'yep', 'right']
    return any(phrase in text.lower() for phrase in confirmation_phrases)

def is_rejection(text):
    """Check if the text is a rejection"""
    rejection_phrases = ['no', 'that\'s wrong', 'incorrect', 'that is wrong','nah', 'nope', 'not correct']
    return any(phrase in text.lower() for phrase in rejection_phrases)

def process_confirmation(po_number):
    """Process a confirmed PO number"""
    po_exists = po_number in po_dict
    details = get_po_details(po_number) if po_exists else None
    
    if po_exists:
        ai_text = f"Found {po_number}. Here are the details."
    else:
        ai_text = f"PO {po_number} was not found in our system. Please try another PO number."
    
    synthesize_speech(ai_text, AI_AUDIO_PATH)
    
    return {
        "message": "Confirmation processed",
        "po_number": po_number,
        "po_exists": po_exists,
        "details": details,
        "show_confirm_options": False
    }

def process_rejection():
    """Process a rejection of the detected PO number"""
    ai_text = "Let's try again. Please provide the PO number."
    synthesize_speech(ai_text, AI_AUDIO_PATH)
    
    return {
        "message": "Retry requested",
        "po_number": None,
        "show_confirm_options": False
    }

def process_new_po(transcript):
    """Process a new PO number input"""
    clean_transcript = transcript.strip().rstrip('.').rstrip(',').rstrip('?')
    po_number = clean_transcript.upper()
    
    # If no speech was recognized, handle that case
    if transcript == "No speech could be recognized":
        ai_text = "I didn't hear anything. Please try again."
        show_confirm = False
    else:
        ai_text = f"I heard {transcript}, is that correct?"
        show_confirm = True
    
    synthesize_speech(ai_text, AI_AUDIO_PATH)
    
    return {
        "message": "File processed successfully",
        "po_number": transcript if transcript != "No speech could be recognized" else None,
        "show_confirm_options": show_confirm
    }

@app.route('/')
def serve_react():
    return send_file('static/index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_file(f'static/{path}')

@app.route('/upload', methods=['POST'])
def upload_audio():
    global last_detected_po
    
    # Getting the audio file from the request
    audio_file = request.files['audio']
    audio_file.save(ORIGINAL_PATH)
    
    # Convert WebM to WAV format that Azure likes
    convert_audio_to_wav(ORIGINAL_PATH, WAV_PATH)

    # Transcribe speech
    transcript = recognize_speech_from_file(WAV_PATH)
    
    # Check if this is a confirmation, rejection, or new PO
    if transcript == "No speech could be recognized" or transcript.startswith("Speech recognition canceled"):
        response_data = process_new_po(transcript)
    elif last_detected_po and is_confirmation(transcript):
        po_number = last_detected_po
        last_detected_po = None  # Reset for next input
        response_data = process_confirmation(po_number)
    elif last_detected_po and is_rejection(transcript):
        last_detected_po = None  # Reset for next input
        response_data = process_rejection()
    else:
        # It's a new PO number
        clean_transcript = transcript.strip().rstrip('.').rstrip(',').rstrip('?')
        last_detected_po = clean_transcript.upper()
        response_data = process_new_po(transcript)
    
    return jsonify(response_data)

@app.route('/get-ai-audio', methods=['GET'])
def get_ai_audio():
    return send_file(AI_AUDIO_PATH, mimetype="audio/wav")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

    
#Button for yes/no
# @app.route('/button-confirm', methods=['POST'])
# def button_confirm():
#     global last_detected_po
    
#     data = request.json
#     confirmed = data.get('confirmed', True)
    
#     if not confirmed:
#         # Handle "No" button click
#         ai_text = "Let's try again. Please provide the PO number."
#         last_detected_po = None
        
#         # Generate AI response
#         ai_audio_path = os.path.join('data/ai_audio', "ai_response.wav")
#         synthesize_speech(ai_text, ai_audio_path)
        
#         return jsonify({
#             "message": "Retry requested",
#             "show_confirm_options": False
#         })
    
#     # Handle "Yes" button click
#     po_number = last_detected_po if last_detected_po else data.get('po_number', '').upper()
    
#     po_exists = po_number in po_dict
#     details = get_po_details(po_number) if po_exists else None
    
#     if po_exists:
#         ai_text = f"Found PO {po_number}. Here are the details."
#     else:
#         ai_text = f"PO {po_number} was not found in our system. Please try another PO number."
    
#     # Reset the last detected PO
#     last_detected_po = None
    
#     # Generate AI response
#     ai_audio_path = os.path.join('data/ai_audio', "ai_response.wav")
#     synthesize_speech(ai_text, ai_audio_path)
    
#     return jsonify({
#         "po_exists": po_exists,
#         "details": details,
#         "po_number": po_number,
#         "message": "Confirmation processed successfully"
#     })