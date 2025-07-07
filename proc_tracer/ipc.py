# proc_tracer/ipc.py

import socket
import json


class TCPClient:
    def __init__(self, host="127.0.0.1", port=9090):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self) -> bool:
        """
        Connect to the TCP server at the specified host and port.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")
            return True
        except ConnectionRefusedError:
            print(f"The server at {self.host}:{self.port} is not running.")
            self.socket = None
            return False
        except Exception as e:
            print(f"An error occurred while connecting: {e}")
            self.socket = None
            return False

    def send_data(self, data_dict: dict) -> None:
        """
        Send a dictionary as a JSON string to the server.
        """
        if self.socket is None:
            print("Socket is not connected. Cannot send data.")
            return

        try:
            json_data = json.dumps(data_dict) + "\n"
            self.socket.sendall(json_data.encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError):
            print("Connection lost. Attempting to reconnect...")
            self.connect()
            self.send_data(data_dict)
        except Exception as e:
            print(f"An error occurred while sending data: {e}")

    def close(self) -> None:
        """
        Close the socket connection.
        """
        if self.socket:
            try:
                self.socket.close()
                print("Connection closed.")
            except Exception as e:
                print(f"An error occurred while closing the socket: {e}")
            finally:
                self.socket = None
