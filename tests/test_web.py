"""Garante que a versao web (web/calc.js) da os mesmos resultados que maromba_calc.py.

Rodar na raiz do projeto: python3 -m unittest discover -s tests -v
O teste de paridade exige Node.js; sem ele, e pulado.
"""
import argparse
import dataclasses
import datetime
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import maromba_calc as mc  # noqa: E402

NODE = shutil.which("node")
CASOS = 1500


def entrada_aleatoria(rng):
    """Uma entrada valida qualquer, cobrindo os campos opcionais e os extremos."""
    def opcional(valor, chance=0.5):
        return valor if rng.random() < chance else None

    passo = rng.choice([1, 0.5, 0.1])
    sexo = rng.choice(["m", "f"])
    altura = rng.randint(130, 230) if rng.random() < 0.1 else rng.randint(150, 200)
    peso = round(rng.uniform(35, 250) if rng.random() < 0.1 else rng.uniform(45, 130), 1)
    peso = round(peso / passo) * passo
    cintura = opcional(float(rng.randint(60, 130)))
    pescoco = opcional(float(rng.randint(28, 50)))
    marcadores = rng.sample(sorted(mc.EXAMES), rng.randint(0, 5))
    nomes = ["supino", "agachamento", "terra", "desenvolvimento", "rosca", "constructor", "__proto__"]
    return {
        "peso": peso, "altura": float(altura), "idade": rng.randint(18, 90), "sexo": sexo,
        "gordura": opcional(round(rng.uniform(3, 60), 1), 0.4),
        "cintura": cintura, "pescoco": pescoco,
        "quadril": opcional(float(rng.randint(70, 140)), 0.8 if sexo == "f" else 0.2),
        "biotipo": rng.choice(sorted(mc.BIOTIPOS)), "objetivo": rng.choice(["secar", "manter", "crescer"]),
        "perfil": rng.choice(sorted(mc.PERFIS)), "experiencia": rng.choice(sorted(mc.EXPERIENCIA)),
        "atividade": rng.choice(sorted(mc.ATIVIDADE)), "treinos_semana": rng.randint(0, 7),
        "gordura_alvo": opcional(float(rng.randint(4, 30)), 0.4),
        "semanas": rng.randint(1, 16), "refeicoes": rng.randint(2, 8),
        "cardapio": rng.random() < 0.7, "treino": rng.random() < 0.7,
        "levantamento": [[rng.choice(nomes), rng.choice([20.0, 42.5, 60.0, 81.25, 100.0, 140.0, 202.5]),
                          rng.randint(1, 15)] for _ in range(rng.randint(0, 4))],
        "exame": [[m, round(rng.uniform(0, 80) if m in ("hematocrito", "hdl") else rng.uniform(0, 400), 1)]
                  for m in marcadores],
        "pressao": opcional([rng.randint(90, 200), rng.randint(50, 89)], 0.5),
    }


def resultado_python(entrada):
    args = argparse.Namespace(registrar=None, data=None, **entrada)
    args.levantamento = [tuple(item) for item in entrada["levantamento"]]
    args.exame = [tuple(item) for item in entrada["exame"]]
    args.pressao = tuple(entrada["pressao"]) if entrada["pressao"] else None
    try:
        res = mc.calcular(args)
    except ValueError as erro:
        return {"erro": str(erro)}
    return {"ok": json.loads(json.dumps(dataclasses.asdict(res)))}


def historico_aleatorio(rng):
    inicio = datetime.date(2026, 1, 1)
    dias = sorted(rng.sample(range(0, 200), rng.randint(1, 10)))
    if rng.random() < 0.3:
        dias.append(rng.choice(dias))
    rng.shuffle(dias)
    registros = [[(inicio + datetime.timedelta(days=d)).isoformat(), round(rng.uniform(60, 100), 1)] for d in dias]
    ajuste = round(rng.uniform(-900, 500), 1)
    return {
        "registros": registros, "objetivo": rng.choice(["secar", "manter", "crescer"]),
        "esperado": ajuste * 7 / mc.KCAL_POR_KG, "calorias": round(rng.uniform(1200, 3500), 1),
        "ajuste": ajuste, "piso": rng.choice([1200.0, 1500.0]),
    }


