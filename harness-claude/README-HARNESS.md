# Harness Claude — do ticket à retrospectiva (.NET)

_Harness Engineering com Claude — do ticket à PR_.

Você digita `/task <id>`; o orquestrador conduz o ticket por todas as fases e para nos
pontos em que a decisão é sua.

Além disso esse harness possui a inteligencia através do Subagent `retro` após a finalização da PR que cria skills
automaticamente conforme aprende com o desenvolvimento de issues/tickets.

## Estrutura

```text
CLAUDE.md                              # memória do projeto (adapte ao seu serviço)
.claude/
├── settings.json                      # permissões + hook de format/build
├── hooks/
│   ├── post-edit.sh                   # PostToolUse: dotnet format + build em arquivos .NET
│   └── guard-task-docs.py             # PreToolUse: planner e retro só escrevem em docs/tasks/
├── agents/
│   ├── explorer.md                    # lê a codebase (somente leitura)
│   ├── planner.md                     # análise + plano, cabeçalho fixo
│   ├── implementer.md                 # TDD, um único agente por ticket
│   ├── reviewer.md                    # revisão do diff (somente leitura)
│   └── retro.md                       # propõe skill, regra ou hook
└── skills/
    ├── task/                          # orquestrador /task
    │   ├── SKILL.md
    │   ├── state.template.json
    │   ├── scripts/
    │   │   ├── check-header.py        # valida o cabeçalho de 02-analise.md
    │   │   ├── qrun.py                # roda dotnet build/test/format e imprime só o resumo
    │   │   ├── test_qrun.py           # testes do qrun.py
    │   │   └── show-changes.sh        # código criado/alterado por commit, em blocos diff
    │   └── templates/                 # 01-ticket, 02-analise, 03-plano, progress-update, 04-retro
    ├── ticket/SKILL.md                # lê o ticket e classifica perguntas
    └── pr/SKILL.md                    # abre a PR com travas de entrada
docs/tasks/                            # uma pasta por ticket, criada pelo /task
```

## Modelos e cores dos subagentes

Cada subagente fixa o próprio `model:` e `color:` no frontmatter, então não herda o modelo do
orquestrador (ex.: orquestrador em Opus, implementação em Sonnet). A cor identifica no terminal
qual agente está rodando.

| Agente | Modelo | Cor | Motivo |
|---|---|---|---|
| explorer | haiku | cyan | só leitura, saída curta, roda muitas vezes |
| planner | opus | purple | análise e plano: erro aqui custa caro adiante |
| implementer | sonnet | green | ciclo TDD longo, plano já aprovado, maior consumo de tokens |
| reviewer | opus | orange | revisão independente do modelo que implementou |
| retro | sonnet | pink | resumo e proposta de melhorias |

Os valores são aliases (`haiku`/`sonnet`/`opus`) e acompanham a versão mais recente. Se a variável
de ambiente `CLAUDE_CODE_SUBAGENT_MODEL` estiver definida, ela sobrescreve o `model:` de todos.

## Instalação

1. Copie o conteúdo deste pacote para a raiz do repositório (mesclando com `.claude/` e
   `CLAUDE.md`, se já existirem).
2. Adapte o `CLAUDE.md`: nome do serviço, stack e regras reais.
3. Garanta que os scripts são executáveis: `chmod +x .claude/hooks/* .claude/skills/task/scripts/*`.
4. Pré-requisitos na máquina: `python`, `dotnet`, `git` e `gh` autenticado (`gh auth login`).
5. Conecte o gerenciador de tarefas (opcional; sem ele, a skill `ticket` usa `gh issue view`):
   ```bash
   claude mcp add --transport http github https://api.githubcopilot.com/mcp/
   claude mcp add --transport http linear https://mcp.linear.app/mcp
   ```
6. Se a branch base não for `main`, ajuste `.claude/agents/reviewer.md`.
7. Faça commit de `.claude/` e `CLAUDE.md`: o harness é código e evolui por PR.

## Uso

```text
/task ENG-1234
```

O mesmo comando inicia e retoma. O orquestrador lê `docs/tasks/<id>/state.json` e segue
da fase em que a tarefa parou.

| Fase (`phase`)                | O que acontece                                        | Você decide?                                  |
| ----------------------------- | ----------------------------------------------------- | --------------------------------------------- |
| `ticket`                      | Skill `ticket` lê e classifica as perguntas           | Se houver bloqueante: responder ou estacionar |
| `awaiting-answers`            | Aguarda respostas no ticket                           | Sim (você ou o PO)                            |
| `explore`                     | Subagent `explorer` mapeia a codebase                 | Não                                           |
| `plan`                        | Subagent `planner` + `check-header.py`                | Não                                           |
| `awaiting-decision` / `split` | Decisão estrutural ou ticket G                        | Sim                                           |
| `plan-review`                 | Resumo do plano                                       | Sim: aprovar, ajustar ou estacionar           |
| `implementing`                | Subagent `implementer`, TDD, `progress-update.md`     | Só se `blocked`                               |
| `validating`                  | `dotnet test` + `reviewer`, até 2 rodadas `[REVISÃO]` | Só na 3ª rodada bloqueada                     |
| `pr`                          | Skill `pr` abre a PR                                  | Não                                           |
| `pr-review`                   | Triagem dos comentários novos da PR                   | Sim, item a item, inclusive Mudança           |
| `done`                        | Subagent `retro` propõe melhorias                     | Sim, proposta a proposta                      |
| `closed`                      | Tarefa encerrada                                      | —                                             |

