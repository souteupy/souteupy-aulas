from __future__ import annotations

import threading
import unittest
from urllib.error import URLError
from unittest.mock import MagicMock, PropertyMock, patch

from scraper import (
    USER_AGENT,
    coletar_produtos,
    criar_parser,
    permitido_por_robots,
)
from servidor_demo import criar_servidor

ESPERADO = [
    {"id": "python-web", "nome": "Python para Web", "preco": "R$ 79,90"},
    {
        "id": "automacao",
        "nome": "Automação com Selenium",
        "preco": "R$ 99,90",
    },
    {"id": "dados", "nome": "Dados com Python", "preco": "R$ 89,90"},
]


class ScraperIntegracaoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.servidor = criar_servidor("127.0.0.1", 0)
        cls.thread = threading.Thread(
            target=cls.servidor.serve_forever,
            daemon=True,
        )
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.servidor.server_port}/"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.thread.join(timeout=2)

    def test_extrai_tres_produtos_carregados_por_javascript(self) -> None:
        self.assertEqual(coletar_produtos(self.base_url), ESPERADO)

    def test_respeita_bloqueio_do_robots_txt(self) -> None:
        with self.assertRaises(PermissionError):
            coletar_produtos(f"{self.base_url}privado.html")


class ScraperSegurancaTest(unittest.TestCase):
    @patch("scraper.urlopen")
    def test_robots_usa_timeout_e_user_agent_do_scraper(self, urlopen) -> None:
        resposta = MagicMock()
        resposta.read.return_value = b"User-agent: *\nAllow: /\n"
        resposta.headers.get_content_charset.return_value = "utf-8"
        urlopen.return_value.__enter__.return_value = resposta

        self.assertTrue(permitido_por_robots("https://example.com/", timeout=4))

        requisicao = urlopen.call_args.args[0]
        self.assertEqual(requisicao.get_header("User-agent"), USER_AGENT)
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 4)
        resposta.read.assert_called_once_with(64 * 1024 + 1)

    @patch("scraper.urlopen")
    def test_robots_invalido_bloqueia_coleta(self, urlopen) -> None:
        corpos_invalidos = (
            b"",
            b"<html>indisponivel</html>",
            b"User-agent: *\n" + b"#" * (64 * 1024),
        )
        for corpo in corpos_invalidos:
            with self.subTest(corpo=corpo):
                resposta = MagicMock()
                resposta.read.return_value = corpo
                resposta.headers.get_content_charset.return_value = "utf-8"
                urlopen.return_value.__enter__.return_value = resposta

                with self.assertRaisesRegex(RuntimeError, "robots.txt inválido"):
                    permitido_por_robots("https://example.com/")

    @patch("scraper.urlopen", side_effect=URLError("indisponivel"))
    def test_falha_ao_ler_robots_bloqueia_coleta(self, _urlopen) -> None:
        with self.assertRaisesRegex(RuntimeError, "robots.txt"):
            permitido_por_robots("https://example.com/", timeout=2)

    @patch("scraper.criar_driver")
    @patch("scraper.permitido_por_robots", side_effect=[True, False])
    def test_revalida_robots_apos_redirecionamento(
        self, permitido, criar_driver
    ) -> None:
        driver = MagicMock()
        driver.current_url = "https://destino.example/privado"
        criar_driver.return_value = driver

        with self.assertRaises(PermissionError):
            coletar_produtos("https://origem.example/", timeout=3)

        self.assertEqual(
            permitido.call_args_list,
            [
                unittest.mock.call("https://origem.example/", timeout=3),
                unittest.mock.call(
                    "https://destino.example/privado", timeout=3
                ),
            ],
        )
        driver.set_page_load_timeout.assert_called_once_with(3)
        driver.find_elements.assert_not_called()
        driver.quit.assert_called_once_with()

    @patch("scraper.WebDriverWait")
    @patch("scraper.criar_driver")
    @patch("scraper.permitido_por_robots", side_effect=[True, False])
    def test_revalida_robots_em_redirecionamento_tardio(
        self, permitido, criar_driver, web_driver_wait
    ) -> None:
        origem = "https://origem.example/"
        destino = "https://destino.example/privado"
        driver = MagicMock()
        driver.current_url = origem
        driver.find_elements.return_value = []
        criar_driver.return_value = driver

        def executar_espera(condicao):
            self.assertFalse(condicao(driver))
            driver.current_url = destino
            return condicao(driver)

        web_driver_wait.return_value.until.side_effect = executar_espera

        with self.assertRaises(PermissionError):
            coletar_produtos(origem, timeout=3)

        self.assertEqual(
            permitido.call_args_list,
            [
                unittest.mock.call(origem, timeout=3.0),
                unittest.mock.call(destino, timeout=3.0),
            ],
        )
        driver.find_elements.assert_called_once_with(
            unittest.mock.ANY, "[data-produto]"
        )
        driver.quit.assert_called_once_with()

    @patch("scraper.WebDriverWait")
    @patch("scraper.criar_driver")
    @patch("scraper.permitido_por_robots", return_value=True)
    def test_descarta_cartoes_se_url_muda_durante_a_leitura(
        self, permitido, criar_driver, web_driver_wait
    ) -> None:
        origem = "https://origem.example/"
        destino = "https://destino.example/"
        driver = MagicMock()
        type(driver).current_url = PropertyMock(
            side_effect=[origem, origem, destino, destino, destino, destino]
        )
        criar_driver.return_value = driver

        def criar_cartoes(prefixo):
            cartoes = []
            for indice in range(3):
                cartao = MagicMock()
                cartao.get_attribute.return_value = f"{prefixo}-{indice}"
                nome = MagicMock()
                nome.text = f"Nome {prefixo} {indice}"
                preco = MagicMock()
                preco.text = f"R$ {indice},00"
                cartao.find_element.side_effect = [nome, preco]
                cartoes.append(cartao)
            return cartoes

        driver.find_elements.side_effect = [
            criar_cartoes("antigo"),
            criar_cartoes("novo"),
        ]

        def executar_espera(condicao):
            self.assertFalse(condicao(driver))
            return condicao(driver)

        web_driver_wait.return_value.until.side_effect = executar_espera

        dados = coletar_produtos(origem, timeout=3)

        self.assertEqual(
            [item["id"] for item in dados],
            ["novo-0", "novo-1", "novo-2"],
        )
        self.assertEqual(
            permitido.call_args_list,
            [
                unittest.mock.call(origem, timeout=3.0),
                unittest.mock.call(destino, timeout=3.0),
            ],
        )
        self.assertEqual(driver.find_elements.call_count, 2)
        driver.quit.assert_called_once_with()

    @patch("scraper.urlopen")
    def test_timeout_invalido_na_consulta_de_robots(self, urlopen) -> None:
        for timeout in (0, -1, float("nan"), float("inf"), "1"):
            with self.subTest(timeout=timeout):
                with self.assertRaisesRegex(ValueError, "timeout"):
                    permitido_por_robots(
                        "https://example.com/", timeout=timeout
                    )
        urlopen.assert_not_called()

    @patch("scraper.permitido_por_robots")
    def test_timeout_invalido_na_api(self, permitido) -> None:
        for timeout in (0, -1, float("nan"), float("inf"), "1"):
            with self.subTest(timeout=timeout):
                with self.assertRaisesRegex(ValueError, "timeout"):
                    coletar_produtos("https://example.com/", timeout=timeout)
        permitido.assert_not_called()

    def test_timeout_invalido_na_cli(self) -> None:
        for timeout in ("0", "-1", "nan", "inf"):
            with self.subTest(timeout=timeout), patch("sys.stderr"):
                with self.assertRaises(SystemExit):
                    criar_parser().parse_args(["--timeout", timeout])


if __name__ == "__main__":
    unittest.main()
