import { useState, useRef } from 'react';

function App() {
  // states to check if recording is in progress
  const [isRecording, setIsRecording] = useState(false);
  // AI-generated audio URL
  const [audioURL, setAudioURL] = useState(null); 
  // reference to mediarecorder instance
  const mediaRecorderRef = useRef(null);
  // reference to audio chunks
  const audioChunksRef = useRef([]);

  // function to start recording
  const startRecording = () => {
    // Reset before starting new recording
    audioChunksRef.current = [];

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

  // function to stop recording
  const stopRecording = () => {
    mediaRecorderRef.current.stop();
    setIsRecording(false);
    
    // when the recording stops, create a blob from the audio chunks
    mediaRecorderRef.current.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      console.log('Sending audio to backend...');
      // send the audio blob to the backend
      const response = await fetch('http://localhost:5001/upload', {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      console.log("Transcript:", data.transcript);
      console.log("Detected PO:", data.po_number);

      // Fetch and play AI-generated speech file
      fetch("http://localhost:5001/get-ai-audio")
        .then((res) => res.blob())
        .then((audioBlob) => {
          const audioURL = URL.createObjectURL(audioBlob);
          setAudioURL(audioURL);
        })
        .catch((error) => console.error("Error fetching AI audio:", error));
    };
  };

  // render the button to start and stop recording
  return (
    <div className="flex items-center justify-center h-screen">
      <button 
        className="btn btn-primary"
        // toggle the recording state whenever user clicks button
        onClick={isRecording ? stopRecording : startRecording}
      >
        {isRecording ? 'Stop Recording' : 'Record'}
      </button>

      {/* Automatically play AI-generated response */}
      {audioURL && (
        <audio controls autoPlay>
          <source src={audioURL} type="audio/wav" />
          Your browser does not support the audio element.
        </audio>
      )}
    </div>
  );
}

export default App;