## Arquivos de cada tarefa (`docs/tasks/<id>/`)

| Arquivo              | Escrito por                           | Conteúdo                                                     |
| -------------------- | ------------------------------------- | ------------------------------------------------------------ |
| `state.json`         | Orquestrador                          | Fase, `outputMode`, perguntas, premissas, `prUrl`            |
| `01-ticket.md`       | Skill `ticket`                        | Resumo do ticket e perguntas classificadas                   |
| `01b-codebase.md`    | Orquestrador (resposta do `explorer`) | Mapa da codebase                                             |
| `02-analise.md`      | `planner`                             | Cabeçalho fixo + análise                                     |
| `03-plano.md`        | `planner`                             | Decisões, premissas, passos, critérios de pronto             |
| `progress-update.md` | `implementer`                         | Subtasks, status, hashes; seções `[REVISÃO]` e `[REVIEW-PR]` |
| `review-<N>.md`      | Orquestrador (resposta do `reviewer`) | Verdict e achados de cada rodada                             |
| `04-retro.md`        | `retro`                               | Propostas e observações                                      |

## Modos de saída

Ao iniciar uma tarefa nova, antes de ler o ticket, o orquestrador pergunta o modo de saída e
grava a escolha em `outputMode` no `state.json`. Retomar a tarefa reaproveita o modo sem
perguntar; `/task ENG-1234 --verbose` ou `--headless` pula a pergunta. Para trocar no meio,
peça ao orquestrador ("mude para modo verboso").

- **Verboso:** saída padrão do Claude Code. O harness não adiciona nenhuma regra de saída:
  comandos rodam direto, agentes respondem como de costume e nada é resumido.
- **Headless:** saída enxuta, descrita abaixo. Vale a seção "Modo headless" da skill `task` e o
  mesmo bloco de cada agente, ativado pela linha `Modo de saída: headless` que o orquestrador
  coloca no início do prompt de cada subagent.

O modo é uma instrução ao modelo, não uma imposição: o que a interface do Claude Code recolhe por
padrão não muda, só o que o harness pede aos agentes. `Ctrl+O` vale nos dois modos.

### Modo headless

- **Comandos:** `dotnet build/test/format` rodam por `qrun.py`. Sucesso vira uma linha
  (`✔ dotnet test · 42 passed · 0 failed · 1 skipped · 3.2s`); falha mostra `✖ ... · exit N` e
  até 40 linhas relevantes. Nada é gravado em disco: o wrapper só imprime. Para mais detalhe de
  uma falha, o agente roda de novo em escopo menor (`dotnet test --filter ...`).
- **Fases:** o orquestrador emite `<id> · <fase> · <detalhe>` antes e depois de cada subagent.
- **Código:** após o `implementer`, o orquestrador roda `show-changes.sh` e cola o diff por
  commit (arquivos novos marcados `(novo)`), sem resumir. Lockfiles, `bin/`, `obj/`, migrations
  geradas e `docs/tasks/` ficam fora; arquivos acima de 150 linhas são truncados com o
  `git show` que mostra o resto.
- **Atalhos nativos:** `Ctrl+O` abre o transcript completo; `/diff` mostra o diff da sessão.
  `/focus` esconde o código das edições, então não é usado por este harness.
- **Testes dos scripts:** `python -m unittest discover -s .claude/skills/task/scripts`.

## Roteiro de adoção (4 semanas)

- [ ] Semana 1: `CLAUDE.md` + hook + skill `ticket` + `state.json`; `/task` só até `explore`.
- [ ] Semana 2: `planner` + `check-header.py` + checkpoint do plano; implementar à mão.
- [ ] Semana 3: `implementer` + `progress-update.md` + `reviewer` com rodadas `[REVISÃO]`.
- [ ] Semana 4: skill `pr` + triagem do review da PR + `retro`.

## Pontos a verificar na sua versão do Claude Code

- **Hooks no frontmatter dos subagents** (`planner.md`, `retro.md`): se a sua versão não
  suportar, mova o `PreToolUse` para o `.claude/settings.json`. Nesse caso ele vale para
  todos os agentes, então restrinja o `matcher` ou ajuste o script.
- **Skills como slash command:** confirme que `/task` aparece no menu. Se não aparecer,
  peça "rode a skill task para ENG-1234".
- **Subagents e diffs:** confirme se, na sua versão, as chamadas internas do `implementer` aparecem
  recolhidas e se o Edit/Write mostra o diff dentro do subagent. O `show-changes.sh` cobre os dois casos.
- **Hook de build:** o `post-edit.sh` roda `dotnet build` a cada edição de arquivo .NET.
  Em soluções grandes, troque por um build do projeto afetado.
