import os
import requests
import configparser
import re
from datetime import datetime

import API.ApiTokenUpdater

SevenBitBarcodes = []

# Configs to handle Authentication Error
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
        'APIClientID': api_client_id,
        'APISecret': api_secret,
        'APIToken': config['API credentials'].get('APIToken', ''),
        'EndpointUrl': config['API URLS'].get('APIEndpointUrl', '')
    }

    return current_configs

def generate_urls(base_url, report_id, barcodes, batch_size):
    urls = []
    total_barcodes = len(barcodes)
    config = configparser.RawConfigParser()
    config.read('Configs/UserSettings.ini')
    library = config['Conditions'].get('Library', '')
    department = config['Conditions'].get('Department', '')
    
    for i in range(0, total_barcodes, batch_size):
        url = f'{base_url}?report_id={report_id}&param1={library}&param2={department}&param3={barcodes[i]}'
        
        for j in range(1, batch_size):
            if i + j < total_barcodes:
                url += '\n{}'.format(barcodes[i + j])
        
        urls.append(url)
    
    return urls

def dataRequest(url, APIToken):
    headerVar = {'Content-Type': 'application/json', 'Authorization': f'Bearer {APIToken}'}
    #print("Sending Request")
    try:
        response = requests.get(url, headers=headerVar)
        
        if response.status_code == 200:
            json_data = response.json()
            print(json_data)
            return json_data
        else:
            print("Auhtentication error, updating token")
            API.ApiTokenUpdater.token_update_status = "Yhteys Kohaan ei välttämättä toimi, käynnistä ohjelma uudelleen."
            API.ApiTokenUpdater.updateToken(configs=read_config())
            API.ApiTokenUpdater.token_update_status = "Yhteys Kohaan ei välttämättä toimi, käynnistä ohjelma uudelleen."
            return {"error": f"Failed: {response.status_code} - {response.text}"}
    
    except Exception as e:
        return {"error": f"Error: {str(e)}"}
    

