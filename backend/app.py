# Flask for web server
import json
from flask import Flask, request, jsonify, send_file, send_from_directory
# CORS library to allow requests from frontend
from flask_cors import CORS
# for filepath stuff
import os
from pydub import AudioSegment
import azure.cognitiveservices.speech as speechsdk
from collections import deque  # New import for queue functionality
import re
from difflib import get_close_matches

# Azure API keys
speech_key = "put azure api key here"
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
        print("PO data loaded successfully!")
except FileNotFoundError:
    print(f"Error: File not found at {itemsFilePath}. Check the path.")
except json.JSONDecodeError:
    print("Error: Invalid JSON format in items.json.")


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
        print(f"PO Number '{po_number}' not found.")
        return None

def convert_audio_to_wav(input_path, output_path):
    """Convert audio to WAV format compatible with Azure"""
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format='wav')

def recognize_speech_from_file(audio_path):
    """Recognize speech and detect language from audio file using Azure"""
    auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["es-US", "en-US"])
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)

    # Use auto-detect language config
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config, auto_detect_source_language_config=auto_detect_source_language_config)

    result = speech_recognizer.recognize_once_async().get()

    # Get the detected language from the result
    detected_lang = result.properties.get(speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult)
    detected_lang = detected_lang or "es-US"

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text, detected_lang
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return "No speech could be recognized", detected_lang
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("CANCELED: Reason =", cancellation_details.reason)
        print("CANCELED: ErrorDetails =", cancellation_details.error_details)
        return f"Speech recognition canceled: {result.cancellation_details.reason}", detected_lang


def synthesize_speech(text, output_path, language="es-US"):
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)

    if language == "es-US":
        speech_config.speech_synthesis_voice_name = "es-US-PalomaNeural"
    else:
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    result = synthesizer.speak_text_async(text).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print("TTS Canceled: ", cancellation_details.reason)
            print("TTS Error Details: ", cancellation_details.error_details)
        else:
            print("TTS failed for an unknown reason.")
        return
    
    print("TTS synthesis completed successfully.")

    if os.path.exists(output_path):
        print("Audio file written:", output_path)
    else:
        print("Audio file not found after synthesis:", output_path)




def is_arrival(text, language):
    confirmations = {
        "en-US": [
            'im there', 'i am there', 'im there'
        ],
        "es-US": [
            'ya llegue', 'he llegado', 'llegue', 'estoy aqui', 'Ya yage', 'Ya, ya, ya', 'Ya ya gay'
        ]
    }
    print(f"Raw transcript: {text}")

def is_placement(text, lang):
    if lang == "es-US":
        return any(p in text.lower() for p in ["ya lo coloqué", "ya lo puse", "coloqué"])
    return any(p in text.lower() for p in ["i've placed it", "i placed it", "i have placed it"])


def is_confirmation(text, language):
    """Check if the text is a confirmation, localized by language"""
    confirmations = {
        "en-US": [
            'yes', 'correct', 'that is correct', "that's correct", 'yeah', 'yep', 'right'
        ],
        "es-US": [
            'sí', 'si', 'es correcto', 'eso es correcto', 'claro', 'afirmativo'
        ]
    }

    words = text.lower().split()
    phrases = confirmations.get(language, confirmations["es-US"])
    return any(get_close_matches(word, phrases, cutoff=0.6) for word in words)

def is_rejection(text, language):
    """Check if the text is a rejection, localized by language"""
    rejections = {
        "en-US": [
            'no', "that's wrong", 'incorrect', 'that is wrong', 'nah', 'nope', 'not correct'
        ],
        "es-US": [
            'no', 'no es correcto', 'eso es incorrecto', 'incorrecto', 'negativo'
        ]
    }

    phrases = rejections.get(language, rejections["es-US"])
    return any(phrase in text.lower() for phrase in phrases)

