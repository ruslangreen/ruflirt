#!/bin/sh
# Read-only diagnostic for the existing local Debian; does not install or restart anything.
echo "HOST: $(hostname)"
echo "MEMORY:"; free -h
echo "CPU:"; nproc
echo "OLLAMA BINARY:"; command -v ollama || true
echo "OLLAMA SERVICE:"; systemctl is-active ollama 2>/dev/null || true
echo "OLLAMA MODELS:"; timeout 4 ollama list 2>&1 || true
echo "OLLAMA API:"; curl -sS --max-time 3 http://127.0.0.1:11434/api/tags | head -c 1000; echo
echo "LISTENERS:"; ss -ltn | grep -E ':(11434|8765) ' || true
