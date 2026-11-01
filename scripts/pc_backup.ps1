# PC 매일 백업 (2026-11-01 병한님 결정: PC가 죽어도 되살릴 수 있게). 복구 순서는 docs/recovery.md.
# Windows 작업 스케줄러 "폐차_백업"(매일 밤 11시 40분, 놓치면 켜질 때 바로)이 부른다.
#   powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File scripts\pc_backup.ps1
# 저장: G:\내 드라이브\폐차_백업\YYYY-MM-DD\ (14일 지난 날짜 폴더는 지움, 드라이브 휴지통으로 감)
#   업무위키.zip  병한-업무위키 전체(영상·녹음 파일, .tmp.driveupload 빼고)
#   분석.zip      통화녹음백업\_분석 (영상·녹음 파일 빼고)
#   예약작업\windows\*.xml   이름이 "폐차"로 시작하는 Windows 작업 정의(schtasks /create /xml 로 되살림)
#   예약작업\claude\         Claude 앱 예약 작업 지시문(SKILL.md) + 목록.txt
#   열쇠_목록.txt  열쇠·env 파일 이름과 수정일만(내용은 읽지 않음)
#   파이썬_패키지.txt  pip freeze (새 PC에서 pip install -r)
#   recovery.md    저장소 docs/recovery.md 사본
# 로그: 통화녹음백업\_분석\폐차_백업_log.txt 한 줄(날짜·크기·성공/실패)
param([int]$KeepDays = 14)

$ErrorActionPreference = 'Stop'
$Today = Get-Date -Format 'yyyy-MM-dd'
$Repo = Split-Path $PSScriptRoot -Parent
$Home_ = 'C:\Users\AOMG'
$Wiki = "$Home_\Documents\병한-업무위키"
$Ana = "$Home_\Documents\통화녹음백업\_분석"
$Base = 'G:\내 드라이브\폐차_백업'
$Dest = Join-Path $Base $Today
$Log = Join-Path $Ana '폐차_백업_log.txt'
$Stage = Join-Path $env:TEMP 'pyecha_backup'
$Keys = 'gsc-key.json', 'naver_search.env', 'naver_searchad.env', 'daglo.env'
# 녹음·영상 원본은 넣지 않음(용량·개인정보), 열쇠 파일이 섞여 있어도 복사하지 않음
$Skip = '*.mp4', '*.mov', '*.avi', '*.mkv', '*.mp3', '*.m4a', '*.wav', '*.aac', '*.amr', '*.3gp', '*.ogg',
        '*.env', '*gsc-key*.json', '*.pem', '*.lock'

Add-Type -AssemblyName System.IO.Compression.FileSystem

function Write-Log($msg) {
    $line = "{0} {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
    Write-Output $line
}

function Zip-Folder($src, $zip, $xd) {
    # robocopy 로 임시 폴더에 걸러 담고, 한글 파일 이름이 깨지지 않게 UTF-8 로 압축
    $tmp = Join-Path $Stage ([IO.Path]::GetFileNameWithoutExtension($zip))
    $args_ = @($src, $tmp, '/E', '/R:1', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/XF') + $Skip
    if ($xd) { $args_ += @('/XD') + $xd }
    & robocopy @args_ | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "복사 실패: $src (robocopy $LASTEXITCODE)" }
    [IO.Compression.ZipFile]::CreateFromDirectory($tmp, $zip, [IO.Compression.CompressionLevel]::Optimal,
                                                  $false, [Text.Encoding]::UTF8)
}

