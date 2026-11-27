"""Testes do coletor da Câmara (sem internet).

Rodar:  python -X utf8 -m unittest discover -s coletor -p "test_*.py" -v
"""
import contextlib, io, os, sys, unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coletar

# Página da Mesa Diretora simulada: o cargo vem antes do link "Detalhes" de cada vereador (como no site da Câmara).
PAGINA_MESA = """
<html><body>
<script>var x = "Presidente";</script>
<div class="card"><span>Presidente</span><a href="/Vereadores/Details?id=1">Detalhes</a></div>
<div class="card"><span>Vice-Presidente</span><a href="/Vereadores/Details?id=2">Detalhes</a></div>
<div class="card"><span>1º Secretário</span><a href="/Vereadores/Details?id=3">Detalhes</a></div>
<div class="card"><span>2° Secretario</span><a href="/Vereadores/Details?id=4">Detalhes</a></div>
</body></html>
"""


def rodar_mesa(vers):
    """Roda mesa_diretora com a página simulada; devolve o que foi impresso."""
    saida = io.StringIO()
    with mock.patch.object(coletar, "get", return_value=PAGINA_MESA), contextlib.redirect_stdout(saida):
        coletar.mesa_diretora(vers)
    return saida.getvalue()


class TestApelido(unittest.TestCase):
    def test_nome_com_apelido_entre_parenteses(self):
        self.assertEqual(coletar.apelido("JOAO DA SILVA (JOAOZINHO)"), "Joaozinho")

    def test_nome_sem_parenteses_usa_nome_inteiro(self):
        self.assertEqual(coletar.apelido("MARIA DE SOUZA"), "Maria De Souza")

    def test_ignora_parenteses_vereador(self):
        self.assertEqual(coletar.apelido("PEDRO LIMA (PEDRINHO) (VEREADOR)"), "Pedrinho")
        # Comportamento atual (mantido): se o único parêntese é "(VEREADOR)", o apelido é o nome inteiro como veio.
        self.assertEqual(coletar.apelido("ANA COSTA (VEREADOR)"), "Ana Costa (Vereador)")


class TestMesaDiretora(unittest.TestCase):
    def test_vereadores_com_apelido(self):
        vers = [{"id": i, "nome": f"VEREADOR NUMERO {i} (APELIDO{i})", "apelido": f"Apelido{i}"} for i in (1, 2, 3, 4, 5)]
        texto = rodar_mesa(vers)
        self.assertEqual([v.get("cargo") for v in vers],
                         ["Presidente da Câmara", "Vice-presidente da Câmara", "1º Secretário da Câmara",
                          "2º Secretário da Câmara", None])
        self.assertIn("Apelido1", texto)

    def test_vereadores_sem_apelido_nao_quebram(self):
        # Registros como chegam do SISCAM (só id e nome), sem o campo "apelido".
        vers = [{"id": 1, "nome": "JOAO DA SILVA (JOAOZINHO)"}, {"id": 2, "nome": "MARIA DE SOUZA"},
                {"id": 9, "nome": "CARLOS PEREIRA"}]
        originais = [dict(v) for v in vers]
        texto = rodar_mesa(vers)  # antes desta proteção: KeyError: 'apelido'
        self.assertEqual(len(vers), 3)  # nenhum vereador descartado
        self.assertEqual(vers[0]["cargo"], "Presidente da Câmara")
        self.assertEqual(vers[1]["cargo"], "Vice-presidente da Câmara")
        self.assertNotIn("cargo", vers[2])
        for v, o in zip(vers, originais):  # id e nome oficiais intactos; nenhum apelido inventado no registro
            self.assertEqual((v["id"], v["nome"]), (o["id"], o["nome"]))
            self.assertNotIn("apelido", v)
        self.assertIn("Joaozinho", texto)
        self.assertIn("Maria De Souza", texto)

    def test_mistura_com_e_sem_apelido(self):
        vers = [{"id": 1, "nome": "JOAO DA SILVA (JOAOZINHO)", "apelido": "Joaozinho"}, {"id": 2, "nome": "MARIA DE SOUZA"}]
        texto = rodar_mesa(vers)
        self.assertEqual([v["cargo"] for v in vers], ["Presidente da Câmara", "Vice-presidente da Câmara"])
        self.assertIn("Joaozinho", texto)
        self.assertIn("Maria De Souza", texto)

    def test_cargo_existente_nao_e_sobrescrito(self):
        vers = [{"id": 1, "nome": "JOAO DA SILVA", "cargo": "Presidente da Câmara"}]
        rodar_mesa(vers)
        self.assertEqual(vers[0]["cargo"], "Presidente da Câmara")


if __name__ == "__main__":
    unittest.main()
