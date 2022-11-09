#!/bin/bash
# mostly follwing https://gitlab.cern.ch/gitlabci-examples/kinit_example
test -d ~/.ssh || mkdir -p ~/.ssh
test -f ~/.ssh/known_hosts || touch ~/.ssh/known_hosts
grep -q "^lxplus.cern.ch ecdsa-sha2-nistp256" ~/.ssh/known_hosts || echo "lxplus.cern.ch ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBPZvfRF+9L7TR3FRPyLFdcsXSZ6RQYJHfOjzzWB94sX0gP34Cgij9p4ukL900sVVvw3LPM5OxxFSNIXGztFYu4o=" >> ~/.ssh/known_hosts
echo -e "Host *\nGSSAPIAuthentication yes\nGSSAPIDelegateCredentials yes\nGSSAPITrustDNS yes\nStrictHostKeyChecking no\n\n" > ~/.ssh/config
echo "${KRB_PASS}" | kinit -V -A -f ${KRB_USER}@CERN.CH