def format_library_data(data):
    # Initialize the ConfigParser
    config = configparser.RawConfigParser()
    config.read('Configs/UserSettings.ini')

    tableConfig = configparser.RawConfigParser()
    tableConfig.read('Configs/config.ini')


    # Get the comma-separated branches from the config file and convert them to a list
    homebranches = config['Library'].get('text', '')
    currentbranches = config['Library'].get('text2', '')
    departments = config['Department'].get('text', '')
    
    # Split the branches into a list and strip any extra spaces
    libraryBranches = [branch.strip() for branch in homebranches.split(',')]
    currentlibrary = [currentbranch.strip() for currentbranch in currentbranches.split(',')]

    departments = [department.strip() for department in departments.split(',')]


    # Get special states from config
    collectAllEnabled = config['Conditions'].getboolean('collectall', False)
    check_item_lost = config['Conditions'].getboolean('CheckItemLost', False)
    check_on_loan = config['Conditions'].getboolean('CheckOnLoan', False)
    notforloan = config['Conditions'].getboolean('NotForLoan', False)

    callnumberEnabled = config['Callnumber'].getboolean('enabled', False)
    callNumberIncluded = config['Callnumber'].getboolean('option1', False)
    callNumberNotIncluded = config['Callnumber'].getboolean('option2', False)
    callnumberValue = config['Callnumber'].get('text', '')

    departmentEnabled = config['Department'].getboolean('enabled', False)
    departmentIncluded = config['Department'].getboolean('option1', False)
    departmentNotIncluded = config['Department'].getboolean('option2', False)

    countEnabled = config['Count'].getboolean('enabled', False)
    countHigher = config['Count'].getboolean('option1', False)
    countLower = config['Count'].getboolean('option2', False)
    countValue = config['Count'].get('text', '')
    countWholeKoha = config['Count'].getboolean('option3', False)
    countLibrary = config['Count'].getboolean('option4', False)
    countDepartment = config['Count'].getboolean('option5', False)

    libraryEnabled = config['Library'].getboolean('enabled', False)
    libraryIncluded = config['Library'].getboolean('option1', False)
    libraryNotIncluded = config['Library'].getboolean('option2', False)
    currentLibraryIncluded = config['Library'].getboolean('option3', False)
    currentLibraryNotIncluded = config['Library'].getboolean('option4', False)
    
    loanEnabled = config['Loan'].getboolean('enabled', False)
    loanAfter = config['Loan'].getboolean('option1', False)
    loanBefore = config['Loan'].getboolean('option2', False)
    loanValue = config['Loan'].get('text', '')
    
    collectionEnabled = config['Collection'].getboolean('enabled', False)
    collectionIncluded = config['Collection'].getboolean('option1', False)
    collectionNotIncluded = config['Collection'].getboolean('option2', False)
    collectionNoValue = config['Collection'].getboolean('option3', False)
    collectionAnyValue = config['Collection'].getboolean('option4', False)
    collectionValue = config['Collection'].get('text', '')

    barcodeEnabled = config['Barcode'].getboolean('enabled', False)
    barcodeValue = config['Barcode'].get('text', '')

    foundEnabled = config['Found'].getboolean('enabled', False)
    inTransport = config['Found'].getboolean('option1', False)
    inWaitings = config['Found'].getboolean('option2', False)
    inProcessing = config['Found'].getboolean('option3', False)
    foundEquals = config['Found'].getboolean('option4', False)
    foundNotEquals = config['Found'].getboolean('option5', False)
    
    listsEnabled = config.getboolean('Lists', 'enabled', fallback=False)
    enabled_lists_str = config.get('Lists', 'text', fallback='')
    enabled_lists = [lst.strip() for lst in enabled_lists_str.split(',') if lst.strip()]

    merged_data = []

    field_mappings = tableConfig['jsonMap']

    # Return an empty list if no data is provided
    if not data:
        return merged_data
    
    all_list_barcodes = {}  # barcode -> set of list_names
    if listsEnabled and enabled_lists:
        for list_name in enabled_lists:
            list_path = os.path.join("Lists", list_name)
            if os.path.exists(list_path):
                try:
                    with open(list_path, 'r') as f:
                        for line in f:
                            barcode = line.strip().upper()
                            if barcode:
                                if barcode not in all_list_barcodes:
                                    all_list_barcodes[barcode] = set()
                                all_list_barcodes[barcode].add(list_name)
                except Exception as e:
                    print(f"Error loading list {list_name}: {str(e)}")

    # Loop through the data and merge items based on conditions
    for item in data:
        merged_item = {}
        
        

        # Dynamically populate merged_item based on field mappings
        for merged_key, data_key in field_mappings.items():
            merged_item[merged_key] = item.get(data_key, '')
        
        # Custom formatting for title if it exists
        if 'title' in merged_item and merged_item['title'] != 'N/A' and len(merged_item['title']) > 45:
            merged_item['title'] = merged_item['title'][:45] + '...'

        merged_item['itemlost'] = item.get('itemlost', 0) != 0
        merged_item['onloan'] = item.get('onloan') is not None

        # Adding flags based on conditions
        merged_item['flags'] = []


        # Apply the conditions based on the UserSettings file
        append_item = False
        
        item_barcode = item.get('barcode', '').upper()
        if listsEnabled and item_barcode in all_list_barcodes:
            append_item = True
            list_names = ', '.join(sorted(all_list_barcodes[item_barcode]))
            merged_item['flags'].append(f'Lista: {list_names}')

        if collectAllEnabled:
            append_item = True

        if check_item_lost and item.get('itemlost', 0) == 1:
            append_item = True
            merged_item['flags'].append('Kadonnut')

        if check_on_loan and item.get('onloan') is not None:
            append_item = True
            merged_item['flags'].append('Lainassa')

        if notforloan and item.get('notforloan') != '0':
            append_item = True
            merged_item['flags'].append('Ei lainata')

        if foundEnabled:
            if foundEquals:
                if inTransport and item.get('found') == 'T':
                    append_item = True
                    merged_item['flags'].append('Kuljetus')
                if inWaitings and item.get('found') == 'W':
                    append_item = True
                    merged_item['flags'].append('Noudettava varaus')
                if inProcessing and item.get('found') == 'P':
                    append_item = True
                    merged_item['flags'].append('Käsittely')
            elif foundNotEquals:
                if inTransport and item.get('found') != 'T':
                    append_item = True
                    merged_item['flags'].append('Ei kuljetuksessa')
                if inWaitings and item.get('found') != 'W':
                    append_item = True
                    merged_item['flags'].append('Ei noudettava varaus')
                if inProcessing and item.get('found') != 'P':
                    append_item = True
                    merged_item['flags'].append('Ei käsittelyssä')
        
        if callnumberEnabled:
            numeric_part_match = re.search(r'\d+(\.\d+)?', item.get('itemcallnumber', ''))
            if numeric_part_match:
                # Extract numeric parts as strings
                callnumber_numeric_str = numeric_part_match.group(0)
                placeholder_numeric_str = str(callnumberValue)
                
                if callNumberIncluded:
                    # Check if item call number starts with the input call number (up to its length)
                    if callnumber_numeric_str.startswith(placeholder_numeric_str):
                        append_item = True
                        merged_item['flags'].append('Luokka')
                
                elif callNumberNotIncluded:
                    # Check if item call number does not start with the input call number (up to its length)
                    if not callnumber_numeric_str.startswith(placeholder_numeric_str):
                        append_item = True
                        merged_item['flags'].append('Luokka')

        if departmentEnabled and departmentIncluded:

            # Check if the item's department matches any department in the list
            if any(item.get('permanent_location', '') == department.strip() for department in departments):
                append_item = True
                merged_item['flags'].append('Osasto')

        if departmentEnabled and departmentNotIncluded:

            # Exclude items that match any department in the list
            if all(item.get('permanent_location', '') != department.strip() for department in departments):
                append_item = True
                merged_item['flags'].append('Osasto')
                
        if countEnabled:
            if isinstance(countValue, int):
                if countHigher:
                    if countWholeKoha:
                        if item.get('NiteetYht') is not None and item.get('NiteetYht') > int(countValue):
                            append_item = True
                            merged_item['flags'].append('Määrä')
                    if countLibrary:
                        if item.get('NiteetHylly') is not None and item.get('NiteetHylly') > int(countValue):
                            append_item = True
                            merged_item['flags'].append('Määrä')
                    if countDepartment:
                        if item.get('NiteetOsastolla') is not None and item.get('NiteetOsastolla') > int(countValue):
                            append_item = True
                            merged_item['flags'].append('Määrä')
                if countLower:
                    if countWholeKoha:
                        if item.get('NiteetYht') is not None and item.get('NiteetYht') < int(countValue):
                            append_item = True
                            merged_item['flags'].append('Määrä')
                    if countLibrary:
                        if item.get('NiteetHylly') is not None and item.get('NiteetHylly') < int(countValue):
                            append_item = True
                            merged_item['flags'].append('Määrä')
                    if countDepartment:
                        if item.get('NiteetOsastolla') is not None and item.get('NiteetOsastolla') < int(countValue):
                            append_item = True
                            merged_item['flags'].append('Määrä')
        
        if libraryEnabled and libraryIncluded:
            if any(item.get('homebranch', '').startswith(branch) for branch in libraryBranches):
                append_item = True
                merged_item['flags'].append('Kirjasto')

        if libraryEnabled and libraryNotIncluded:
            if all(not item.get('homebranch', '').startswith(branch) for branch in libraryBranches):
                append_item = True
                merged_item['flags'].append('Kirjasto')

        if libraryEnabled and currentLibraryIncluded:
            if any(item.get('holdingbranch', '').startswith(currentbranch) for currentbranch in currentlibrary):
                append_item = True
                merged_item['flags'].append('Sijantikirjasto')

        if libraryEnabled and currentLibraryNotIncluded:
            if all(not item.get('holdingbranch','').startswith(currentbranch) for currentbranch in currentlibrary):
                append_item = True
                merged_item['flags'].append('Sijaintikirjasto')
                
        if loanEnabled and loanValue:
            # Attempt to parse loanValue in both YYYY-MM-DD and YYYY.MM.DD formats
            try:
                loan_date = datetime.strptime(loanValue, '%Y-%m-%d')
            except ValueError:
                try:
                    loan_date = datetime.strptime(loanValue, '%Y.%m.%d')
                except ValueError:
                    loan_date = None  # Set loan_date to None if neither format works

            item_loan_date_str = item.get('datelastborrowed', '')

            if loan_date and item_loan_date_str:
                try:
                    # Parse item loan date if available
                    item_loan_date = datetime.strptime(item_loan_date_str, '%Y-%m-%d')

                    if loanAfter and item_loan_date < loan_date:
                        append_item = True
                        merged_item['flags'].append('LainaPVM')

                    if loanBefore and item_loan_date > loan_date:
                        append_item = True
                        merged_item['flags'].append('LainaPVM')
                except ValueError:
                    pass  # If item_loan_date_str is invalid, ignore it
                    
        if collectionEnabled and collectionIncluded:
            if item.get('ccode') == collectionValue:
                append_item = True
                merged_item['flags'].append('Kokoelma')

        if collectionEnabled and collectionNotIncluded:
            if item.get('ccode') != collectionValue:
                append_item = True
                merged_item['flags'].append('Kokoelma')
                
        if collectionEnabled and collectionNoValue:
            if item.get('ccode') == None:
                append_item = True
                merged_item['flags'].append('Kokoelma')
                
        if collectionEnabled and collectionAnyValue:
            if item.get('ccode') != None:
                append_item = True
                merged_item['flags'].append('Kokoelma')

        #Matches Koha barcode, not actual
        if barcodeEnabled:
            if item.get('barcode').upper() == barcodeValue.upper():
                append_item = True
                merged_item['flags'].append('Viivakoodi')

        item_barcode = item.get('barcode')
        item_barcode = item_barcode.upper()
        if item_barcode and item_barcode in SevenBitBarcodes:
            append_item = True
            merged_item['flags'].append('SevenBit')
            remove_sevenbit_barcode()

        # Append the item if any of the conditions matched
        if append_item:
            merged_item['flags'] = ', '.join(merged_item['flags']) 
            merged_data.append(merged_item)

        # New barcode list check
        
    print(f"Merged data: {merged_data}")
    return merged_data

# Function to remove a barcode from SevenBitBarcodes
def remove_sevenbit_barcode():
    SevenBitBarcodes.clear()

def requestProcessor(urls, APIToken):
    all_merged_data = []

    for url in urls:
        result = dataRequest(url, APIToken)
        #result = [] #debugging data entry
        
        if isinstance(result, list):
            merged_data = format_library_data(result)
            all_merged_data.extend(merged_data)
        else:
            print(result.get("error"))  # Handle or log the error

    return all_merged_data


