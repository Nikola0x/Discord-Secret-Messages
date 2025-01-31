import sys
import json
import requests
import hashlib
import os
from datetime import datetime
from cryptography.fernet import Fernet
from typing import Optional, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QLineEdit, 
    QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, QStyle, 
    QSystemTrayIcon, QMenu, QCheckBox, QProgressBar, QFrame
)
from PyQt5.QtCore import QTimer, Qt, QSettings, pyqtSignal, QObject
from PyQt5.QtGui import QIcon, QPalette, QColor, QFont
# You dont need this, it is better to turn this off, if you want to see extra logs you can enable it :)
# logging.basicConfig(
#     filename='discord_monitor.log',
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )

@dataclass
class ConnectionConfig:
   
    api_url: str = "http://localhost:8000" # replace with your API URL, it will be on port 8000 since that is what the backend is configurated.
    ping_interval: int = 15000  # 15 seconds
    max_retries: int = 3 # How many times it retries before it gives up
    timeout: int = 5 # How long it waits for a response from the server before it gives up

class StyleConfig:
    
    DARK_THEME = """
    QMainWindow {
        background-color: #1a1b1e;
    }
    QWidget {
        background-color: #1a1b1e;
        color: #ffffff;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    QLabel {
        color: #ffffff;
        font-size: 13px;
        padding: 6px;
    }
    QPushButton {
        background-color: #7289da;
        border: none;
        color: white;
        padding: 10px 20px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #5b6eae;
    }
    QPushButton:pressed {
        background-color: #4e5d94;
    }
    QPushButton:disabled {
        background-color: #4a4a4a;
        color: #7a7a7a;
    }
    QLineEdit {
        background-color: #2c2f33;
        border: 2px solid #40444b;
        color: white;
        padding: 10px;
        border-radius: 6px;
        font-size: 13px;
    }
    QLineEdit:focus {
        border: 2px solid #7289da;
    }
    QProgressBar {
        border: 2px solid #7289da;
        border-radius: 6px;
        text-align: center;
        color: white;
        background-color: #2c2f33;
        height: 20px;
    }
    QProgressBar::chunk {
        background-color: #7289da;
        border-radius: 4px;
    }
    QFrame#statusFrame {
        border: 2px solid #40444b;
        border-radius: 8px;
        padding: 15px;
        background-color: #2c2f33;
    }
    QCheckBox {
        color: #ffffff;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid #7289da;
    }
    QCheckBox::indicator:checked {
        background-color: #7289da;
    }
    """

class ConnectionStatus:
 
    DISCONNECTED = "⚫ Not active"
    CONNECTING = "🟡 Connecting..."
    CONNECTED = "🟢 Active"
    ERROR = "🔴 Error"

