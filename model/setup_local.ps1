$ErrorActionPreference = 'Stop'
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { throw 'Install Ollama first: https://ollama.com/download' }
$model = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { 'gemma4:e2b' }
Write-Host "Pulling $model ..."
ollama pull $model
Write-Host "Ollama is ready. Set PROVIDER_CHAIN=ollama,mock in .env."
