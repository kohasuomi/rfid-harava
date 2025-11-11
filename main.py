import configparser
import API.ApiTokenUpdater as ApiTokenUpdater
import os
import API.ApiRequests as ApiRequests
from API.ApiRequests import SevenBitBarcodes

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QRunnable, QThreadPool, Slot, Signal, QObject
from GUI.UI import MainWindow 

import sys
import threading

import Decoders.IsoDecoder as IsoDecoder
import Decoders.IntegerDecoder as IntegerDecoder
import Decoders.NumericDecoder as NumericDecoder
import Decoders.SevenBitDecoder as SevenBitDecoder

import DataHandling.Messagesplitter as Messagesplitter

from Decoders.FINDecoder import FINDecoder

from Communication.ReaderCommunication import communicate_with_server, restart_communication

import logging
from logging.handlers import TimedRotatingFileHandler

from datetime import datetime
import time
from API.ApiTokenUpdater import updateToken

import queue

# For debugging without RFID scanner
# Barcodes listed one per line, no separator character
barcodesArray = []
barcodes = barcodesArray
EncodedData = []
# Raw data from RFID scanner as continious hexstring
RawResponses = []

def read_config():
    config = configparser.RawConfigParser()
    config.read('Configs/config.ini', encoding='utf-8')

    # Get the credential source (config or env)
    credential_source = config['API'].get('CredentialSource', 'config').lower()

    # Read API credentials based on the source
    if credential_source == 'env':
        api_client_id = os.getenv('APIClientID', '')
        api_secret = os.getenv('APISecret', '')
    else:  # Default to config file
        api_client_id = config['API'].get('Client', '')
        api_secret = config['API'].get('Secret', '')

    current_configs = {
        'app_name': config['Info'].get('AppName', ''),
        'version': config['Info'].get('Version', ''),
        'APIClientID': api_client_id,
        'APISecret': api_secret,
        'APIToken': config['API credentials'].get('APIToken', ''),
        'EndpointUrl': config['API URLS'].get('APIEndpointUrl', ''),
        'ReporterApiUrl': config['API URLS'].get('ReporterAPIUrl', ''),
        'ReportID': config['Other'].get('ReportID', ''),
        'BatchSize': int(config['Other'].get('BatchSize', 15)),
        'UpdateRate': int(config['Other'].get('UpdateRate', 0.1)),
        'HaravaIP': config['Harava'].get('IP', ''),
        'HaravaPort': int(config['Harava'].get('Port', 10001)),
        'CommunicationRate': float(config['Harava'].get('CommunicationRate', 0.15))
    }

    return current_configs

data_queue = queue.Queue()

class DataFetcher(threading.Thread):
    def __init__(self, urls, api_token, data_queue):
        super().__init__()
        self.urls = urls
        self.api_token = api_token
        self.data_queue = data_queue

    def run(self):
        # Fetch data in the background
        merged_data = ApiRequests.requestProcessor(self.urls, self.api_token)
        self.data_queue.put(merged_data)



