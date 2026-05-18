import pathlib
import re

def parse_test_file(path: pathlib.Path) -> list[str]:
    """Parse a SQL test file into a list of executable commands.

    Supports handling:
        - Single-line and multi-line comments
        - Dollar-quoted PL/pgSQL blocks
        - psql meta-commands
        - COPY FROM STDIN commands
        - Multi-line SQL statements ending with semicolon

    Args:
        path (Path): Path to the SQL test file.

    Returns:
        list[str]: List of commands.
    """
    text = path.read_text()
    commands = []
    buffer = []
    in_dollar = False # Flag indicating being inside the "dollar quotes"
    in_multiline_comment = False # Flag indicating being inside a multiline comment
    multiline_comment_in_command = False # Flag indicating that a multiline comment is inside the command
    lines = text.splitlines(keepends=True) # List of file lines, saving newline characters

    i = 0
    # Line-by-line parsing
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skipping empty lines out of context
        if not stripped and not buffer and not in_dollar and not in_multiline_comment:
            i += 1
            continue
        
        # Processing of psql meta-commands
        if not in_dollar and not in_multiline_comment and stripped.startswith("\\") and not (stripped.startswith("\\.")):
            if buffer:
                commands.append("".join(buffer))
                buffer = []
            commands.append(line.rstrip())
            i += 1
            continue
        
        # Processing single-line comments
        if not in_dollar and not in_multiline_comment and stripped.startswith("--"):
            # If the comment is inside the command
            if buffer:
                buffer.append(line)
                i += 1
                continue
            
            commands.append(line)
            i += 1
            continue
        
        # Processing multiline comments
        if not in_dollar:
            if in_multiline_comment:
                buffer.append(line)
                if "*/" in line:
                    in_multiline_comment = False
                    if not multiline_comment_in_command:
                        commands.append("".join(buffer))
                        buffer = []
                    else: # In the case where the comment was inside the command, don't include it as a separate command
                        multiline_comment_in_command = False
                i += 1
                continue
            elif stripped.startswith("/*"):
                if buffer:
                    multiline_comment_in_command = True
                in_multiline_comment = True
                buffer.append(line)
                if "*/" in line:
                    in_multiline_comment = False
                    if not multiline_comment_in_command:
                        commands.append("".join(buffer))
                        buffer = []
                    else:
                        multiline_comment_in_command = False
                i += 1
                continue
        
        # Processing strings where "dollar" quotes are detected
        if not in_dollar and not in_multiline_comment:
            matches = list(re.finditer(r"(\$\w*\$)", line)) # Looking for all the places in the string containing "dollar" quotes
            if matches:
                in_dollar = matches[0].group(1) # Take the first "dollar" quotation mark found
                buffer.append(line)
                rest_of_line = line[matches[0].end():] # Take the rest of the string after the first found "dollar" quotation mark
                # If find another "dollar" quotation mark (closing) in the rest of the line, then add the entire line as a command
                if (re.search(rf"{re.escape(in_dollar)}", rest_of_line) is not None):
                    commands.append("".join(buffer))
                    buffer = []
                    in_dollar = False
                i += 1
                continue

        # Processing the continuation of "dollar" blocks
        if in_dollar:
            buffer.append(line)
            # If find a closing "dollar" quotation mark, then add the entire block from the buffer as a command
            if (re.search(rf"{re.escape(in_dollar)}", line) is not None):
                commands.append("".join(buffer))
                buffer = []
                in_dollar = False
            i += 1
            continue
        
        # Processing SQL commands
        buffer.append(line)
        # If the command is COPY FROM STDIN, then such a command is guaranteed not to be one-line and must read the following line
        if not (line.lower().startswith("copy") and ("from stdin" in line.lower())):
            # Check for the end characters of the command: "\." means the end of the COPY FROM STDIN command, ";" means the end of other SQL commands
            if ("\\." in line) or (';' in line):
                commands.append("".join(buffer))
                buffer = []
        i += 1
    
    # Adding the remainder to the commands
    if buffer:
        commands.append("".join(buffer))

    return [cmd.rstrip() for cmd in commands if cmd.strip()] # Return a list of non-empty commands without trailing spaces and "\n"