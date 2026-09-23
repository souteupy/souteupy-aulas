# `print()` não é log: observabilidade prática com Python

Nesta aula, você vai separar a saída normal do programa dos registros usados para acompanhar a execução, investigar falhas e operar uma automação sem ficar olhando o terminal.

> A aula expande o post **“Print não é log”** do [@souteu.py](https://www.instagram.com/souteu.py/). O exemplo usa apenas a biblioteca padrão do Python.

## O que você vai aprender

Ao final, você conseguirá:

- decidir quando usar `print()`, exceção, aviso ou logger;
- configurar níveis, formato e contexto com `logging`;
- manter a saída normal em `stdout` e logs em `stderr`;
- registrar o traceback correto com `logger.exception()`;
- gravar arquivos com rotação sem ocupar o disco indefinidamente;
- evitar segredos, dados pessoais desnecessários e entradas forjadas no log.

## Pré-requisitos

- Python 3.10 ou mais recente;
- um terminal;
- noções básicas de funções, exceções e argumentos de linha de comando.

Não há dependências externas.

## O problema

Imagine uma automação que roda de madrugada. Pela manhã, ela não entregou o resultado e deixou apenas isto:

```python
print("deu erro")
```

A frase não informa quando ocorreu, qual parte do programa falou, qual era o pedido, qual a gravidade ou qual exceção aconteceu. Se a saída do processo não foi capturada, talvez nem exista histórico.

O problema não está em `print()`: ele continua adequado para entregar uma resposta ao usuário. O erro é usar uma saída comum como se ela fosse um sistema de registro operacional.

## Modelo mental: saída, evento e falha

| Necessidade | Ferramenta |
|---|---|
| Entregar ao usuário o resultado pedido | `print()` / `stdout` |
| Registrar operação normal ou diagnóstico | `logger.info()` / `logger.debug()` |
| Registrar algo inesperado, mas tolerado | `logger.warning()` |
| Comunicar uma falha ao código chamador | levantar uma exceção |
| Registrar uma exceção tratada com traceback | `logger.exception()` dentro do `except` |
| Avisar quem usa uma biblioteca sobre uso obsoleto ou evitável | `warnings.warn()` |

Um evento de log tem mais do que texto:

- **horário** — quando ocorreu;
- **nível** — qual é a gravidade;
- **origem** — qual logger ou módulo emitiu;
- **mensagem** — o que aconteceu;
- **contexto** — qual pedido, requisição ou tarefa estava envolvida.

O destino vem depois: console, arquivo, coletor centralizado ou plataforma de observabilidade. O código da aplicação registra o evento; handlers decidem para onde ele vai.

## Os cinco níveis

Do menor para o maior:

| Nível | Use quando |
|---|---|
| `DEBUG` | detalhe útil durante diagnóstico, normalmente desligado |
| `INFO` | uma etapa normal começou ou terminou |
| `WARNING` | algo inesperado ocorreu, mas o fluxo ainda funciona |
| `ERROR` | uma operação não pôde ser concluída |
| `CRITICAL` | a aplicação pode não conseguir continuar |

Sem configuração, o logger raiz começa em `WARNING`. Por isso `DEBUG` e `INFO` não aparecem no exemplo mínimo. Escolher tudo como `ERROR` não aumenta a observabilidade: apenas destrói o significado dos níveis.

## Tutorial passo a passo

### 1. Conheça os arquivos

Esta pasta contém:

- [`app.py`](./app.py) — automação fictícia que processa um pedido;
- [`log_config.py`](./log_config.py) — configuração central dos handlers e do formato;
- [`test_app.py`](./test_app.py) — testes de níveis, contexto, traceback, rotação e segurança.

### 2. Execute o caminho normal

```bash
python app.py --pedido-id PED-42 --quantidade 3
```

O programa produz dois fluxos diferentes. Em `stdout`, a resposta para quem chamou:

```json
{"pedido_id": "PED-42", "itens_processados": 3, "status": "concluído"}
```

Em `stderr`, os eventos operacionais:

```text
2026-09-23 00:38:20,997 | INFO | automacao | pedido_id=PED-42 | Processamento iniciado; quantidade=3
2026-09-23 00:38:20,997 | INFO | automacao | pedido_id=PED-42 | Processamento concluído; quantidade=3
```

O horário muda a cada execução. Essa separação permite redirecionar a resposta para outro programa sem misturá-la com diagnóstico.

No Windows PowerShell 5.1, use `cmd /c` para preservar os bytes emitidos pelo
processo. O redirecionamento nativo dessa versão pode reformatar `stderr` como
`NativeCommandError` e gravar os arquivos em UTF-16LE:

```powershell
cmd /d /c "python app.py 1>resultado.json 2>execucao.log"
```

No Bash:

```bash
python app.py > resultado.json 2> execucao.log
```

### 3. Configure uma vez

Em [`log_config.py`](./log_config.py), cada handler recebe o mesmo formatador:

```python
FORMATO = (
    "%(asctime)s | %(levelname)s | %(name)s | "
    "pedido_id=%(pedido_id)s | %(message)s"
)
```

O logger se chama `automacao`, não usa o logger raiz e tem `propagate = False`. Isso evita que o mesmo evento suba para um handler ancestral e apareça duplicado.

A configuração central também é idempotente: handlers antigos são fechados e removidos antes de uma nova configuração. Isso ajuda em testes e processos que recarregam configurações.

### 4. Adicione contexto sem concatenar tudo

O exemplo usa `LoggerAdapter`:

```python
logger = logging.LoggerAdapter(
    logger_base,
    extra={"pedido_id": pedido_id},
)
```

Todas as chamadas feitas com esse adapter carregam `pedido_id`. Um filtro fornece `pedido_id=-` quando outro código usa o logger sem o adapter, evitando erro no formatador.

Para valores variáveis na mensagem, passe argumentos separados:

```python
logger.info("Processamento iniciado; quantidade=%s", quantidade)
```

O `logging` adia a interpolação até saber que o nível está habilitado. Evite uma f-string só para um log que pode ser descartado:

```python
# Funciona, mas calcula a string mesmo com DEBUG desligado.
logger.debug(f"Resposta completa: {resposta_custosa()}")
```

Se o próprio argumento for caro de produzir, proteja a operação:

```python
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Resposta completa: %s", resposta_custosa())
```

### 5. Mude o nível sem editar o código

```bash
python app.py --log-level DEBUG
```

Ou configure por ambiente:

```powershell
$env:LOG_LEVEL = "DEBUG"
python app.py
Remove-Item Env:LOG_LEVEL
```

```bash
LOG_LEVEL=DEBUG python app.py
```

Com `DEBUG`, aparece a validação intermediária. Um valor desconhecido, como `VERBOSE`, é rejeitado antes do processamento.

### 6. Registre uma exceção com traceback

```bash
python app.py --falhar
```

A execução termina com código `1`, não imprime resultado em `stdout` e registra a exceção em `stderr`:

```text
ERROR | automacao | pedido_id=PED-42 | Processamento falhou
Traceback (most recent call last):
...
RuntimeError: falha simulada no provedor
```

O código responsável é:

```python
try:
    resultado = processar_pedido(...)
except RuntimeError:
    logger.exception("Processamento falhou")
    return 1
```

`logger.exception()` deve ser usado dentro do tratamento da exceção atual. Ele registra em `ERROR` e inclui o traceback. Registrar não corrige a falha: o programa ainda precisa devolver um estado coerente, tentar novamente quando for seguro ou encerrar.

### 7. Grave em arquivo com rotação

Para manter uma cópia local:

```bash
python app.py --log-file logs/automacao.log
```

O exemplo usa `RotatingFileHandler` com limite de 1 MB e três backups. Quando o arquivo atinge o limite, surgem `automacao.log.1`, `automacao.log.2` e `automacao.log.3`; os mais antigos são descartados.

Rotação limita o uso do disco, mas não define sozinha retenção legal, backup, busca ou alertas. Esses pontos pertencem à operação do sistema.

## Teste você mesmo

Execute:

```bash
python -m unittest -v
```

Os 12 testes verificam que:

- nível desconhecido é rejeitado;
- `DEBUG` some quando o limiar é `INFO`;
- o contexto do pedido entra em cada evento;
- o arquivo gira e respeita a quantidade de backups;
- `WARNING` representa um pedido ignorado;
- `logger.exception()` inclui o traceback;
- `stdout` contém só a resposta e `stderr` contém os logs;
- a falha devolve código `1` sem uma falsa resposta de sucesso;
- um token fictício do ambiente não aparece nas saídas;
- um identificador com quebra de linha é rejeitado antes de chegar ao log.

Para provar a separação dos fluxos:

```powershell
cmd /d /c "python app.py 1>resultado.json 2>execucao.log"
Get-Content resultado.json
Get-Content execucao.log
```

```bash
python app.py > resultado.json 2> execucao.log
cat resultado.json
cat execucao.log
```

## Dicas e truques

### Descubra de onde um evento veio

Use um logger por módulo:

```python
logger = logging.getLogger(__name__)
```

Em aplicações com vários módulos, nomes hierárquicos como `meuapp.pagamentos` permitem aumentar o detalhe somente em uma área.

### Evite a mensagem duplicada

Se você adiciona um handler a um logger filho e o evento também se propaga para o logger raiz, ele pode ser emitido duas vezes. Configure handlers na raiz **ou** no logger da aplicação; se escolher o segundo, use `propagate = False`, como no exemplo.

### Não chame `basicConfig()` em bibliotecas

A aplicação decide formato, nível e destino. Uma biblioteca reutilizável deve apenas criar `logging.getLogger(__name__)` e emitir eventos; configurar o logger raiz surpreende todos os consumidores.

### Um evento deve responder uma pergunta

Prefira:

```text
pedido_id=PED-42 | Processamento falhou
```

em vez de:

```text
deu ruim
```

Inclua identificadores estáveis e estado suficiente para correlacionar eventos. Não despeje objetos inteiros “por garantia”.

### Teste logs como comportamento

Use um stream em memória ou `assertLogs` do `unittest`. Evite testes que dependem do horário exato. Nesta aula, os testes procuram nível, logger, contexto e mensagem, deixando o timestamp variar.

## Erros comuns

### `INFO` não aparece

**Sintoma:** `logger.info()` parece não funcionar.<br>
**Causa:** o limiar padrão é `WARNING` ou um handler filtra níveis menores.<br>
**Correção:** configure o nível antes do primeiro evento e confira o nível do logger e dos handlers.

### A mesma linha aparece duas vezes

**Sintoma:** eventos duplicados.<br>
**Causa:** handler no logger filho e propagação para um ancestral também configurado.<br>
**Correção:** centralize handlers ou desative a propagação conscientemente.

### `basicConfig()` não muda nada

**Sintoma:** uma segunda configuração é ignorada.<br>
**Causa:** `basicConfig()` normalmente não faz nada quando o logger raiz já tem handlers.<br>
**Correção:** configure uma vez no ponto de entrada. Em testes isolados, controle handlers explicitamente; use `force=True` somente quando você realmente pretende substituir a configuração global.

### O arquivo ocupa o disco inteiro

**Sintoma:** `automacao.log` cresce sem limite.<br>
**Causa:** `FileHandler` apenas acrescenta linhas.<br>
**Correção:** use rotação, retenção e monitoramento de espaço. Em contêiner, prefira o fluxo coletado pela plataforma.

### O traceback sumiu

**Sintoma:** o log mostra “falhou”, mas não a pilha.<br>
**Causa:** foi usado `logger.error("falhou")` sem `exc_info`, ou o registro ocorreu fora do `except`.<br>
**Correção:** use `logger.exception()` dentro do `except`.

### Alguém forjou outra linha no log

**Sintoma:** um identificador recebido externamente contém `\nERROR ...` e cria uma linha visualmente falsa.<br>
**Causa:** dado não confiável foi interpolado sem validação ou codificação.<br>
**Correção:** use um formato estruturado ou valide/escape caracteres de controle. O exemplo aceita apenas letras, números, ponto, `_` e `-` em `pedido_id`.

## Log não é lixeira

Nunca registre deliberadamente:

- senhas, tokens, chaves de API ou cookies de sessão;
- números completos de cartão ou credenciais em URLs;
- corpos e cabeçalhos completos de requisições sem revisão;
- dados pessoais que não sejam necessários à finalidade do evento.

“Depois eu mascaro” é uma defesa fraca: filtros cobrem apenas padrões conhecidos, enquanto segredos surgem em mensagens, exceções e objetos inesperados. A primeira defesa é não enviar o valor ao logger. O teste desta aula define `APP_TOKEN` com um valor fictício e comprova que ele não aparece em `stdout` nem em `stderr`.

Logs também são dados: limite acesso, proteja integridade, monitore volume e apague de acordo com uma política de retenção. Um invasor pode tentar ler segredos, forjar eventos ou encher o disco.

## Em um ambiente real

### Configuração

Defina o nível fora do código (`LOG_LEVEL`) e mantenha a configuração no ponto de entrada. Desenvolvimento pode usar `DEBUG`; produção normalmente começa em `INFO` ou `WARNING`. Não habilite `DEBUG` permanentemente sem avaliar volume e conteúdo.

### Deploy e coleta

Em CLI, logs em `stderr` preservam `stdout` para a resposta. Em contêineres e plataformas gerenciadas, o ambiente de execução costuma capturar os fluxos do processo; evite escrever arquivo dentro de um contêiner efêmero sem motivo operacional claro. A abordagem Twelve-Factor recomenda tratar logs como fluxo de eventos e delegar roteamento e armazenamento à plataforma.

### Contexto e formato

Inclua IDs de correlação — requisição, tarefa, pedido — e campos estáveis. Em escala, logs estruturados (por exemplo, JSON) simplificam busca e agregação, mas o esquema precisa ser documentado. OpenTelemetry define um modelo para correlacionar logs com traces e métricas; isso é um próximo passo, não requisito para este exemplo.

### Segurança e privacidade

Crie uma lista permitida de campos registráveis, não uma lista infinita do que mascarar. Valide dados não confiáveis para evitar injeção de log. Restrinja quem lê, escreve e apaga; transmita para o coletor por canal protegido; defina retenção proporcional à finalidade e à legislação aplicável.

### Alertas e falhas

Log não é alerta. Um evento `ERROR` só gera ação se a plataforma tiver regra, destino e responsável. Monitore taxa de erros, latência, fila, uso de disco e ausência de eventos esperados. Se o sistema de logs estiver indisponível, decida se a aplicação continua, aplica buffer limitado ou falha — nunca deixe uma fila sem limite consumir toda a memória.

### Concorrência

O módulo `logging` é seguro para múltiplas threads de um processo. Vários processos escrevendo diretamente no mesmo arquivo exigem outra arquitetura: `QueueHandler`/`QueueListener`, um coletor ou o fluxo da plataforma. O cookbook oficial alerta que handlers de arquivo comuns não serializam múltiplos processos.

## Desafio rápido

Adicione a opção `--formato json` e implemente um `logging.Formatter` que escreva um objeto JSON por linha com `timestamp`, `level`, `logger`, `pedido_id` e `message`.

<details>
<summary>Critérios para considerar o desafio pronto</summary>

1. Cada linha deve ser JSON válido independentemente das outras.
2. Quebras de linha da mensagem precisam ser escapadas pelo encoder JSON.
3. `pedido_id` deve continuar validado.
4. O token fictício do teste não pode aparecer.
5. Exceções precisam manter tipo, mensagem e traceback sem transformar a linha em JSON inválido.

</details>

## Resumo

- `print()` entrega saída; `logging` registra eventos para operação e investigação.
- Nível, origem, horário e contexto tornam o evento pesquisável e acionável.
- `stdout` e `stderr` separados facilitam automação e coleta.
- `logger.exception()` preserva o traceback quando usado dentro do `except`.
- Rotação controla crescimento local; retenção, busca e alerta dependem da infraestrutura.
- A defesa mais segura contra vazamento é nunca enviar segredos ao logger.

## Para estudar mais

- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html) — tutorial oficial sobre níveis, configuração, arquivos, formatação e exceções.
- [Referência do módulo `logging`](https://docs.python.org/3/library/logging.html) — API oficial de loggers, handlers, filtros, formatadores e records.
- [`logging.handlers`](https://docs.python.org/3/library/logging.handlers.html) — referência oficial de rotação, filas, rede e outros destinos.
- [Python Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html) — receitas oficiais para múltiplos módulos, processos, contexto e configuração avançada.
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) — seleção de eventos, proteção de dados, injeção, retenção e ataques contra logs.
- [The Twelve-Factor App: Logs](https://12factor.net/logs) — modelo de logs como fluxo capturado pelo ambiente de execução.
- [OpenTelemetry Logging](https://opentelemetry.io/docs/specs/otel/logs/) — modelo para integrar logs existentes com traces, métricas e coletores.
