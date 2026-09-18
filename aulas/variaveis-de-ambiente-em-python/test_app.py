from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import (
    Configuracao,
    ErroDeConfiguracao,
    carregar_configuracao,
    resumo_seguro,
    validar_url_http,
)


class ConfiguracaoTest(unittest.TestCase):
    def criar_env(self, conteudo: str) -> Path:
        diretorio = tempfile.TemporaryDirectory()
        self.addCleanup(diretorio.cleanup)
        caminho = Path(diretorio.name) / ".env"
        caminho.write_text(conteudo, encoding="utf-8")
        return caminho

    def test_carrega_env_e_converte_booleano(self) -> None:
        caminho = self.criar_env(
            "APP_API_URL=https://api.example.com/v1\n"
            "APP_API_TOKEN=credencial-ficticia\n"
            "APP_DEBUG=true\n"
        )
        with patch.dict(os.environ, {}, clear=True):
            config = carregar_configuracao(caminho)

        self.assertEqual(config.api_url, "https://api.example.com/v1")
        self.assertEqual(config.api_token, "credencial-ficticia")
        self.assertTrue(config.debug)

    def test_ambiente_tem_prioridade_sobre_arquivo(self) -> None:
        caminho = self.criar_env(
            "APP_API_URL=https://arquivo.example.com\n"
            "APP_API_TOKEN=valor-do-arquivo\n"
        )
        ambiente = {
            "APP_API_URL": "https://ambiente.example.com",
            "APP_API_TOKEN": "valor-do-ambiente",
        }
        with patch.dict(os.environ, ambiente, clear=True):
            config = carregar_configuracao(caminho)

        self.assertEqual(config.api_host, "ambiente.example.com")
        self.assertEqual(config.api_token, "valor-do-ambiente")

    def test_falha_quando_variavel_obrigatoria_esta_ausente(self) -> None:
        caminho = self.criar_env("APP_API_URL=https://api.example.com\n")
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ErroDeConfiguracao, "APP_API_TOKEN"):
                carregar_configuracao(caminho)

    def test_rejeita_url_invalida(self) -> None:
        caminho = self.criar_env(
            "APP_API_URL=api.example.com\n"
            "APP_API_TOKEN=credencial-ficticia\n"
        )
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ErroDeConfiguracao, "URL HTTP"):
                carregar_configuracao(caminho)

    def test_rejeita_url_com_userinfo_sem_expor_credenciais(self) -> None:
        usuario = "usuario-sensivel"
        senha = "senha-super-secreta"
        valor = f"https://{usuario}:{senha}@api.example.com"

        with self.assertRaises(ErroDeConfiguracao) as contexto:
            validar_url_http("APP_API_URL", valor)

        mensagem = str(contexto.exception)
        self.assertNotIn(usuario, mensagem)
        self.assertNotIn(senha, mensagem)

    def test_rejeita_porta_invalida_ou_fora_da_faixa(self) -> None:
        for valor in (
            "https://api.example.com:abc",
            "https://api.example.com:65536",
        ):
            with self.subTest(valor=valor):
                with self.assertRaises(ErroDeConfiguracao):
                    validar_url_http("APP_API_URL", valor)

    def test_rejeita_url_com_espaco(self) -> None:
        with self.assertRaises(ErroDeConfiguracao):
            validar_url_http(
                "APP_API_URL", "https://api.example.com/caminho com espaco"
            )

    def test_rejeita_ipv6_malformado_com_erro_de_configuracao(self) -> None:
        with self.assertRaises(ErroDeConfiguracao):
            validar_url_http("APP_API_URL", "https://[::1")

    def test_rejeita_booleano_ambiguo(self) -> None:
        caminho = self.criar_env(
            "APP_API_URL=https://api.example.com\n"
            "APP_API_TOKEN=credencial-ficticia\n"
            "APP_DEBUG=talvez\n"
        )
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ErroDeConfiguracao, "APP_DEBUG"):
                carregar_configuracao(caminho)

    def test_resumo_nao_expoe_token(self) -> None:
        segredo = "nao-imprimir-este-valor"
        caminho = self.criar_env(
            "APP_API_URL=https://api.example.com\n"
            f"APP_API_TOKEN={segredo}\n"
        )
        with patch.dict(os.environ, {}, clear=True):
            config = carregar_configuracao(caminho)
            resumo = resumo_seguro(config)

        self.assertNotIn(segredo, resumo)
        self.assertIn("valor oculto", resumo)
        self.assertNotIn(segredo, repr(config))

    def test_resumo_nao_expoe_userinfo_da_url(self) -> None:
        usuario = "usuario-sensivel"
        senha = "senha-super-secreta"
        config = Configuracao(
            api_url=f"https://{usuario}:{senha}@api.example.com/v1",
            api_token="token-ficticio",
        )

        resumo = resumo_seguro(config)

        self.assertEqual(config.api_host, "api.example.com")
        self.assertNotIn(usuario, resumo)
        self.assertNotIn(senha, resumo)


if __name__ == "__main__":
    unittest.main()
