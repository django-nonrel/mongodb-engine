def dict_keys_to_str(dictionary, recursive=False):
    return dict([(str(k), (not isinstance(v, dict) and v) or (recursive and dict_keys_to_str(v)) or v) for k,v in dictionary.items()])