def main_loop():
    class ExcludeFilter(logging.Filter):
        def filter(self, record):
            # Exclude messages that contain "APISecret", "APIClientID", or "APIToken"
            excluded_terms = ["APISecret", "APIClientID", "APIToken"]
            message = record.getMessage()
            return not any(term in message for term in excluded_terms)

    logger = logging.getLogger('my_logger')
    logger.setLevel(logging.DEBUG)  # Capture all levels of logging

    # Ensure the 'log' folder exists, create it if not
    log_directory = 'logs'
    os.makedirs(log_directory, exist_ok=True)

    # Generate log file name with date suffix
    log_filename = os.path.join(log_directory, f"output_{datetime.now().strftime('%Y-%m-%d')}.log")

    # Create file handler that rotates every day
    file_handler = TimedRotatingFileHandler(
        filename=log_filename,  # Log files will be stored in 'logs' folder
        when='midnight',
        interval=1,
        backupCount=96,  
        encoding='utf-8',
        delay=False,
        utc=False
    )
    file_handler.setLevel(logging.DEBUG)

    # Customize the log file name with date in the suffix
    file_handler.suffix = "%Y-%m-%d.log"
    # Create a console handler for logging to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Set a format for the logs
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    file_handler.addFilter(ExcludeFilter())

    # Add both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Redirect prints to the logger as INFO level
    class PrintLogger:
        def write(self, message):
            if message.strip():  # Avoid logging empty lines
                logger.debug(message.strip())
        def flush(self):  # Required method for file-like object
            pass

    # Redirect sys.stdout to the PrintLogger to catch crash logs
    sys.stdout = PrintLogger()

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow program to exit gracefully if interrupted by the user
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        for handler in logger.handlers:
            handler.flush()
        # Exit the program after logging the critical error
        sys.exit(1)

    # Set the global exception handler to our function
    sys.excepthook = handle_exception

    logger.debug("SEPARATOR BETWEEN LOGS")
    #logger.debug("This is a debug message.")
    #logger.debug("This is an info message.")
    #logger.error("This is an error message.")

    def handle_server_response(formatted_response):
        global RawResponses
        RawResponses.append(formatted_response)
        logger.debug(f"Appended to RawResponses: {formatted_response}")

    configs = read_config()
    logger.debug(configs)

    # Open connection for client to send over barcodes
    server_ip = configs['HaravaIP']
    server_port = configs['HaravaPort']
    com_rate = configs['CommunicationRate']
    
    # Store the listener thread and its parameters
    listener_thread = None

    def start_listener():
        nonlocal listener_thread
        # Fetch the latest config to get the server_ip
        configs = read_config()
        server_ip = configs['HaravaIP']
        logger.debug(f"Starting listener with server_ip: {server_ip}")
        
        if server_ip: 
            logger.debug(f"Creating new listener thread for IP: {server_ip}")
            listener_thread = threading.Thread(
                target=communicate_with_server, 
                args=(
                    server_ip, 
                    server_port,
                    handle_server_response,  # Pass the callback
                    0.1,  # Delay between sending commands
                    com_rate  # Communication rate
                )
            )
            listener_thread.daemon = True  # Allows thread to exit when main program exits
            listener_thread.start()
            logger.debug(f"Listener thread started for IP: {server_ip}")
        else:
            logger.debug("Invalid IP address (0.0.0.0 or empty), skipping thread start")
            listener_thread = None  # Ensure thread is None if not started

    def restart_listener():
        nonlocal listener_thread
        logger.debug("Attempting to restart listener thread")
        
        # Signal the communication to stop
        logger.debug("Calling restart_communication to stop existing thread")
        restart_communication()  # Ensure this properly signals the thread to stop
        
        # Wait for the thread to exit if it exists
        if listener_thread is not None and listener_thread.is_alive():
            logger.debug("Joining existing listener thread")
            listener_thread.join(timeout=5.0)  # Wait up to 2 seconds
            if listener_thread.is_alive():
                logger.warning("Listener thread did not terminate within timeout")
            else:
                logger.debug("Existing listener thread terminated")
        
        # Always clear the thread reference before starting a new one
        listener_thread = None
        
        # Start a new listener thread with the latest config
        logger.debug("Calling start_listener to create new thread")
        start_listener()
        logger.debug("Listener thread restart process completed")

    # Start the initial listener thread
    logger.debug("Initializing listener thread")
    start_listener()

    ApiTokenUpdater.updateToken(configs)
    configs = read_config()

    # Start the QApplication
    app = QApplication(sys.argv)
    window = MainWindow()

    # Expose restart_listener to the window for UI integration
    window.restart_listener = restart_listener
    
    def update_config_on_shutdown():
        """Updates the config file with the last shutdown timestamp."""
        config = configparser.RawConfigParser()
        config.read('Configs/config.ini', encoding='utf-8')
        
        # Ensure the [Info] section exists
        if 'Harava' not in config:
            config['Harava'] = {}
        
        config['Harava']['ip'] = "0"
        
        # Write the updated config back to the file
        with open('Configs/config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        logger.debug("Reset HaravaIp")

    # Connect the shutdown hook to the aboutToQuit signal
    app.aboutToQuit.connect(update_config_on_shutdown)

    def token_needs_update():
        config = configparser.RawConfigParser()
        config.read('Configs/config.ini', encoding='utf-8')

        try:
            last_updated_str = config['API credentials'].get('APITokenLastUpdated', '').strip()
            
            if not last_updated_str:
                logger.debug("APITokenLastUpdated missing or empty — assuming token needs update.")
                return True  # If missing or empty, force update

            last_updated = int(last_updated_str)
            token_age = int(time.time()) - last_updated

            if token_age > 1500:
                logger.debug(f"Token expired (age: {token_age}s) — needs update.")
                return True
            else:
                logger.debug(f"Token still valid (age: {token_age}s).")
                return False

        except (ValueError, KeyError) as e:
            logger.warning(f"Error reading token timestamp: {e} — forcing token update.")
            return True

    def token_update_loop():
        logger.debug("Token update loop")
        configs = read_config()
        while True:
            if token_needs_update():
                updateToken(configs)
            time.sleep(60)  # Wait for 60s before checking again

    # Start the token update loop in a separate thread
    token_thread = threading.Thread(target=token_update_loop)
    token_thread.daemon = True  # Allows program to exit even if thread is running
    token_thread.start()
    

    # Setup QThreadPool
    thread_pool = QThreadPool()

    def handle_data(merged_data):
        # Populate the new data into the table
        window.add_items_to_table(window.table, merged_data)

    def fetch_data():
        global barcodes
        global RawResponses
        global EncodedData

        logger.debug(f"Barcodes available before processing: {len(barcodes)}") if len(barcodes) != 0 else None

        # Process if there are new unprocessed responses from the scanner
        if RawResponses:
            raw_response_string = ''.join(RawResponses)
            batch = [raw_response_string]
            RawResponses = []
            for response in batch:
                EncodedData.extend(Messagesplitter.split_and_process(response))
                logger.debug(f"EncodedData after processing: {EncodedData}")

        # Process each encoded data item
        for encoded in EncodedData:  
            # Check the starting bytes of data to route it to correct decoder
            if not isinstance(encoded, str):
                logger.warning(f"Skipping non-string encoded item: {encoded}")
                continue

            if encoded.startswith('04110100') or encoded.startswith('04110101') or encoded.startswith("04110001"):
                hex_string = encoded
                # Remove first byte as it is part of RFID scanners communication, not from data itself
                hex_string = hex_string[2:]
                decoder = FINDecoder(hex_string)  # Create an instance of FINDecoder
                barcode = decoder.decode()
                logger.debug(f"Decoded FIN Barcode: {barcode}")
                barcode = barcode.upper()
                # Append the decoded barcode to the barcodes array
                barcodes.append(barcode)

            # 6Bit decoder
            elif encoded.startswith('04c1') or encoded.startswith('0441'):
                # Locked Tag
                if encoded.startswith('04c1'):
                    hex_string = encoded
                    lenght_byte = 6
                    start_index = 8
                    decodedData = IsoDecoder.isoDecoder(hex_string, lenght_byte, start_index)
                    barcode = decodedData
                    logger.debug(f"Decoded ISO Barcode (locked) 6bit: {barcode}")
                    barcode = barcode.upper()
                    barcodes.append(barcode)
                
                # Unlocked Tag
                elif encoded.startswith('0441'):
                    hex_string = encoded
                    lenght_byte = 4
                    start_index = 6
                    decodedData = IsoDecoder.isoDecoder(hex_string, lenght_byte, start_index)
                    barcode = decodedData
                    logger.debug(f"Decoded ISO Barcode (unlocked) 6bit: {barcode}")
                    barcode = barcode.upper()
                    barcodes.append(barcode)
            
            # Integer decoder
            elif encoded.startswith('0491') or encoded.startswith('0411'):
                # Locked Tag
                if encoded.startswith('0491'):
                    hex_string = encoded
                    lenght_byte = 6
                    start_index = 8
                    decodedData = IntegerDecoder.integerDecoder(hex_string, lenght_byte, start_index)
                    barcode = decodedData
                    logger.debug(f"Decoded ISO Barcode (locked) int: {barcode}")
                    barcode = barcode.upper()
                    barcodes.append(barcode)
                    
                # Unlocked Tag
                if encoded.startswith('0411'):
                    hex_string = encoded
                    lenght_byte = 4
                    start_index = 6
                    decodedData = IntegerDecoder.integerDecoder(hex_string, lenght_byte, start_index)
                    barcode = decodedData
                    logger.debug(f"Decoded ISO Barcode (unlocked) int: {barcode}")
                    barcode = barcode.upper()
                    barcodes.append(barcode)
                    
            elif encoded.startswith('04a1') or encoded.startswith('0421'):
                # Locked Tag
                if encoded.startswith('04a1'):
                    hex_string = encoded
                    lenght_byte = 6
                    start_index = 8
                    decodedData = NumericDecoder.numericDecoder(hex_string, lenght_byte, start_index)
                    barcode = decodedData
                    logger.debug(f"Decoded ISO Barcode (locked) num: {barcode}")
                    barcode = barcode.upper()
                    barcodes.append(barcode)
                    
                # Unlocked Tag
                if encoded.startswith('0421'):
                    hex_string = encoded
                    lenght_byte = 4
                    start_index = 6
                    decodedData = NumericDecoder.numericDecoder(hex_string, lenght_byte, start_index)
                    barcode = decodedData
                    logger.debug(f"Decoded ISO Barcode (unlocked) num: {barcode}")
                    barcode = barcode.upper()
                    barcodes.append(barcode)
                    
            elif encoded.startswith('04d1') or encoded.startswith('0451'):
                # Locked Tag
                if encoded.startswith('04d1'):
                    hex_string = encoded
                    lenght_byte = 6
                    start_index = 8
                    decodedData = SevenBitDecoder.decode7Bit(hex_string, lenght_byte, start_index)
                    barcode = decodedData
                    logger.debug(f"Decoded ISO Barcode (locked) 7bit : {barcode}")
                    barcode = barcode.upper()
                    barcodes.append(barcode)
                    
                # Unlocked Tag
                if encoded.startswith('0451'):
                    hex_string = encoded
                    lenght_byte = 4
                    start_index = 6
                    decodedData = SevenBitDecoder.decode7Bit(hex_string, lenght_byte, start_index)
                    barcode = decodedData
                    logger.debug(f"Decoded ISO Barcode (unlocked) 7bit : {barcode}")
                    barcode = barcode.upper()
                    barcodes.append(barcode)

            # Detect RFID tags that have no written data
            elif encoded.startswith('0400000000000000'):
                logger.debug("NULL")
                nullData = {
                    'title': "RIFFAAMATON TAGI || TOIMITA NIDE RIFFATTAVAKSI",
                    'homebranch': "",
                    'itemnumber': "",
                    'biblionumber': "",
                    'itemlost_flag': "",
                    'onloan_flag': "",
                    'homebranch_flag': "",
                    'callnumber': "",
                    'deleted_on': "",
                    'barcode': "000000000000",
                    'permanent_location': "",
                    'found': "",
                    'department_count': "",
                    'shelf_count': "",
                    'total_count': ""
                }
                handle_data([nullData])

        # Clear EncodedData after processing to avoid duplicates
        EncodedData.clear()
        EncodedData = barcodes.copy()

        # Form API request urls if there are any barcodes decoded
        if len(barcodes) > 0:
            batch_size = min(len(barcodes), configs['BatchSize'])
            batch = barcodes[:batch_size]
            barcodes = barcodes[batch_size:]

            urls = ApiRequests.generate_urls(
                configs['ReporterApiUrl'],
                configs['ReportID'],
                batch,
                batch_size
            )

            # Start the DataFetcher thread with data_queue for communication
            fetcher = DataFetcher(urls, configs['APIToken'], data_queue)
            fetcher.start()
        else:
            pass

    def update_ui_from_queue():
        # Check if there is data in the queue
        while not data_queue.empty():
            merged_data = data_queue.get()
            window.add_items_to_table(window.table, merged_data)

    # Timer to periodically call fetch_data()
    data_timer = QTimer()
    data_timer.timeout.connect(fetch_data)
    data_timer.start(configs['UpdateRate'])

    # Timer to periodically check the queue and update the UI
    ui_update_timer = QTimer()
    ui_update_timer.timeout.connect(update_ui_from_queue)
    ui_update_timer.start(100)  # Update frequency ms
    
    def reload_configs():
        nonlocal configs
        new_configs = read_config()
        
        # Only log if changes detected (optional but helpful)
        if new_configs != configs:
            configs = new_configs

    config_reload_timer = QTimer()
    config_reload_timer.timeout.connect(reload_configs)
    config_reload_timer.start(5000)
    
    
    # Show the window
    window.show()

    # Execute the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main_loop()