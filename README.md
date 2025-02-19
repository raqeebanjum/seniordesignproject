# Senior Design Project

## Things to install beforehand
- Node.js
- Python3


## Frontend Setup
- cd to frontend folder, run command "npm install" and that should install all the dependencies

## Backend Setup
- cd into the backend folder and run "python3 -m venv venv" to create the virtual environment
- "source venv/bin/activate" to activate the virtual environment( Be sure you're either on mac or linux)
- After it's activated, run: "pip install -r requirements.txt" to install backend dependencies
- Make sure to install Azure Cognitive Services Speech SDK: "pip install azure-cognitiveservices-speech"
- NOTE: ignore the yellow errors for flask if you get them, idk why they won't go away

## Usage
- open a terminal and cd to the frontend folder and run "npm run dev" to start the frontend
- open another terminal and cd to the backend folder and "python3 app.py" to start the backend