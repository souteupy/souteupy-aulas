# /// script
# requires-python = ">=3.10"
# dependencies = ["cowsay==6.1"]
# ///
"""Script com dependência declarada no próprio arquivo (PEP 723).

Execute com `uv run demo_uv.py`: o ambiente é criado sob demanda, fora do projeto,
e descartado do seu caminho de trabalho. Nada é instalado no Python do sistema.
"""

import sys

import cowsay


def main() -> None:
    print(f"Ambiente usado por este script: {sys.prefix}")
    cowsay.cow("dependencia declarada no proprio arquivo")


if __name__ == "__main__":
    main()
