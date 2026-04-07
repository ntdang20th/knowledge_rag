#!/bin/bash
echo "Pulling embedding model..."
ollama pull nomic-embed-text

echo "Pulling LLM model..."
ollama pull qwen2.5-coder:7b-instruct

echo "Done! Models ready."
ollama list
