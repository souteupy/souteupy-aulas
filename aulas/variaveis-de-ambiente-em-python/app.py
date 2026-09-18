from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


class ErroDeConfiguracao(RuntimeError):
    """Indica que a aplicação não pode iniciar com a configuração atual."""


@dataclass(frozen=True)
class Configuracao:
    api_url: str
    api_token: str = field(repr=False)
    debug: bool = False

    @property
    def api_host(self) -> str:
        return urlparse(self.api_url).hostname or ""


def ler_obrigatoria(nome: str) -> str:
    valor = os.getenv(nome)
    if valor is None or not valor.strip():
        raise ErroDeConfiguracao(f"Variável obrigatória ausente: {nome}")
    return valor.strip()


def ler_booleano(nome: str, padrao: bool = False) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao

    normalizado = valor.strip().lower()
    if normalizado in {"1", "true", "yes", "on"}:
        return True
    if normalizado in {"0", "false", "no", "off"}:
        return False
    raise ErroDeConfiguracao(
        f"{nome} deve ser true/false, 1/0, yes/no ou on/off"
    )


def validar_url_http(nome: str, valor: str) -> str:
    try:
        if any(caractere.isspace() for caractere in valor):
            raise ValueError
        url = urlparse(valor)
        hostname = url.hostname
        url.port
    except ValueError:
        raise ErroDeConfiguracao(
            f"{nome} deve ser uma URL HTTP ou HTTPS completa"
        ) from None

    if (
        url.scheme not in {"http", "https"}
        or not url.netloc
        or not hostname
        or url.username is not None
        or url.password is not None
    ):
        raise ErroDeConfiguracao(
            f"{nome} deve ser uma URL HTTP ou HTTPS completa"
        )
    return valor


def carregar_configuracao(
    caminho_env: Path | str = Path(".env"),
) -> Configuracao:
    # Conveniência para desenvolvimento local. Variáveis já injetadas pelo
    # ambiente têm prioridade porque override=False.
    load_dotenv(dotenv_path=caminho_env, override=False)

    api_url = validar_url_http("APP_API_URL", ler_obrigatoria("APP_API_URL"))
    api_token = ler_obrigatoria("APP_API_TOKEN")
    debug = ler_booleano("APP_DEBUG", padrao=False)
    return Configuracao(api_url=api_url, api_token=api_token, debug=debug)


def resumo_seguro(config: Configuracao) -> str:
    modo_debug = "ligado" if config.debug else "desligado"
    return "\n".join(
        [
            "Configuração carregada.",
            f"API host: {config.api_host}",
            f"Debug: {modo_debug}",
            "Token: configurado (valor oculto)",
        ]
    )


def main() -> None:
    config = carregar_configuracao()
    print(resumo_seguro(config))


if __name__ == "__main__":
    main()
