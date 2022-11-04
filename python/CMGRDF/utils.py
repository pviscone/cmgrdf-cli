from collections import defaultdict
import struct
from typing import Union
import copy
import hashlib
import sys
import os.path
import re

class OptionDecl(object):
    def __init__(self, name, default=None, type=str, cmdline=None, **kwargs):
        self.name = name
        self.default = default
        self.type = type
        self.cmdline = cmdline
        self.kwargs = kwargs

class Options(object):
    def __init__(self, *optionDeclarations : list[OptionDecl]):
        self._values = dict()
        self._declarations = []
        for opt in optionDeclarations:
            self.declare(opt.name,default=opt.default,type=opt.type,cmdline=opt.cmdline,**opt.kwargs)
    def declare(self,name,default=None,type=str,cmdline=None,**kwargs):
        self._declarations.append((name,default,type,cmdline,kwargs))
        if name in self._values:
            if default != None:
                raise RuntimeError("Duplicate definition of "+name)
        else:
            self._values[name] = default
        return self
    def addToParser(self,parser):
        for (name,default,type,cmdline,kwargs) in self._declarations:
            if type == bool:
                if not cmdline: cmdline = ["--no"+name] if default else ["--"+name]
                action = "store_false" if default else "store_true"
                parser.add_argument(*cmdline, dest=name, action=action, **kwargs)
            else:
                if not cmdline: cmdline = ["--"+name]
                parser.add_argument(*cmdline, dest=name, type=type, default=self._values[name], **kwargs)
    def __getattr__(self, name : str):
        return self._values[name]
    def __getitem__(self, name : str):
        return self._values[name]
    def __hasattr__(self, name : str):
        return name in self._values
    def __contains__(self, name : str):
        return name in self._values
    def __setattr__(self, name : str, value):
        if name[0] == "_" or name not in self._values:
            object.__setattr__(self, name, value)
        else:
            self._values[name] = value
    def __setitem__(self, name : str, value):
        self._values[name] = value
    def __len__(self):
        return len(self._values)
    def update(self,**kwargs):
        self._values.update(kwargs)
        return self
    def items(self):
        return self._values.items()
    def keys(self):
        return self._values.keys()
    def cloneAndUpdate(self,**kwargs):
        ret = Options()
        ret._values = dict(self._values.items())
        ret._values.update(**kwargs)
        return ret
    def cloneAndExtend(self, *optionDeclarations : list[OptionDecl]):
        ret = Options()
        ret._values = copy.copy(self._values)
        ret._declarations = copy.copy(self._declarations)
        for opt in optionDeclarations:
            self.declare(opt.name,default=opt.default,type=opt.type,cmdline=opt.cmdline,**opt.kwargs)
        return ret

class MultiKey(object):
    """A multi-field key to identify results, e.g. a histogram by its selection flow, variable name, and sample used"""
    def __init__(self, **kwargs):
        self._keys = sorted(kwargs.keys())
        self._values = dict(kwargs.items())
    def idTuple(self):
        return tuple([id(self._values[k]) for k in self._keys])
    def keys(self):
        return self._keys
    def items(self):
        return self._values.items()
    def __len__(self):
        return len(self._keys())
    def __getattr__(self, name : str):
        return self._values[name]
    def __getitem__(self, name : str):
        return self._values[name]
    def __hasattr__(self, name : str):
        return name in self._values
    def __contains__(self, name : str):
        return name in self._values
    def isSuperSet(self, other : "MultiKey"):
        """Returns true if our key is a superset of `other`, i.e. if all our fields match those of `other`,
        (but `other` may have more fields that we don't have)"""
        return all((other._values[k] == v) for k,v in self._values.items())
    def removeKeys(self, *keysToRemove : list[str]):
        """Produces a new multi-key removing the specified fields"""
        assert(all((k in self._keys) for k in keysToRemove))
        filtered = dict((k,v) for (k,v) in self.items() if k not in keysToRemove)
        return MultiKey(**filtered)
    def selectKeys(self, *keys):
        """Produces a new multi-key selecting only the specified fields"""
        assert(all((k in self._keys) for k in keys))
        filtered = dict((k,v) for (k,v) in self.items() if k in keys)
        return MultiKey(**filtered)
    def addKeys(self, **kwargs):
        """Produces a new multi-key adding the specified fields"""
        extended = copy.copy(self._values)
        for (k,v) in kwargs.items():
            assert(k not in extended)
            extended[k] = v
        return MultiKey(**extended)
    def __hash__(self):
        return hash(tuple((k,self._values[k]) for k in self._keys))
    def __eq__(self, other) -> bool:
        if other.__class__ == MultiKey:
            if self._keys != other._keys: return False
            return all(self[k] == other[k] for k in self._keys)
        return id(self) == id(other)
    def __str__(self):
        return "(%s)" % (",".join("%s=%s"%(k,self._values[k]) for k in self._keys)) 
    def __repr__(self):
        return "MultiKey(%s)" % (",".join("%s=%r"%(k,self._values[k]) for k in self._keys))

