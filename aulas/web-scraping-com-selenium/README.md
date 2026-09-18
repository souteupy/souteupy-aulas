# Web scraping com Selenium: extraia dados de uma página dinâmica

Nesta aula, você vai controlar um navegador com Python, esperar o JavaScript carregar e salvar dados estruturados em JSON — sem depender de `sleep()` nem de um site de terceiros.

> Esta aula expande o [primeiro post do @souteu.py](https://www.instagram.com/p/DU7KMgdDJTq/), publicado em 18/02/2026.

## O que você vai aprender

Ao final, você conseguirá:

- decidir quando Selenium faz sentido;
- abrir uma página dinâmica em Chrome headless;
- localizar elementos com seletores CSS estáveis;
- usar espera explícita para evitar condições de corrida;
- verificar `robots.txt` antes da coleta;
- salvar os resultados em um arquivo JSON reproduzível.

## Pré-requisitos

- Python 3.10 ou mais recente;
- Google Chrome instalado;
- acesso à internet na primeira execução, caso o Selenium Manager precise obter um driver compatível.

Não é preciso baixar `chromedriver` manualmente. Quando nenhum driver é informado, o Selenium Manager tenta descobrir o navegador e resolver o driver adequado.

## O problema

Copiar nomes e preços de uma página funciona para três itens. Com centenas de páginas, o processo fica lento, repetitivo e sujeito a erros.

Uma requisição HTTP comum pode bastar quando os dados já vêm no HTML ou em uma API. Mas páginas modernas também podem inserir conteúdo no DOM depois que o JavaScript roda. Nesses casos, Selenium é uma opção porque dirige um navegador real.

Nesta aula, uma página local adiciona três cursos depois de 600 ms. O scraper precisa esperar pelo estado correto, extrair os campos e produzir `dados.json`.

## Modelo mental

Pense no fluxo em cinco etapas:

1. **Permissão:** consulte `robots.txt`, os termos de uso e, quando aplicável, obtenha autorização.
2. **Navegação:** o WebDriver abre a URL em um navegador.
3. **Sincronização:** uma espera explícita aguarda uma condição observável no DOM.
4. **Extração:** seletores localizam os elementos e seus textos/atributos.
5. **Persistência:** os dados são normalizados e gravados em um formato estruturado.

`document.readyState == "complete"` não garante que um componente carregado por JavaScript já apareceu. Por isso, esperar pela quantidade esperada de elementos é mais confiável do que pausar por um número fixo de segundos.

## Tutorial passo a passo

### 1. Prepare o ambiente

No terminal, entre nesta pasta e crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative-o:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux ou macOS
source .venv/bin/activate
```

Instale a dependência:

```bash
python -m pip install -r requirements.txt
```

### 2. Conheça a página de demonstração

O arquivo [`site/index.html`](./site/index.html) começa sem produtos. Um `setTimeout` insere três cartões no DOM:

```javascript
setTimeout(() => {
  catalogo.forEach((produto) => {
    const card = document.createElement("article");
    card.dataset.produto = produto.id;
    card.innerHTML = `
      <h2 data-campo="nome">${produto.nome}</h2>
      <p data-campo="preco">${produto.preco}</p>
    `;
    lista.appendChild(card);
  });
}, 600);
```

Os atributos `data-produto` e `data-campo` funcionam como um contrato de seleção. Em um projeto sob seu controle, eles costumam ser mais estáveis que classes usadas apenas para aparência.

### 3. Inicie o servidor local

Em um terminal com o ambiente virtual ativo:

```bash
python servidor_demo.py
```

A página ficará disponível em `http://127.0.0.1:8000/`. Mantenha esse terminal aberto.

O servidor também publica um `robots.txt` de demonstração. Ele permite a página principal e bloqueia `/privado.html`.

### 4. Execute o scraper

Em outro terminal, na mesma pasta e com o ambiente virtual ativo:

```bash
python scraper.py
```

Em versão resumida, a condição de espera em [`scraper.py`](./scraper.py) segue este fluxo:

```python
def extrair_quando_pronto(navegador):
    url_atual = validar_url_atual(navegador)
    cartoes = navegador.find_elements(By.CSS_SELECTOR, "[data-produto]")
    if len(cartoes) < 3:
        return False
    dados = extrair(cartoes)
    return dados if navegador.current_url == url_atual else False


dados = WebDriverWait(driver, timeout).until(extrair_quando_pronto)
```

A implementação completa mantém a última URL aprovada dentro da condição: cada mudança observada é validada antes da próxima busca no DOM, e cartões lidos durante outra mudança são descartados para a espera recomeçar de forma determinística. A espera gera `TimeoutException` após o limite. O mesmo `--timeout`, que deve ser finito e maior que zero, limita a leitura de `robots.txt` e o carregamento da página. A leitura usa `User-Agent`, aceita no máximo 64 KiB e bloqueia a coleta se falhar, vier vazia ou não contiver uma diretiva `User-agent` válida. O navegador é fechado em um bloco `finally`, inclusive quando há falha.

Por padrão, o Chrome roda sem interface gráfica. Para acompanhar a navegação:

```bash
python scraper.py --com-janela
```

Para escolher outra saída:

```bash
python scraper.py --saida minha-coleta.json
```

## Teste você mesmo

Com o servidor em execução, rode:

```bash
python scraper.py
python -m json.tool dados.json
```

Resultado esperado:

```json
[
  {
    "id": "python-web",
    "nome": "Python para Web",
    "preco": "R$ 79,90"
  },
  {
    "id": "automacao",
    "nome": "Automação com Selenium",
    "preco": "R$ 99,90"
  },
  {
    "id": "dados",
    "nome": "Dados com Python",
    "preco": "R$ 89,90"
  }
]
```

Execute também o teste automatizado. Ele sobe o servidor em uma porta livre, abre o navegador e compara os dados coletados:

```bash
python -m unittest -v
```

<details>
<summary>O que o teste comprova?</summary>

Ele comprova que, no seu ambiente, o servidor local responde, o navegador inicia, o JavaScript cria os elementos, os seletores encontram os três cartões e o parser devolve a estrutura esperada. Ele não comprova compatibilidade com qualquer site externo.

</details>

## Dicas e truques

- **Prefira a fonte mais simples:** procure uma API documentada ou os dados no HTML antes de automatizar um navegador inteiro.
- **Espere por condições:** aguarde um elemento, uma quantidade ou um estado. `time.sleep(5)` pode ser lento quando sobra tempo e instável quando falta.
- **Escolha seletores semânticos:** IDs ou atributos `data-*` sob seu controle são melhores que cadeias longas de classes visuais.
- **Extraia e normalize separadamente:** coletar texto do DOM e converter moeda/data em outra função facilita testes.
- **Seja identificável quando permitido:** em crawlers reais, use um `User-Agent` que identifique o projeto e ofereça contato, sem fingir ser outra aplicação.

## Erros comuns

### `NoSuchElementException`

**Sintoma:** o elemento “não existe”, embora apareça no navegador.<br>
**Causa provável:** seletor incorreto, página errada ou busca feita antes do JavaScript terminar.<br>
**Correção:** confira o seletor no DevTools e use uma espera explícita para a condição necessária.

### `TimeoutException`

**Sintoma:** a espera chega ao limite.<br>
**Causa provável:** o elemento mudou, a rede falhou, houve bloqueio ou a condição esperada nunca ocorreu.<br>
**Correção:** registre URL, título e uma captura de tela na falha; revise a condição antes de simplesmente aumentar o timeout.

### `StaleElementReferenceException`

**Sintoma:** um elemento localizado deixa de responder.<br>
**Causa provável:** o JavaScript substituiu aquele nó no DOM.<br>
**Correção:** guarde o seletor e localize o elemento novamente, em vez de reutilizar indefinidamente a referência antiga.

### Driver ou navegador incompatível

**Sintoma:** a sessão do Chrome não inicia.<br>
**Causa provável:** navegador ausente, rede/proxy bloqueando o Selenium Manager ou driver manual incompatível no `PATH`.<br>
**Correção:** confirme a instalação do Chrome, remova drivers antigos do `PATH` e configure proxy/cache de forma explícita no ambiente de execução.

### `robots.txt` permite, então posso coletar tudo

**Sintoma:** o crawler tecnicamente acessa uma rota, mas viola regras do serviço ou trata dados pessoais sem base adequada.<br>
**Causa:** `robots.txt` foi confundido com autorização. A RFC 9309 afirma que essas regras não são controle de acesso.<br>
**Correção:** verifique também termos, licença, finalidade, legislação e autorização. Na dúvida, use a API oficial ou peça permissão.

## Em um ambiente real

### Configuração e segredos

Não coloque usuário, senha, cookies ou tokens no código. Se a automação autorizada exigir autenticação, injete configuração por variáveis de ambiente ou por um secret manager e mantenha apenas nomes fictícios em `.env.example`. Nunca versione o perfil do navegador.

### Segurança e privacidade

- não contorne login, CAPTCHA, rate limit ou controles de acesso;
- não colete dados pessoais “porque estão visíveis” sem finalidade e base adequadas;
- trate HTML, `robots.txt` e downloads como entrada não confiável;
- restrinja os domínios permitidos para evitar transformar URLs fornecidas por terceiros em acesso indevido à rede interna;
- prefira APIs oficiais quando elas existirem.

### Carga, escala e falhas

Um navegador consome muito mais CPU e memória que uma requisição HTTP. Limite concorrência, aplique intervalos e backoff, respeite respostas de bloqueio e evite repetir páginas já processadas. Em lotes, salve checkpoints para retomar sem duplicar toda a carga.

Defina timeout para cada etapa. Classifique falhas como transitórias (rede, `429`, `5xx`) ou permanentes (rota proibida, seletor inválido) antes de tentar novamente. Retentativas sem limite podem piorar uma indisponibilidade.

### Observabilidade e manutenção

Registre pelo menos URL, duração, número de itens, tentativa e tipo de erro — sem registrar credenciais ou dados sensíveis. Preserve captura de tela e HTML somente quando necessário, com retenção curta. Monitore queda brusca na quantidade de itens: ela pode indicar mudança de layout, não “zero resultados”.

Fixe dependências, teste a atualização de navegador/driver e mantenha um pequeno smoke test. Se o DOM mudar, atualize os seletores e faça rollback da implantação se a coleta começar a produzir dados incorretos.

## Desafio rápido

Adicione `categoria` a cada item em `site/index.html`, mostre esse campo no cartão e inclua-o na saída de `scraper.py`.

<details>
<summary>Pistas</summary>

1. Acrescente `categoria` aos objetos de `catalogo`.
2. Renderize um elemento com `data-campo="categoria"`.
3. Localize esse elemento dentro de cada cartão.
4. Atualize `test_scraper.py` antes de alterar o código de extração.

</details>

## Resumo

- Selenium é útil quando você realmente precisa do comportamento de um navegador, especialmente em páginas dinâmicas.
- A espera deve observar o estado da página, não adivinhar uma duração.
- Seletores estáveis reduzem manutenção.
- Uma coleta responsável considera permissão, carga, privacidade, falhas e observabilidade.
- `robots.txt` orienta crawlers, mas não concede autorização.

## Para estudar mais

- [Primeiro script com Selenium](https://www.selenium.dev/documentation/webdriver/getting_started/first_script/) — apresenta os componentes básicos de uma sessão WebDriver.
- [Estratégias de espera do Selenium](https://www.selenium.dev/documentation/webdriver/waits/) — explica condições de corrida, espera implícita e espera explícita.
- [Estratégias de localização](https://www.selenium.dev/documentation/webdriver/elements/locators/) — referência oficial dos localizadores suportados.
- [Selenium Manager](https://www.selenium.dev/documentation/selenium_manager/) — detalha a resolução automática de navegadores e drivers, cache e limitações de conectividade.
- [Erros comuns no Selenium](https://www.selenium.dev/documentation/webdriver/troubleshooting/errors/) — relaciona sintomas, causas e correções para falhas frequentes.
- [RFC 9309 — Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html) — padrão primário do protocolo e seus limites como autorização.
- [`urllib.robotparser` na documentação do Python](https://docs.python.org/3/library/urllib.robotparser.html) — API usada pelo exemplo para interpretar `robots.txt`.