def process_confirmation(po_number, language):
    global current_state, current_item, current_po_number
    
    po_exists = po_number in po_dict
    details = get_po_details(po_number) if po_exists else None
    bin_location = None  # default

    if po_exists:
        # This is for tracking which PO number we're currently working with
        current_po_number = po_number
        
        # Enqueue items
        enqueue_po_items(po_number)
        if queue:
            current_item = queue[0]
            bin_location = current_item["bin_location"]
            current_state = 'awaiting_arrival'
            if language == "es-US":
                ai_text = (
                    f"PO {po_number} encontrado. "
                    f"Tu primera ubicación del contenedor es {bin_location}. "
                    "Di 'Ya llegué' cuando llegues para recibir instrucciones de colocación."
                )
            else:
                ai_text = (
                    f"Found {po_number}. "
                    f"Your first bin location is {bin_location}. "
                    "Say 'I'm there' when you arrive to get placement instructions."
                )
        else:
            if language == "es-US":
                ai_text = f"PO {po_number} encontrado, pero no hay artículos en la cola."
            else:
                ai_text = f"Found {po_number}, but there are no items in the queue."
            current_state = 'awaiting_po'  # Reset state if no items
    else:
        ai_text = f"PO {po_number} was not found in our system. Please try another PO number."
        current_state = 'awaiting_po'  # Reset state if PO not found

    synthesize_speech(ai_text, AI_AUDIO_PATH, language=language)

    return {
        "message": ai_text,
        "po_number": po_number,
        "po_exists": po_exists,
        "details": details,
        "show_confirm_options": False,
        "bin_location": bin_location
    }

def process_rejection(language):
    """Process a rejection of the detected PO number"""
    if language == 'es-US':
        ai_text = "Intentémoslo de nuevo. Por favor proporcione el número de orden de compra."
    else:
        ai_text = "Let's try again. Please provide the PO number."
    synthesize_speech(ai_text, AI_AUDIO_PATH, language=language)
    
    return {
        "message": "Retry requested",
        "po_number": None,
        "show_confirm_options": False
    }

# This is a helper function that's for whenever the user says something that isn't expected
def handle_unexpected_input(transcript, current_state, language):
    
    if current_state == 'awaiting_po':
        if language == "es-US":
            ai_text = "Lo siento, no entendí eso. Por favor proporcione un número de orden de compra válido."
        else:
            ai_text = "I'm sorry, I didn't understand that. Please provide a valid PO number."
    
    elif current_state == 'awaiting_arrival':
        if language == "es-US":
            ai_text = "Lo siento, no entendí eso. Por favor diga 'Ya llegué' cuando llegue a la ubicación del contenedor."
        else:
            ai_text = "I'm sorry, I didn't understand that. Please say 'I'm there' when you arrive at the bin location."
    
    elif current_state == 'awaiting_placement':
        if language == "es-US":
            ai_text = "Lo siento, no entendí eso. Por favor diga 'Ya lo puse' cuando haya colocado el artículo en el contenedor."
        else:
            ai_text = "I'm sorry, I didn't understand that. Please say 'I've placed it' once you've put the item in the bin."
    
    elif current_state == 'completed':
        if language == "es-US":
            ai_text = "Lo siento, no entendí eso. Por favor proporcione un número de orden de compra para comenzar una nueva tarea."
        else:
            ai_text = "I'm sorry, I didn't understand that. Please provide a PO number to start a new task."
    
    else:
        # Default fallback for unknown states
        if language == "es-US":
            ai_text = "Lo siento, no entendí eso. Por favor, inténtalo de nuevo."
        else:
            ai_text = "I'm sorry, I didn't understand that. Please try again."
    
    synthesize_speech(ai_text, AI_AUDIO_PATH, language=language)
    
    return {
        "message": ai_text,
        "understood": False,
        "show_confirm_options": False
    }

