import { useState, useRef } from 'react';

function App() {
  // states to check if recording is in progress
  const [isRecording, setIsRecording] = useState(false);
  // reference to mediarecorder instance
  const mediaRecorderRef = useRef(null);
  // reference to audio chunks
  const audioChunksRef = useRef([]);

  // function to start recording
  const startRecording = () => {
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        mediaRecorderRef.current = new MediaRecorder(stream);
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
    mediaRecorderRef.current.onstop = () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.wav');

      console.log('Sending audio to backend...');
      // send the audio blob to the backend
      fetch('http://localhost:5000/upload', {
        method: 'POST',
        body: formData
      });
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
    </div>
  );
}

export default App;