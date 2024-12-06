#!/usr/bin/env python3
import socket
import tempfile
import subprocess
import os

def defaultSchedulerUrl(port=8786):
    addrs = socket.getaddrinfo(socket.gethostname(), port)
    (ip,port) = [s for s in addrs if s[0] == socket.AF_INET][0][-1]
    return f"tcp://{ip}:{port}"

def guessEnvFile():
    path = subprocess.check_output(["which","root"],text=True).rstrip()
    if not path.endswith("/bin/root") or not path.startswith("/cvmfs"):
        raise RuntimeError(f"Bad root path {path}")
    setup = path[:-len("/bin/root")]+"/setup.sh"
    if not os.path.isfile(setup):
        raise RuntimeError(f"Guessed env setup file {setup} which doesn't exist")
    return setup

if __name__ == '__main__':
    import argparse
    import re
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--scheduler", help="scheduler URL (default is this host)")
    parser.add_argument("-e", "--envfile", help="environment setup file")
    parser.add_argument("-j", "--ncpu", help="number of CPU cores per job", default=1, type=int)
    parser.add_argument("-m", "--mem", help="memory per core, in GiB", default=2, type=float)
    parser.add_argument("--logdir", help="directory for logs")
    parser.add_argument("nworkers", help="number of workers", type=int)
    parser.add_argument("time", help="job duration", nargs="?", default="8h")
    args = parser.parse_args()
    scheduler = args.scheduler if args.scheduler else defaultSchedulerUrl()
    envscript = args.envfile if args.envfile else guessEnvFile()
    logdir = args.logdir if args.logdir else os.getcwd()+"/logs"
    os.makedirs(logdir, exist_ok=True)
    if not re.match(r"\d+[hmsd]?", args.time):
        raise RuntimeError(f"Time should be <number> or <number><unit>, with <uint> = s, m, h, d; got {args.time}")
    (num, unit) = (args.time, 's') if args.time[-1].isdigit() else (args.time[:-1], args.time[-1])
    runtime_secs = int(num) * ({'s':1, 'm':60, 'h':3600, 'd':24*3600}[unit])
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sub") as fp:
        CMGRDF = os.environ['CMGRDF']
        fp.write(f"""
CMGRDF = {CMGRDF}
Universe = vanilla
Log = {logdir}/job$(Sep).condor
Output = {logdir}/job$(Sep).out
Error = {logdir}/job$(Sep).err
getenv      = True
transfer_output_files = ""
RequestCpus = {args.ncpu}
+MaxRuntime = {runtime_secs}

Executable = $(CMGRDF)/examples/condor_runner.sh 
Arguments = {envscript} {scheduler} --nworkers {args.ncpu} --nthreads 1 --memory-limit {args.mem:.1f}GiB --worker-port 10000:10100

Queue {args.nworkers}\n""".lstrip())
        fp.flush()
        subprocess.check_call(["condor_submit", fp.name])