#!/bin/bash
echo "Setting up Smart Attendance System for macOS (Apple Silicon M1/M2/M3)"

# Check if brew is installed
if ! command -v brew &> /dev/null
then
    echo "Homebrew could not be found. Please install Homebrew from https://brew.sh/"
    exit
fi

echo "Installing cmake (required for dlib on macOS)..."
brew install cmake

echo "Creating python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "Upgrading pip..."
pip3 install --upgrade pip

echo "Installing requirements..."
pip3 install -r requirements.txt

echo "Setup complete! To activate the environment, run 'source venv/bin/activate'"
echo "Then, initialize the database by running: python3 init_db.py"
echo "Finally, start the server with: python3 app.py"
