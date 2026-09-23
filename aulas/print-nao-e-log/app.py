"""Automação fictícia que separa saída para o usuário e logs operacionais."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from log_config import configurar_logging


@dataclass(frozen=True)
class Resultado:
    pedido_id: str
    itens_processados: int
    status: str


PADRAO_PEDIDO_ID = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")


def validar_pedido_id(valor: str) -> str:
    """Aceita um identificador curto sem controles que possam forjar linhas de log."""
    if not PADRAO_PEDIDO_ID.fullmatch(valor):
        raise ValueError(
            "pedido-id inválido: use de 1 a 64 letras, números, ponto, _ ou -"
        )
    return valor


def processar_pedido(
    pedido_id: str,
    quantidade: int,
    logger: logging.LoggerAdapter,
    *,
    falhar: bool = False,
) -> Resultado:
    """Processa um pedido fictício, registrando eventos úteis para operação."""
    logger.info("Processamento iniciado; quantidade=%s", quantidade)

    if quantidade <= 0:
        logger.warning("Pedido ignorado: quantidade não positiva")
        return Resultado(pedido_id, 0, "ignorado")

    logger.debug("Validando itens; quantidade=%s", quantidade)
    if falhar:
        raise RuntimeError("falha simulada no provedor")

    logger.info("Processamento concluído; quantidade=%s", quantidade)
    return Resultado(pedido_id, quantidade, "concluído")


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pedido-id", default="PED-42")
    parser.add_argument("--quantidade", type=int, default=3)
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="DEBUG, INFO, WARNING, ERROR ou CRITICAL",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="também grava em arquivo com rotação por tamanho",
    )
    parser.add_argument("--falhar", action="store_true", help="simula uma falha")
    return parser


def main(argumentos: list[str] | None = None) -> int:
    parser = criar_parser()
    opcoes = parser.parse_args(argumentos)

    try:
        pedido_id = validar_pedido_id(opcoes.pedido_id)
        logger_base = configurar_logging(
            nivel=opcoes.log_level,
            arquivo=opcoes.log_file,
        )
    except ValueError as erro:
        parser.error(str(erro))

    logger = logging.LoggerAdapter(
        logger_base,
        extra={"pedido_id": pedido_id},
    )

    # A credencial pode existir para uma integração real, mas nunca entra no log.
    _token = os.getenv("APP_TOKEN")

    try:
        resultado = processar_pedido(
            pedido_id,
            opcoes.quantidade,
            logger,
            falhar=opcoes.falhar,
        )
    except RuntimeError:
        logger.exception("Processamento falhou")
        return 1

    # Saída útil para quem chamou o programa: JSON limpo em stdout.
    print(json.dumps(asdict(resultado), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
