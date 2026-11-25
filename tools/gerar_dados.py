#!/usr/bin/env python3
"""Gera web/dados.js a partir das tabelas de maromba_calc.py (fonte unica dos dados).

Uso: python3 tools/gerar_dados.py            grava web/dados.js
     python3 tools/gerar_dados.py --conferir sai com 1 se web/dados.js estiver desatualizado
"""
import argparse
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import maromba_calc as mc  # noqa: E402

DESTINO = os.path.join(RAIZ, "web", "dados.js")
TABELAS = (
    "KCAL_POR_KG", "DEFICIT_MINIMO", "META_MAX_SEMANAS", "DESVIO_MAX_CARDAPIO", "HISTORICO_MAX_DIAS",
    "IMC_MINIMO_PARA_SECAR", "PROTEINA_MINIMA", "AGUA_MAXIMA_L", "NOTA_EXAME_PADRAO", "NOTA_EXAME_GRAVE",
    "EXAMES_GRAVE", "PSA_LIMITE_ATE_50_ANOS",
    "ATIVIDADE", "PERFIS", "BIOTIPOS", "EXPERIENCIA", "FFMI_FAIXAS", "FFMI_ROTULOS",
    "PADROES_FORCA", "NIVEIS_FORCA", "PRESSAO_ROTULOS", "EXAMES", "ALIMENTOS", "MODELOS_REFEICAO",
    "EXERCICIOS", "REPS_ESPECIAIS", "MODELOS_TREINO", "DIVISOES", "DIAS_TREINO", "VOLUME_ROTULOS",
    "LINHA_DO_TEMPO", "CHECKLIST_BASE", "CHECKLIST_HORMONAL",
)


def gerar():
    dados = {nome: getattr(mc, nome) for nome in TABELAS}
    corpo = json.dumps(dados, ensure_ascii=False, indent=1)
    return (
        "// Arquivo gerado por tools/gerar_dados.py a partir de maromba_calc.py. Nao edite a mao.\n"
        "(function (raiz, dados) {\n"
        '  if (typeof module === "object" && module.exports) module.exports = dados;\n'
        "  else raiz.MAROMBA_DADOS = dados;\n"
        '})(typeof self !== "undefined" ? self : this, ' + corpo + ");\n"
    )


def main():
    parser = argparse.ArgumentParser(description="Gera web/dados.js a partir de maromba_calc.py.")
    parser.add_argument("--conferir", action="store_true", help="apenas verifica se o arquivo esta em dia")
    args = parser.parse_args()
    conteudo = gerar()
    if args.conferir:
        try:
            with open(DESTINO, encoding="utf-8") as arquivo:
                atual = arquivo.read()
        except OSError as erro:
            print(f"Erro ao ler {DESTINO}: {erro}", file=sys.stderr)
            return 1
        if atual != conteudo:
            print("web/dados.js desatualizado: rode python3 tools/gerar_dados.py", file=sys.stderr)
            return 1
        print("web/dados.js em dia")
        return 0
    try:
        os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
        with open(DESTINO, "w", encoding="utf-8") as arquivo:
            arquivo.write(conteudo)
    except OSError as erro:
        print(f"Erro ao gravar {DESTINO}: {erro}", file=sys.stderr)
        return 1
    print(f"gravado {DESTINO} ({len(conteudo)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
