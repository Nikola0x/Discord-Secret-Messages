
# Discord Secret Messages

**Discord Secret Messages** is a Discord bot that lets you manage private messages—view, add, and delete them—without exposing the content publicly. It uses a backend API to authenticate users and then securely sends the data to your Discord direct messages (DMs).  
> **Note:** Make sure to allow messages in DMs from bots for this to work properly.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Usage](#usage)
- [Commands](#commands)
- [Security Considerations](#security-considerations)
- [Future Updates](#future-updates)
- [License](#license)

---

## Overview

The bot operates by interfacing with a backend server through a secure API. When a user issues a command, the bot first checks if the user is authenticated. Once verified, the backend sends the relevant data directly to the user's DM, ensuring that messages remain private. If an unauthorized user attempts to use a command, they will receive an error message.

---

## Features

- **Private Message Management:** Add, view, and delete messages securely.
- **API-Driven:** Communicates with a backend server for data management.
- **Authentication:** Only authorized users can access certain commands.
- **User-Friendly:** Offers a simple user interface for connecting to the backend.

---

## Installation

Before getting started, ensure you have Python installed on your system. Follow the instructions below to set up both the backend and frontend components.

### Backend Setup

1. **Download and Unzip Files:**
   - Download the repository files and unzip them.

2. **Environment Configuration:**
   - Navigate to the `Backend` folder.
   - Create a file named `.env` in the `Backend` folder with the following content:
     ```dotenv
     DISCORD_TOKEN=your_discord_bot_token_here
     OWNER_ID=your_owner_id_here
     API_KEY=your_randomly_generated_api_key_here
     ```
     - **DISCORD_TOKEN:** Replace with your Discord bot token.
     - **OWNER_ID:** Replace with the Discord ID of the user who has full permissions.
     - **API_KEY:** Generate a strong, random key. This key is crucial as it is used to authenticate connections between the bot and the backend server.

3. **Install Dependencies and Run the Server:**
   - Open a terminal in the `Backend` folder and run the following commands:
     ```bash
     pip install -r requirements.txt
     python main.py
     ```
   - You should see a message indicating that the server is up and running.

### Frontend Setup

1. **Configure the Frontend:**
   - Navigate to the `Frontend` folder.
   - Open the file `client.py` in your preferred text editor.
   - Locate **line 29** (or the section where the API URL is defined) and update the `api_url` variable:
     ```python
     api_url = "http://<YOUR_SERVER_IP_OR_HOSTNAME>:8000"
     ```
     - If you are running the backend on your local machine, you can set `api_url` to `http://localhost:8000`.
     - Otherwise, replace `<YOUR_SERVER_IP_OR_HOSTNAME>` with your server's IP address or hostname (e.g., `http://178.95.208.84:8000`).

2. **Run the Client:**
   - Save your changes to `client.py` and run the file:
     ```bash
     python client.py
     ```
   - This will open a user interface (UI) for the bot.

3. **Connect the Client:**
   - In the UI, enter your Discord ID and the same API key you set in the backend `.env` file.
   - Optionally, click the button to save this data for future sessions.
   - Click **Connect**. The UI will notify you once you are successfully connected.

---

## Usage

After setting up both the backend and frontend, and ensuring that the bot is connected, you can use the following commands in your Discord server:

- `!viewadd` — Adds a message to the database. You can also specify categories.
- `!view` — Sends you a DM with all the messages you have created.
- `!viewdelete` — Deletes a message from the database. **Important:** You need to provide the unique randomized key associated with the message to delete it.

---

## Security Considerations

- **Authentication:** Only authenticated users (using the API key and Discord ID) can interact with the bot’s sensitive commands.
- **API Key:** Ensure that your API key is strong and kept secret. Regularly update it as needed.
- **Private Communication:** The bot sends data directly to your DMs, ensuring that no one else in the server can view your messages.
- **Continuous Updates:** The project will continue to receive updates to enhance security, performance, and add additional features.

---

## Future Updates

The project is under active development. Future updates will focus on:
- Enhanced security measures.
- Performance improvements.
- Additional features and commands to improve usability.

---


*If you have any questions or run into issues, please open an issue in the GitHub repository.*

Happy coding!
