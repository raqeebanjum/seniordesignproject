// import react hooks
import { useState, useRef, useEffect } from 'react';

// Translation strings
const translations = {
  "en-US": {
    recording: "Recording...",
    processing: "Processing audio...",
    error: "Error processing audio. Please try again.",
    ready: "Ready to record",
    retry: "Let's try again. Please record PO number.",
    notHeard: "I couldn't hear anything. Please try again.",
    foundPO: (po) => `Found PO: ${po}`,
    notFound: (po) => `PO ${po} not found`,
    confirmPrompt: (po) => `Detected: ${po}. Please say \"yes\" to confirm or \"no\" to try again.`,
    reset: "Reset",
    recordBtn: "Record Voice Input",
    stopBtn: "Stop Recording"
  },
  "es-US": {
    recording: "Grabando...",
    processing: "Procesando audio...",
    error: "Error al procesar el audio. Por favor, inténtalo de nuevo.",
    ready: "Listo para grabar",
    retry: "Intentémoslo de nuevo. Por favor graba el número de orden.",
    notHeard: "No escuché nada. Por favor, inténtalo de nuevo.",
    foundPO: (po) => `Orden de compra encontrada: ${po}`,
    notFound: (po) => `Orden ${po} no encontrada`,
    confirmPrompt: (po) => `¿Dijiste ${po}? Di \"sí\" para confirmar o \"no\" para intentarlo de nuevo.`,
    reset: "Reiniciar",
    recordBtn: "Grabar entrada de voz",
    stopBtn: "Detener grabación"
  }
};

// Helper to get translation object by language
const getT = (lang) => translations[lang] || translations["en-US"];

// Component for the audio controls
const AudioControls = ({ isRecording, startRecording, stopRecording, resetApp, hasData, detectedLang }) => {
  const t = getT(detectedLang);
  return (
    <div className="flex gap-4 mb-4">
      <button 
        className={`btn ${isRecording ? 'btn-error' : 'btn-primary'}`}
        onClick={isRecording ? stopRecording : startRecording}
      >
        {isRecording ? t.stopBtn : t.recordBtn}
      </button>

      {!isRecording && hasData && (
        <button 
          className="btn btn-neutral"
          onClick={resetApp}
        >
          {t.reset}
        </button>
      )}
    </div>
  );
};

