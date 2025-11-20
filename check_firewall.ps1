# Check firewall rules in detail
Write-Host "=== Checking Train Dashboard Firewall Rules ===" -ForegroundColor Cyan
Write-Host ""

# Check the Train Dashboards rule
$trainRule = Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Train*"}
foreach ($rule in $trainRule) {
    Write-Host "Rule: $($rule.DisplayName)" -ForegroundColor Yellow
    Write-Host "  Enabled: $($rule.Enabled)"
    Write-Host "  Direction: $($rule.Direction)"
    Write-Host "  Action: $($rule.Action)"
    Write-Host "  Profile: $($rule.Profile)"

    # Get port filter
    $portFilter = $rule | Get-NetFirewallPortFilter
    if ($portFilter) {
        Write-Host "  Protocol: $($portFilter.Protocol)"
        Write-Host "  LocalPort: $($portFilter.LocalPort)"
    }
    Write-Host ""
}

# Check current network profile
Write-Host "=== Current Network Profile ===" -ForegroundColor Cyan
Get-NetConnectionProfile | Select-Object Name, NetworkCategory, InterfaceAlias | Format-Table -AutoSize
Write-Host ""

# Test if ports are actually open
Write-Host "=== Testing Ports ===" -ForegroundColor Cyan
$ports = @(8050, 8051, 8052)
foreach ($port in $ports) {
    $listener = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($listener) {
        Write-Host "Port $port : LISTENING on $($listener.LocalAddress)" -ForegroundColor Green
    } else {
        Write-Host "Port $port : NOT LISTENING" -ForegroundColor Red
    }
}
