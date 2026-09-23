# Ambientes virtuais em Python: um projeto não bagunça o outro

Nesta aula, você vai isolar dependências com `venv`, provar qual interpretador está em uso, recriar o ambiente em outra máquina e aplicar truques que evitam os erros mais comuns do dia a dia.

> Esta aula expande o post de ambiente virtual do [@souteu.py](https://www.instagram.com/souteu.py/). O carrossel mostra o caminho básico; aqui ele vira um exemplo executável, com testes e uso em ambiente real.

## O que você vai aprender

Ao final, você conseguirá:

- explicar o que um ambiente virtual isola — e o que ele não isola;
- criar, ativar e usar um ambiente sem depender do prompt do terminal;
- provar em qual ambiente um comando está rodando;
- registrar e recriar dependências com `requirements.txt`;
- aplicar truques de produtividade e proteção contra instalação no Python errado;
- decidir quando `venv` basta e quando um gerenciador como o `uv` ajuda.

## Pré-requisitos

- Python 3.10 ou mais recente;
- um terminal (PowerShell, bash ou zsh);
- noções básicas de `pip install`.

## O problema

Dois projetos na mesma máquina, o mesmo Python do sistema:

- o projeto A depende de uma versão antiga de uma biblioteca;
- o projeto B precisa da versão nova;
- você atualiza para o B e o A para de funcionar.

Sem isolamento, `site-packages` é uma prateleira compartilhada: só existe uma versão instalada de cada pacote por interpretador. Não há como satisfazer os dois ao mesmo tempo.

Em muitos sistemas o problema é ainda mais direto: o Python que vem com o sistema operacional é usado por ferramentas do próprio sistema. Por isso distribuições modernas marcam esse interpretador como “externally managed” e o `pip` recusa a instalação, sugerindo um ambiente virtual.

## Modelo mental

Um ambiente virtual é **uma pasta com um `site-packages` próprio**, criada a partir de um Python já instalado — a “base”.

Três fatos que explicam quase tudo:

1. O ambiente **não contém outro Python**: ele aponta para o interpretador base registrado em `pyvenv.cfg`.
2. Quando o interpretador do ambiente roda, `sys.prefix` aponta para a pasta do ambiente e `sys.base_prefix` continua apontando para a instalação base. Fora de um ambiente, os dois são iguais.
3. Ativar é conveniência: o script de ativação ajusta o `PATH` da sessão. Chamar `.venv/Scripts/python.exe` (ou `.venv/bin/python`) direto produz exatamente o mesmo isolamento.

| Item | Isolado por um venv? |
|---|---|
| Pacotes instalados com `pip` | Sim |
| Executáveis criados por pacotes (`black`, `pytest`) | Sim |
| Versão do interpretador | Não — é a do Python base |
| Variáveis de ambiente e segredos | Não |
| Arquivos, rede e permissões do sistema | Não |

A última linha importa: **venv não é sandbox de segurança**. Ele não protege você de código malicioso instalado por engano.

## Tutorial passo a passo

### 1. Crie o ambiente

Nesta pasta:

```bash
python -m venv .venv
```

No Linux ou macOS, pode ser necessário usar `python3 -m venv .venv`.

### 2. Ative (ou nem ative)

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# Linux ou macOS
source .venv/bin/activate
```

Se o PowerShell bloquear a execução do script de ativação, você não precisa mudar a política de segurança da máquina: chame o interpretador do ambiente diretamente.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Essa forma também é a mais confiável em scripts de CI e em tarefas agendadas, onde “ativar” costuma não fazer sentido.

### 3. Instale as dependências

```bash
python -m pip install -r requirements.txt
```

Use `python -m pip` em vez de `pip`. Assim o pacote vai para o interpretador que você chamou, e não para o primeiro `pip` que aparecer no `PATH`.

### 4. Prove onde você está

Não confie apenas no `(.venv)` do prompt: ele é um texto configurável e pode ficar desatualizado. O arquivo [`inspetor.py`](./inspetor.py) faz a verificação que vale:

```python
def esta_em_ambiente_virtual(modulo_sys=sys) -> bool:
    return modulo_sys.prefix != modulo_sys.base_prefix
```

Execute:

```bash
python inspetor.py
```

Saída obtida em uma máquina Windows com Python 3.11.16 (os caminhos variam):

```text
Python............: 3.11.16
Ambiente virtual..: sim
sys.prefix........: ...\aulas\ambientes-virtuais-em-python\.venv
sys.base_prefix...: ...\Python311
VIRTUAL_ENV.......: (não definida)
pyvenv.cfg........: ...\.venv\pyvenv.cfg
site-packages do usuário ativo: não
Pacotes visíveis..: 3
```

Repare que `VIRTUAL_ENV` pode estar vazia mesmo com o isolamento funcionando: ela só é definida pelo script de ativação. Quando você chama o interpretador diretamente, o isolamento existe e a variável não. É por isso que ela não serve como prova.

Para usar o inspetor como porteiro em um script ou pipeline:

```bash
python inspetor.py --exigir-venv
```

Fora de um ambiente virtual ele termina com código diferente de zero e a mensagem `ErroDeAmbiente: Este interpretador não está em um ambiente virtual.`

### 5. Registre e recrie

Com o ambiente em uso:

```bash
python -m pip freeze > requirements.txt
```

Na outra máquina, crie um ambiente novo e instale:

```bash
python -m venv .venv
python -m pip install -r requirements.txt
```

Nunca versione a pasta `.venv`. Ela contém caminhos absolutos e binários da sua máquina; o que se versiona é o código e a lista de dependências.

## Teste você mesmo

```bash
python -m unittest -v
```

Os 10 testes comprovam que:

- a detecção usa `sys.prefix` e `sys.base_prefix`;
- a variável `VIRTUAL_ENV` não é aceita como prova;
- `pyvenv.cfg` é localizado quando existe;
- a saída JSON é válida;
- `--exigir-venv` falha fora de um ambiente virtual e passa dentro dele;
- o relatório não imprime outras variáveis de ambiente.

## Truques que valem o tempo

### 1. Prompt com o nome do projeto

```bash
python -m venv --prompt . .venv
```

O `.` usa o nome da pasta atual como prefixo do prompt, em vez de `(.venv)` repetido em todo projeto. O valor fica gravado em `pyvenv.cfg`:

```text
prompt = 'venvlab'
```

### 2. Impedir instalação no Python errado

```bash
export PIP_REQUIRE_VIRTUALENV=1       # Linux/macOS
```

```powershell
$env:PIP_REQUIRE_VIRTUALENV = "1"     # PowerShell, sessão atual
```

Com essa variável, um `pip install` distraído fora de um ambiente falha assim:

```text
ERROR: Could not find an activated virtualenv (required).
```

Dentro do ambiente, o mesmo comando funciona normalmente. É uma rede de proteção barata para quem alterna entre vários terminais.

### 3. Configuração de `pip` por ambiente

Cada ambiente pode ter seu próprio arquivo de configuração — `.venv/pip.ini` no Windows, `$VIRTUAL_ENV/pip.conf` no Linux e macOS. Para descobrir o caminho exato:

```bash
python -m pip config debug
```

A seção `site:` mostra o arquivo daquele ambiente, mesmo que ele ainda não exista (`exists: False`). Útil para fixar um índice interno em um projeto sem alterar a configuração global da máquina.

### 4. Separar o que você pediu do que veio junto

```bash
python -m pip list --not-required --format=freeze
```

`pip freeze` lista tudo que está instalado, inclusive dependências transitivas. O comando acima mostra apenas os pacotes que nada mais requer — quase sempre é essa a lista que você realmente escolheu instalar, acrescida das ferramentas de base do próprio ambiente (`pip` e, em versões anteriores à 3.12, `setuptools`). Ela ajuda a manter um `requirements.txt` legível, mas não substitui o `freeze` quando você quer reprodutibilidade exata.

### 5. Ambiente é descartável — recrie sem medo

```bash
python -m venv --clear .venv
```

`--clear` apaga o conteúdo do diretório antes de recriar. Quando algo fica estranho, recriar costuma ser mais rápido que investigar. Mantenha `requirements.txt` atualizado e essa operação fica sem custo.

Outras opções úteis do mesmo comando:

- `--upgrade-deps`: já cria o ambiente com o `pip` atualizado;
- `--system-site-packages`: dá acesso aos pacotes da instalação base (use com parcimônia, porque enfraquece o isolamento);
- `--upgrade`: ajusta o ambiente depois de uma atualização do Python base feita no mesmo lugar.

A partir do Python 3.13, `venv` também grava um `.gitignore` dentro da pasta do ambiente. Em versões anteriores — como a 3.11 usada nos testes desta aula — esse arquivo não é criado, então acrescente `.venv/` ao `.gitignore` do projeto você mesmo.

### 6. Script com dependência declarada no próprio arquivo

Para um script solto, criar um projeto inteiro é exagero. O formato de metadados embutidos permite declarar a dependência dentro do arquivo, e o `uv` cria o ambiente sob demanda:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["cowsay==6.1"]
# ///
```

```bash
uv run demo_uv.py
```

Saída obtida nos testes:

```text
Installed 1 package in 92ms
Ambiente usado por este script: ...\uv\cache\environments-v2\demo-uv-513f02e84f1fb210
```

O ambiente vive no cache do `uv`, não na sua pasta. O `uv` é uma ferramenta de terceiros e precisa ser instalado à parte; o formato de metadados, esse sim, é um padrão da linguagem.

## Erros comuns

### `pip install` instalou, mas o `import` falha

**Sintoma:** o pacote aparece instalado e o programa não encontra.<br>
**Causa:** o `pip` do `PATH` pertence a outro interpretador.<br>
**Correção:** use `python -m pip install` e confira `python inspetor.py`.

### Movi ou renomeei a pasta do ambiente e parou de funcionar

**Sintoma:** os executáveis do ambiente deixam de rodar, mesmo que o `import` ainda funcione.<br>
**Causa:** os scripts instalados guardam o caminho absoluto do interpretador. No teste desta aula, após renomear a pasta, `cowsay.exe` saiu com código 1 enquanto `python.exe -c "import cowsay"` ainda funcionou.<br>
**Correção:** ambientes não são portáteis. Recrie no novo caminho com `python -m venv` e reinstale a partir do `requirements.txt`.

### `error: externally-managed-environment`

**Sintoma:** o `pip` recusa instalar no Python do sistema.<br>
**Causa:** a distribuição marcou a instalação base como gerenciada externamente.<br>
**Correção:** crie e use um ambiente virtual. Evite forçar a instalação global só para “sair do erro”.

### O `.venv` foi parar no repositório

**Sintoma:** o repositório fica pesado e os arquivos não funcionam em outra máquina.<br>
**Causa:** a pasta não foi ignorada.<br>
**Correção:** adicione `.venv/` ao `.gitignore` e remova do índice com `git rm -r --cached .venv`.

### Achei que estava isolado porque o prompt mostrava `(.venv)`

**Sintoma:** a instalação foi para outro lugar.<br>
**Causa:** o prompt é texto; pode estar personalizado ou vir de outro shell.<br>
**Correção:** verifique `sys.prefix`, como faz o inspetor.

### O ambiente virtual não me protege de um pacote malicioso

**Sintoma:** expectativa errada de segurança.<br>
**Causa:** o isolamento é de pacotes, não de privilégios.<br>
**Correção:** trate a instalação de dependências como execução de código de terceiros: fixe versões, revise o que instala e, para código desconhecido, use uma máquina ou contêiner descartável.

## Em um ambiente real

### Desenvolvimento e CI

Padronize um ambiente por projeto, sempre em `.venv`, e chame o interpretador pelo caminho completo nos scripts de automação. Em CI, crie o ambiente do zero a cada execução: é isso que revela dependência faltando no `requirements.txt` antes que o problema chegue em produção.

Fixe versões (`pacote==versão`) para builds reproduzíveis. `pip freeze` registra o que está instalado; ele não é um lockfile com hashes nem garante compatibilidade entre sistemas operacionais e versões de Python diferentes. Quando isso for necessário, avalie ferramentas de lock dedicadas.

### Deploy

Em contêiner, o isolamento do ambiente já vem da imagem, mas um ambiente virtual continua útil para separar as dependências da aplicação daquelas do sistema e para copiar apenas o necessário entre estágios de build. Nunca copie um `.venv` da sua máquina para a imagem: reinstale a partir do `requirements.txt`.

Cuidado com contas de serviço: a aplicação deve rodar com o interpretador do ambiente definido no processo (`ExecStart` do systemd, `CMD` do Docker), não depender de um `activate` executado por alguém.

### Segurança e observabilidade

- fixe versões e revise atualizações de dependência como revisa código;
- prefira índices confiáveis e, em ambiente corporativo, um espelho interno configurado por projeto;
- registre no log de inicialização a versão do Python e do pacote principal — isso encurta o diagnóstico de “funciona na minha máquina”;
- nunca coloque credenciais dentro do ambiente virtual ou de `requirements.txt`; configuração sensível vem do ambiente do processo ou de um gerenciador de segredos.

### Falhas típicas em produção

Uma atualização do Python base pode quebrar ambientes criados com a versão anterior, porque o ambiente aponta para o interpretador base. Trate atualização de interpretador como mudança de infraestrutura: recrie os ambientes e rode os testes antes de liberar.

## Desafio rápido

Acrescente ao `inspetor.py` a opção `--exigir-pacotes requests,cowsay`, que falha quando algum dos pacotes informados não está instalado no ambiente atual. Use `importlib.metadata` e escreva testes para: pacote presente, pacote ausente e lista vazia.

<details>
<summary>Pistas</summary>

1. `importlib.metadata.version("cowsay")` levanta `PackageNotFoundError` quando o pacote não existe.
2. Trate a lista separada por vírgulas e ignore espaços em branco.
3. Reaproveite `ErroDeAmbiente` para manter uma única forma de falhar.

</details>

## Resumo

- Um ambiente virtual dá a cada projeto o seu próprio `site-packages`, criado sobre um Python já instalado.
- `sys.prefix != sys.base_prefix` é a prova; o prompt e `VIRTUAL_ENV` não são.
- Ativar é conveniência: chamar o interpretador do ambiente pelo caminho funciona igual e é melhor para automação.
- Ambientes são descartáveis e não portáteis: versione `requirements.txt`, nunca a pasta `.venv`.
- O isolamento é de pacotes; segredos e segurança são outro assunto.

## Para estudar mais

- [Documentação do módulo `venv`](https://docs.python.org/3/library/venv.html) — criação, opções, `pyvenv.cfg`, `sys.prefix` e a nota de que ambientes não são portáteis.
- [PEP 405 – Python Virtual Environments](https://peps.python.org/pep-0405/) — a proposta que originou o mecanismo e explica suas decisões de projeto.
- [Python Packaging User Guide: instalar pacotes com pip e venv](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/) — o passo a passo oficial de empacotamento.
- [Externally Managed Environments (PEP 668)](https://packaging.python.org/en/latest/specifications/externally-managed-environments/) — por que o `pip` recusa instalar no Python do sistema.
- [Referência da linha de comando do pip](https://pip.pypa.io/en/stable/cli/pip/) — documenta `--require-virtualenv` e a variável `PIP_REQUIRE_VIRTUALENV`.
- [Configuração do pip](https://pip.pypa.io/en/stable/topics/configuration/) — níveis global, usuário e por ambiente, incluindo `$VIRTUAL_ENV/pip.conf`.
- [PEP 723 – Inline script metadata](https://peps.python.org/pep-0723/) — o padrão para declarar dependências dentro de um script.
- [uv: executando scripts](https://docs.astral.sh/uv/guides/scripts/) — como o `uv` cria ambientes sob demanda a partir desses metadados.
