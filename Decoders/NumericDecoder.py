def hex_to_decimal(hex_str, length_byte, start_index):
    """Convert a hex string to a string of decimal digits by processing 4-bit segments."""
    # Extract the length of encoded data based on the third byte
    third_byte = hex_str[length_byte:length_byte+2]
    num_bytes_to_take = int(third_byte, 16)
    
    # Extract the relevant hex string
    end_index = start_index + num_bytes_to_take * 2  # Multiply by 2 since each byte is 2 hex characters
    extracted_hex = hex_str[start_index:end_index]
    
    # Convert hex string to binary string
    binary = bin(int(extracted_hex, 16))[2:].zfill(num_bytes_to_take * 8)  # Pad with zeros if needed
    
    # Process 4 bits at a time to get decimal digits
    decimal_digits = ""
    for i in range(0, len(binary), 4):
        four_bits = binary[i:i+4]
        if four_bits:  # Ensure we don't process empty strings
            digit = int(four_bits, 2)  # Convert 4-bit binary to decimal (0-15)
            decimal_digits += str(digit)
    
    return decimal_digits

def numericDecoder(hex_input, length_byte, start_index):
    """Main function to decode a given hex string into a string of decimal digits."""
    try:
        decimal_value = hex_to_decimal(hex_input, length_byte, start_index)
        return decimal_value
    except ValueError:
        return None

if __name__ == "__main__":
    hex_input = "04A1000607800116607F0201E0030632408E05CB7F14010B050110"
    hex_input = hex_input.replace(" ", "")
    
    # Decode the hex string and print the result
    decoded_integer = numericDecoder(hex_input, 6, 8)
    if decoded_integer is not None:
        print(f"Decimal Digits: {decoded_integer}")