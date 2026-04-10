# 1. Use the CERN image as the base
FROM gitlab-registry.cern.ch/cms-new-cmgtools/cmgrdf-prototype/el10-root-master:latest

USER root

# 2. Install what IS available in dnf
RUN dnf clean all && \
    dnf install -y epel-release && \
    dnf install -y poppler-utils zsh bat fzf git curl ripgrep procps-ng rsync graphviz graphviz-devel && \
    dnf clean all

# 3. Manually install 'micro' editor
RUN curl https://getmic.ro | bash && \
    mv micro /usr/local/bin/

# 4. Manually install 'eza' (using the static binary method)
# We download the latest release from GitHub
RUN curl -L https://github.com/eza-community/eza/releases/latest/download/eza_x86_64-unknown-linux-gnu.tar.gz | tar xz && \
    mv eza /usr/local/bin/

# 5. Manually install 'zoxide'
# We set BINDIR to /usr/local/bin so the script puts it where we want it
RUN (curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | BINDIR=/usr/local/bin sh); mv /root/.local/bin/zoxide /usr/local/bin

# 6. Install Neovim (nvim)
RUN curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz && \
    tar -C /usr/local --strip-components 1 -xzf nvim-linux-x86_64.tar.gz && \
    rm nvim-linux-x86_64.tar.gz

# 7. Manually install 'fd'
RUN URL=$(curl -s https://api.github.com/repos/sharkdp/fd/releases/latest | grep "browser_download_url.*x86_64-unknown-linux-musl.tar.gz" | cut -d '"' -f 4) && \
    curl -L "$URL" | tar xz --strip-components=1 && \
    mv fd /usr/local/bin/ && \
    rm -f autocomplete/* README.md LICENSE*

# 8. Install Bottom (Faster/Better top)
RUN URL_BTM=$(curl -s https://api.github.com/repos/ClementTsang/bottom/releases/latest | grep "browser_download_url.*x86_64-unknown-linux-musl.tar.gz" | cut -d '"' -f 4) && \
    curl -L "$URL_BTM" | tar xz && \
    mv btm /usr/local/bin/

# 9. Alias python3 with python
RUN ln -s /usr/bin/python3 /usr/bin/python

#10. Install dust
RUN curl -sSfL https://raw.githubusercontent.com/bootandy/dust/refs/heads/master/install.sh | sh

#11. Install rmz and cpz (FUC tools)
RUN curl -L https://github.com/SUPERCILEX/fuc/releases/download/3.1.1/x86_64-unknown-linux-musl-cpz -o /usr/local/bin/cpz && \
    curl -L https://github.com/SUPERCILEX/fuc/releases/download/3.1.1/x86_64-unknown-linux-musl-rmz -o /usr/local/bin/rmz && \
    curl -L https://github.com/dandavison/delta/releases/download/0.18.2/delta-0.18.2-x86_64-unknown-linux-musl.tar.gz | tar xz --strip-components=1 && \
    mv delta /usr/local/bin/delta_bin && mv /usr/local/bin/delta_bin /usr/local/bin/delta && \
    chmod +x /usr/local/bin/cpz /usr/local/bin/rmz /usr/local/bin/delta

#12. Install pygraphviz
RUN pip install pygraphviz

# 13. FIX OWNERSHIP (The "Clean Slate" Step)                                                                                                                                                                                                                                
RUN chown -R root:root /usr/local/bin
 
WORKDIR /work
#CMD ["/bin/zsh"]