// Component for displaying PO details
const PODetails = ({ details }) => {
  if (!details) return null;

  const parsed = details.split('\n').filter(line => line.trim() !== '');
  const poNumber = parsed[0].replace('PO Number: ', '');
  const items = [];

  for (let i = 2; i < parsed.length; i += 3) {
    items.push({
      name: parsed[i].replace('- ', ''),
      itemNumber: parsed[i + 1].replace('  Item Number: ', ''),
      binLocation: parsed[i + 2].replace('  Bin Location: ', ''),
    });
  }

  return (
    <div className="card bg-base-200 shadow-lg mt-4 w-full max-w-2xl">
      <div className="card-body">
        <h2 className="card-title mb-2">PO Number: {poNumber}</h2>
        <div className="overflow-x-auto">
          <table className="table table-zebra w-full text-sm">
            <thead>
              <tr>
                <th>Item Name</th>
                <th>Item Number</th>
                <th>Bin Location</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr key={idx}>
                  <td>{item.name}</td>
                  <td>{item.itemNumber}</td>
                  <td>{item.binLocation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

// Main Audio Player component
const AudioPlayer = ({ url, audioRef }) => {
  return url ? (
    <div className="mt-4">
      <audio ref={audioRef} controls autoPlay className="w-full">
        <source src={url} type="audio/wav" />
        Your browser does not support the audio element.
      </audio>
    </div>
  ) : null;
};

// Main App component
function App() {
  const [detectedLang, setDetectedLang] = useState("en-US");

  // State management with custom hook
  const useAudioRecorder = () => {
    const [isRecording, setIsRecording] = useState(false);
    const [audioURL, setAudioURL] = useState(null);
    const [statusMessage, setStatusMessage] = useState("Ready to record");
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const audioRef = useRef(null);

    // Reset audio when a new one is loaded
    useEffect(() => {
      if (audioURL && audioRef.current) {
        audioRef.current.load();
      }
    }, [audioURL]);

    return {
      isRecording, setIsRecording,
      audioURL, setAudioURL,
      statusMessage, setStatusMessage,
      mediaRecorderRef, audioChunksRef, audioRef
    };
  };

  const {
    isRecording, setIsRecording,
    audioURL, setAudioURL,
    statusMessage, setStatusMessage,
    mediaRecorderRef, audioChunksRef, audioRef
  } = useAudioRecorder();

  // PO states
  const [detectedPO, setDetectedPO] = useState(null);
  const [showConfirmOptions, setShowConfirmOptions] = useState(false);
  const [poDetails, setPoDetails] = useState(null);

  // function to start recording
  const startRecording = () => {
    const t = getT(detectedLang);
    audioChunksRef.current = [];
    setStatusMessage(t.recording);

    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        mediaRecorderRef.current = new MediaRecorder(stream, {
          mimeType: 'audio/webm'
        });
        mediaRecorderRef.current.ondataavailable = (event) => {
          audioChunksRef.current.push(event.data);
        };
        mediaRecorderRef.current.start();
        setIsRecording(true);
      });
  };

  // function to stop recording and process audio
  const stopRecording = () => {
    const t = getT(detectedLang);
    mediaRecorderRef.current.stop();
    setIsRecording(false);
    setStatusMessage(t.processing);

    mediaRecorderRef.current.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      try {
        const response = await fetch('/upload', {
          method: 'POST',
          body: formData
        });
        
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          const data = await response.json();
          updateUIBasedOnResponse(data);
        } else {
          throw new Error("Received non-JSON response");
        }
      } catch (error) {
        console.error("Error processing audio:", error);
        setStatusMessage(t.error);
      }
    };
  };

  // Helper to update UI based on backend response
  const updateUIBasedOnResponse = async (data) => {
    // 1. Always update language FIRST
    let lang = detectedLang;

    // Only update language if it's not a failure message
    if (
      data.detected_lang &&
      !(data.po_number === null && data.message === "Retry requested")
    ) {
      lang = data.detected_lang;
      setDetectedLang(lang);
    }
    
    const t = getT(lang);
  
    // 2. Then update message state using new language
    if (data.details) {
      setPoDetails(data.details);
      setDetectedPO(data.po_number);
      setShowConfirmOptions(false);
      setStatusMessage(
        data.po_exists ? t.foundPO(data.po_number) : t.notFound(data.po_number)
      );
    } else if (data.show_confirm_options) {
      setDetectedPO(data.po_number);
      setShowConfirmOptions(true);
      setStatusMessage(t.confirmPrompt(data.po_number)); // now uses updated lang
    } else if (data.message === "Retry requested") {
      resetApp();
      setStatusMessage(t.retry);
    } else if (data.message === "No voice recognized") {
      setStatusMessage(t.notHeard);
    }
  
    // Play AI audio
    try {
      const audioResponse = await fetch("/get-ai-audio");
      const audioBlob = await audioResponse.blob();
      const audioURL = URL.createObjectURL(audioBlob);
      setAudioURL(audioURL);
    } catch (error) {
      console.error("Error fetching audio:", error);
    }
  };  

  // Reset the app state for a new recording
  const resetApp = async () => {
    const t = getT(detectedLang);
  
    // Reset backend state too
    try {
      await fetch("/reset", { method: "POST" });
    } catch (error) {
      console.error("Failed to reset backend state:", error);
    }
  
    setDetectedPO(null);
    setShowConfirmOptions(false);
    setPoDetails(null);
    setStatusMessage(t.ready);
    setAudioURL(null);
  };
  

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-4">
      <h1 className="text-2xl font-bold mb-4">Receiving System</h1>

      <div className="text-lg font-medium mb-2">{statusMessage}</div>

      {/* Main control buttons */}
      <AudioControls 
        isRecording={isRecording}
        startRecording={startRecording}
        stopRecording={stopRecording}
        resetApp={resetApp}
        hasData={detectedPO || poDetails}
        detectedLang={detectedLang}
      />

      {/* PO Details display */}
      <PODetails details={poDetails} />

      {/* Audio player */}
      <AudioPlayer url={audioURL} audioRef={audioRef} />
    </div>
  );
}

export default App;