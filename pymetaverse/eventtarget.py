class EventTarget:
    def __init__(self):
        self._listeners = {}
    
    def on(self, event, func = None):
        if not event in self._listeners:
            self._listeners[event] = []
        
        def _(func):
            self._listeners[event].append(func)
            return func
        
        if func:
            return _(func)
        return _
    
    def off(self, event, func):
        if event in self._listeners:
            self._listeners[event].remove(func)
    
    def fire(self, event, *args, **kwargs):
        if event in self._listeners:
            for func in self._listeners[event]:
                func(*args, **kwargs)