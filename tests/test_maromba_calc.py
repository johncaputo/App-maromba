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
            self.assertGreater(ciclo["carbo_treino_g"], ciclo["carbo_descanso_g"])
            self.assertGreater(ciclo["kcal_treino"], ciclo["kcal_descanso"])

    def test_ciclo_carbo_respeita_o_piso(self):
        ciclo = mc.calcular_ciclo_carbo(100, 1300, 4, 1250)
        self.assertEqual(ciclo["kcal_descanso"], 1250)
        self.assertAlmostEqual(4 * ciclo["carbo_treino_g"] + 3 * ciclo["carbo_descanso_g"], 700, delta=7)
        self.assertEqual(mc.calcular_ciclo_carbo(100, 1200, 4, 1200), {})

    def test_ciclo_carbo_sem_descanso_ou_sem_treino(self):
        self.assertEqual(mc.calcular_ciclo_carbo(250, 2500, 0), {})
        self.assertEqual(mc.calcular_ciclo_carbo(250, 2500, 7), {})

    def test_um_rm(self):
        unico = mc.analisar_forca([("supino", 100.0, 1)], 80, "m")[0]
        self.assertEqual(unico["rm_estimado_kg"], 100.0)
        cinco = mc.analisar_forca([("supino", 100.0, 5)], 80, "m")[0]
        self.assertAlmostEqual(cinco["rm_estimado_kg"], (100 * (1 + 5 / 30) + 100 * 36 / 32) / 2, delta=0.06)
        self.assertEqual(cinco["nivel"], "intermediário")
        self.assertIsNone(mc.analisar_forca([("rosca", 40.0, 8)], 80, "m")[0]["nivel"])

    def test_meta_de_gordura(self):
        meta = mc.calcular_meta(85, 18, 10, -0.5, 2200, 2800)
        self.assertAlmostEqual(meta["peso_alvo_kg"], 85 * 0.82 / 0.90, delta=0.06)
        self.assertEqual((meta["semanas_deficit"], meta["semanas_pausa"], meta["semanas_total"]), (16, 1, 17))
        self.assertEqual(meta["perder_kg"], 7.6)
        exato = mc.calcular_meta(60, 32, 20, -0.36, 2000, 2400)
        self.assertEqual(exato["semanas_deficit"], 25, "divisao exata nao pode ganhar uma semana por erro de float")
        self.assertEqual(sum(f["semanas"] for f in meta["fases"]), meta["semanas_total"])


