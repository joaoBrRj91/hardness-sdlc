#!/usr/bin/env bash
# PostToolUse: dotnet format + build, só quando um arquivo .NET foi alterado.
# O build é do projeto (.csproj) dono do arquivo, não da solução inteira.
# Exit 2 devolve o erro de build ao agente, que corrige antes de seguir.
set -uo pipefail

file=$(python -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
file="${file//\\//}"

case "$file" in
  *.cs|*.csproj|*.props|*.targets) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# Projeto dono do arquivo: o próprio .csproj ou o mais próximo subindo as pastas.
# .props/.targets (ex.: Directory.Build.props) valem para vários projetos: sem alvo, build padrão.
proj=""
case "$file" in
  *.csproj) proj="$file" ;;
  *.cs)
    dir="${file%/*}"
    while [ -n "$dir" ] && [ -d "$dir" ]; do
      found=$(ls "$dir"/*.csproj 2>/dev/null | head -n 1)
      if [ -n "$found" ]; then proj="$found"; break; fi
      parent=$(dirname "$dir")
      [ "$parent" = "$dir" ] && break
      dir="$parent"
    done
    ;;
esac

target=()
[ -n "$proj" ] && target=("$proj")

dotnet format "${target[@]}" --no-restore --include "$file" >/dev/null 2>&1 || true

if ! out=$(dotnet build "${target[@]}" --no-restore -v q 2>&1); then
  echo "dotnet build falhou após editar $file${proj:+ (projeto $proj)}:" >&2
  echo "$out" | grep -E " error " | head -20 >&2
  exit 2
fi
exit 0
