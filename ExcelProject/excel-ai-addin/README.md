# AI Analyst Excel Add-in (MVP)

This project is a modern, web-based Excel add-in that uses AI to analyze data. It is structured as a commercial-ready MVP with a separate frontend (the Excel task pane) and backend (a local Python server).

## Project Structure

- **`backend/`**: Contains the core Python logic for data analysis and interacting with GPT.
  - `gpt_agent.py`: Manages calls to the OpenAI API.
  - `code_executor.py`: Executes the AI-generated Python code.
  - `data_utils.py`: Provides helper functions for cleaning data.
- **`assets/`**: Contains icons for the add-in.
- **`server.py`**: A Flask web server that acts as the API backend. It receives requests from the Excel frontend, uses the backend logic to process them, and returns the result.
- **`manifest.xml`**: The configuration file that defines the add-in for Microsoft Excel, including the custom ribbon button.
- **`taskpane.html`**: The HTML structure for the sidebar that opens in Excel.
- **`taskpane.css`**: The CSS for styling the task pane.
- **`taskpane.js`**: The core JavaScript logic for the frontend. It handles user interaction, gets data from the sheet, calls the backend API, and displays the result.
- **`requirements.txt`**: A list of all required Python packages.
- **`.gitignore`**: Specifies files that should be ignored by version control.
- **`commands.html`**: A required, but currently empty, file for the add-in manifest.


## How to Run the MVP

This MVP requires two servers to be running simultaneously: a Python server for the backend (HTTPS) and a simple HTTPS server for the frontend. No ngrok is needed.

### **Step 1: Run the Backend Server**

This server runs the Python and AI logic.

1.  Navigate to the `excel-ai-addin` directory in your terminal.
2.  Make sure your virtual environment is activated: `source ../.venv/bin/activate`
3.  Generate a self-signed certificate if you don't have one:
    ```bash
    cd excel-ai-addin
    openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes
    ```
4.  Start the Flask server (serves HTTPS on 5001 automatically when `server.pem` is present):
    ```bash
    python server.py
    ```
5.  This server will start on `https://localhost:5001`. Leave this terminal window open.

### **Step 2: Run the Frontend HTTPS Server**

Excel requires add-ins to be served over HTTPS for security.

1.  Open a **new, separate terminal window**.
2.  Navigate to the `excel-ai-addin` directory.
3.  We will use a simple Python command to start a secure HTTPS server. First, you may need to generate a self-signed certificate:
    ```bash
    openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes
    ```
    (You can press Enter for all the questions it asks).
4.  Now, start the HTTPS server on port 3000:
    ```bash
    python -m http.server --certfile server.pem 3000
    ```
5.  Leave this second terminal window open.

### **Step 3: Sideload the Add-in in Excel**

1.  Open Excel.
2.  Go to the menu **`Tools` > `Excel Add-ins...`**.
3.  Click on the **`Developer`** tab at the bottom.
4.  Click **`Add from File...`**.
5.  Navigate to your `excel-ai-addin` folder and select the **`manifest.xml`** file.
   - The manifest points to `https://localhost:3000` for the taskpane and `https://localhost:5001` for the API calls via JavaScript.
6.  A new **`Run AI Analysis`** button will appear on your `Home` ribbon tab.

### **Step 4: Use the Add-in**

1.  Click the **`Run AI Analysis`** button on the `Home` tab.
2.  The add-in sidebar will open. If you see a security warning about the certificate, you may need to click "trust" or "proceed".
3.  Select data in your spreadsheet.
4.  Type a prompt into the input box in the sidebar.
5.  Click the **"Run Analysis"** button in the sidebar.

The result from your local Python server will appear in the sidebar or as a chart in your sheet.

## License
MIT
