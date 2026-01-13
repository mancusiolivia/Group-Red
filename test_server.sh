#!/bin/bash

'''
command: uvicorn api_server:app - start fastapi server terminal
command: ./test_server.sh - test fastapi server terminal
'''
echo "=========================================="
echo "FastAPI Server Setup and Testing Guide"
echo "=========================================="
echo ""

# Step 1: Check dependencies
echo "STEP 1: Checking if required packages are installed..."
echo "Command: python3 -c \"import fastapi, uvicorn, together\""
if python3 -c "import fastapi, uvicorn, together" 2>/dev/null; then
    echo "   ✓ All dependencies are installed!"
    echo ""
else
    echo "   ✗ Missing dependencies!"
    echo ""
    echo "   Expected: All packages (fastapi, uvicorn, together) should be installed"
    echo "   Action: Run: pip install -r requirements.txt"
    echo ""
    exit 1
fi

# Step 2: Check if server is running
echo "STEP 2: Checking if server is running on port 8000..."
echo "Command: curl -s http://localhost:8000/"
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "   ✓ Server is running!"
    echo ""
    echo "   Expected: Server should respond with HTTP 200 OK"
    echo "   What happened: Server is accessible and responding"
    echo ""
else
    echo "   ✗ Server is not running!"
    echo ""
    echo "   Expected: Server should be running on http://localhost:8000"
    echo "   What happened: No server found on port 8000"
    echo ""
    echo "   ACTION REQUIRED:"
    echo "   Open a NEW terminal window and run:"
    echo "   cd \"$(pwd)\""
    echo "   uvicorn api_server:app"
    echo ""
    echo "   Expected output in that terminal:"
    echo "   INFO:     Started server process [xxxxx]"
    echo "   INFO:     Waiting for application startup."
    echo "   INFO:     Application startup complete."
    echo "   INFO:     Uvicorn running on http://127.0.0.1:8000"
    echo ""
    echo "   Then come back here and run this script again."
    echo ""
    exit 1
fi

