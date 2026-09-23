"""Testes executáveis da aula — somente biblioteca padrão."""

from __future__ import annotations

import io
import logging
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import app
from log_config import configurar_logging, converter_nivel


class TesteConfiguracao(unittest.TestCase):
    def tearDown(self):
        logger = logging.getLogger("automacao")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def test_nivel_invalido_e_rejeitado(self):
        with self.assertRaisesRegex(ValueError, "Nível de log inválido"):
            converter_nivel("verbose")

    def test_aliases_nao_documentados_sao_rejeitados(self):
        for nome in ("NOTSET", "WARN", "FATAL"):
            with self.subTest(nome=nome), self.assertRaises(ValueError):
                converter_nivel(nome)

    def test_debug_e_filtrado_em_info(self):
        stream = io.StringIO()
        logger = configurar_logging(nivel="INFO", stream=stream)
        logger.debug("detalhe oculto")
        logger.info("evento visível")
        texto = stream.getvalue()
        self.assertNotIn("detalhe oculto", texto)
        self.assertIn("INFO | automacao | pedido_id=- | evento visível", texto)

    def test_logger_adapter_inclui_contexto(self):
        stream = io.StringIO()
        base = configurar_logging(nivel="INFO", stream=stream)
        logger = logging.LoggerAdapter(base, {"pedido_id": "PED-99"})
        logger.info("Pedido recebido")
        self.assertIn("pedido_id=PED-99 | Pedido recebido", stream.getvalue())

    def test_arquivo_rotaciona(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "automacao.log"
            logger = configurar_logging(
                nivel="INFO",
                arquivo=caminho,
                stream=io.StringIO(),
                max_bytes=220,
                backups=2,
            )
            try:
                for numero in range(20):
                    logger.info("evento número %s com conteúdo", numero)
                for handler in logger.handlers:
                    handler.flush()
                self.assertTrue(caminho.exists())
                self.assertTrue((Path(f"{caminho}.1")).exists())
                self.assertLessEqual(
                    len(list(Path(pasta).glob("automacao.log*"))), 3
                )
            finally:
                # No Windows, o arquivo precisa ser fechado antes do diretório temporário.
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)


class TesteAplicacao(unittest.TestCase):
    def tearDown(self):
        logger = logging.getLogger("automacao")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def test_processamento_concluido(self):
        stream = io.StringIO()
        base = configurar_logging(nivel="INFO", stream=stream)
        logger = logging.LoggerAdapter(base, {"pedido_id": "PED-42"})
        resultado = app.processar_pedido("PED-42", 3, logger)
        self.assertEqual(resultado.status, "concluído")
        self.assertEqual(resultado.itens_processados, 3)
        self.assertIn("Processamento concluído", stream.getvalue())

    def test_quantidade_invalida_gera_warning(self):
        stream = io.StringIO()
        base = configurar_logging(nivel="INFO", stream=stream)
        logger = logging.LoggerAdapter(base, {"pedido_id": "PED-42"})
        resultado = app.processar_pedido("PED-42", 0, logger)
        self.assertEqual(resultado.status, "ignorado")
        self.assertIn("WARNING", stream.getvalue())

    def test_pedido_id_com_quebra_de_linha_e_rejeitado(self):
        with self.assertRaisesRegex(ValueError, "pedido-id inválido"):
            app.validar_pedido_id("PED-42\nERROR evento forjado")

    def test_exception_inclui_traceback(self):
        stream = io.StringIO()
        base = configurar_logging(nivel="INFO", stream=stream)
        logger = logging.LoggerAdapter(base, {"pedido_id": "PED-42"})
        try:
            app.processar_pedido("PED-42", 1, logger, falhar=True)
        except RuntimeError:
            logger.exception("Processamento falhou")
        texto = stream.getvalue()
        self.assertIn("ERROR", texto)
        self.assertIn("Traceback", texto)
        self.assertIn("RuntimeError: falha simulada no provedor", texto)

    def test_token_do_ambiente_nao_aparece_na_saida(self):
        segredo = "segredo-ficticio-que-nao-pode-vazar"
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.dict(os.environ, {"APP_TOKEN": segredo}), mock.patch(
            "sys.stdout", stdout
        ), mock.patch("sys.stderr", stderr):
            codigo = app.main(["--pedido-id", "PED-7", "--quantidade", "2"])
        self.assertEqual(codigo, 0)
        self.assertNotIn(segredo, stdout.getvalue())
        self.assertNotIn(segredo, stderr.getvalue())

    def test_stdout_e_saida_e_stderr_e_log(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
            codigo = app.main(["--pedido-id", "PED-8", "--quantidade", "1"])
        self.assertEqual(codigo, 0)
        self.assertEqual(
            stdout.getvalue().strip(),
            '{"pedido_id": "PED-8", "itens_processados": 1, "status": "concluído"}',
        )
        self.assertIn("INFO", stderr.getvalue())
        self.assertNotIn("INFO", stdout.getvalue())

    def test_falha_retorna_codigo_um_sem_saida_normal(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
            codigo = app.main(["--falhar"])
        self.assertEqual(codigo, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Processamento falhou", stderr.getvalue())
        self.assertIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
