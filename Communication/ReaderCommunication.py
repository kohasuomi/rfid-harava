import socket
import time
import select

connection_status = "Testaus"
should_stop = False
mode = 'scan'  # Default mode: 'scan' or 'AFI'
selected_command = None  # The command to send in 'AFI' mode (bytes)

# Commands used to communicate with RFID scanner in 'scan' mode
read_command = bytes([0x02, 0x00, 0x09, 0x00, 0x22, 0x00, 0xFF, 0xAB, 0xAC]) # Request data from scanner
clear_command = bytes([0x02, 0x00, 0x07, 0x00, 0x32, 0x94, 0xB8]) # Clear scanners buffer

# Commands used to change AFI-values with RFID scanner in 'AFI' mode
enable_afi_command = bytes([0x02, 0x00, 0x0A, 0xFF, 0xB0, 0x27, 0x00, 0x07, 0xAA, 0x31]) # Set AFI-value to "Checked in"
disable_afi_command = bytes([0x02, 0x00, 0x0A, 0xFF, 0xB0, 0x27, 0x00, 0xC2, 0x0B, 0xA0]) # Set AFI-value to "Checked out"

def update_status(status):
    global connection_status
    connection_status = status

def get_status():
    """Returns the current connection status."""
    global connection_status
    return connection_status

def set_communication_mode(new_mode):
    """Sets the communication mode: 'scan' or 'AFI'."""
    global mode
    if new_mode in ['scan', 'AFI']:
        mode = new_mode
    else:
        raise ValueError("Invalid mode. Must be 'scan' or 'AFI'.")

def set_selected_command(cmd):
    """Sets the selected command for 'AFI' mode (must be bytes)."""
    global selected_command
    if isinstance(cmd, bytes):
        selected_command = cmd
    else:
        raise ValueError("Command must be of type bytes.")

def restart_communication():
    """Signals the communication thread to stop for restarting."""
    global should_stop
    should_stop = True

def communicate_with_server(
    server_ip,
    server_port,
    on_response_callback,
    delay=0.1,
    timeout=0.15,  # Reduced timeout for faster disconnection detection
    buffer_size=65535,
    max_retries=1000,
    min_length=25
):
    """
    Connects to the scanner, sends commands, and logs responses based on the current mode.
    In 'scan' mode: Sends read command, processes responses, and clears buffer.
    In 'AFI' mode: Constantly sends the selected AFI command and discards any responses.
    Calls on_response_callback with the received data only in 'scan' mode.
    :param server_ip: IP address of the server
    :param server_port: Port of the server
    :param on_response_callback: Function to call with received data (used only in 'scan' mode)
    :param delay: Delay between commands
    :param timeout: Timeout for receiving data
    :param buffer_size: Buffer size for receiving responses
    :param max_retries: Maximum number of times to retry the connection if it closes
    :param min_length: Minimum length of the response to be processed in 'scan' mode
    """

    
    
    global connection_status, should_stop, mode, selected_command

    def format_hex(data):
        """Formats raw data (bytes or integers) into a single continuous hex string."""
        return ''.join(f'{item:02x}' for item in data)

    def receive_all_responses(sock):
        """Receives all available responses from the socket until timeout."""
        all_data = b""
        try:
            while True:
                response = sock.recv(buffer_size)
                if response:
                    all_data += response
                else:
                    break
        except socket.timeout:
            pass
        return all_data

    def try_reconnect(attempt):
        """Attempts to reconnect to the server."""
        update_status("Yritetään muodostaa yhteyttä")
        print(f"Attempting to reconnect ({attempt}/{max_retries})...")
        time.sleep(1)  # Delay between reconnection attempts
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect_and_communicate():
        retries = 0
        while retries < max_retries and not should_stop:
            update_status("Yritetään muodostaa yhteyttä")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            # Enable keepalive to detect disconnection faster
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            try:
                update_status("Yritetään muodostaa yhteyttä")
                sock.connect((server_ip, server_port))
                print(f"Connected to {server_ip}:{server_port}")
                update_status("Harava on yhdistetty")
                while not should_stop:
                    try:
                        if mode == 'scan':
                            # Scan mode: Send read command, wait for response, process if valid, clear buffer
                            sock.sendall(read_command)
                            time.sleep(delay)
                            ready_to_read, _, _ = select.select([sock], [], [], 0.5)
                            if ready_to_read:
                                all_responses = receive_all_responses(sock)
                                if len(all_responses) > 0:
                                    if len(all_responses) < min_length:
                                        continue
                                    formatted_response = format_hex(all_responses)
                                    print(f"Received Notification:\n{formatted_response}")
                                    # Callback with the formatted response
                                    on_response_callback(formatted_response)
                                    # Send the clear command
                                    print(f"Sending Clear Data Buffer Command (0x32).")
                                    sock.sendall(clear_command)
                                    time.sleep(delay)
                            else:
                                print("No response from server, possible disconnection detected.")
                                update_status("Yhteys haravaan katkesi")
                                break
                        elif mode == 'AFI':
                            # Command mode: Send selected command repeatedly, discard any responses
                            if selected_command is None:
                                time.sleep(0.1)
                                continue
                            sock.sendall(selected_command)
                            #print(f"Sent command {selected_command}")
                            time.sleep(delay)
                            # Read and discard any response to keep the connection healthy
                            all_responses = receive_all_responses(sock)
                            #print(f"Discarded response: {format_hex(all_responses)}") if len(all_responses) > 0 else None
                    except socket.error as e:
                        print(f"Socket error: {e}")
                        update_status("Yhteys haravaan katkesi")
                        break
            except socket.error as e:
                print(f"Failed to connect to {server_ip}:{server_port} - {e}")
                retries += 1
                if retries < max_retries:
                    update_status("Yritetään muodostaa yhteyttä")
                    sock = try_reconnect(retries)
                else:
                    print(f"Max retries reached. Could not reconnect to {server_ip}:{server_port}.")
                    update_status("Ohjelma on käynnistettävä uudelleen")
                    break
            finally:
                sock.close()
                print("Connection closed.")
                update_status("Yhteys haravaan katkesi")
        if retries >= max_retries:
            print(f"Failed to establish a connection after {max_retries} retries.")
            connection_status = "Ohjelma on käynnistettävä uudelleen"

    while not should_stop:
        connect_and_communicate()
        if should_stop:
            break
        time.sleep(1)  # Brief pause before restarting the loop
    should_stop = False  # Reset the flag after stopping