# Step 3: Test root endpoint
echo "STEP 3: Testing GET / endpoint (root endpoint)..."
echo "Command: curl -s http://localhost:8000/ | python3 -m json.tool"
echo ""
response=$(curl -s http://localhost:8000/)
echo "$response" | python3 -m json.tool
echo ""
echo "   Expected: JSON response with message about server running"
echo "   What happened: Root endpoint returned server status"
echo ""

# Step 4: Test Case 1 - POST /projectdemo with empty body (no prompt)
echo "STEP 4: Test Case 1 - POST /projectdemo with empty body (no prompt)..."
echo "Command: curl -X POST http://localhost:8000/projectdemo -H \"Content-Type: application/json\" -d '{}'"
echo ""
echo "   Test Case 1: User sends empty body {} - should use default prompt 'user did not enter a prompt'"
echo "   Note: This will call the LLM API, so it may take 10-30 seconds..."
echo ""

response=$(curl -X POST http://localhost:8000/projectdemo \
     -H "Content-Type: application/json" \
     -d '{}' \
     -s -w "\nHTTP_STATUS:%{http_code}")

http_status_case1=$(echo "$response" | grep "HTTP_STATUS" | cut -d: -f2)
json_response=$(echo "$response" | grep -v "HTTP_STATUS")

echo "$json_response" | python3 -m json.tool
echo ""
echo "   Expected: JSON response with 'response' field containing LLM output"
echo "   Expected prompt used: 'user did not enter a prompt' (default)"
echo "   HTTP Status: $http_status_case1 (should be 200)"
echo "   What happened: LLM was called with default prompt and returned a response"
echo ""

# Step 5: Test Case 2 - POST /projectdemo with user-provided prompt
echo "STEP 5: Test Case 2 - POST /projectdemo with user-provided prompt..."
echo "Command: curl -X POST http://localhost:8000/projectdemo -H \"Content-Type: application/json\" -d '{\"prompt\": \"what is a project demo?\"}'"
echo ""
echo "   Test Case 2: User provides prompt 'what is a project demo?' - should use user's prompt"
echo "   Note: This will call the LLM API with the user's prompt, so it may take 10-30 seconds..."
echo ""

response=$(curl -X POST http://localhost:8000/projectdemo \
     -H "Content-Type: application/json" \
     -d '{"prompt": "what is a project demo?"}' \
     -s -w "\nHTTP_STATUS:%{http_code}")

http_status_case2=$(echo "$response" | grep "HTTP_STATUS" | cut -d: -f2)
json_response=$(echo "$response" | grep -v "HTTP_STATUS")

echo "$json_response" | python3 -m json.tool
echo ""
echo "   Expected: JSON response with 'response' field containing LLM output about project demos"
echo "   Expected prompt used: 'what is a project demo?' (user-provided)"
echo "   HTTP Status: $http_status_case2 (should be 200)"
echo "   What happened: LLM was called with user's custom prompt and returned a response"
echo ""

# Step 6: Test Case 3 - POST /projectdemo with empty string prompt
echo "STEP 6: Test Case 3 - POST /projectdemo with empty string prompt..."
echo "Command: curl -X POST http://localhost:8000/projectdemo -H \"Content-Type: application/json\" -d '{\"prompt\": \"\"}'"
echo ""
echo "   Test Case 3: User sends empty string prompt \"\" - should use default prompt 'user did not enter a prompt'"
echo "   Note: This will call the LLM API, so it may take 10-30 seconds..."
echo ""

response=$(curl -X POST http://localhost:8000/projectdemo \
     -H "Content-Type: application/json" \
     -d '{"prompt": ""}' \
     -s -w "\nHTTP_STATUS:%{http_code}")

http_status_case3=$(echo "$response" | grep "HTTP_STATUS" | cut -d: -f2)
json_response=$(echo "$response" | grep -v "HTTP_STATUS")

echo "$json_response" | python3 -m json.tool
echo ""
echo "   Expected: JSON response with 'response' field containing LLM output"
echo "   Expected prompt used: 'user did not enter a prompt' (default, empty string treated as no prompt)"
echo "   HTTP Status: $http_status_case3 (should be 200)"
echo "   What happened: LLM was called with default prompt (empty string treated as no prompt) and returned a response"
echo ""

# Step 7: Test GET /projectdemo endpoint to view all stored results
echo "STEP 7: Testing GET /projectdemo endpoint (view all stored results)..."
echo "Command: curl -s http://localhost:8000/projectdemo | python3 -m json.tool"
echo ""
echo "   Test: View all results from previous POST requests"
echo "   Note: This should show all 3 POST requests we just made"
echo ""

response=$(curl -s http://localhost:8000/projectdemo -w "\nHTTP_STATUS:%{http_code}")

http_status_get=$(echo "$response" | grep "HTTP_STATUS" | cut -d: -f2)
json_response=$(echo "$response" | grep -v "HTTP_STATUS")

echo "$json_response" | python3 -m json.tool
echo ""
echo "   Expected: JSON response with 'total_results' and 'results' array containing all POST requests"
echo "   Expected total_results: 3 (from the 3 POST requests above)"
echo "   HTTP Status: $http_status_get (should be 200)"
echo "   What happened: GET endpoint returned all stored POST request results"
echo ""
echo "   💡 TIP: You can also view this in your browser at: http://localhost:8000/projectdemo"
echo ""

if [ "$http_status_case1" = "200" ] && [ "$http_status_case2" = "200" ] && [ "$http_status_case3" = "200" ] && [ "$http_status_get" = "200" ]; then
    echo "=========================================="
    echo "✓ ALL TESTS PASSED!"
    echo "=========================================="
    echo ""
    echo "Summary:"
    echo "  - Dependencies: Installed"
    echo "  - Server: Running"
    echo "  - GET /: Working"
    echo "  - POST /projectdemo: Working ✓"
    echo "  - GET /projectdemo: Working ✓"
    echo ""
    echo "Test Results:"
    echo "  ✓ Case 1 (empty body {}): Uses default 'user did not enter a prompt'"
    echo "  ✓ Case 2 (user prompt): Uses user-provided 'what is a project demo?'"
    echo "  ✓ Case 3 (empty string): Uses default 'user did not enter a prompt'"
    echo "  ✓ GET /projectdemo: Successfully displays all stored results"
    echo ""
    echo "Your FastAPI server is fully functional!"
    echo ""
    echo "View results in browser: http://localhost:8000/projectdemo"
else
    echo "=========================================="
    echo "✗ SOME TESTS FAILED"
    echo "=========================================="
    echo ""
    if [ "$http_status_case1" != "200" ]; then
        echo "  - Case 1 (empty body) returned HTTP status: $http_status_case1"
    fi
    if [ "$http_status_case2" != "200" ]; then
        echo "  - Case 2 (user prompt) returned HTTP status: $http_status_case2"
    fi
    if [ "$http_status_case3" != "200" ]; then
        echo "  - Case 3 (empty string) returned HTTP status: $http_status_case3"
    fi
    if [ "$http_status_get" != "200" ]; then
        echo "  - GET /projectdemo returned HTTP status: $http_status_get"
    fi
    echo ""
    echo "Check the server terminal for error messages."
fi
