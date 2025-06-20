# CrisisAid - News and Awareness Website

CrisisAid is a real-time crisis awareness platform built to inform, support, and mobilize action during humanitarian emergencies across the globe.

This full-stack web application aggregates live crisis news using web scraping and public APIs, and visualizes them on an interactive world map using Leaflet.js. Each crisis is geo-tagged, filtered by country, and linked with verified donation sources to encourage timely aid.

In addition to providing situational updates, the platform features a newsletter subscription, country-based filters, and an intuitive UI for engagement. The backend, powered by FastAPI and Flask, supports scalable API endpoints and handles real-time data updates.

### Tech stack:
  Flask, FastAPI, Uvicorn, SQLite, HTML, CSS, JavaScript, Leaflet.js

###💡 **Key Features**:

🔄 Real-time crisis news aggregation

🌍 Interactive world map with geo-tagged popups

✅ Verified donation links for direct relief

📨 Country filter & newsletter subscription

⚙️ SQLite backend with FastAPI and Flask APIs

🧠 Designed with scalability and impact in mind


### 🔧 Setup Steps

1. 📥 **Clone the repository** :
    ```bash
    git clone https://github.com/iam-salma/CrisisAid-news-and-awareness-website.git
    cd CrisisAid-news-and-awareness-website
    ```

2. 🐍 **Make sure you have Python 3 installed.** :

   Here’s the official link to install Python 3:
    🔗 https://www.python.org/downloads/
   
4. 📦 **Create a virtual environment** :
    ```bash
    python -m venv venv
    ```
   
5. ⚙️ **Activate the virtual environment**

   On Windows :
      ```bash
      .\venv\Scripts\activate
      ```
    On macOS/Linux :
      ```bash
      source venv/bin/activate
      ```

7. 📌 **Install dependencies** :
    ```bash
    pip install -r requirements.txt
    ```

8. 🗝️ **Create .env folder to store secrets** :

     refer the .env.example for reference

9. **📂 Create an instance/ folder** :

     create a **news.db** file in the folder
  
10. **To Run the Project**:
   ```bash
   python main.py
   ```

ENJOY 😊🎉
