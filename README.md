# Ai-Traffic-System

A real-time AI-powered traffic monitoring system that detects vehicles, identifies traffic signal colors directly from video feeds, and flags red-light violations automatically.

Traffic Eye TensorFlow.js License

Features

Three Input Modes: Simulation, Live Camera, Upload Video
AI Vehicle Detection: Real-time detection using COCO-SSD (TensorFlow.js)
Signal Color Identification: Automatically detects RED / GREEN / YELLOW from video by analyzing RGB pixels of the detected traffic light region
Red Light Violation Tracking: Flags vehicles crossing the detection line during red signal
Vehicle Classification: Categorizes into Car, Bike/Cycle, Truck, Bus
Speed Analysis: Tracks average, max, and min speeds
Detection Confidence: Shows real-time AI confidence scores
Violation Log: Timestamped log of all red-light violations
Live Dashboard: Charts, stats, and analytics updating in real-time
Manual Fallback: Double-click to manually mark traffic light if AI misses it
How It Works

Signal Detection from Video

COCO-SSD detects the traffic light object in the video frame
The bounding box region is cropped and pixel-level RGB analysis is performed
Each pixel is classified:
RED: R > 130, G < 100, B < 100
GREEN: G > 120, R < 100, B < 110
YELLOW: R > 140, G > 100, B < 70
Position bonus is applied (red = top, yellow = middle, green = bottom of traffic light)
The dominant color becomes the detected signal state
If COCO-SSD doesn't find the traffic light, user can double-click to manually mark it
Vehicle Tracking

Centroid-based tracking across frames
Vehicles crossing the detection line are counted
If signal is RED during crossing, violation is recorded
Tech Stack

Layer	Technology
Frontend	HTML5, Tailwind CSS, JavaScript
AI Model	TensorFlow.js + COCO-SSD (lite_mobilenet_v2)
Charts	Chart.js
Server	Flask (Python)
Icons	Font Awesome 6
Project Structure

traffic-eye/ ├── app.py ├── index.html ├── requirements.txt ├── .gitignore ├── LICENSE └── README.md



## Setup & Run

### Prerequisites
- Python 3.8+ installed
- Modern browser (Chrome/Edge recommended)

### Steps

```bash
git clone https://github.com/54nitinjat/Ai-Traffic-System
cd traffic-eye
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
Open http://localhost:5000 in your browser.

Without Python

Open index.html directly in any modern browser. No server required for basic functionality.

 Camera access requires serving from localhost or https. Direct file open may block camera in some browsers.

Usage

Simulation Mode

Opens by default. Vehicles auto-spawn, auto-detect, signal auto-cycles.

Live Camera Mode

Click Start Camera, point at a road with traffic signal. AI detects vehicles and identifies signal color automatically.

Upload Video Mode

Click Choose Video, select a traffic video. AI detects traffic light and reads its color. If AI misses it, double-click on it to mark manually.

Signal Detection Priority

PRIORITY
METHOD
DESCRIPTION
1st	AI Detected	COCO-SSD finds traffic light, auto pixel analysis
2nd	Manual Mark	User double-clicks to mark the region
3rd	Not Visible	No traffic light found in frame
 
Known Limitations

 COCO-SSD lite model may miss small or distant traffic lights
 Pixel-based color analysis works best when traffic light is clearly visible
 Night mode or low-light conditions may reduce detection accuracy
 Speed values in camera/video mode are estimated
Future Improvements

 YOLOv8 integration for better accuracy
 Night vision enhancement
 Number plate recognition (ANPR)
 Multi-camera support
 Database integration for violation records
License

MIT License — see LICENSE file for details.

Made by

Nitin Kumar