class CryptoHandler:

    def __init__(self, key_file: str = "config.key"):
        self.key_file = key_file
        self._ensure_key_directory()
        self.key = self._initialize_key()
        self.cipher_suite = Fernet(self.key)

    def _ensure_key_directory(self) -> None:

        try:
            directory = os.path.dirname(os.path.abspath(self.key_file))
            if not os.path.exists(directory):
                os.makedirs(directory, mode=0o700)  
        except Exception as e:
            logging.error(f"Failed to create key directory: {e}")
            raise RuntimeError(f"Could not create key directory: {e}")

    def _initialize_key(self) -> bytes:
 
        try:
            if os.path.exists(self.key_file):
           
                try:
                    with open(self.key_file, "rb") as key_file:
                        existing_key = key_file.read().strip()
                        if self._is_valid_key(existing_key):
                            return existing_key
                except Exception as e:
                    logging.warning(f"Existing key file corrupted, creating new: {e}")

            return self._generate_new_key()

        except Exception as e:
            logging.error(f"Critical error initializing encryption key: {e}")
            raise RuntimeError(f"Failed to initialize encryption key: {e}")

    def _generate_new_key(self) -> bytes:
 
        try:
            key = Fernet.generate_key()
            
            if os.name == 'posix':  
                os.umask(0o077)  
            
            with open(self.key_file, "wb") as key_file:
                key_file.write(key)
            
            if os.name == 'nt':
                import win32security
                import ntsecuritycon as con
                
                security = win32security.GetFileSecurity(
                    self.key_file, 
                    win32security.OWNER_SECURITY_INFORMATION
                )
                user = security.GetSecurityDescriptorOwner()
                
                dacl = win32security.ACL()
                dacl.AddAccessAllowedAce(
                    win32security.ACL_REVISION,
                    con.FILE_ALL_ACCESS,
                    user
                )
                
                security.SetSecurityDescriptorDacl(1, dacl, 0)
                win32security.SetFileSecurity(
                    self.key_file, 
                    win32security.DACL_SECURITY_INFORMATION,
                    security
                )

            logging.info("Generated and saved new encryption key")
            return key

        except Exception as e:
            logging.error(f"Failed to generate new key: {e}")
            raise RuntimeError(f"Could not generate new encryption key: {e}")

    def _is_valid_key(self, key: bytes) -> bool:
        
        try:
            Fernet(key)
            return True
        except Exception:
            return False

    def encrypt(self, data: str) -> str:
  
        try:
            return self.cipher_suite.encrypt(data.encode()).decode()
        except Exception as e:
            logging.error(f"Encryption error: {e}")
            raise RuntimeError(f"Encryption failed: {e}")

    def decrypt(self, encrypted_data: str) -> str:

        try:
            return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
           
            return ""

class ApiClient:

    def __init__(self, config: ConnectionConfig):
        self.config = config

    def send_ping(self, api_key: str, user_id: str) -> requests.Response:
        headers = {
            "X-API-Key": api_key,
            "User-Agent": "Discord-Monitor/1.0"
        }
        try:
            response = requests.post(
                f"{self.config.api_url}/ping/{user_id}",
                headers=headers,
                timeout=self.config.timeout
            )
            return response
        except requests.RequestException as e:
            logging.error(f"API request error: {e}")
            raise

class SettingsManager:

    def __init__(self, crypto_handler: CryptoHandler):
        self.settings = QSettings("DiscordClient", "Settings")
        self.crypto = crypto_handler

    def save_credentials(self, api_key: str, user_id: str):
        try:
            self.settings.setValue("api_key", self.crypto.encrypt(api_key))
            self.settings.setValue("user_id", self.crypto.encrypt(user_id))
            self.settings.setValue("remember_credentials", True)
        except Exception as e:
            logging.error(f"Error saving credentials: {e}")
            raise

    def load_credentials(self) -> tuple[str, str, bool]:
        try:
            remember = self.settings.value("remember_credentials", False, type=bool)
            if remember:
                api_key = self.crypto.decrypt(self.settings.value("api_key", ""))
                user_id = self.crypto.decrypt(self.settings.value("user_id", ""))
                return api_key, user_id, True
            return "", "", False
        except Exception as e:
            logging.error(f"Error loading credentials: {e}")
            return "", "", False

    def clear_settings(self):
        self.settings.clear()

