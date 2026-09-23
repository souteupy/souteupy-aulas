"""Inspeciona o ambiente Python em execução e explica onde os pacotes vão parar.

Uso:
    python inspetor.py
    python inspetor.py --exigir-venv
    python inspetor.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path


class ErroDeAmbiente(RuntimeError):
    """Erro de uso do ambiente Python, com mensagem voltada a quem está aprendendo."""


@dataclass(frozen=True)
class Ambiente:
    """Retrato do interpretador que está rodando agora."""

    versao_python: str
    prefixo: str
    prefixo_base: str
    em_ambiente_virtual: bool
    variavel_virtual_env: str | None
    arquivo_pyvenv_cfg: str | None
    site_packages_do_usuario_ativo: bool
    pacotes_instalados: int


def esta_em_ambiente_virtual(modulo_sys=sys) -> bool:
    """Compara `sys.prefix` com `sys.base_prefix`, como descrito na documentação de venv.

    O prompt do terminal e a variável `VIRTUAL_ENV` podem ser personalizados ou
    herdados de outro processo, então nenhum dos dois é usado como prova aqui.
    """
    return modulo_sys.prefix != modulo_sys.base_prefix


def localizar_pyvenv_cfg(prefixo: str | os.PathLike[str] | None = None) -> Path | None:
    """Devolve o caminho de `pyvenv.cfg` do ambiente atual, quando ele existe."""
    caminho = Path(prefixo if prefixo is not None else sys.prefix) / "pyvenv.cfg"
    return caminho if caminho.is_file() else None


def contar_pacotes_instalados() -> int:
    """Conta distribuições visíveis para este interpretador."""
    return sum(1 for _ in metadata.distributions())


def _site_packages_do_usuario_ativo() -> bool:
    """Indica se o diretório `site-packages` do usuário está habilitado.

    Dentro de um ambiente virtual criado por `venv`, ele fica desabilitado, o que
    evita que um `pip install --user` antigo contamine o projeto.
    """
    import site

    return bool(getattr(site, "ENABLE_USER_SITE", False))


def descrever_ambiente() -> Ambiente:
    """Monta o retrato do ambiente sem ler valores de variáveis sensíveis."""
    arquivo = localizar_pyvenv_cfg()
    return Ambiente(
        versao_python=sys.version.split()[0],
        prefixo=sys.prefix,
        prefixo_base=sys.base_prefix,
        em_ambiente_virtual=esta_em_ambiente_virtual(),
        variavel_virtual_env=os.environ.get("VIRTUAL_ENV"),
        arquivo_pyvenv_cfg=str(arquivo) if arquivo else None,
        site_packages_do_usuario_ativo=_site_packages_do_usuario_ativo(),
        pacotes_instalados=contar_pacotes_instalados(),
    )


def formatar(ambiente: Ambiente) -> str:
    """Formata o retrato em texto curto para o terminal."""
    estado = "sim" if ambiente.em_ambiente_virtual else "NÃO"
    variavel = ambiente.variavel_virtual_env or "(não definida)"
    cfg = ambiente.arquivo_pyvenv_cfg or "(não encontrado)"
    usuario = "sim" if ambiente.site_packages_do_usuario_ativo else "não"
    return "\n".join(
        [
            f"Python............: {ambiente.versao_python}",
            f"Ambiente virtual..: {estado}",
            f"sys.prefix........: {ambiente.prefixo}",
            f"sys.base_prefix...: {ambiente.prefixo_base}",
            f"VIRTUAL_ENV.......: {variavel}",
            f"pyvenv.cfg........: {cfg}",
            f"site-packages do usuário ativo: {usuario}",
            f"Pacotes visíveis..: {ambiente.pacotes_instalados}",
        ]
    )


def main(argumentos: list[str] | None = None) -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument(
        "--exigir-venv",
        action="store_true",
        help="falha quando o interpretador não está em um ambiente virtual",
    )
    analisador.add_argument(
        "--json",
        action="store_true",
        dest="como_json",
        help="imprime o retrato em JSON",
    )
    opcoes = analisador.parse_args(argumentos)

    ambiente = descrever_ambiente()
    if opcoes.como_json:
        print(json.dumps(asdict(ambiente), ensure_ascii=False, indent=2))
    else:
        print(formatar(ambiente))

    if opcoes.exigir_venv and not ambiente.em_ambiente_virtual:
        raise ErroDeAmbiente(
            "Este interpretador não está em um ambiente virtual. "
            "Crie um com 'python -m venv .venv' e use o Python de dentro dele."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
