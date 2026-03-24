#!/bin/bash
# Start both the Python API server and the Node SSR server

# Start the Python API backend
pyrite-server &
PYTHON_PID=$!

# Wait for Python API to be ready
echo "Waiting for Pyrite API..."
for i in $(seq 1 30); do
    if python -c "import urllib.request; urllib.request.urlopen('http://localhost:8088/health')" 2>/dev/null; then
        echo "Pyrite API ready"
        break
    fi
    sleep 1
done

# Start the Node SSR server
cd /app/web
ORIGIN=${PYRITE_ORIGIN:-http://localhost:3000} PORT=3000 BODY_SIZE_LIMIT=10M node build &
NODE_PID=$!

echo "Node SSR server started on port 3000"

# Wait for either to exit
wait -n $PYTHON_PID $NODE_PID
EXIT_CODE=$?

# Kill the other
kill $PYTHON_PID $NODE_PID 2>/dev/null
exit $EXIT_CODE