class ClientApp(QMainWindow):
  
    def __init__(self):
        super().__init__()
        self.config = ConnectionConfig()
        self.crypto = CryptoHandler()
        self.settings_manager = SettingsManager(self.crypto)
        self.api_client = ApiClient(self.config)
        
        self.init_ui()
        self.setup_tray()
        self.load_saved_settings()
        
        self.ping_timer = QTimer()
        self.ping_timer.timeout.connect(self.send_ping)
        
        self.retry_count = 0
        self.is_connected = False
        self.successful_pings = 0

    def init_ui(self):
        
        self.setWindowTitle("Nikola Security")
        self.setGeometry(100, 100, 450, 550)
        self.setStyleSheet(StyleConfig.DARK_THEME)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(20)
        
        self._setup_title_section(layout)
        
        self._setup_credentials_section(layout)
        
        self._setup_status_section(layout)
        
        self._setup_buttons_section(layout)
        
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)

    def _setup_title_section(self, layout: QVBoxLayout):
        title_label = QLabel("Nikola Security")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

    def _setup_credentials_section(self, layout: QVBoxLayout):
        credentials_frame = QFrame()
        credentials_frame.setObjectName("statusFrame")
        credentials_layout = QVBoxLayout(credentials_frame)
        
        api_key_layout = QVBoxLayout()
        self.api_key_label = QLabel("API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        api_key_layout.addWidget(self.api_key_label)
        api_key_layout.addWidget(self.api_key_input)
        credentials_layout.addLayout(api_key_layout)
        
        user_id_layout = QVBoxLayout()
        self.user_id_label = QLabel("User ID:")
        self.user_id_input = QLineEdit()
        user_id_layout.addWidget(self.user_id_label)
        user_id_layout.addWidget(self.user_id_input)
        credentials_layout.addLayout(user_id_layout)
        
        self.remember_checkbox = QCheckBox("Remember Data")
        credentials_layout.addWidget(self.remember_checkbox)
        
        layout.addWidget(credentials_frame)

    def _setup_status_section(self, layout: QVBoxLayout):
        status_frame = QFrame()
        status_frame.setObjectName("statusFrame")
        status_layout = QVBoxLayout(status_frame)
        
        self.status_label = QLabel(ConnectionStatus.DISCONNECTED)
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)
        
        self.ping_progress = QProgressBar()
        self.ping_progress.setMaximum(15)
        self.ping_progress.setValue(15)
        status_layout.addWidget(self.ping_progress)
        
        self.ping_counter_label = QLabel("Successful pings: 0")
        self.ping_counter_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.ping_counter_label)
        
        layout.addWidget(status_frame)

    def _setup_buttons_section(self, layout: QVBoxLayout):
        button_layout = QHBoxLayout()
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.start_connection)
        button_layout.addWidget(self.connect_button)
        
        self.minimize_button = QPushButton("Minimize")
        self.minimize_button.clicked.connect(self.hide)
        button_layout.addWidget(self.minimize_button)
        
        layout.addLayout(button_layout)

    def setup_tray(self):
       
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("Close")
        quit_action.triggered.connect(self.cleanup_and_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def load_saved_settings(self):
       
        api_key, user_id, remember = self.settings_manager.load_credentials()
        if remember:
            self.api_key_input.setText(api_key)
            self.user_id_input.setText(user_id)
            self.remember_checkbox.setChecked(True)

    def start_connection(self):
      
        if not self.is_connected:
            self._initiate_connection()
        else:
            self.disconnect()

    def _initiate_connection(self):

        api_key = self.api_key_input.text()
        user_id = self.user_id_input.text()
        
        if not api_key or not user_id:
            QMessageBox.warning(self, "Error", "Please enter API key and User ID.")
            return
        
        self.status_label.setText(ConnectionStatus.CONNECTING)
        try:
            response = self.api_client.send_ping(api_key, user_id)
            if response.status_code == 200:
                self.connect_success()
            else:
                self.handle_connection_error(f"HTTP {response.status_code}")
        except Exception as e:
            self.handle_connection_error(str(e))

    def connect_success(self):
       
        self.is_connected = True
        self.connect_button.setText("End connection")
        self.status_label.setText(ConnectionStatus.CONNECTED)
        self.ping_timer.start(self.config.ping_interval)
        self.progress_timer.start(1000)
        
        self._disable_input_fields()
        
        if self.remember_checkbox.isChecked():
            self.settings_manager.save_credentials(
                self.api_key_input.text(),
                self.user_id_input.text()
            )
        
        self.tray_icon.showMessage(
            "Nikola security",
            "successfully connected!",
            QSystemTrayIcon.Information,
            2000
        )

    def _disable_input_fields(self):
        
        self.api_key_input.setEnabled(False)
        self.user_id_input.setEnabled(False)
        self.remember_checkbox.setEnabled(False)

    def disconnect(self):
      
        self.ping_timer.stop()
        self.progress_timer.stop()
        self.is_connected = False
        self.connect_button.setText("Connect")
        self.status_label.setText(ConnectionStatus.DISCONNECTED)
        self.retry_count = 0
        self.successful_pings = 0
        self.ping_counter_label.setText("Successful pings: 0")
        self.ping_progress.setValue(15)
        
        self.api_key_input.setEnabled(True)
        self.user_id_input.setEnabled(True)
        self.remember_checkbox.setEnabled(True)
        
        logging.info("Application disconnected successfully")
    
    def send_ping(self) -> None:
       
        try:
            response = self.api_client.send_ping(
                self.api_key_input.text(),
                self.user_id_input.text()
            )
            
            if response.status_code == 200:
                self._handle_successful_ping()
            else:
                self._handle_failed_ping(f"HTTP {response.status_code}")
                
        except requests.RequestException as e:
            self._handle_failed_ping(f"Network error: {str(e)}")
        except Exception as e:
            self._handle_failed_ping(f"Unexpected error: {str(e)}")
            

    def _handle_successful_ping(self) -> None:

        self.successful_pings += 1
        self.ping_counter_label.setText(f"Successful pings: {self.successful_pings}")
        self.retry_count = 0
        self.ping_progress.setValue(15)
        self.status_label.setText(ConnectionStatus.CONNECTED)
        logging.info(f"Successful ping - Total: {self.successful_pings}")


    def _handle_failed_ping(self, error_msg: str) -> None:
       
        self.status_label.setText(ConnectionStatus.ERROR)
        self.retry_count += 1
        logging.warning(f"Ping failed - Attempt {self.retry_count}/{self.config.max_retries}: {error_msg}")

        if self.retry_count >= self.config.max_retries:
            self._handle_max_retries_exceeded(error_msg)
        else:
            self._show_retry_warning(error_msg)

    def _handle_max_retries_exceeded(self, error_msg: str) -> None:
     
        self.disconnect()
        QMessageBox.critical(
            self,
            "Error",
            f"Your connection ended after {self.config.max_retries} tries.\n: {error_msg}"
        )
        logging.error(f"Connection terminated after max retries: {error_msg}")




    def _show_retry_warning(self, error_msg: str) -> None:
        """Display warning message for retry attempts"""
        QMessageBox.warning(
            self,
            "Warning",
            f"Try {self.retry_count}/{self.config.max_retries}\nError: {error_msg}"
        )

    def update_progress(self) -> None:
     
        try:
            current_value = self.ping_progress.value()
            if current_value > 0:
                self.ping_progress.setValue(current_value - 1)
        except Exception as e:
            logging.error(f"Error updating progress: {e}")

    def cleanup_and_quit(self) -> None:
      
        try:
            if self.is_connected:
                self.disconnect()
            
            if self.remember_checkbox.isChecked():
                self.settings_manager.save_credentials(
                    self.api_key_input.text(),
                    self.user_id_input.text()
                )
            
            logging.info("Application shutting down normally")
            QApplication.quit()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            QApplication.quit()

    def closeEvent(self, event) -> None:
  
        try:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Nikola Security",
                "Application is minimised in the tray",
                QSystemTrayIcon.Information,
                2000
            )
        except Exception as e:
            logging.error(f"Error handling close event: {e}")

    def tray_icon_activated(self, reason) -> None:
      
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()

def main():

    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        sys.excepthook = lambda type, value, traceback: logging.error(
            f"Uncaught exception: {str(value)}",
            exc_info=(type, value, traceback)
        )
        
        client = ClientApp()
        client.show()
        
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"Fatal error during application startup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
        