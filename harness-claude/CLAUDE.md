# <Nome do serviço>

## Stack
.NET 10, ASP.NET Core Minimal APIs, EF Core, PostgreSQL, xUnit.

## Arquitetura
Hexagonal + DDD + CQRS.
- Domain não referencia nenhum outro projeto.
- Application expõe Commands/Queries via MediatR.
- Infrastructure implementa as Ports definidas em Application.

## Comandos
- Build: dotnet build
- Testes: dotnet test
- Format: dotnet format

## Regras
- Toda feature nova começa por um teste que falha.
- Nunca editar migrations já aplicadas.
- Commits no padrão Conventional Commits, citando o ticket (ex.: feat(ENG-1234): ...).
- Rodar build/test/format por `python .claude/skills/task/scripts/qrun.py <rótulo> -- <comando>` e não colar
  output bruto de ferramenta nas respostas; o código criado/alterado continua sendo exibido.

## Fluxo de tarefas
- Toda tarefa começa por `/task <id>`. O estado fica em `docs/tasks/<id>/`.
- Nunca fazer merge de PR; o merge é do humano.
