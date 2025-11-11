#Integer Decoder
def hex_to_bitstring(hex_str, lenght_byte, start_index):
    """Convert a hex string to a bitstring based on the third byte."""
    
    # Extract the lenght of encoded data based on datamodel
    data_lenght = hex_str[lenght_byte:lenght_byte+2]
    
    num_bytes_to_take = int(data_lenght, 16)
    
    # Extracting encoded data based on the lenght
    end_index = start_index + num_bytes_to_take * 2  # Multiply by 2 since each byte is 2 hex characters
    extracted_hex = hex_str[start_index:end_index]
    
    # Convert hex to integer, then to binary, remove the '0b' prefix
    bitstring = bin(int(extracted_hex, 16))[2:]  # Convert to binary
    bitstring = bitstring.zfill(num_bytes_to_take * 8)  # Ensure length matches num_bytes_to_take * 8
    
    return bitstring

def DecodeInteger(bitstring):
    """Convert the entire bitstring to an integer."""
    return int(bitstring, 2)

def integerDecoder(hex_input, lenght_byte, start_index):
    """Main function to decode a given hex string into a concatenated number string."""
    bitstring = hex_to_bitstring(hex_input, lenght_byte, start_index)
    
    if bitstring is None:
        return None
    
    number = DecodeInteger(bitstring)
    return str(number)

if __name__ == "__main__":
    hex_input = "041110619F0CD7BFB770201A80501106702424103063240BE3E8B0F"
    hex_input = hex_input.replace(" ","")
    
    # Decode the hex string and print the result
    decoded_string = integerDecoder(hex_input, 4, 6)
    if decoded_string:
        print(f"ISO 646 Character String: {decoded_string}")
