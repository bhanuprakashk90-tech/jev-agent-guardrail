# 🚀 How to Run the Streamlit Dashboard

## Option 1: Local Machine
1. Install Python (if not installed): https://python.org
2. Open Command Prompt/PowerShell
3. Navigate to your project:
   ```bash
   cd Desktop\jev projects
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the Streamlit app:
   ```bash
   streamlit run streamlit_app.py
   ```
6. Open your browser to: http://localhost:8501

## Option 2: Replit (Recommended for Easy Sharing)
1. Zip your `jev projects` folder
2. Go to [replit.com](https://replit.com) → Sign up/Login
3. Click "+ Create" → "Upload files"
4. Upload your zipped project or extract and upload contents
5. In the Replit shell, run:
   ```bash
   pip install -r requirements.txt
   streamlit run streamlit_app.py --server.port 8080 --server.host 0.0.0.0
   ```
6. Click the "Webview" tab to see your dashboard

## Option 3: Streamlit Cloud (Free Hosting)
1. Push your project to GitHub
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Sign up and deploy your app from the GitHub repository
4. Share the public URL with your team

## Features Available:
- 🔧 **Live Configuration**: Adjust approval/rejection thresholds in real-time
- 🧪 **Test Tool Calls**: Try different tool calls with custom agent states
- 📊 **Live Monitor**: See real-time statistics and validation activity
- 📜 **Audit Log**: Review all validated calls with full details
- 📋 **Documentation**: Built-in help and integration guide

## Your Jev API Key:
Set your API key in `config.py` or `.env`:
```
your_jev_api_key_here
```

## Troubleshooting:
- **Module not found errors**: Run `pip install -r requirements.txt` again
- **Streamlit not found**: Make sure you installed the updated requirements.txt
- **Port already in use**: Try `streamlit run streamlit_app.py --server.port 8502`
- **API connection issues**: Check your internet connection and Jev API status

Enjoy monitoring your AI agent's safety with Jev! 🛡️