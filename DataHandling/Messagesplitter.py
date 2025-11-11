import re

# Recursive function to split hex string based on '0411' or '04c1' and ensure minimum length
def recursive_split_hex_string(hex_string):
    # Split the string by '0411', '04c1', or other patterns and keep these as separators
    parts = re.split(r'(04(?:11|c1|41|000000000000|91|11|a1|21|d1|51))', hex_string.lower())
    
    # Initialize the messages list to store the final split results
    messages = []
    current_message = ""

    i = 1  # Start from index 1 to skip the initial part before the first match
    while i < len(parts) - 1:
        # Combine the pattern (parts[i]) and the following segment (parts[i+1])
        segment = parts[i] + parts[i + 1]
        current_message += segment

        # Check if the current message has reached the minimum length of 40 characters
        if len(current_message) >= 40:
            messages.append(current_message)
            current_message = ""  # Reset current message

        # Increment by 2 to process the next pair of parts
        i += 2

    # Append any remaining message that hasn't been added, ensuring it meets the length requirement
    if current_message:
        if messages and len(messages[-1]) < 40:
            # Combine the last two messages to meet the length requirement
            messages[-1] += current_message
        else:
            # Only append if it will not be a short leftover
            if len(current_message) >= 40:
                messages.append(current_message)

    return messages

# Wrapper function to initiate the splitting process
def split_and_process(hex_string):
    # First, split the string into initial segments
    initial_split = recursive_split_hex_string(hex_string)

    # This will hold all final messages
    all_messages = []
    
    # Process each initially split message
    for message in initial_split:
        # Check if the message contains further split points (0411 or 04c1)
        further_split = recursive_split_hex_string(message)
        
        # If further splits are found, extend; otherwise, add the original message
        all_messages.extend(further_split if further_split else [message])

    print(f'Split messages: {all_messages}') if all_messages else None
    return all_messages

# Main test to run the code
if __name__ == "__main__":
    # Example hex string to test
    hex_string = "0200450022000a0002001d000604d1000dd9db0f3d6c593362c18376cc3f0201a80501106702001d000604d1000dd9db0f3d6c593362c18376cc3f0201a8050110670289ed"
    
    # Split and process the hex string
    split_and_process(hex_string)
