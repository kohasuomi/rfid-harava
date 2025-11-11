def hex_to_bitstring(hex_str, lenght_byte, start_index):
    """Convert a hex string to a bitstring based on the third byte"""
    
    # Extract the length of encoded data based on datamodel, in this case third byte
    third_byte = hex_str[lenght_byte:lenght_byte+2]
    
    num_bytes_to_take = int(third_byte, 16)

    
    # Extracting encoded data based on the length
    end_index = start_index + num_bytes_to_take * 2  # Multiply by 2 since each byte is 2 hex characters
    extracted_hex = hex_str[start_index:end_index]
    
    # Convert hex to integer, then to binary, remove the '0b' prefix, and pad with zeros
    bitstring = bin(int(extracted_hex, 16))[2:]  # Convert to binary
    bitstring = bitstring.zfill((len(bitstring) + 7) // 8 * 8)  # Ensure length is a multiple of 8 for data validation
    
    return bitstring

def decode_7bit(bitstring):
    """Process the bitstring into 7-bit segments, add a leading 0 to make 8-bit segments."""
    segments = [bitstring[i:i+7] for i in range(0, len(bitstring), 7)]  # Split into 7-bit segments
    modified_segments = []
    
    for segment in segments:
        if len(segment) == 7:  # Only process complete 7-bit segments
            modified_segments.append('0' + segment)  # Add leading 0 to make 8 bits
    
    # Check if the last segment is '01111111' and discard it if true
    if modified_segments and modified_segments[-1] == '01111111':
        modified_segments.pop()
    
    return modified_segments  # Return as a list of 8-bit segments

def bits_to_ascii(segments):
    """Convert a list of 8-bit segments to ASCII characters and filter out non-alphanumeric."""
    ascii_string = ''
    for segment in segments:
        # Convert each 8-bit segment to an integer and then to a character
        character = chr(int(segment, 2))  # Convert binary string to an integer, then to a character
        
        # Only append the character if it's alphanumeric (letters or digits)
        if character.isalnum():
            ascii_string += character
    
    return ascii_string

def decode7Bit(hex_input, lenght_byte, start_index):
    """Main function to decode a given hex string into ASCII characters."""
    bitstring = hex_to_bitstring(hex_input, lenght_byte, start_index)
    
    if not bitstring:
        return None
    
    segments = decode_7bit(bitstring)
    
    ascii_string = bits_to_ascii(segments)
    
    return ascii_string

if __name__ == "__main__":
    hex_input = "0451464954001d000604c1020b3160532f1cb3e79df7c39880800201a80501106702001d0006"
    hex_input = hex_input.replace(" ","")
    
    # Decode the hex string and print the result
    decoded_string = decode7Bit(hex_input, 4, 6)
    if decoded_string:
        print(f"ASCII Character String: {decoded_string}")