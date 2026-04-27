import os
import random
import subprocess


def select_files_by_fraction(file_sizes, fraction, offset=0):
    """
    Select files whose total size is as close as possible to fraction * total_size + offset.

    Args:
        file_sizes: dict {filepath: size_in_bytes}
        fraction:   float in [0, 1], target fraction of total size
        offset:     int, additive offset to the target (default 0)

    Returns:
        (selected_files, difference)
        selected_files: list of filepaths whose size sum is closest to target
        difference:     fraction * total_size - sum(selected sizes)
    """
    total_size = sum(file_sizes.values())
    target = fraction * total_size - offset

    # Shuffle with constant seed for reproducibility
    files = list(file_sizes.keys())
    random.Random(666).shuffle(files)

    # Greedy accumulation: add files as long as it brings us closer to target
    selected = []
    current_size = 0
    for f in files:
        size = file_sizes[f]
        before = abs(target - current_size)
        after = abs(target - (current_size + size))
        if after <= before:
            selected.append(f)
            current_size += size
        else:
            break

    difference = target - current_size
    return selected, current_size, difference


def get_file_sizes(pattern):
    """
    Get file sizes for local or EOS files, supporting glob patterns.

    Args:
        pattern: Local glob pattern or XRootD URL with glob
                 e.g. '/tmp/*.root' or 'root://eosuser.cern.ch//eos/user/j/jdoe/*.root'

    Returns:
        dict: {filepath: size_in_bytes}
    """
    if pattern.startswith("root://"):
        server, path = pattern[7:].split("//", 1)
        server = "root://" + server
        path = "/" + path

        # Fall back to xrdfs CLI
        directory = os.path.dirname(path)
        basename = os.path.basename(path)

        result = subprocess.run(
            ["xrdfs", server, "ls", "-l", directory], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"xrdfs ls failed: {result.stderr}")

        import fnmatch

        sizes = {}
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                name = os.path.basename(parts[-1])
                if fnmatch.fnmatch(name, basename):
                    filepath = f"{server}/{parts[-1]}"
                    sizes[filepath] = int(parts[3])
        return sizes

    else:
        import glob

        return {f: os.path.getsize(f) for f in glob.glob(pattern)}
