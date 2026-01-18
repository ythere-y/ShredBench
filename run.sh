#!/bin/bash

PREPROCESS_SCRIPT="preprocess_.py"
BLENDER_SCRIPT="blenderprocess_.py"

if [[ ! -f "$PREPROCESS_SCRIPT" ]]; then
    echo "Error: Script $PREPROCESS_SCRIPT not found."
    exit 1
fi

if [[ ! -f "$BLENDER_SCRIPT" ]]; then
    echo "Error: Script $BLENDER_SCRIPT not found."
    exit 1
fi

echo "--------------------------------------"
echo "[1/2] Starting preprocessing phase..."
echo "--------------------------------------"

python "$PREPROCESS_SCRIPT"

if [ $? -eq 0 ]; then
    echo "✅ Preprocessing complete."
else
    echo "❌ Preprocessing failed. Aborting."
    exit 1
fi

echo ""
echo "--------------------------------------"
echo "[2/2] Starting Blender processing phase..."
echo "--------------------------------------"

python "$BLENDER_SCRIPT"

if [ $? -eq 0 ]; then
    echo "✅ Blender processing completed successfully!"
else
    echo "❌ Error occurred during Blender processing."
    exit 1
fi