try {
    if (-not (Test-Path -LiteralPath 'G:\내 드라이브')) { throw '구글 드라이브(G:\내 드라이브)가 없음' }
    if (Test-Path -LiteralPath $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force }
    if (Test-Path -LiteralPath $Dest) { Remove-Item -LiteralPath $Dest -Recurse -Force }   # 같은 날 다시 돌리면 새로
    New-Item -ItemType Directory -Force -Path $Stage, $Dest | Out-Null

    # ① 업무위키 ② _분석
    Zip-Folder $Wiki (Join-Path $Dest '업무위키.zip') @("$Wiki\.tmp.driveupload")
    Zip-Folder $Ana (Join-Path $Dest '분석.zip') $null

    # ③ 예약 작업 정의
    $win = Join-Path $Dest '예약작업\windows'
    New-Item -ItemType Directory -Force -Path $win | Out-Null
    $tasks = @(Get-ScheduledTask | Where-Object { $_.TaskName -like '폐차*' })
    foreach ($t in $tasks) {
        # schtasks /create /xml 은 UTF-16 파일을 읽는다
        Export-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath |
            Out-File -LiteralPath (Join-Path $win "$($t.TaskName).xml") -Encoding Unicode
    }
    $cl = Join-Path $Dest '예약작업\claude'
    New-Item -ItemType Directory -Force -Path $cl | Out-Null
    $skills = "$Home_\.claude\scheduled-tasks"
    $list = @("Claude 앱 예약 작업 ($Today 기준). 시간·켜짐 여부 표는 같이 들어 있는 recovery.md 의 'Claude 앱 예약 작업' 표.", '')
    if (Test-Path -LiteralPath $skills) {
        Copy-Item -LiteralPath $skills -Destination $cl -Recurse -Force
        foreach ($f in Get-ChildItem -LiteralPath $skills -Recurse -Filter 'SKILL.md') {
            $desc = (Get-Content -LiteralPath $f.FullName -Encoding UTF8 | Where-Object { $_ -like 'description:*' } |
                     Select-Object -First 1) -replace '^description:\s*', ''
            $list += "- $($f.Directory.Name): $desc"
            $list += "    지시문: $($f.FullName)"
        }
    }
    $list | Set-Content -LiteralPath (Join-Path $cl '목록.txt') -Encoding UTF8

    # ④ 열쇠 파일은 이름·수정일만
    $keyLines = @("열쇠·env 파일 목록 ($Today). 내용은 백업하지 않음 — 새 PC에서는 docs/recovery.md 대로 다시 받는다.", '')
    foreach ($k in $Keys) {
        $p = Join-Path $Home_ $k
        if (Test-Path -LiteralPath $p) {
            $keyLines += "{0}  있음  수정 {1:yyyy-MM-dd HH:mm}  ({2})" -f $k, (Get-Item -LiteralPath $p).LastWriteTime, $p
        } else {
            $keyLines += "$k  없음  ($p)"
        }
    }
    $keyLines | Set-Content -LiteralPath (Join-Path $Dest '열쇠_목록.txt') -Encoding UTF8

    # 새 PC에서 같은 파이썬 패키지를 깔 수 있게
    $py = 'C:\Users\AOMG\AppData\Local\Programs\Python\Python314\python.exe'
    if (Test-Path -LiteralPath $py) {
        & $py -m pip freeze 2>$null | Set-Content -LiteralPath (Join-Path $Dest '파이썬_패키지.txt') -Encoding UTF8
    }

    Copy-Item -LiteralPath (Join-Path $Repo 'docs\recovery.md') -Destination $Dest -ErrorAction SilentlyContinue

    # 14일 지난 날짜 폴더 지우기
    $cut = (Get-Date).Date.AddDays(-$KeepDays)
    foreach ($d in Get-ChildItem -LiteralPath $Base -Directory) {
        $when = [datetime]::MinValue
        if ([datetime]::TryParseExact($d.Name, 'yyyy-MM-dd', $null, 'None', [ref]$when) -and $when -lt $cut) {
            Remove-Item -LiteralPath $d.FullName -Recurse -Force
        }
    }

    $mb = (Get-ChildItem -LiteralPath $Dest -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
    Write-Log ("성공 {0:N1}MB {1} (Windows 작업 {2}개)" -f $mb, $Dest, $tasks.Count)
} catch {
    Write-Log "실패 $($_.Exception.Message)"
    exit 1
} finally {
    if (Test-Path -LiteralPath $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue }
}
