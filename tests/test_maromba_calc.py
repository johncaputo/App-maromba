"""Testes da maromba_calc. Rodar na raiz do projeto: python3 -m unittest discover -s tests -v"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import maromba_calc as mc  # noqa: E402

BASE = ["--peso", "85", "--altura", "178", "--idade", "28"]


def rodar(argumentos):
    """Executa main() e devolve (codigo de saida, stdout, stderr)."""
    saida, erro = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
        try:
            codigo = mc.main(argumentos)
        except SystemExit as fim:
            codigo = fim.code
    return codigo, saida.getvalue(), erro.getvalue()


def rodar_json(argumentos):
    codigo, saida, erro = rodar(argumentos + ["--json"])
    if codigo != 0:
        raise AssertionError(f"saida {codigo}: {erro}")
    return json.loads(saida)


class TestFormulas(unittest.TestCase):
    def test_mifflin_st_jeor(self):
        self.assertAlmostEqual(mc.calcular_tmb(85, 178, 28, "m", None), 1827.5)
        self.assertAlmostEqual(mc.calcular_tmb(85, 178, 28, "f", None), 1661.5)

    def test_katch_mcardle(self):
        self.assertAlmostEqual(mc.calcular_tmb(85, 178, 28, "m", 18), 370 + 21.6 * 85 * 0.82)

    def test_gordura_navy(self):
        self.assertAlmostEqual(mc.gordura_navy("m", 178, 85, 38, None), 16.4, delta=0.3)
        self.assertAlmostEqual(mc.gordura_navy("f", 165, 70, 32, 95), 24.9, delta=0.3)

    def test_gordura_navy_entradas_invalidas(self):
        with self.assertRaises(ValueError):
            mc.gordura_navy("m", 178, 38, 40, None)
        with self.assertRaises(ValueError):
            mc.gordura_navy("f", 165, 70, 32, None)

    def test_ciclo_carbo_preserva_media_semanal(self):
        for treinos in range(1, 7):
            ciclo = mc.calcular_ciclo_carbo(250, 2500, treinos)
            total = treinos * ciclo["carbo_treino_g"] + (7 - treinos) * ciclo["carbo_descanso_g"]
            self.assertAlmostEqual(total, 7 * 250, delta=7, msg=f"treinos={treinos}")

    def test_ciclo_carbo_sem_descanso_ou_sem_treino(self):
        self.assertEqual(mc.calcular_ciclo_carbo(250, 2500, 0), {})
        self.assertEqual(mc.calcular_ciclo_carbo(250, 2500, 7), {})

    def test_um_rm(self):
        unico = mc.analisar_forca([("supino", 100.0, 1)], 80, "m")[0]
        self.assertEqual(unico["rm_estimado_kg"], 100.0)
        cinco = mc.analisar_forca([("supino", 100.0, 5)], 80, "m")[0]
        self.assertAlmostEqual(cinco["rm_estimado_kg"], (100 * (1 + 5 / 30) + 100 * 36 / 32) / 2, delta=0.06)
        self.assertEqual(cinco["nivel"], "intermediario")
        self.assertIsNone(mc.analisar_forca([("rosca", 40.0, 8)], 80, "m")[0]["nivel"])

    def test_meta_de_gordura(self):
        meta = mc.calcular_meta(85, 18, 10, -0.5, 2200, 2800)
        self.assertAlmostEqual(meta["peso_alvo_kg"], 85 * 0.82 / 0.90, delta=0.06)
        self.assertEqual(meta["semanas_total"], meta["semanas_deficit"] + meta["semanas_pausa"])
        self.assertEqual(sum(f["semanas"] for f in meta["fases"]), meta["semanas_total"])


class TestSaude(unittest.TestCase):
    def test_pressao(self):
        self.assertEqual(mc.avaliar_pressao(115, 75)["classe"], "otima")
        self.assertEqual(mc.avaliar_pressao(125, 80)["classe"], "normal")
        self.assertEqual(mc.avaliar_pressao(118, 92)["classe"], "hipertensao estagio 1")
        self.assertEqual(mc.avaliar_pressao(185, 95)["classe"], "hipertensao estagio 3")

    def test_exames(self):
        resultado = {e["marcador"]: e for e in mc.avaliar_exames(
            [("hematocrito", 55.0), ("hdl", 35.0), ("glicemia", 90.0), ("psa", 1.0)], "m")}
        self.assertEqual(resultado["hematocrito"]["situacao"], "acima (critico)")
        self.assertEqual(resultado["hdl"]["situacao"], "abaixo")
        self.assertEqual(resultado["glicemia"]["situacao"], "dentro")
        self.assertEqual(resultado["glicemia"]["nota"], "")
        self.assertEqual(mc.avaliar_exames([("psa", 1.0)], "f")[0]["situacao"], "sem faixa generica")


class TestTreino(unittest.TestCase):
    def test_numero_de_sessoes(self):
        self.assertEqual(mc.montar_treino(0, "iniciante", "secar", "natural", 30, []), {})
        for dias in range(1, 8):
            plano = mc.montar_treino(dias, "intermediario", "secar", "natural", 30, [])
            self.assertEqual(len(plano["sessoes"]), dias, msg=f"dias={dias}")

    def test_modelos_usam_exercicios_existentes(self):
        for chave, (_, codigos) in mc.MODELOS_TREINO.items():
            for codigo in codigos:
                self.assertIn(codigo, mc.EXERCICIOS, msg=chave)
        for chaves in mc.DIVISOES.values():
            for chave in chaves:
                self.assertIn(chave, mc.MODELOS_TREINO)

    def test_carga_sugerida_usa_o_1rm(self):
        forca = mc.analisar_forca([("supino", 100.0, 1)], 80, "m")
        plano = mc.montar_treino(4, "intermediario", "crescer", "natural", 30, forca)
        supino = [e for s in plano["sessoes"] for e in s["exercicios"] if e["exercicio"].startswith("Supino reto")]
        self.assertTrue(supino)
        self.assertEqual(supino[0]["carga_sugerida_kg"], 75.0)


class TestLinhaDeComando(unittest.TestCase):
    def test_macros_fecham_as_calorias(self):
        for objetivo in ("secar", "manter", "crescer"):
            for perfil in mc.PERFIS:
                dados = rodar_json(BASE + ["--objetivo", objetivo, "--perfil", perfil])
                soma = dados["proteina_g"] * 4 + dados["carbo_g"] * 4 + dados["gordura_g"] * 9
                self.assertAlmostEqual(soma, dados["calorias"], delta=12, msg=f"{objetivo}/{perfil}")

    def test_relatorio_completo_em_texto(self):
        codigo, saida, _ = rodar(BASE + [
            "--cintura", "88", "--pescoco", "39", "--gordura-alvo", "10", "--cardapio", "--treino",
            "--levantamento", "supino:100x5", "--exame", "hdl=35", "--pressao", "125x80",
        ])
        self.assertEqual(codigo, 0)
        for secao in ("ENERGIA E MACROS", "COMPOSICAO CORPORAL", "META", "CARDAPIO EXEMPLO",
                      "PLANO DE TREINO", "FORCA", "EXAMES", "PRESSAO ARTERIAL", "CHECKLIST"):
            self.assertIn(secao, saida)

    def test_obrigatorios_e_valores_invalidos(self):
        self.assertEqual(rodar(["--peso", "85"])[0], 2)
        self.assertEqual(rodar(BASE + ["--exame", "inexistente=1"])[0], 2)
        self.assertEqual(rodar(BASE + ["--pressao", "80x120"])[0], 2)
        self.assertEqual(rodar(BASE + ["--levantamento", "supino:100"])[0], 2)
        self.assertEqual(rodar(["--peso", "85", "--altura", "178", "--idade", "17"])[0], 2)

    def test_erro_de_calculo_devolve_1(self):
        codigo, _, _ = rodar(BASE + ["--sexo", "f", "--cintura", "70", "--pescoco", "32"])
        self.assertEqual(codigo, 1)

    def test_config_e_precedencia(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "config.json")
            with open(caminho, "w", encoding="utf-8") as arquivo:
                json.dump({"peso": 70, "altura": 165, "idade": 45, "objetivo": "crescer",
                           "exame": ["tsh=5"], "treino": True}, arquivo)
            dados = rodar_json(["--config", caminho, "--objetivo", "manter"])
            self.assertEqual(dados["objetivo"], "manter")
            self.assertEqual(dados["exames"][0]["situacao"], "acima")
            self.assertTrue(dados["treino"])
            with open(caminho, "w", encoding="utf-8") as arquivo:
                json.dump({"chave_errada": 1}, arquivo)
            self.assertEqual(rodar(["--config", caminho])[0], 2)

    def test_historico_mede_ritmo_real(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "historico.csv")
            primeiro = rodar_json(BASE + ["--registrar", caminho, "--data", "2026-01-01"])
            self.assertEqual(primeiro["historico"]["registros"], 1)
            segundo = rodar_json(["--peso", "83.5", "--altura", "178", "--idade", "28",
                                  "--registrar", caminho, "--data", "2026-01-22"])
            self.assertEqual(segundo["historico"]["registros"], 2)
            self.assertEqual(segundo["historico"]["dias_analisados"], 21)
            self.assertAlmostEqual(segundo["historico"]["ritmo_real_kg_semana"], -0.5, delta=0.01)
            with open(caminho, encoding="utf-8") as arquivo:
                self.assertEqual(len(arquivo.read().strip().splitlines()), 3)

    def test_historico_com_cabecalho_errado(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "historico.csv")
            with open(caminho, "w", encoding="utf-8") as arquivo:
                arquivo.write("a,b,c\n1,2,3\n")
            self.assertEqual(rodar(BASE + ["--registrar", caminho])[0], 1)
            with open(caminho, encoding="utf-8") as arquivo:
                self.assertEqual(arquivo.read(), "a,b,c\n1,2,3\n")


if __name__ == "__main__":
    unittest.main()