def diferencas(a, b, caminho=""):
    """Lista os caminhos em que duas estruturas JSON divergem."""
    if isinstance(a, dict) and isinstance(b, dict):
        saida = []
        for chave in sorted(set(a) | set(b)):
            if chave not in a or chave not in b:
                saida.append(f"{caminho}.{chave}: presente em apenas um dos lados")
            else:
                saida.extend(diferencas(a[chave], b[chave], f"{caminho}.{chave}"))
        return saida
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{caminho}: tamanhos {len(a)} e {len(b)}"]
        saida = []
        for indice, (x, y) in enumerate(zip(a, b)):
            saida.extend(diferencas(x, y, f"{caminho}[{indice}]"))
        return saida
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
        return [] if a is b else [f"{caminho}: {a!r} != {b!r}"]
    return [] if a == b else [f"{caminho}: {a!r} != {b!r}"]


class TestDadosWeb(unittest.TestCase):
    def test_dados_js_em_dia(self):
        sys.path.insert(0, os.path.join(RAIZ, "tools"))
        import gerar_dados
        with open(gerar_dados.DESTINO, encoding="utf-8") as arquivo:
            self.assertEqual(arquivo.read(), gerar_dados.gerar(),
                             "web/dados.js desatualizado: rode python3 tools/gerar_dados.py")


@unittest.skipUnless(NODE, "Node.js nao encontrado")
class TestParidade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = random.Random(20261125)
        cls.entradas = [entrada_aleatoria(rng) for _ in range(CASOS)]
        cls.historicos = [historico_aleatorio(rng) for _ in range(400)]
        cls.arredondamentos = [[v, c] for c in (0, 1, 2) for v in
                               (0.5, 1.5, 2.5, -0.5, -2.5, 0.125, 0.375, 102.25, 2.675, 1e-9, 99999.995, 7.45, 0.0)]
        cls.arredondamentos += [[round(rng.uniform(-500, 5000), rng.randint(0, 4)), rng.randint(0, 2)]
                                for _ in range(500)]
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "casos.json")
            with open(caminho, "w", encoding="utf-8") as arquivo:
                json.dump({"calcular": cls.entradas, "historico": cls.historicos,
                           "arred": cls.arredondamentos}, arquivo)
            processo = subprocess.run([NODE, os.path.join(RAIZ, "tests", "paridade.js"), caminho],
                                      capture_output=True, text=True, encoding="utf-8", timeout=300)
        if processo.returncode != 0:
            raise AssertionError(f"node falhou: {processo.stderr[-2000:]}")
        cls.js = json.loads(processo.stdout)

    def test_arredondamento_igual_ao_python(self):
        for (valor, casas), obtido in zip(self.arredondamentos, self.js["arred"]):
            self.assertEqual(obtido, round(valor, casas), msg=f"round({valor!r}, {casas})")

    def test_calcular(self):
        falhas = []
        erros = 0
        for entrada, obtido in zip(self.entradas, self.js["calcular"]):
            esperado = resultado_python(entrada)
            erros += "erro" in esperado
            difs = diferencas(esperado, obtido)
            if difs:
                falhas.append(f"{json.dumps(entrada, ensure_ascii=False)}\n   " + "\n   ".join(difs[:6]))
        self.assertFalse(falhas, f"{len(falhas)} de {CASOS} casos divergem:\n" + "\n".join(falhas[:5]))
        self.assertGreater(erros, 0, "a amostra deveria incluir medidas inconsistentes")
        self.assertLess(erros, CASOS // 2)

    def test_historico(self):
        falhas = []
        for caso, obtido in zip(self.historicos, self.js["historico"]):
            registros = [(datetime.date.fromisoformat(d), p) for d, p in caso["registros"]]
            esperado = mc.analisar_historico(registros, caso["objetivo"], caso["esperado"], caso["calorias"],
                                             caso["ajuste"], caso["piso"])
            difs = diferencas(json.loads(json.dumps(esperado)), obtido)
            if difs:
                falhas.append(f"{json.dumps(caso)}\n   " + "\n   ".join(difs[:6]))
        self.assertFalse(falhas, f"{len(falhas)} casos divergem:\n" + "\n".join(falhas[:5]))


if __name__ == "__main__":
    unittest.main()
