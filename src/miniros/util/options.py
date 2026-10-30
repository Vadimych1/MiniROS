_HANDLERS_ENABLED = False

def enable_on_handlers():
    """
    Enables automatic parsing and subscribing of `on_{node}_{topic}` and `on_{anon_topic}` functions in nodes
    """
    
    global _HANDLERS_ENABLED
    _HANDLERS_ENABLED = True

def on_handlers_enabled():
    return _HANDLERS_ENABLED