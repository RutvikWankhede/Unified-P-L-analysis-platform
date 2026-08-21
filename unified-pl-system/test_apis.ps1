$response = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/v1/auth/login" -Method Post -Body '{"username":"admin", "password":"admin123", "email":"admin@unifiedpl.com"}' -ContentType "application/json"
$token = $response.access_token
$summary = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/v1/pl/summary" -Method Get -Headers @{Authorization="Bearer $token"}
$summary | ConvertTo-Json -Depth 5
$charts = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/v1/pl/charts" -Method Get -Headers @{Authorization="Bearer $token"}
$charts | ConvertTo-Json -Depth 5