class TestSaude(unittest.TestCase):
    def test_pressao(self):
        self.assertEqual(mc.avaliar_pressao(115, 75)["classe"], "ótima")
        self.assertEqual(mc.avaliar_pressao(125, 80)["classe"], "normal")
        self.assertEqual(mc.avaliar_pressao(118, 92)["classe"], "hipertensão estágio 1")
        self.assertEqual(mc.avaliar_pressao(185, 95)["classe"], "hipertensão estágio 3")

    def test_exames(self):
        resultado = {e["marcador"]: e for e in mc.avaliar_exames(
            [("hematocrito", 55.0), ("hdl", 35.0), ("glicemia", 90.0), ("psa", 1.0)], "m", 30)}
        self.assertEqual(resultado["hematocrito"]["situacao"], "acima (crítico)")
        self.assertEqual(resultado["hdl"]["situacao"], "abaixo")
        self.assertEqual(resultado["glicemia"]["situacao"], "dentro")
        self.assertEqual(resultado["glicemia"]["nota"], "")
        self.assertEqual(mc.avaliar_exames([("psa", 1.0)], "f", 30)[0]["situacao"], "sem faixa genérica")

    def test_nota_do_exame_segue_a_direcao_do_desvio(self):
        baixo = mc.avaliar_exames([("hematocrito", 30.0)], "m", 30)[0]
        self.assertEqual(baixo["situacao"], "abaixo")
        self.assertIn("anemia", baixo["nota"])
        self.assertNotIn("trombose", baixo["nota"])
        self.assertEqual(mc.avaliar_exames([("lh", 20.0)], "m", 30)[0]["nota"], mc.NOTA_EXAME_PADRAO)
        self.assertEqual(mc.avaliar_exames([("psa", 3.0)], "m", 40)[0]["situacao"], "acima")
        self.assertEqual(mc.avaliar_exames([("psa", 3.0)], "m", 55)[0]["situacao"], "dentro")
        leve, grave = mc.avaliar_exames([("tgo", 60.0), ("tgo", 200.0)], "m", 30)
        self.assertEqual((leve["situacao"], grave["situacao"]), ("acima", "acima (crítico)"))
        self.assertEqual(grave["nota"], mc.NOTA_EXAME_GRAVE)

    def test_pressao_extrema_e_cafeina(self):
        self.assertEqual(mc.avaliar_pressao(85, 55)["classe"], "baixa")
        crise = rodar_json(BASE + ["--pressao", "185x112"])
        self.assertTrue(any("atendimento agora" in a for a in crise["avisos"]))
        self.assertTrue(any("Cafeína: evitar" in item for item in crise["suplementos"]))
        self.assertTrue(any("Cafeína: até" in item for item in rodar_json(BASE)["suplementos"]))

    def test_checklist_por_sexo(self):
        homem = " ".join(rodar_json(BASE + ["--perfil", "trt"])["checklist"])
        mulher = " ".join(rodar_json(BASE + ["--perfil", "trt", "--sexo", "f"])["checklist"])
        self.assertIn("PSA", homem)
        self.assertNotIn("PSA", mulher)
        self.assertNotIn("médico (endocrinologista", " ".join(rodar_json(BASE)["checklist"]))


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

    def test_series_por_experiencia_idade_e_objetivo(self):
        def series(plano):
            exercicios = plano["sessoes"][0]["exercicios"]
            return (next(e["series"] for e in exercicios if e["descanso"] == "2-3 min"),
                    next(e["series"] for e in exercicios if e["descanso"] == "60-90 s"),
                    exercicios[0]["reps"])
        self.assertEqual(series(mc.montar_treino(4, "iniciante", "crescer", "natural", 30, [])), (3, 2, "8-12"))
        self.assertEqual(series(mc.montar_treino(4, "intermediario", "crescer", "natural", 30, [])), (4, 3, "6-10"))
        self.assertEqual(series(mc.montar_treino(4, "avancado", "crescer", "natural", 30, [])), (4, 4, "6-10"))
        self.assertEqual(series(mc.montar_treino(4, "intermediario", "crescer", "natural", 55, [])), (3, 2, "6-10"))
        self.assertEqual(series(mc.montar_treino(4, "intermediario", "manter", "natural", 30, [])), (4, 2, "6-10"))

    def test_divisao_de_tres_dias_e_volume(self):
        iniciante = mc.montar_treino(3, "iniciante", "crescer", "natural", 30, [])
        self.assertEqual([s["treino"] for s in iniciante["sessoes"]],
                         ["Corpo inteiro A", "Corpo inteiro B", "Corpo inteiro C"])
        plano = mc.montar_treino(3, "intermediario", "crescer", "natural", 30, [])
        self.assertEqual([s["dia"] for s in plano["sessoes"]], ["seg", "qua", "sex"])
        self.assertTrue(plano["sessoes"][0]["treino"].startswith("Empurrar"))
        volume = {grupo: (v["series"], v["classe"]) for grupo, v in plano["volume_semanal"].items()}
        self.assertEqual(volume["costas"], (12, "faixa ideal"))
        self.assertEqual(volume["peito"], (8, "mínimo eficaz"))
        self.assertEqual(volume["core"], (3, "baixo"))
        somado = {}
        for sessao in plano["sessoes"]:
            for exercicio in sessao["exercicios"]:
                self.assertEqual(len({e["exercicio"] for e in sessao["exercicios"]}), len(sessao["exercicios"]))
                somado[exercicio["grupo"]] = somado.get(exercicio["grupo"], 0) + exercicio["series"]
        self.assertEqual(somado, {grupo: v[0] for grupo, v in volume.items()})

    def test_cardio_e_notas_por_perfil(self):
        self.assertIn("3-4 sessões", mc.montar_treino(4, "iniciante", "secar", "natural", 30, [])["cardio"])
        self.assertIn("saúde do coração", mc.montar_treino(4, "iniciante", "crescer", "hormonizado", 30, [])["cardio"])
        self.assertIn("2 sessões leves", mc.montar_treino(4, "iniciante", "crescer", "natural", 30, [])["cardio"])
        self.assertEqual(mc.montar_treino(7, "avancado", "manter", "natural", 30, [])["sessoes"][-1]["exercicios"], [])
        self.assertIn("4-6", mc.montar_treino(4, "iniciante", "secar", "natural", 45, [])["semana_leve"])

    def test_carga_do_plano_igual_a_tabela_de_forca(self):
        for experiencia, faixa, levantamento in (("intermediario", "75%", ("supino", 100.0, 7)),
                                                 ("iniciante", "70%", ("agachamento", 87.0, 9))):
            forca = mc.analisar_forca([levantamento], 80, "m")
            plano = mc.montar_treino(4, experiencia, "crescer", "natural", 30, forca)
            cargas = [e["carga_sugerida_kg"] for s in plano["sessoes"] for e in s["exercicios"]
                      if e["carga_sugerida_kg"] is not None]
            self.assertTrue(cargas)
            self.assertEqual(set(cargas), {forca[0]["cargas_treino"][faixa]})
        sem_carga = mc.montar_treino(4, "iniciante", "crescer", "natural", 30, [])
        self.assertTrue(all(e["carga_sugerida_kg"] is None for s in sem_carga["sessoes"] for e in s["exercicios"]))

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
        for secao in ("ENERGIA E MACROS", "COMPOSIÇÃO CORPORAL", "META", "CARDÁPIO EXEMPLO",
                      "PLANO DE TREINO", "FORÇA", "EXAMES", "PRESSÃO ARTERIAL", "CHECKLIST"):
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
                json.dump({"peso": 70, "altura": 165, "idade": 45, "chave_errada": 1}, arquivo)
            codigo, _, erro = rodar(["--config", caminho])
            self.assertEqual(codigo, 2)
            self.assertIn("chave desconhecida", erro)

    def test_config_repetiveis_somam_e_erros_de_arquivo(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "config.json")
            with open(caminho, "w", encoding="utf-8") as arquivo:
                json.dump({"peso": 70, "altura": 165, "idade": 45, "treinos-semana": 3, "cardapio": False,
                           "levantamento": ["supino:80x5"]}, arquivo)
            self.assertEqual([f["exercicio"] for f in rodar_json(["--config", caminho])["forca"]], ["supino"])
            dados = rodar_json(["--config", caminho, "--levantamento", "terra:120x3"])
            self.assertEqual([f["exercicio"] for f in dados["forca"]], ["terra"], "a linha de comando substitui a lista")
            self.assertEqual(dados["ciclo_carbo"]["treinos_semana"], 3)
            self.assertEqual(dados["cardapio"], [])
            self.assertEqual(rodar(["--conf", caminho])[0], 2, "abreviar --config nao pode ignorar o arquivo")
            self.assertEqual(rodar(["--config", os.path.join(pasta, "nao_existe.json")])[0], 2)
            for conteudo in ("{isto nao e json", "[1, 2, 3]", '{"config": "outro.json"}'):
                with open(caminho, "w", encoding="utf-8") as arquivo:
                    arquivo.write(conteudo)
                self.assertEqual(rodar(["--config", caminho] + BASE)[0], 2, msg=conteudo)

    def test_config_de_exemplo_funciona(self):
        exemplo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.exemplo.json")
        with tempfile.TemporaryDirectory() as pasta:
            dados = rodar_json(["--config", exemplo, "--registrar", os.path.join(pasta, "h.csv"),
                                "--data", "2026-01-01"])
            self.assertEqual(len(dados["forca"]), 3)
            self.assertTrue(dados["treino"]["sessoes"])
            self.assertTrue(dados["cardapio"])

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

    def test_recomendacao_do_historico(self):
        import datetime

        def analisar(pesos, objetivo, esperado, calorias=2200, ajuste=-550, piso=1500):
            registros = [(datetime.date(2026, 1, 1) + datetime.timedelta(days=d), p) for d, p in pesos]
            return mc.analisar_historico(registros, objetivo, esperado, calorias, ajuste, piso)

        self.assertIn("Perda abaixo do esperado: reduza 150", analisar([(0, 85), (21, 84.7)], "secar", -0.5)["recomendacao"])
        self.assertIn("Perda rápida demais", analisar([(0, 85), (21, 81)], "secar", -0.5)["recomendacao"])
        self.assertIn("mantenha o plano", analisar([(0, 85), (21, 83.5)], "secar", -0.5)["recomendacao"])
        no_piso = analisar([(0, 85), (21, 84.9)], "secar", -0.3, calorias=1520, ajuste=-300)
        self.assertIn("sem cortar comida", no_piso["recomendacao"])
        self.assertIn("sem déficit efetivo", analisar([(0, 60), (21, 60)], "secar", 0.02, 1200, 21, 1200)["recomendacao"])
        pequeno = analisar([(0, 80), (21, 80.6)], "crescer", 0.06, calorias=2900, ajuste=64)
        self.assertIn("Ganho rápido demais: reduza 50", pequeno["recomendacao"])
        self.assertIn("Ganho abaixo do esperado", analisar([(0, 80), (21, 80)], "crescer", 0.25, 2900, 275)["recomendacao"])
        self.assertIn("reduza 150", analisar([(0, 80), (21, 81)], "manter", 0.0, 2500, 0)["recomendacao"])
        self.assertIn("Menos de 7 dias", analisar([(0, 80), (5, 79.5)], "secar", -0.5)["recomendacao"])
        self.assertIn("Menos de 14 dias", analisar([(0, 80), (10, 79.5)], "secar", -0.5)["recomendacao"])
        janela = analisar([(0, 80), (7, 79.5), (14, 79), (55, 77), (58, 76.9)], "secar", -0.44)
        self.assertEqual(janela["dias_analisados"], 44, "registro recente demais nao pode impedir o calculo")
        repetido = analisar([(0, 80), (21, 79), (21, 78.5)], "secar", -0.5)
        self.assertEqual((repetido["registros"], repetido["ritmo_real_kg_semana"]), (2, -0.5))

    def test_historico_tolera_arquivo_imperfeito(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "historico.csv")
            with open(caminho, "w", encoding="utf-8") as arquivo:
                arquivo.write("data,peso,gordura,cintura,calorias\n2026-01-01,86,,,2200\nlixo,abc,,,\n2026-01-08,85.5,,,2200")
            dados = rodar_json(BASE + ["--registrar", caminho, "--data", "2026-01-22"])
            self.assertEqual(dados["historico"]["registros"], 3)
            self.assertEqual(dados["historico"]["dias_analisados"], 21)
            with open(caminho, encoding="utf-8") as arquivo:
                linhas = arquivo.read().splitlines()
            self.assertEqual(len(linhas), 5)
            self.assertEqual(linhas[-1].split(",")[:2], ["2026-01-22", "85"])
            self.assertEqual(rodar(BASE + ["--registrar", pasta])[0], 2, "gravar em uma pasta e erro de arquivo")

    def test_avisos_de_plano_sem_deficit_e_meta_fora_de_alcance(self):
        sem = rodar_json(["--peso", "52", "--altura", "150", "--idade", "62", "--sexo", "f", "--atividade",
                          "sedentario", "--gordura", "38", "--gordura-alvo", "18", "--biotipo", "endomorfo"])
        self.assertEqual(sem["meta"], {})
        self.assertEqual(sem["ciclo_carbo"], {})
        self.assertTrue(any("sem déficit efetivo" in a for a in sem["avisos"]))
        longe = rodar_json(["--peso", "140", "--altura", "170", "--idade", "55", "--sexo", "f", "--atividade",
                            "sedentario", "--gordura", "55", "--gordura-alvo", "15"])
        self.assertEqual(longe["meta"], {})
        self.assertTrue(any("fora de alcance" in a for a in longe["avisos"]))

    def test_protecoes_de_saude(self):
        magro = rodar_json(["--peso", "50", "--altura", "175", "--idade", "25"])
        self.assertEqual(magro["ajuste_kcal"], 0)
        self.assertTrue(any("IMC abaixo de 18,5" in a for a in magro["avisos"]))
        essencial = rodar_json(BASE + ["--sexo", "f", "--gordura", "25", "--gordura-alvo", "10"])
        self.assertEqual(essencial["meta"], {})
        self.assertTrue(any("gordura essencial" in a for a in essencial["avisos"]))
        self.assertEqual(rodar_json(["--peso", "200", "--altura", "190", "--idade", "30"])["agua_l"], 5.0)
        self.assertEqual(rodar(BASE + ["--cintura", "60", "--pescoco", "59"])[0], 1, "medidas fora do metodo de fita")
        obeso = rodar_json(["--peso", "130", "--altura", "175", "--idade", "30", "--gordura", "40"])
        self.assertIn("não interpretável", obeso["composicao"]["ffmi_classe"])

    def test_calorias_que_nao_comportam_o_plano(self):
        cede = rodar_json(["--peso", "67", "--altura", "170", "--idade", "73", "--sexo", "f", "--biotipo",
                           "ectomorfo", "--atividade", "sedentario"])
        self.assertEqual(cede["carbo_g"], 50, "a proteina cede antes de o carboidrato zerar")
        self.assertTrue(any("reduzida para" in a for a in cede["avisos"]))
        extremo = rodar_json(["--peso", "150", "--altura", "158", "--idade", "34", "--sexo", "f", "--gordura",
                              "54.9", "--biotipo", "endomorfo", "--perfil", "trt", "--atividade", "leve"])
        self.assertEqual(extremo["carbo_g"], 0)
        self.assertTrue(any("plano recalculado" in a for a in extremo["avisos"]))
        for dados in (cede, extremo):
            soma = dados["proteina_g"] * 4 + dados["carbo_g"] * 4 + dados["gordura_g"] * 9
            self.assertAlmostEqual(soma, dados["calorias"], delta=8)
            for prato in dados["refeicoes"]:
                self.assertEqual(prato["kcal"],
                                 prato["proteina_g"] * 4 + prato["carbo_g"] * 4 + prato["gordura_g"] * 9)

    def test_projecao_segue_as_fases_da_meta(self):
        dados = rodar_json(BASE + ["--gordura", "20", "--gordura-alvo", "10", "--semanas", "30"])
        pesos = [p["peso_kg"] for p in dados["projecao"]]
        self.assertEqual(pesos[7], pesos[8], "a 9a semana e pausa na manutencao")
        self.assertEqual(pesos[-1], dados["meta"]["peso_alvo_kg"], "a projecao para no peso alvo")

    def test_datas_e_caminhos_invalidos(self):
        self.assertEqual(rodar(BASE + ["--data", "2999-01-01"])[0], 2)
        self.assertEqual(rodar(BASE + ["--registrar", ""])[0], 2)
        self.assertEqual(rodar(BASE + ["--config", ""])[0], 2)
        self.assertEqual(rodar(["--help"])[0], 0)

    def test_cardapio_fecha_os_macros_ou_avisa(self):
        dados = rodar_json(["--peso", "63.2", "--altura", "192", "--idade", "20", "--objetivo", "crescer",
                            "--biotipo", "ectomorfo", "--experiencia", "avancado", "--atividade", "intenso",
                            "--refeicoes", "2", "--cardapio"])
        for alvo, prato in zip(dados["refeicoes"], dados["cardapio"]):
            self.assertFalse(prato["aproximado"])
            for macro in ("proteina_g", "carbo_g", "gordura_g"):
                self.assertAlmostEqual(prato[macro], alvo[macro], delta=4)

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
