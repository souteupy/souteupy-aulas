# Variáveis de ambiente em Python: configuração sem segredo no código

Nesta aula, você vai tirar configurações do código, carregá-las de forma previsível e falhar com uma mensagem clara quando algo estiver ausente — sem imprimir credenciais no terminal.

> Esta aula expande o [segundo post do @souteu.py](https://www.instagram.com/p/DU-GVoajtb7/), publicado em 19/02/2026. O pacote local não contém a página 5 do carrossel; a aula usa somente o conteúdo disponível e fontes verificadas.

## O que você vai aprender

Ao final, você conseguirá:

- ler variáveis com `os.getenv()`;
- usar um arquivo `.env` apenas como conveniência local;
- definir precedência entre o ambiente do sistema e o `.env`;
- validar configurações obrigatórias antes de iniciar a aplicação;
- evitar vazamento de segredos em código, Git e logs;
- decidir quando migrar para um gerenciador de segredos.

## Pré-requisitos

- Python 3.10 ou mais recente;
- um terminal;
- noções básicas de funções e exceções.

## O problema

O post parte de um erro comum:

```python
SENHA = "SUA_SENHA_SEGURA"
```

Isso pode funcionar em um teste rápido, mas mistura código com uma configuração que muda entre máquinas e ambientes. Se o arquivo for enviado ao Git, copiado para uma imagem ou incluído em um log, trocar o código não apaga todas as cópias do segredo.

A solução não é “esconder” a senha em outra variável Python. É fornecer a configuração ao processo em tempo de execução e manter valores reais fora do repositório.

## Modelo mental

Há três peças diferentes:

1. **Código:** conhece apenas nomes como `APP_API_TOKEN`.
2. **Ambiente do processo:** contém pares de texto `NOME=valor` disponíveis durante a execução.
3. **Fonte do valor:** pode ser o terminal, a plataforma de deploy, o CI/CD, um arquivo `.env` local ou um gerenciador de segredos.

O módulo `os` lê o ambiente que o processo recebeu. Já `python-dotenv` interpreta um arquivo `.env` e adiciona seus pares a `os.environ`. Portanto, `.env` não é um cofre nem um recurso especial do Python: é um arquivo de texto usado como conveniência, principalmente no desenvolvimento local.

Nesta aula, variáveis já definidas no ambiente têm prioridade sobre o arquivo porque usamos `override=False`.

## Tutorial passo a passo

### 1. Prepare o ambiente

Entre nesta pasta e crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative-o:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# Linux ou macOS
source .venv/bin/activate
```

Instale a dependência:

```bash
python -m pip install -r requirements.txt
```

### 2. Crie sua configuração local

O repositório contém apenas [`.env.example`](./.env.example), com nomes esperados e valores fictícios. Faça uma cópia local:

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# Linux ou macOS
cp .env.example .env
```

O `.gitignore` do repositório ignora `.env`, mas mantém `.env.example`. Confirme antes de commitar:

```bash
git status --short
```

Nunca coloque uma credencial real em `.env.example`.

### 3. Carregue e valide

O arquivo [`app.py`](./app.py) carrega o `.env` sem substituir uma variável já fornecida pelo sistema:

```python
load_dotenv(dotenv_path=caminho_env, override=False)

api_url = validar_url_http("APP_API_URL", ler_obrigatoria("APP_API_URL"))
api_token = ler_obrigatoria("APP_API_TOKEN")
debug = ler_booleano("APP_DEBUG", padrao=False)
```

`ler_obrigatoria()` rejeita valor ausente ou vazio. `ler_booleano()` não usa `bool(texto)`, pois `bool("false")` também seria `True`: em Python, qualquer string não vazia é verdadeira.

A configuração é representada por uma `dataclass`. O campo `api_token` usa `repr=False`, o que reduz o risco de exibição acidental ao inspecionar o objeto. Isso é uma proteção adicional, não autorização para registrar o objeto sem cuidado.

### 4. Execute sem revelar o segredo

```bash
python app.py
```

Saída esperada:

```text
Configuração carregada.
API host: api.example.com
Debug: desligado
Token: configurado (valor oculto)
```

O programa confirma que o token existe, mas não mostra seu conteúdo.

### 5. Sobrescreva por ambiente

O arquivo local é útil durante o desenvolvimento. Em deploy, a plataforma pode injetar os valores diretamente.

No PowerShell:

```powershell
$env:APP_DEBUG = "true"
python app.py
Remove-Item Env:APP_DEBUG
```

No Bash:

```bash
APP_DEBUG=true python app.py
```

Como `override=False`, esse `APP_DEBUG=true` vence o `APP_DEBUG=false` do `.env`.

## Teste você mesmo

Execute:

```bash
python -m unittest -v
```

Os testes comprovam que:

- o `.env` é carregado;
- o ambiente do processo tem prioridade;
- configuração obrigatória ausente interrompe a inicialização;
- URL e booleano inválidos são rejeitados;
- o resumo e o `repr` da configuração não exibem o token.

Teste também a falha rápida:

```powershell
# Windows PowerShell 5.1 ou mais recente
$tokenAnterior = [Environment]::GetEnvironmentVariable("APP_API_TOKEN", "Process")
try {
    $env:APP_API_TOKEN = " "
    python app.py
}
finally {
    if ($null -eq $tokenAnterior) {
        Remove-Item Env:APP_API_TOKEN -ErrorAction SilentlyContinue
    }
    else {
        $env:APP_API_TOKEN = $tokenAnterior
    }
}
```

```bash
# Linux ou macOS
APP_API_TOKEN=' ' python app.py
```

O valor contém um espaço para continuar presente no ambiente, inclusive no PowerShell 5.1, mas é rejeitado depois de `strip()`. No PowerShell, o bloco `finally` restaura o valor anterior ou remove somente a variável criada pelo teste. No Bash, a atribuição vale apenas para esse comando.

A última linha esperada do traceback é:

```text
ErroDeConfiguracao: Variável obrigatória ausente: APP_API_TOKEN
```

<details>
<summary>Por que falhar na inicialização?</summary>

Uma aplicação sem credencial obrigatória não está pronta para servir tráfego. Interromper cedo produz um erro direto; continuar costuma gerar uma falha distante e mais difícil de diagnosticar.

</details>

## Dicas e truques

- Use nomes com prefixo, como `APP_`, para separar suas variáveis das do sistema.
- Trate tudo que vem do ambiente como texto: converta e valide booleanos, números, URLs e listas.
- Documente nomes e exemplos fictícios em `.env.example`, nunca valores reais.
- Mantenha `override=False` quando a configuração injetada pelo deploy deve vencer o arquivo local.
- Não imprima o dicionário de ambiente, a configuração inteira nem cabeçalhos de autenticação.
- Configuração não secreta também pertence fora do código quando varia entre deploys.

## Erros comuns

### “Adicionei `.env` ao `.gitignore`; agora o segredo está seguro”

**Sintoma:** o arquivo não aparece em novos commits, mas o valor já existe no histórico.<br>
**Causa:** `.gitignore` não remove arquivos que já foram versionados.<br>
**Correção:** revogue ou rotacione o segredo primeiro. Depois avalie a remoção do histórico e a limpeza de clones com o procedimento oficial do GitHub.

### A variável definida no deploy não tem efeito

**Sintoma:** a aplicação usa o valor do arquivo local.<br>
**Causa:** `load_dotenv(override=True)` substituiu o ambiente do processo.<br>
**Correção:** use `override=False` e teste a precedência.

### `APP_DEBUG=false` ativa o modo debug

**Sintoma:** uma opção aparentemente falsa vira verdadeira.<br>
**Causa:** `bool("false")` é `True` porque a string não está vazia.<br>
**Correção:** normalize e aceite explicitamente valores conhecidos, como no exemplo.

### A aplicação inicia e falha somente na primeira requisição

**Sintoma:** o erro de configuração aparece tarde.<br>
**Causa:** o valor não foi validado na inicialização.<br>
**Correção:** carregue toda a configuração, valide e falhe antes de aceitar tráfego.

### O segredo aparece no log

**Sintoma:** token, senha ou URL com credencial fica armazenado na observabilidade.<br>
**Causa:** impressão direta, `repr` automático, traceback ou dump do ambiente.<br>
**Correção:** registre apenas estado não sensível, aplique redação e teste a saída.

## Em um ambiente real

### Configuração e deploy

Injete configuração por ambiente no momento do deploy e valide tudo ao iniciar. Separe desenvolvimento, homologação e produção sem criar nomes agrupados como `APP_CONFIG_PRODUCAO`: cada variável deve ter uma responsabilidade clara.

Um `.env` é aceitável para desenvolvimento local quando está ignorado e tem permissões restritas. Em produção, prefira a integração da plataforma com um gerenciador de segredos. O secret manager oferece controle de acesso, auditoria e rotação; a aplicação recebe apenas o necessário.

### Segurança

- conceda privilégio mínimo à identidade da aplicação;
- prefira credenciais curtas ou temporárias quando o provedor permitir;
- rotacione periodicamente e imediatamente após suspeita de vazamento;
- não trate variável de ambiente como criptografia: processos autorizados, dumps e ferramentas de diagnóstico podem expô-la;
- nunca grave segredo em `Dockerfile` com `ARG` ou `ENV`; para segredos necessários durante o build, use mounts de segredo do BuildKit;
- não inclua `.env` na imagem, no artefato ou no backup sem proteção adequada.

### Observabilidade e falhas

Registre quais configurações não sensíveis estão ativas, a versão da aplicação e se uma credencial foi carregada — nunca o valor. Crie alertas para falha de autenticação, mas cuide para não anexar requisições completas.

Se o provedor de segredos estiver indisponível, defina o comportamento: falhar na inicialização costuma ser mais seguro que iniciar parcialmente. Para rotação sem indisponibilidade, aceite por um período controlado a credencial nova e a anterior, atualize os consumidores e então revogue a antiga.

### Incidente e rollback

Se um segredo for publicado, considere-o comprometido. Revogue ou rotacione antes de reescrever o histórico: cópias podem existir em forks, clones, caches e pull requests. Investigue logs de uso, distribua a nova credencial por canal seguro e registre o incidente sem repetir o valor vazado.

Um rollback de código não deve restaurar uma credencial revogada. Mantenha versão de configuração e aplicação compatíveis durante a reversão.

## Desafio rápido

Adicione `APP_TIMEOUT_SEGUNDOS` ao `.env.example`. Converta-o para `float`, aceite apenas valores maiores que zero e escreva testes para ausência, valor válido e valor inválido.

<details>
<summary>Pistas</summary>

1. Leia com `os.getenv("APP_TIMEOUT_SEGUNDOS", "5")`.
2. Capture `ValueError` durante a conversão.
3. Rejeite zero e números negativos.
4. Não reutilize o token em mensagens de erro.

</details>

## Resumo

- Variáveis de ambiente separam configuração que varia do código.
- `python-dotenv` leva pares de um `.env` para `os.environ`; ele não transforma o arquivo em cofre.
- Valores devem ser convertidos, validados e carregados antes de a aplicação servir tráfego.
- `.env.example` documenta nomes com valores fictícios; `.env` não deve ser versionado.
- Produção pede controle de acesso, rotação, observabilidade sem vazamento e, para segredos importantes, um gerenciador dedicado.

## Para estudar mais

- [Documentação de `os.environ` e `os.getenv()`](https://docs.python.org/3/library/os.html#os.environ) — fonte oficial sobre o ambiente do processo em Python.
- [Documentação do `python-dotenv`](https://bbc2.github.io/python-dotenv/) — descreve carregamento, busca do arquivo e precedência com `override`.
- [The Twelve-Factor App: Config](https://12factor.net/config) — explica por que configuração que varia entre deploys deve ficar fora do código.
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html) — cobre ciclo de vida, acesso, rotação, auditoria e limites de variáveis de ambiente.
- [GitHub: remover dados sensíveis de um repositório](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) — procedimento de resposta quando um segredo já entrou no histórico.
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning) — explica a detecção de padrões de credenciais em repositórios.
- [Docker Build secrets](https://docs.docker.com/build/building/secrets/) — mostra por que `ARG` e `ENV` não são adequados para segredos de build e como usar mounts temporários.
