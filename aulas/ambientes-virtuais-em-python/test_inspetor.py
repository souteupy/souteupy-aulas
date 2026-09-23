"""Testes do inspetor de ambiente. Rodam sem rede e sem criar ambientes."""

from __future__ import annotations

import io
import json
import os
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import inspetor


def _sys_falso(prefixo: str, prefixo_base: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(prefix=prefixo, base_prefix=prefixo_base)


class TesteDeteccaoDeAmbiente(unittest.TestCase):
    def test_prefixos_diferentes_indicam_ambiente_virtual(self):
        falso = _sys_falso("/projeto/.venv", "/usr")
        self.assertTrue(inspetor.esta_em_ambiente_virtual(falso))

    def test_prefixos_iguais_indicam_python_base(self):
        falso = _sys_falso("/usr", "/usr")
        self.assertFalse(inspetor.esta_em_ambiente_virtual(falso))

    def test_variavel_virtual_env_nao_e_usada_como_prova(self):
        falso = _sys_falso("/usr", "/usr")
        with mock.patch.dict(os.environ, {"VIRTUAL_ENV": "/projeto/.venv"}):
            self.assertFalse(inspetor.esta_em_ambiente_virtual(falso))


class TestePyvenvCfg(unittest.TestCase):
    def test_encontra_arquivo_existente(self):
        with TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "pyvenv.cfg"
            arquivo.write_text("home = /usr\n", encoding="utf-8")
            self.assertEqual(inspetor.localizar_pyvenv_cfg(pasta), arquivo)

    def test_retorna_none_quando_nao_existe(self):
        with TemporaryDirectory() as pasta:
            self.assertIsNone(inspetor.localizar_pyvenv_cfg(pasta))


class TesteRetratoDoAmbiente(unittest.TestCase):
    def test_campos_basicos_sao_coerentes(self):
        ambiente = inspetor.descrever_ambiente()
        self.assertEqual(ambiente.prefixo, sys.prefix)
        self.assertEqual(ambiente.prefixo_base, sys.base_prefix)
        self.assertEqual(
            ambiente.em_ambiente_virtual, sys.prefix != sys.base_prefix
        )
        self.assertGreater(ambiente.pacotes_instalados, 0)

    def test_saida_nao_expoe_outras_variaveis_de_ambiente(self):
        segredo = "valor-ficticio-de-teste"
        with mock.patch.dict(os.environ, {"APP_API_TOKEN": segredo}):
            texto = inspetor.formatar(inspetor.descrever_ambiente())
        self.assertNotIn(segredo, texto)
        self.assertNotIn("APP_API_TOKEN", texto)


class TesteCLI(unittest.TestCase):
    def test_saida_json_e_valida(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            codigo = inspetor.main(["--json"])
        dados = json.loads(buffer.getvalue())
        self.assertEqual(codigo, 0)
        self.assertIn("em_ambiente_virtual", dados)
        self.assertEqual(dados["prefixo"], sys.prefix)

    def test_exigir_venv_falha_fora_de_ambiente_virtual(self):
        retrato = inspetor.descrever_ambiente()
        fora = type(retrato)(
            **{**retrato.__dict__, "em_ambiente_virtual": False}
        )
        with mock.patch.object(inspetor, "descrever_ambiente", return_value=fora):
            buffer = io.StringIO()
            with redirect_stdout(buffer), self.assertRaises(inspetor.ErroDeAmbiente):
                inspetor.main(["--exigir-venv"])

    def test_exigir_venv_passa_dentro_de_ambiente_virtual(self):
        retrato = inspetor.descrever_ambiente()
        dentro = type(retrato)(
            **{**retrato.__dict__, "em_ambiente_virtual": True}
        )
        with mock.patch.object(inspetor, "descrever_ambiente", return_value=dentro):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                self.assertEqual(inspetor.main(["--exigir-venv"]), 0)


if __name__ == "__main__":
    unittest.main()
