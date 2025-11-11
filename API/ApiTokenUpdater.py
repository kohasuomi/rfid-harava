import requests
import configparser
import time

token_update_status = ""  # Default starting status

def update_token_status(status):
    """Updates the global token update status."""
    global token_update_status
    token_update_status = status

def get_token_status():
    """Returns the current token update status."""
    global token_update_status
    return token_update_status

def updateToken(configs):
    #Endpointdata config for API token request
    endpointdata = {
    'grant_type': 'client_credentials',
    'client_id': configs['APIClientID'],
    'client_secret': configs['APISecret'],
    }
    #Default header for API token request
    endpointHeader = {
    'Content-Type': 'application/json'
    }
    #Request new API token and update it to configuration file
    update_token_status("Haetaan API-tokeni")  # Set status at the start
    NewApiToken = requestToken(configs['EndpointUrl'], endpointHeader, endpointdata)
    if NewApiToken:
        updateAPITokenInConfig(NewApiToken)
    else:
        update_token_status("Ei yhteyttä Kohaan")

#Function to request a new API token from POST endpoint using API id and secret
def requestToken(endpointUrl, endpointdata, endpointheader):
    import requests, configparser, time

    config = configparser.ConfigParser()
    config.read('Configs/config.ini', encoding='utf-8')

    try:
        response = requests.post(endpointUrl, endpointheader, endpointdata, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        update_token_status("Ei yhteyttä Kohaan")
        return None

    config['API credentials']['APITokenLastUpdated'] = str(int(time.time()))
    with open('Configs/config.ini', 'w', encoding='utf-8') as configfile:
        config.write(configfile)

    try:
        response_json = response.json()
        token = response_json.get('access_token')
        if not token:
            print("Warning: No access token in response.")
            update_token_status("Ei yhteyttä Kohaan")
            return None
    except ValueError:
        print("Response was not valid JSON.")
        update_token_status("Ei yhteyttä Kohaan")
        return None

    update_token_status("OK")
    return token


# Function to update the token in the config file
def updateAPITokenInConfig(newToken):
    config = configparser.ConfigParser()
    config.read('Configs/config.ini', encoding='utf-8')

    if 'API credentials' in config:
        config['API credentials']['APIToken'] = str(newToken)
        with open('Configs/config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    else:
        error_msg = "API tunnukset puuttuvat."
        print(error_msg)
        update_token_status(error_msg)  # Set failure status