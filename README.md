<p align="center">
    <img width="100" height="100" alt="gitlogo" src="https://github.com/user-attachments/assets/6b06fa9b-f025-4e51-aff3-378157f8b016" alt="Crisis Aid Logo"/>
</p>

<p align="center">
  <h2><b>Crisis Aid</b> – 🌍 A humanitarian crisis news and donation platform</h2>
</p>

<p align="center">
  <a href="https://github.com/iam-salma/crisis-news-tracker/stargazers">
    <img src="https://img.shields.io/github/stars/iam-salma/crisis-news-tracker?style=social" alt="Stars"/>
  </a>
  <a href="https://github.com/iam-salma/crisis-news-tracker/fork">
    <img src="https://img.shields.io/github/forks/iam-salma/crisis-news-tracker?style=social" alt="Forks"/>
  </a>
  <a href="https://github.com/iam-salma/crisis-news-tracker/issues">
    <img src="https://img.shields.io/github/issues/iam-salma/crisis-news-tracker" alt="Issues"/>
  </a>
  <a href="https://github.com/iam-salma/crisis-news-tracker/pulls">
    <img src="https://img.shields.io/github/issues-pr/iam-salma/crisis-news-tracker" alt="Pull Requests"/>
  </a>
  <img src="https://img.shields.io/github/last-commit/iam-salma/crisis-news-tracker" alt="Last Commit"/>
</p>

CrisisAid is more than just a news site — it's your real-time window into global emergencies, designed to inform, support, and spark action when it matters most.

Built with a powerful full-stack setup, CrisisAid pulls in live crisis updates from around the world using trusted public APIs. These updates are then brought to life on an interactive world map 🌐 with geo-tagged markers, country filters, and verified donation links 💸 — so you're never just a bystander.

Whether you're tracking events, sharing updates, or looking to help, CrisisAid gives you:

🗺️ A global crisis map (thanks to Leaflet.js)

📬 A newsletter to stay in the loop

🧠 A clean and responsive UI that actually feels good to use

On the backend, it's powered by FastAPI + Flask for lightning-fast data delivery, and built to scale — just like the impact we’re aiming for.

Join us in turning awareness into action ⚡.


### 💡 Key Features:

🔄 Real-time crisis news aggregation

🌍 Interactive world map with geo-tagged popups

✅ Verified donation links for direct relief

📨 Country filter & newsletter subscription

⚙️ SQLite backend with FastAPI and Flask APIs

🧠 Designed with scalability and impact in mind



## 🔧 Setup Steps :

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

9. **📂 Delete the instance/ folder** :
    create it again and add **news.db** file in the folder
       
10. 🏃**To Run the Project**:
     ```bash
     python main.py
     ```
## 🌐 Live Demo

👉 [Click here to view the deployed website](https://crisisaid-news-and-awareness.onrender.com)

ENJOY 😊🎉
