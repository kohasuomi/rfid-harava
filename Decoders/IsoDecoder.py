def hex_to_bitstring(hex_str, lenght_byte, start_index):
    """Convert a hex string to a bitstring based on the third byte"""
    
    third_byte = hex_str[lenght_byte:lenght_byte+2]
    
    num_bytes_to_take = int(third_byte, 16)
    
    # Extracting encoded data based on the lenght
    end_index = start_index + num_bytes_to_take * 2  # Multiply by 2 since each byte is 2 hex characters
    extracted_hex = hex_str[start_index:end_index]
    
    # Convert hex to integer, then to binary, remove the '0b' prefix, and pad with zeros
    bitstring = bin(int(extracted_hex, 16))[2:]  # Convert to binary
    bitstring = bitstring.zfill((len(bitstring) + 7) // 8 * 8)  # Ensure length is a multiple of 8 for data validation
    
    return bitstring


def Decode6Bit(bitstring):
    """Process the bitstring into 6-bit segments, then convert to 8-bit segments."""
    segments = [bitstring[i:i+6] for i in range(0, len(bitstring), 6)]  # Split into 6-bit segments
    modified_segments = []

    for segment in segments:
        if segment.startswith('0'):
            modified_segments.append('01' + segment)
        else:
            modified_segments.append('00' + segment)

    # Concatenate all segments into one bitstring
    final_bitstring = ''.join(modified_segments)

    # Now split the final bitstring into 8-bit segments
    eight_bit_segments = [final_bitstring[i:i+8] for i in range(0, len(final_bitstring), 8)]
    
    return eight_bit_segments  # Return as a list of 8-bit segments

def bits_to_iso_646(segments):
    """Convert a list of 8-bit segments to ISO 646 characters and filter out special characters."""
    iso_string = ''
    for segment in segments:
        # Convert each 8-bit segment to an integer and then to a character
        character = chr(int(segment, 2))  # Convert binary string to an integer, then to a character
        
        # Only append the character if it's alphanumeric (letters or digits)
        if character.isalnum():
            iso_string += character
    
    return iso_string


def isoDecoder(hex_input, lenght_byte, start_index):
    """Main function to decode a given hex string into ISO 646 characters."""
    bitstring = hex_to_bitstring(hex_input, lenght_byte, start_index)

    if bitstring is None:
        return None
    
    segments = Decode6Bit(bitstring)
    
    iso_string = bits_to_iso_646(segments)
    
    return iso_string


if __name__ == "__main__":

    hex_input = "044109DB1C4EC30D77DB5DF80201E0030632410E3E4E0F14010B050110"
    
    hex_input = hex_input.replace(" ", "")
    
    # Decode the hex string and print the result
    decoded_string = isoDecoder(hex_input, 4, 6)
    print(hex_input)
    if decoded_string:
        print(f"ISO 646 Character String: {decoded_string}")
