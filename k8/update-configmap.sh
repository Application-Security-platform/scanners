#!/bin/bash

# Copy scanner files
cp ../script/consumer.py .
cp ../script/requirements.txt scanner-requirements.txt
cp ../script/scanner_config.py .

# Copy preprocessing files
cp ../../preprocessing/multi_format_parser.py .
cp ../../preprocessing/requirements.txt preprocess-requirements.txt
cp ../../preprocessing/store_data.py .
cp ../../preprocessing/preprocess_data.py .

# Apply kustomization
kubectl apply -k .

# Clean up the copied files
rm consumer.py scanner-requirements.txt scanner_config.py
rm multi_format_parser.py preprocess-requirements.txt store_data.py preprocess_data.py