# Define the file paths
$files = @(
    "C:\CryptoBot\crypto_bot\__init__.py",
    "C:\CryptoBot\crypto_bot\modules\__init__.py"
)

# Initialize report for console output
$report = "File Check and Clear Report`n"
$report += "Generated: $(Get-Date)`n"
$report += "===================================`n`n"

# Process each file
foreach ($file in $files) {
    # Check if the file exists
    if (Test-Path $file) {
        # Get file info
        $fileInfo = Get-Item $file
        $fileSize = $fileInfo.Length

        # Check if file is not empty (size > 0)
        if ($fileSize -gt 0) {
            try {
                # Clear the file by writing an empty string
                Set-Content -Path $file -Value "" -ErrorAction Stop
                $report += "File: $file`nStatus: Cleared (was $fileSize bytes)`n`n"
                Write-Host "Cleared: $file (was $fileSize bytes)" -ForegroundColor Green
            }
            catch {
                $report += "File: $file`nStatus: Error clearing file - $($_.Exception.Message)`n`n"
                Write-Host "Error clearing $file - $($_.Exception.Message)" -ForegroundColor Red
            }
        }
        else {
            $report += "File: $file`nStatus: Already empty`n`n"
            Write-Host "Skipped: $file (already empty)" -ForegroundColor Yellow
        }
    }
    else {
        $report += "File: $file`nStatus: Does not exist`n`n"
        Write-Host "Not found: $file" -ForegroundColor Red
    }
}

# Write report to a timestamped file
$outputFile = "C:\CryptoBot_FileClearReport_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
$report | Out-File -FilePath $outputFile -Encoding UTF8
Write-Host "`nReport saved to: $outputFile" -ForegroundColor Green