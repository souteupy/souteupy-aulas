"""Configuração central de logging para o exemplo da aula."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TextIO

FORMATO = (
    "%(asctime)s | %(levelname)s | %(name)s | "
    "pedido_id=%(pedido_id)s | %(message)s"
)


class ContextoPadrao(logging.Filter):
    """Garante os campos de contexto esperados pelo formatador."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "pedido_id"):
            record.pedido_id = "-"
        return True


def converter_nivel(nome: str) -> int:
    """Converte um nome de nível em inteiro e rejeita valores desconhecidos."""
    niveis = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    nivel = niveis.get(nome.upper())
    if nivel is None:
        permitidos = "DEBUG, INFO, WARNING, ERROR, CRITICAL"
        raise ValueError(f"Nível de log inválido: {nome!r}. Use: {permitidos}.")
    return nivel


def configurar_logging(
    *,
    nivel: str = "INFO",
    arquivo: str | Path | None = None,
    stream: TextIO | None = None,
    max_bytes: int = 1_000_000,
    backups: int = 3,
) -> logging.Logger:
    """Configura e devolve o logger da aplicação.

    Os logs de console vão para stderr, preservando stdout para a saída normal.
    Quando ``arquivo`` é informado, também há rotação por tamanho.
    """
    if max_bytes <= 0:
        raise ValueError("max_bytes deve ser maior que zero")
    if backups < 0:
        raise ValueError("backups não pode ser negativo")

    logger = logging.getLogger("automacao")
    logger.setLevel(converter_nivel(nivel))
    logger.propagate = False

    # Torna chamadas repetidas previsíveis em testes e processos que recarregam config.
    for handler_antigo in logger.handlers[:]:
        handler_antigo.close()
        logger.removeHandler(handler_antigo)

    formatador = logging.Formatter(FORMATO)
    contexto = ContextoPadrao()

    console = logging.StreamHandler(stream if stream is not None else sys.stderr)
    console.setFormatter(formatador)
    console.addFilter(contexto)
    logger.addHandler(console)

    if arquivo is not None:
        caminho = Path(arquivo)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        rotativo = RotatingFileHandler(
            caminho,
            maxBytes=max_bytes,
            backupCount=backups,
            encoding="utf-8",
        )
        rotativo.setFormatter(formatador)
        rotativo.addFilter(contexto)
        logger.addHandler(rotativo)

    return logger
