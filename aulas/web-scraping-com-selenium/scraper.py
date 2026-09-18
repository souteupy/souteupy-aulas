from __future__ import annotations

import argparse
import json
import math
import re
from numbers import Real
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

USER_AGENT = "souteupy-aulas/1.0"
SELETOR_CARTAO = "[data-produto]"
LIMITE_ROBOTS_BYTES = 64 * 1024
DIRETIVA_USER_AGENT = re.compile(
    r"^\s*user-agent\s*:\s*(?:\*|[!#$%&'*+\-.^_`|~0-9A-Za-z]+)"
    r"\s*(?:#.*)?$",
    re.IGNORECASE,
)


def validar_timeout(timeout: float) -> float:
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, Real)
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout deve ser um número finito maior que zero")
    return float(timeout)


def timeout_cli(valor: str) -> float:
    try:
        return validar_timeout(float(valor))
    except ValueError as erro:
        raise argparse.ArgumentTypeError(str(erro)) from erro


def permitido_por_robots(
    url: str,
    user_agent: str = USER_AGENT,
    timeout: float = 10,
) -> bool:
    """Consulta o robots.txt da origem e verifica a URL informada."""
    timeout = validar_timeout(timeout)
    robots_url = urljoin(url, "/robots.txt")
    requisicao = Request(robots_url, headers={"User-Agent": user_agent})
    try:
        with urlopen(requisicao, timeout=timeout) as resposta:
            charset = resposta.headers.get_content_charset() or "utf-8"
            corpo = resposta.read(LIMITE_ROBOTS_BYTES + 1)
            if len(corpo) > LIMITE_ROBOTS_BYTES:
                raise RuntimeError(
                    f"Coleta bloqueada: robots.txt inválido em {robots_url}"
                )
            linhas = corpo.decode(charset).splitlines()
    except (OSError, URLError, UnicodeError) as erro:
        raise RuntimeError(
            f"Coleta bloqueada: não foi possível ler {robots_url}"
        ) from erro

    if not any(DIRETIVA_USER_AGENT.fullmatch(linha) for linha in linhas):
        raise RuntimeError(
            f"Coleta bloqueada: robots.txt inválido em {robots_url}"
        )

    parser = RobotFileParser(robots_url)
    parser.parse(linhas)
    return parser.can_fetch(user_agent, url)


def criar_driver(com_janela: bool = False) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if not com_janela:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,900")
    options.add_argument(f"--user-agent={USER_AGENT}")
    return webdriver.Chrome(options=options)


def coletar_produtos(
    url: str,
    *,
    timeout: float = 10,
    com_janela: bool = False,
) -> list[dict[str, str]]:
    timeout = validar_timeout(timeout)
    if not permitido_por_robots(url, timeout=timeout):
        raise PermissionError(f"Coleta bloqueada por robots.txt: {url}")

    driver = criar_driver(com_janela)
    try:
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        url_aprovada = url

        def aprovar_url(url_atual: str) -> None:
            nonlocal url_aprovada
            if url_atual == url_aprovada:
                return
            if not permitido_por_robots(url_atual, timeout=timeout):
                raise PermissionError(
                    "Coleta bloqueada por robots.txt após redirecionamento: "
                    f"{url_atual}"
                )
            url_aprovada = url_atual

        def extrair_quando_pronto(navegador):
            url_atual = navegador.current_url
            aprovar_url(url_atual)

            # Se a URL mudou durante a validação, aprova a nova URL e reinicia
            # a condição antes de qualquer busca no DOM.
            url_antes_do_dom = navegador.current_url
            if url_antes_do_dom != url_atual:
                aprovar_url(url_antes_do_dom)
                return False

            cartoes = navegador.find_elements(By.CSS_SELECTOR, SELETOR_CARTAO)
            if len(cartoes) < 3:
                return False

            dados = [
                {
                    "id": cartao.get_attribute("data-produto"),
                    "nome": cartao.find_element(
                        By.CSS_SELECTOR, '[data-campo="nome"]'
                    ).text,
                    "preco": cartao.find_element(
                        By.CSS_SELECTOR, '[data-campo="preco"]'
                    ).text,
                }
                for cartao in cartoes
            ]

            # Descarta deterministicamente o resultado se a navegação mudou
            # enquanto os cartões eram localizados ou lidos.
            url_depois_da_leitura = navegador.current_url
            if url_depois_da_leitura != url_atual:
                aprovar_url(url_depois_da_leitura)
                return False
            return dados

        espera = WebDriverWait(driver, timeout)
        return espera.until(extrair_quando_pronto)
    finally:
        driver.quit()


def salvar_json(dados: list[dict[str, str]], caminho: Path) -> None:
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extrai o catálogo da página dinâmica de demonstração."
    )
    parser.add_argument("--url", default="http://127.0.0.1:8000/")
    parser.add_argument("--saida", type=Path, default=Path("dados.json"))
    parser.add_argument("--timeout", type=timeout_cli, default=10.0)
    parser.add_argument(
        "--com-janela",
        action="store_true",
        help="Mostra a janela do Chrome durante a coleta.",
    )
    return parser


def main() -> None:
    args = criar_parser().parse_args()
    dados = coletar_produtos(
        args.url,
        timeout=args.timeout,
        com_janela=args.com_janela,
    )
    salvar_json(dados, args.saida)
    print(f"{len(dados)} produtos salvos em {args.saida}")


if __name__ == "__main__":
    main()
