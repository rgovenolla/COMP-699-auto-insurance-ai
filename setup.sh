#!/bin/bash

# Check if a zip file name was provided as an argument
if [ -z "$1" ]; then
  echo "Usage: $0 <zip_file.zip>"
  exit 1
fi

ZIP_FILE="$1"

# Check if the zip file exists
if [ ! -f "$ZIP_FILE" ]; then
  echo "Error: File '$ZIP_FILE' not found."
  exit 1
fi

# Extract the contents of the zip file to the current directory
echo "Extracting '$ZIP_FILE' to the current directory..."
unzip "$ZIP_FILE"

# Check if extraction was successful
if [ $? -eq 0 ]; then
  echo "Extraction successful."
else
  echo "Error during extraction."
fi
