import binascii
import string

class FINDecoder:
    
    def __init__(self, hex_string):
        # Ensure hex_string is valid hex and has an even length
        if not self.is_valid_hex(hex_string):
            print(f"Skipping invalid hex string: {hex_string}")
            self.data = None
            return
        
        self.data = binascii.unhexlify(hex_string)
        self.index = 0

    @staticmethod
    def is_valid_hex(hex_string):
        """Check if the hex string is valid (even length and valid hex characters)."""
        return all(c in string.hexdigits for c in hex_string) and len(hex_string) % 2 == 0

    def read_bytes(self, length):
        if self.data is None:
            return None
        
        result = self.data[self.index:self.index + length]
        self.index += length
        return result

    def decode_utf8_string(self, bytes_data):
        """Decodes a byte string, ignoring non-ASCII characters."""
        if bytes_data is None:
            return ""  # Return empty if no data to decode
        return bytes_data.decode('ascii', errors='ignore')

    def decode_numeric(self, length):
        raw_bytes = self.read_bytes(length)
        if raw_bytes is None:
            return 0  # Return 0 if no data to decode
        return int.from_bytes(raw_bytes, 'big')

    def decode_crc(self):
        return self.decode_numeric(2)

    def decode_data_block(self):
        block_length = self.decode_numeric(1)
        block_id = self.decode_numeric(2)
        checksum = self.decode_numeric(1)
        return f"Block Length: {block_length}, Block ID: {block_id}, Checksum: {checksum}"

    def decode_variable_length_string(self, max_length):
        """Reads up to max_length bytes until a null byte is encountered."""
        if self.data is None:
            return ""
        
        # Collect bytes until null byte or max_length
        collected_bytes = bytearray()
        bytes_read = 0
        
        while bytes_read < max_length and self.index < len(self.data):
            current_byte = self.data[self.index]
            if current_byte == 0x00:
                self.index += 1
                break
            collected_bytes.append(current_byte)
            self.index += 1
            bytes_read += 1
        
        # Skip any additional null bytes
        while self.index < len(self.data) and self.data[self.index] == 0x00:
            self.index += 1
        
        return self.decode_utf8_string(collected_bytes)

    def decode(self):
        """Decode the Primary Item ID and return it."""
        # Skip the fixed prefix (11 01 01)
        if self.read_bytes(3) is None:
            return "", "0x0", ""
        
        # Read the variable-length primary item ID (up to 16 bytes)
        primary_item_id = self.decode_variable_length_string(16)
        crc = hex(self.decode_crc())
        data_block_info = self.decode_data_block()
        
        return primary_item_id # crc, data_block_info

if __name__ == "__main__":
    hex_string = "1101003835334e3036323430363030000000003850464954001d0006"
    decoder = FINDecoder(hex_string)
    primary_item_id = decoder.decode()
    #primary_item_id, crc, data_block_info = decoder.decode()


    print(f"Primary Item ID: {primary_item_id}")
    #print(f"CRC: {crc}")
    #print(f"Data Block Info: {data_block_info}")