#!/bin/bash

# 1. Handle Container argument (usage: ./script.sh custom-image:tag)
CONTAINER=${1:-"el9-root-master:latest"}
shift

USER_NAME=$(whoami)
USER_INITIAL=${USER_NAME:0:1}
DOCKER_FLAGS=("-it" "--rm" "--network" "host")

# 2. Detect the SSH key
if [ -f "$HOME/.ssh/id_ed25519" ]; then
    SSH_KEY="~/.ssh/id_ed25519"
elif [ -f "$HOME/.ssh/id_rsa" ]; then
    SSH_KEY="~/.ssh/id_rsa"
fi

# 3. Base Mounts and Environment
DOCKER_FLAGS+=("-v" "$HOME:$HOME")
DOCKER_FLAGS+=("-e" "HOME=$HOME")
DOCKER_FLAGS+=("-e" "GIT_SSH_COMMAND=ssh -i $SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=no")
DOCKER_FLAGS+=("-v" "/etc/passwd:/etc/passwd:ro")
DOCKER_FLAGS+=("-v" "/etc/group:/etc/group:ro")
DOCKER_FLAGS+=("-u" "$(id -u):$(id -g)")
DOCKER_FLAGS+=("-v" "$(pwd):$(pwd)")  # Mount current host dir to same path in container
DOCKER_FLAGS+=("-w" "$(pwd)")         # Set the starting directory inside the container
DOCKER_FLAGS+=("-e" "PYTHONNOUSERSITE=1")
DOCKER_FLAGS+=("-e" "PYTHONPATH=/usr/local/root_install/lib:/usr/local/lib64/python3.11/site-packages:/usr/local/lib/python3.11/site-packages")
DOCKER_FLAGS+=("-e" "LD_PRELOAD=")

# 4. Conditional Mounts (CVMFS, AFS, EOS)
mount_if_exists() {
    if [ -d "$1" ]; then
        echo "Mounting $1..."
        DOCKER_FLAGS+=("-v" "$1:$1")
    else
        echo "Skipping $1 (Not found on host)"
    fi
}

# Check CVMFS
mount_if_exists "/cvmfs"

# Check AFS Work
mount_if_exists "/afs/cern.ch/work/$USER_INITIAL/$USER_NAME"

# Check EOS User
mount_if_exists "/eos/user/$USER_INITIAL/$USER_NAME"

# Check EOS CMS Store
mount_if_exists "/eos/cms/store/cmst3"

# Check grid certificates
mount_if_exists "/etc/grid-security"
mount_if_exists "/etc/vomses"


# 5. Run it
echo "Starting container: $CONTAINER"
docker run "${DOCKER_FLAGS[@]}" "$CONTAINER" "$@"