# this function is for whenever we're actually placing the items
def handle_placement(language):
    global current_state, current_item, current_po_number
    
    placed_item = current_item  # Just to reference it in our response
    
    # Dequeue the item we just placed
    dequeue_item()
    
    # If more items remain, direct the user to the next bin
    if queue:
        current_item = queue[0]
        if language == "es-US":
            ai_text = (
                f"{placed_item['name']} colocado. "
                f"Ahora ve al contenedor {current_item['bin_location']} "
                f"para {current_item['name']} (Artículo {current_item['item_number']}). "
                "Di 'Ya llegué' cuando estés allí."
            )
        else:
            ai_text = (
                f" {placed_item['name']} Placed. "
                f"Next, go to bin location {current_item['bin_location']} "
                f"for {current_item['name']} (Item {current_item['item_number']}). "
                "Say 'I'm there' when you arrive."
            )
        current_state = 'awaiting_arrival'
    else:
        # No more items: we're done with this PO
        if language == "es-US":
            ai_text = f"Todos los artículos del {current_po_number} han sido recibidos. ¡Buen chico!"
        else:
            ai_text = f"All items in {current_po_number} have been received. Good Boy!"
        current_state = 'awaiting_po'
        current_item = None
        current_po_number = None

    synthesize_speech(ai_text, AI_AUDIO_PATH, language=language)
    return {
        "message": ai_text,
        "next_action": "completed" if not queue else "go_to_next_bin"
    }

def process_new_po(transcript, language):
    """Process a new PO number input"""
    clean_transcript = transcript.strip().rstrip('.').rstrip(',').rstrip('?')
    po_number = clean_transcript.upper()
    
    # If no speech was recognized, handle that case
    if transcript == "No speech could be recognized":
        if language == "es-US":
            ai_text = "No escuché nada. Por favor, inténtalo de nuevo."
        else:
            ai_text = "I didn't hear anything. Please try again."
        show_confirm = False
    else:
        if language == "es-US":
            ai_text = f"Escuché {transcript}. ¿Es correcto?"
        else:
            ai_text = f"I heard {transcript}, is that correct?"

        show_confirm = True
    
    synthesize_speech(ai_text, AI_AUDIO_PATH, language=language)
    
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
    global last_detected_po, current_state
    
    # Getting the audio file from the request
    audio_file = request.files['audio']
    audio_file.save(ORIGINAL_PATH)
    
    # Convert WebM to WAV format that Azure likes
    convert_audio_to_wav(ORIGINAL_PATH, WAV_PATH)

    # Transcribe speech
    transcript, detected_lang = recognize_speech_from_file(WAV_PATH)
    print(f"🎙️ Detected language: {detected_lang}")
    
    # Check if this is a confirmation, rejection, or new PO
    # Handle audio transcription result
    if transcript == "No speech could be recognized" or transcript.startswith("Speech recognition canceled"):
        response_data = process_new_po(transcript, detected_lang)
    elif last_detected_po and is_confirmation(transcript, detected_lang):
        po_number = last_detected_po
        last_detected_po = None
        response_data = process_confirmation(po_number, detected_lang)
    elif last_detected_po and is_rejection(transcript, detected_lang):
        last_detected_po = None
        response_data = process_rejection(detected_lang)
    elif current_state == 'awaiting_arrival' and is_arrival(transcript, detected_lang):
        response_data = handle_arrival(detected_lang)
    elif current_state == 'awaiting_arrival':
        response_data = handle_unexpected_input(transcript, current_state, detected_lang)
    elif current_state == 'awaiting_placement' and is_placement(transcript, detected_lang):
        response_data = handle_placement(detected_lang)
    elif current_state == 'awaiting_placement':
        response_data = handle_unexpected_input(transcript, current_state, detected_lang)
    elif current_state == 'completed' or current_state == 'awaiting_po':
        # We're expecting a new PO number
        clean_transcript = re.sub(r'[^a-zA-Z0-9]', '', transcript).upper()
        last_detected_po = clean_transcript
        response_data = process_new_po(transcript, detected_lang)
    else:
        # Default case - assume it's a PO number
        clean_transcript = re.sub(r'[^a-zA-Z0-9]', '', transcript).upper()
        last_detected_po = clean_transcript
        response_data = process_new_po(transcript, detected_lang)
        response_data["detected_lang"] = detected_lang


    # Make sure the frontend ALWAYS gets the language
    response_data["detected_lang"] = detected_lang

    return jsonify(response_data)


