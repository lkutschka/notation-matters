def add_conflict_toolname(tool_name, server_name):
    tool_name_register = tool_name + "__" + server_name
    return tool_name_register

def get_conflict_toolname_original(tool_name, server_name):
    """
        {server_name}__{tool_name}
    """
    tool_name_norm = tool_name
    if tool_name.startswith(server_name):
        tool_name_norm = tool_name.split("__")[-1] if len(tool_name.split("__")) > 0 else tool_name
    return tool_name_norm
