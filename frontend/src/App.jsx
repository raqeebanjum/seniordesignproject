import { useState, useRef, useEffect } from 'react';

// Component for the audio controls
const AudioControls = ({ isRecording, startRecording, stopRecording, resetApp, hasData }) => {
  return (
    <div className="flex gap-4 mb-4">
      <button 
        className={`btn ${isRecording 
          ? 'btn-error' 
          : 'btn-primary'}`}
        onClick={isRecording ? stopRecording : startRecording}
      >
        {isRecording ? 'Stop Recording' : 'Record Voice Input'}
      </button>
      
      {!isRecording && hasData && (
        <button 
          className="btn btn-neutral"
          onClick={resetApp}
        >
          Reset
        </button>
      )}
    </div>
  );
};

// Component for displaying PO details
const PODetails = ({ details }) => {
  return details ? (
    <div className="card bg-base-200 shadow-lg mt-4 max-w-lg w-full">
      <div className="card-body">
        <h2 className="card-title">PO Details:</h2>
        <pre className="whitespace-pre-line text-sm">{details}</pre>
      </div>
    </div>
  ) : null;
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
    // Reset states before starting new recording
    audioChunksRef.current = [];
    setStatusMessage("Recording...");
    
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
    mediaRecorderRef.current.stop();
    setIsRecording(false);
    setStatusMessage("Processing audio...");
    
    // when the recording stops, create a blob from the audio chunks
    mediaRecorderRef.current.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      try {
        // send the audio blob to the backend
        const response = await fetch('/upload', {
          method: 'POST',
          body: formData
        });
        const data = await response.json();
        
        updateUIBasedOnResponse(data);
      } catch (error) {
        console.error("Error processing audio:", error);
        setStatusMessage("Error processing audio. Please try again.");
      }
    };
  };

  // Helper to update UI based on backend response
  const updateUIBasedOnResponse = async (data) => {
    // Update states based on server response
    if (data.details) {
      // This is a confirmation response with PO details
      setPoDetails(data.details);
      setDetectedPO(data.po_number);
      setShowConfirmOptions(false);
      setStatusMessage(data.po_exists ? `Found PO: ${data.po_number}` : `PO ${data.po_number} not found`);
    } else if (data.show_confirm_options) {
      // This is for confirmation
      setDetectedPO(data.po_number);
      setShowConfirmOptions(true);
      setStatusMessage(`Detected: ${data.po_number}. Please say "yes" to confirm or "no" to try again.`);
    } else if (data.message === "Retry requested") {
      // This is when user said "No" via voice
      resetApp();
      setStatusMessage("Let's try again. Please record PO number.");
    } else if (data.message === "No voice recognized") {
      // This is when no voice is recognized
      setStatusMessage("I couldn't hear anything. Please try again.");
    }

    // Fetch and play AI-generated speech file
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
  const resetApp = () => {
    setDetectedPO(null);
    setShowConfirmOptions(false);
    setPoDetails(null);
    setStatusMessage("Ready to record");
    setAudioURL(null);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-4">
      <h1 className="text-2xl font-bold mb-4">PO Lookup System</h1>
      
      <div className="text-lg font-medium mb-2">{statusMessage}</div>
      
      {/* Main control buttons */}
      <AudioControls 
        isRecording={isRecording}
        startRecording={startRecording}
        stopRecording={stopRecording}
        resetApp={resetApp}
        hasData={detectedPO || poDetails}
      />

      {/* PO Details display */}
      <PODetails details={poDetails} />

      {/* Audio player */}
      <AudioPlayer url={audioURL} audioRef={audioRef} />
    </div>
  );
}

export default App;