@app.route('/get-ai-audio', methods=['GET'])
def get_ai_audio():
    return send_file(AI_AUDIO_PATH, mimetype="audio/wav")

# ----------------------- New In-Memory Queue Functionality -----------------------
# Initialize the in-memory queue for PO items
queue = deque()
# Track interaction state: 'awaiting_arrival', 'awaiting_placement', 'completed'
current_state = 'awaiting_po'
current_item = None
current_po_number = None

# Uncommented queue handling endpoints


def get_next_item():
    global current_item
    if queue:
        current_item = queue[0]
        return current_item
    return None

# Function to enqueue all PO items from items.json
def enqueue_po_items(po_number):
    global queue
    queue.clear()

    if po_number not in po_dict:
        print(f"PO Number '{po_number}' not found.")
        return

    items = po_dict[po_number].get("items", {})

    if not items:
        print(f"PO {po_number} has no items to process.")
        return

    for item_name, details in items.items():
        queue.append({
            "name": item_name,
            "item_number": details["item_number"],
            "bin_location": details["bin_location"]
        })

    print(f"Queue successfully populated for PO {po_number}:")
    for i, item in enumerate(queue, 1):
        print(f"{i}. {item['name']} (Item: {item['item_number']}, Bin: {item['bin_location']})")


#po_number = process_confirmation()  
#enqueue_po_items(po_number)


# Function to dequeue an item from the in-memory queue
def dequeue_item():
    if queue:
        return queue.popleft()
    return None



# Endpoint to enqueue all PO items into the queue
@app.route("/enqueue", methods=["POST"])
def enqueue():
    data = request.get_json()
    po_number = data.get("po_number")
    enqueue_po_items(po_number)
    return jsonify({"message": "PO items enqueued", "queue": list(queue)})

# Endpoint to dequeue the next PO item from the queue
@app.route("/dequeue", methods=["POST"])
def dequeue():
    item = dequeue_item()
    if item:
        return jsonify({"message": "Item dequeued", "item": item})
    return jsonify({"message": "Queue is empty"})

# Endpoint to view the current queue state
@app.route("/queue", methods=["GET"])
def get_queue():
    return jsonify({"queue": list(queue)})

# Uncommented queue handling endpoints
def handle_arrival(language):
    global current_state, current_item
    
    if current_state == 'awaiting_arrival' and current_item:
        if language == "es-US":
            ai_text = f"Coloca {current_item['name']} (Artículo {current_item['item_number']}) en el contenedor {current_item['bin_location']}. Di 'ya lo coloqué' cuando termines."
        else:
            ai_text = f"Place {current_item['name']} (Item {current_item['item_number']}) in bin {current_item['bin_location']}. Say 'I\'ve placed it' when finished."
        current_state = 'awaiting_placement'
    else:
        if language == "es-US":
            ai_text = "Por favor, procede a la siguiente ubicación del contenedor."
        else:
            ai_text = "Please proceed to the next bin location."
    
    synthesize_speech(ai_text, AI_AUDIO_PATH, language=language)
    return {
        "message": ai_text,
        "item": current_item,
        "next_action": "confirm_placement"
    }

@app.route('/reset', methods=['POST'])
def reset_backend_state():
    global current_state, current_item, current_po_number, last_detected_po
    queue.clear()
    current_state = 'awaiting_po'
    current_item = None
    current_po_number = None
    last_detected_po = None
    print("🔄 Backend state reset")
    return jsonify({"message": "Backend state reset"})




# -----------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

    
