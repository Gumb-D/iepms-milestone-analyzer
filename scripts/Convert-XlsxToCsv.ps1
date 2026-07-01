$folder = Split-Path -Parent $MyInvocation.MyCommand.Path

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
    Get-ChildItem -LiteralPath $folder -Filter '*.xlsx' -File |
        Where-Object { $_.Name -notlike '~$*' } |
        ForEach-Object {

            $workbook = $null
            $worksheet = $null

            try {
                $inputFile = $_.FullName
                $outputFile = Join-Path $_.DirectoryName ($_.BaseName + '.csv')

                # Remove existing CSV to avoid overwrite prompt
                if (Test-Path -LiteralPath $outputFile) {
                    Remove-Item -LiteralPath $outputFile -Force
                }

                $workbook = $excel.Workbooks.Open($inputFile)
                $worksheet = $workbook.Worksheets.Item(1)

                # 62 = UTF-8 CSV
                $worksheet.SaveAs($outputFile, 62)

                Write-Host "SUCCESS: $($_.Name) -> $($_.BaseName).csv" -ForegroundColor Green
            }
            catch {
                Write-Host "FAILED: $($_.Name)" -ForegroundColor Red
                Write-Host $_.Exception.Message -ForegroundColor Yellow
            }
            finally {
                if ($worksheet) {
                    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($worksheet) | Out-Null
                }

                if ($workbook) {
                    $workbook.Close($false)
                    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($workbook) | Out-Null
                }
            }
        }
}
finally {
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

Write-Host "`nCompleted. Press Enter to close." -ForegroundColor Cyan
Read-Host