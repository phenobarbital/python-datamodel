## install Rust (system-wide):

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh


## install compiler (ubuntu)
source $HOME/.cargo/env

## Activate the compiler
jesuslara@lexotanil:~$ source $HOME/.cargo/env

## Check the version of the compiler
jesuslara@lexotanil:~$ rustc --version
rustc 1.84.0 (9fc6b4312 2025-01-07)

# Install Setup dependencies:
pip install cython maturin sdist setuptools wheel setuptools-rust
