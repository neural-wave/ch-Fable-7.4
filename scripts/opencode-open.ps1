# OpenCode on an open-weights model, the Windows twin of opencode-open.sh; protocol, endpoint, key and model come
# from .env.llm (not versioned). Runs on Windows PowerShell 5.1 and PowerShell 7.
# Usage: scripts\opencode-open.cmd [run|mini|models] [opencode arguments], e.g. scripts\opencode-open.cmd run --auto "..."
# (the .cmd bypasses the execution policy; .\scripts\opencode-open.ps1 works too where scripts are allowed)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root '.env.llm'
if (-not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
  [Console]::Error.WriteLine("missing ${envFile}: copy .env.llm.example and fill in endpoint, key, model and context")
  exit 1
}
# KEY=VALUE lines as `source` reads them: the file wins over the environment, '#' starts a comment after a blank
$vars = [ordered]@{}
foreach ($line in Get-Content -LiteralPath $envFile -Encoding UTF8) {
  $line = ($line -split ' #', 2)[0].Trim()
  if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
    $key, $value = $line -split '=', 2
    $vars[$key.Trim()] = $value.Trim().Trim("'`"")
  }
}
foreach ($name in 'OPEN_BASE_URL', 'OPEN_API_KEY', 'OPEN_MODEL', 'OPEN_CONTEXT') {
  if (-not $vars.Contains($name) -or $vars[$name].Contains('REPLACE_ME')) {
    [Console]::Error.WriteLine("fill in OPEN_BASE_URL, OPEN_API_KEY, OPEN_MODEL and OPEN_CONTEXT in $envFile")
    exit 1
  }
}
if (-not $vars['OPEN_PROTOCOL']) { $vars['OPEN_PROTOCOL'] = 'openai' }
$vars['OPEN_BASE_URL'] = $vars['OPEN_BASE_URL'].TrimEnd('/')
if (-not $vars['OPEN_MAX_OUTPUT']) { $vars['OPEN_MAX_OUTPUT'] = '8192' }   # the 32000 default eats a small window
if ($vars['OPEN_PROTOCOL'] -cnotmatch '^(openai|anthropic)$' -or $vars['OPEN_CONTEXT'] -notmatch '^[0-9]+$' -or
    $vars['OPEN_MAX_OUTPUT'] -notmatch '^[0-9]+$') {
  [Console]::Error.WriteLine('OPEN_PROTOCOL must be openai or anthropic, OPEN_CONTEXT and OPEN_MAX_OUTPUT numbers of tokens')
  exit 1
}
$vars['OPENCODE_CONFIG'] = Join-Path $PSScriptRoot 'opencode-open.jsonc'   # provider "open" with this model, and no other
# run from a PowerShell prompt the script shares its process: the previous values come back when OpenCode exits
$saved = @{}
foreach ($name in $vars.Keys) {
  $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
  [Environment]::SetEnvironmentVariable($name, $vars[$name], 'Process')
}
try {
  # --standalone: a private server started here reads the variables above, the shared background service does not
  $command, $rest = $args
  if ($command -in 'run', 'mini', 'models') { & opencode $command --standalone @rest }
  else { & opencode --standalone @args }
  $code = $LASTEXITCODE
} finally {
  foreach ($name in $saved.Keys) { [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process') }
}
exit $code
