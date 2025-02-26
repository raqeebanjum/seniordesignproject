# Senior Design Project

## Installation Guide

### Windows Setup

1. **Install Docker Desktop**
   - Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
   - Run the installer
   - Follow the installation wizard
   - Restart your computer if prompted
   - Start Docker Desktop and wait for it to fully initialize (whale icon in taskbar becomes steady)



2. **Start the Application**
   - Double-click `start-windows.bat`
      - If you get a warning from windows, click `Run anyway`
   - Wait for the application to initialize
   - The script will automatically:
     - Check if Docker is running
     - Build the application
     - Start the application
   - Open your browser and go to http://localhost:5001
   - Note: Will take a few minutes to build application the first time
   - Note: Might have to run as admin and if you see firewall popups, click allow

### Mac Setup

1. **Install Docker Desktop**
   - Download [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
   - Open the downloaded .dmg file
   - Drag Docker to Applications folder
   - Start Docker Desktop from Applications
   - Wait for Docker to fully initialize (whale icon in menu bar becomes steady)

2. **Start the Application**
   - Open Terminal
   - Navigate to the application folder:
     ```zsh
     cd path/to/SENIORDESIGNPROJECT
     ```
   - Make the start script executable (first time only):
     ```zsh
     chmod +x start.sh
     ```
   - If you have permission issues, run this Command
      ```zsh
     sudo chmod +x start.sh
     ```
   - Run the application:
     ```zsh
     ./start.sh
     ```

   - The script will automatically:
   - Open your browser and go to http://localhost:5001
