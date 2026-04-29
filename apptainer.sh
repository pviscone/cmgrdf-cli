#!/bin/bash

# 1. Setup local tmp/cache to avoid /tmp permission errors
export BASEAPPTAINER=${APPTAINER:-"$(pwd)/.apptainer"}

export APPTAINER_TMPDIR="/tmp/$(whoami)_apptainer_tmp"
export APPTAINER_CACHEDIR="$BASEAPPTAINER/cache"
mkdir -p "$APPTAINER_TMPDIR" "$APPTAINER_CACHEDIR"

# 2. Container Image
CONTAINER_URI=${1:-"docker://pviscone/cmgrdf-cli:el10-root-master"}
shift

# 3. Detect SSH Key
SSH_KEY="$HOME/.ssh/id_rsa"
[ -f "$HOME/.ssh/id_ed25519" ] && SSH_KEY="$HOME/.ssh/id_ed25519"

# 4. Apptainer Flags (The "Host" Setup)
# We REMOVE --net and --network. Apptainer will now use host network by default.
# We keep --userns to ensure it works even if the system SUID is wonky.
APPTAINER_FLAGS=("--userns")

# 5. Environment Variables (Internal to Container)
export APPTAINERENV_GIT_SSH_COMMAND="ssh -i $SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=no"
export APPTAINERENV_PYTHONNOUSERSITE=1
export APPTAINERENV_PYTHONPATH="/usr/local/root_install/lib:/usr/local/lib64/python3.12/site-packages:/usr/local/lib/python3.12/site-packages"

# 6. Bind Mounts
bind_if_exists() {
    [ -d "$1" ] && APPTAINER_FLAGS+=("-B" "$1:$1")
}

# Standard CERN/CMS mounts
bind_if_exists "/cvmfs"
bind_if_exists "/eos"
bind_if_exists "/afs"
bind_if_exists "/data"
bind_if_exists "/scratch"
bind_if_exists "/t3home"
bind_if_exists "/swshare"
bind_if_exists "/pnfs"
bind_if_exists "/work"
bind_if_exists "/tmp"


# Machine-specific logic for grid-security
if [[ $(hostname) == *"olhsw"* ]]; then
    echo "Special host detected (olhsw). Mapping CVMFS grid-security to /etc/grid-security..."
    # Bind the CVMFS path DIRECTLY to the container's /etc/grid-security
    # This effectively acts like the symlink you wanted inside the container.
    APPTAINER_FLAGS+=("-B" "/cvmfs/cms.cern.ch/grid/etc/grid-security:/etc/grid-security")
else
    bind_if_exists "/etc/grid-security"
fi

bind_if_exists "/etc/vomses"

# 7. Run
echo "Running in HOST network mode..."
apptainer run "${APPTAINER_FLAGS[@]}" "$CONTAINER_URI" "$@"
