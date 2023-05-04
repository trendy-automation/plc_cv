class Obj(object):
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, Obj(v) if isinstance(v, dict) else v)