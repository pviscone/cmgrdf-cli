import correctionlib
import re
import ROOT

correctionlib.register_pyroot_binding()


class CorrectionlibFactory(object):
    _ids = dict()  # type: dict[str,str]

    @classmethod
    def _strToId(cls, name: str, prefix : str, hint=None):
        """Returns a unique C++-safe ID string for name, preferrably equal to hint if specified"""
        if name not in cls._ids:
            safe = re.sub("[^A-Za-z0-9_]", "", (hint if hint else name))
            key = prefix + safe
            i = 0
            while key in cls._ids.values():
                key = "%s%s_%d" % (prefix, safe, i + 1)
                i += 1
            cls._ids[name] = key
        return cls._ids[name]

    _files = dict()  # type: dict[str,str]

    @classmethod
    def _loadSet(cls, filename : str, hint=None, check=False):
        """Loads a CorrectionSet from file, with a preferred name."""
        if filename not in cls._files:
            fileid = cls._strToId(filename, "_correctionlibSet_", hint=hint)
            assert (fileid not in cls._files.values())
            corrSet = correctionlib.CorrectionSet.from_file(filename) if check else None
            cls._files[filename] = (fileid, corrSet)
            ROOT.gInterpreter.Declare(f'auto {fileid} = correction::CorrectionSet::from_file("{filename}");')
        return cls._files[filename]

    _correctors = dict()  # type: dict[tuple[str,str],str]

    @classmethod
    def loadCorrector(cls, filename : str, corrector : str, fileHint=None, corrHint=None, check=False):
        if (filename, corrector) not in cls._correctors:
            corrSetId, corrSet = cls._loadSet(filename, hint=fileHint, check=check)
            if check:
                if corrector not in list(corrSet.keys()):
                    raise RuntimeError(f"Error: can't find {corrector} in {filename}: available corrections are " + ", ".join(sorted(corrSet.keys())))
            corrId = cls._strToId(corrector, corrSetId + "_corr_", hint=corrHint)
            ROOT.gInterpreter.Declare(f'auto {corrId} = {corrSetId}->at("{corrector}");')
            corr = corrSet[corrector] if check else None
            cls._correctors[(filename, corrector)] = (corrId, corr)
        return cls._correctors[(filename, corrector)]
