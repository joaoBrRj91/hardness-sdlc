#!/usr/bin/env bash
# Mostra, por commit, os arquivos e o código criado/alterado num intervalo.
# Uso: show-changes.sh <base>[..HEAD]
# A saída já vem em markdown (blocos ```diff) para o orquestrador colar como texto.
set -uo pipefail

range="${1:?uso: show-changes.sh <base>[..HEAD]}"
[[ "$range" == *..* ]] || range="$range..HEAD"
MAX_LINES=150

EXCLUDES=(
  ':(exclude)*.lock' ':(exclude)*lock.json'
  ':(exclude)**/bin/**' ':(exclude)**/obj/**'
  ':(exclude)**/Migrations/*.Designer.cs' ':(exclude)**/*ModelSnapshot.cs'
  ':(exclude)docs/tasks/**'
)

commits=$(git rev-list --reverse --no-merges "$range") || exit 1
[ -z "$commits" ] && { echo "Nenhum commit em $range."; exit 0; }

for c in $commits; do
  echo "### $(git log -1 --format='%h %s' "$c")"
  while IFS=$'\t' read -r status path; do
    case "$status" in
      A) tag="(novo) " ;;
      D) tag="(removido) " ;;
      R*) tag="(renomeado) " ;;
      *) tag="" ;;
    esac
    echo
    echo "**${tag}${path}**"
    echo '```diff'
    git show --format= --no-color -U3 "$c" -- "$path" \
      | grep -v -e '^diff --git' -e '^index ' -e '^new file mode' -e '^deleted file mode' \
      | awk -v max="$MAX_LINES" -v c="$(git log -1 --format=%h "$c")" -v p="$path" '
          NR <= max { print; next }
          NR == max + 1 { omitted = 1 }
          { total = NR }
          END { if (omitted) printf "… %d linhas omitidas (git show %s -- %s)\n", total - max, c, p }'
    echo '```'
  done < <(git show --format= --name-status "$c" -- . "${EXCLUDES[@]}")
  echo
done