class MultiReport(object):
    """A list of pairs (multi-key, object) with some convenience methods for extracting them."""
    def __init__(self, *items):
        self._items = list(items)
        for item in items:
            assert(type(item) == tuple and isinstance(items[0],MultiKey))
    def append(self, key : MultiKey, value):
        self._items.append((key,value))
    def __len__(self):
        return len(self._items)
    def __iter__(self):
        return iter(self._items)
    def groupRemoving(self,*keys):
        """Return a map wh"""
        mergeMap = defaultdict(list)
        for k,v in self._items:
            gk = k.removeKeys(*keys)
            mergeMap[gk].append(v)
        return mergeMap.items()
    def allMatchingKey(self,key):
        """Get the subset of (key,value) pairs whose key matches all the fields in this key"""
        return [ (k,p) for (k,p) in self._items if key.isSuperSet(k) ]
    def getByKey(self,key):
        alls = self.allMatchingKey(key)
        assert(len(alls) == 1)
        return alls[0][1]

def _recursiveAddToHash(obj, hasher):
    if obj == None:
        hasher.update(b"<None>")
        return
    hasher.update(str(type(obj)).encode())
    if type(obj) == str:
        hasher.update(obj.encode())
    elif type(obj) == bool:
        hasher.update(b"1" if obj else b"0")
    elif type(obj) == int:
        hasher.update(obj.to_bytes(8,sys.byteorder))
    elif type(obj) == float:
        hasher.update(struct.pack("d",obj))
    elif isinstance(obj,(list,tuple)):
        _recursiveAddToHash(len(obj),hasher)
        for e in obj: _recursiveAddToHash(e,hasher)
    elif isinstance(obj,set):
        _recursiveAddToHash(len(obj),hasher)
        for e in sorted(obj): _recursiveAddToHash(e,hasher)
    elif isinstance(obj,dict):
        _recursiveAddToHash(len(obj),hasher)
        for k,v in sorted(obj.items()): 
            _recursiveAddToHash(k,hasher)
            _recursiveAddToHash(v,hasher)
    else:
        raise RuntimeError("Don't know how to hash %r of type %s" % (obj,type(obj)))

def safeName(obj):
    return re.sub("[^A-Za-z0-9_]", "", obj.name)

def recursiveHash(*objs):
    hasher = hashlib.sha256()
    for obj in objs:
        _recursiveAddToHash(obj, hasher)
    return hasher.hexdigest()

def localOrEOS(dir,localroot,eosroot,eosurl="root://eoscms.cern.ch/"):
    localPath = os.path.join(localroot,dir)
    if os.path.isdir(localPath):
        return localPath
    if not eosroot.startswith("root://"):
        eosroot = eosurl + eosroot
    return os.path.join(eosroot,dir)

class NormUncertainty(object):
    def __init__(self, name : str, value : Union[float,tuple[float,float]], eras=None):
        self.name = name
        self.value = value
        if type(value) == float:
            self.kappaUp = value
            self.kappaDown = 1./value
        elif type(value) in (list,tuple) and len(value) == 2 and type(value[0]) == float:
            self.kappaDown = value[0]
            self.kappaUp = value[1]
        else:
            raise RuntimeError("Unsupported value %r (type %s) for norm uncertainty %s" % (value, type(value), name))
        self.eras = eras
    @staticmethod
    def parse(optionValue, defaultName : str):
        if optionValue == None:
            return []
        elif type(optionValue) == float or (type(optionValue) in (tuple,list) and type(optionValue[0]) == float):
            return [NormUncertainty(defaultName, optionValue)]
        elif type(optionValue) == list and isinstance(optionValue[0], NormUncertainty):
            return optionValue[:]
        else:
            return [NormUncertainty(k,v) for (k,v) in optionValue.items()]
