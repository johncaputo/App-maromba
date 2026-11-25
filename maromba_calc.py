#!/usr/bin/env python3
"""maromba_calc.py v2 - Macros, composicao corporal, forca e saude na academia.

Perfis: natural, trt, hormonizado. Objetivos: secar, manter, crescer.
Nao calcula dose, substancia nem ciclo: calcula dieta, projeta peso, mede
progresso e confere exames contra faixas de referencia. Uso de hormonios
exige acompanhamento medico e exames.
"""
import argparse
import csv
import datetime
import json
import logging
import math
import os
import sys
from dataclasses import dataclass, asdict, field
from typing import Optional

LOG = logging.getLogger("maromba_calc")
KCAL_POR_KG = 7700.0

ATIVIDADE = {
    "sedentario": 1.2, "leve": 1.375, "moderado": 1.55,
    "intenso": 1.725, "atleta": 1.9,
}

# prot/gord em g por kg; corte/ganho em fracao do peso corporal por semana
PERFIS = {
    "natural": {
        "prot": {"secar": 2.2, "manter": 1.8, "crescer": 1.8},
        "gord": 0.8, "corte": 0.006, "ganho": 0.0025,
    },
    "trt": {
        "prot": {"secar": 2.4, "manter": 2.0, "crescer": 2.0},
        "gord": 0.8, "corte": 0.007, "ganho": 0.003,
    },
    "hormonizado": {
        "prot": {"secar": 2.6, "manter": 2.2, "crescer": 2.2},
        "gord": 0.9, "corte": 0.009, "ganho": 0.005,
    },
}

# Ajuste heuristico: "gasto" multiplica o gasto total, "gord" soma g/kg de gordura
BIOTIPOS = {
    "ectomorfo": {"gasto": 1.05, "gord": -0.1,
                  "nota": "Ectomorfo: gasta mais e come pouco. Mais carboidrato e refeicoes densas."},
    "mesomorfo": {"gasto": 1.00, "gord": 0.0,
                  "nota": "Mesomorfo: responde bem a distribuicao padrao de macros."},
    "endomorfo": {"gasto": 0.95, "gord": 0.2,
                  "nota": "Endomorfo: acumula gordura facil. Menos carboidrato, mais gordura e passos diarios."},
}

# Fracao do ritmo maximo de ganho muscular conforme tempo de treino
EXPERIENCIA = {"iniciante": 1.0, "intermediario": 0.6, "avancado": 0.35}

FFMI_FAIXAS = {"m": (18, 20, 22, 23.5, 25), "f": (14, 16, 18, 19.5, 21)}
FFMI_ROTULOS = ("abaixo da media", "media", "acima da media", "excelente",
                "proximo do limite natural", "acima do limite natural tipico")

# Limiares de 1RM / peso corporal (aproximados)
PADROES_FORCA = {
    "supino": {"m": (0.75, 1.25, 1.75, 2.0), "f": (0.5, 0.75, 1.0, 1.5)},
    "agachamento": {"m": (1.25, 1.5, 2.25, 2.75), "f": (0.75, 1.25, 1.5, 2.0)},
    "terra": {"m": (1.5, 2.0, 2.5, 3.0), "f": (1.0, 1.25, 1.75, 2.25)},
    "desenvolvimento": {"m": (0.55, 0.8, 1.1, 1.4), "f": (0.35, 0.5, 0.75, 1.0)},
}
NIVEIS_FORCA = ("iniciante", "novato", "intermediario", "avancado", "elite")

PRESSAO_ROTULOS = ("otima", "normal", "pre-hipertensao", "hipertensao estagio 1",
                   "hipertensao estagio 2", "hipertensao estagio 3")

# marcador: (unidade, faixa de adulto por sexo (min, max) ou None, nota quando fora da faixa)
EXAMES = {
    "hematocrito": ("%", {"m": (40, 52), "f": (36, 46)},
                    "Sangue mais espesso sobe o risco de trombose. Hidratacao e medico."),
    "hemoglobina": ("g/dL", {"m": (13.5, 17.5), "f": (12.0, 15.5)}, "Avaliar junto com o hematocrito."),
    "hdl": ("mg/dL", {"m": (40, None), "f": (50, None)},
            "HDL baixo eleva risco cardiovascular. Cardio, fibras e gordura boa ajudam."),
    "ldl": ("mg/dL", {"m": (None, 130), "f": (None, 130)}, "LDL alto: rever gordura saturada e levar ao medico."),
    "triglicerides": ("mg/dL", {"m": (None, 150), "f": (None, 150)}, "Reduzir acucar, alcool e excesso calorico."),
    "colesterol_total": ("mg/dL", {"m": (None, 190), "f": (None, 190)}, "Interpretar junto com HDL e LDL."),
    "tgo": ("U/L", {"m": (None, 40), "f": (None, 32)},
            "Treino pesado eleva TGO/TGP por lesao muscular; GGT ajuda a separar do figado."),
    "tgp": ("U/L", {"m": (None, 41), "f": (None, 33)},
            "Treino pesado eleva TGO/TGP por lesao muscular; GGT ajuda a separar do figado."),
    "ggt": ("U/L", {"m": (None, 60), "f": (None, 40)}, "GGT alta aponta sobrecarga do figado. Medico."),
    "creatinina": ("mg/dL", {"m": (0.7, 1.3), "f": (0.6, 1.1)},
                   "Muita massa muscular e creatina elevam o valor sem doenca renal; confirmar com o medico."),
    "glicemia": ("mg/dL", {"m": (70, 99), "f": (70, 99)}, "Valor em jejum. Repetir e levar ao medico."),
    "testosterona_total": ("ng/dL", {"m": (300, 1000), "f": (15, 70)},
                           "Faixa fisiologica de adulto, coleta pela manha. Fora dela, quem define conduta e o medico."),
    "estradiol": ("pg/mL", {"m": (10, 40), "f": None}, "Fora da faixa: avaliar com o medico, sem automedicacao."),
    "lh": ("mUI/mL", {"m": (1.7, 8.6), "f": None}, "LH baixo indica eixo hormonal suprimido; afeta fertilidade."),
    "fsh": ("mUI/mL", {"m": (1.5, 12.4), "f": None}, "FSH baixo indica eixo hormonal suprimido; afeta fertilidade."),
    "prolactina": ("ng/mL", {"m": (4, 15), "f": (5, 23)}, "Alteracao pede investigacao medica."),
    "psa": ("ng/mL", {"m": (None, 4.0), "f": None}, "Abaixo de 50 anos, acima de 2,5 ja pede avaliacao. Urologista."),
    "tsh": ("mUI/L", {"m": (0.4, 4.5), "f": (0.4, 4.5)}, "Tireoide fora da faixa muda gasto calorico. Medico."),
}

# por 100 g: (rotulo, proteina, carboidrato, gordura)
ALIMENTOS = {
    "whey": ("Whey protein (po)", 80.0, 8.0, 6.0),
    "frango": ("Peito de frango grelhado", 31.0, 0.0, 3.6),
    "tilapia": ("Tilapia grelhada", 26.0, 0.0, 2.7),
    "patinho": ("Patinho grelhado", 32.0, 0.0, 7.0),
    "arroz": ("Arroz branco cozido", 2.5, 28.0, 0.2),
    "batata_doce": ("Batata-doce cozida", 0.6, 18.4, 0.1),
    "aveia": ("Aveia em flocos", 14.0, 66.0, 8.5),
    "pao_frances": ("Pao frances", 8.0, 58.0, 3.0),
    "banana": ("Banana", 1.3, 26.0, 0.1),
    "macarrao": ("Macarrao cozido", 5.0, 30.0, 1.0),
    "azeite": ("Azeite de oliva", 0.0, 0.0, 100.0),
    "pasta_amendoim": ("Pasta de amendoim", 25.0, 20.0, 50.0),
    "castanha": ("Castanha-do-para", 14.0, 12.0, 66.0),
    "abacate": ("Abacate", 1.2, 6.0, 8.4),
}

# (fonte de proteina, fonte de carboidrato, fonte de gordura) por refeicao, em rodizio
MODELOS_REFEICAO = [
    ("whey", "aveia", "pasta_amendoim"),
    ("frango", "arroz", "azeite"),
    ("tilapia", "batata_doce", "azeite"),
    ("patinho", "macarrao", "azeite"),
    ("frango", "pao_frances", "abacate"),
    ("whey", "banana", "castanha"),
]

CAMPOS_HISTORICO = ["data", "peso", "gordura", "cintura", "calorias"]

# codigo: (rotulo, grupo principal, composto?, chave de 1RM em --levantamento ou None)
EXERCICIOS = {
    "agachamento": ("Agachamento livre", "quadriceps", True, "agachamento"),
    "leg_press": ("Leg press 45", "quadriceps", True, None),
    "afundo": ("Afundo com halteres", "quadriceps", True, None),
    "cadeira_extensora": ("Cadeira extensora", "quadriceps", False, None),
    "terra": ("Levantamento terra", "posterior", True, "terra"),
    "stiff": ("Stiff com barra", "posterior", True, None),
    "mesa_flexora": ("Mesa flexora", "posterior", False, None),
    "elevacao_pelvica": ("Elevacao pelvica", "gluteos", True, None),
    "panturrilha": ("Panturrilha em pe", "panturrilha", False, None),
    "supino": ("Supino reto com barra", "peito", True, "supino"),
    "supino_inclinado": ("Supino inclinado com halteres", "peito", True, None),
    "crucifixo": ("Crucifixo na maquina", "peito", False, None),
    "desenvolvimento": ("Desenvolvimento com barra", "ombros", True, "desenvolvimento"),
    "elevacao_lateral": ("Elevacao lateral", "ombros", False, None),
    "face_pull": ("Face pull na polia", "ombros", False, None),
    "barra_fixa": ("Barra fixa (ou graviton)", "costas", True, None),
    "puxada": ("Puxada frontal na polia", "costas", True, None),
    "remada_curvada": ("Remada curvada com barra", "costas", True, None),
    "remada_baixa": ("Remada baixa na polia", "costas", True, None),
    "rosca_direta": ("Rosca direta", "biceps", False, None),
    "rosca_martelo": ("Rosca martelo", "biceps", False, None),
    "triceps_corda": ("Triceps na polia com corda", "triceps", False, None),
    "triceps_testa": ("Triceps testa", "triceps", False, None),
    "prancha": ("Prancha", "core", False, None),
    "abdominal": ("Abdominal na polia", "core", False, None),
}
REPS_ESPECIAIS = {"prancha": "30-60 s", "abdominal": "12-20", "panturrilha": "10-15"}

MODELOS_TREINO = {
    "full_a": ("Corpo inteiro A",
               ("agachamento", "supino", "remada_curvada", "elevacao_lateral", "rosca_direta", "prancha")),
    "full_b": ("Corpo inteiro B",
               ("terra", "desenvolvimento", "puxada", "leg_press", "triceps_corda", "abdominal")),
    "full_c": ("Corpo inteiro C",
               ("leg_press", "supino_inclinado", "remada_baixa", "mesa_flexora", "elevacao_lateral", "panturrilha")),
    "push": ("Empurrar A: peito, ombros e triceps",
             ("supino", "supino_inclinado", "desenvolvimento", "elevacao_lateral", "triceps_corda",
              "triceps_testa")),
    "pull": ("Puxar A: costas e biceps",
             ("barra_fixa", "remada_curvada", "puxada", "face_pull", "rosca_direta", "rosca_martelo")),
    "legs": ("Pernas A",
             ("agachamento", "stiff", "leg_press", "mesa_flexora", "panturrilha", "prancha")),
    "push_b": ("Empurrar B: ombros, peito e triceps",
               ("desenvolvimento", "supino_inclinado", "crucifixo", "elevacao_lateral", "triceps_testa",
                "triceps_corda")),
    "pull_b": ("Puxar B: costas e biceps",
               ("terra", "remada_baixa", "puxada", "face_pull", "rosca_martelo", "rosca_direta")),
    "legs_b": ("Pernas B",
               ("leg_press", "elevacao_pelvica", "afundo", "cadeira_extensora", "mesa_flexora",
                "panturrilha", "abdominal")),
    "upper": ("Superiores A",
              ("supino", "remada_curvada", "desenvolvimento", "puxada", "rosca_direta", "triceps_corda")),
    "lower": ("Inferiores A",
              ("agachamento", "stiff", "leg_press", "mesa_flexora", "panturrilha", "prancha")),
    "upper_b": ("Superiores B",
                ("supino_inclinado", "barra_fixa", "elevacao_lateral", "remada_baixa", "rosca_martelo",
                 "triceps_testa")),
    "lower_b": ("Inferiores B",
                ("terra", "leg_press", "afundo", "cadeira_extensora", "panturrilha", "abdominal")),
}

# dias de treino por semana -> sequencia de modelos (3 dias troca para push/pull/legs fora do iniciante)
DIVISOES = {
    1: ("full_a",),
    2: ("full_a", "full_b"),
    3: ("full_a", "full_b", "full_c"),
    4: ("upper", "lower", "upper_b", "lower_b"),
    5: ("push", "pull", "legs", "upper_b", "lower_b"),
    6: ("push", "pull", "legs", "push_b", "pull_b", "legs_b"),
}
DIAS_TREINO = {
    1: ("seg",), 2: ("seg", "qui"), 3: ("seg", "qua", "sex"), 4: ("seg", "ter", "qui", "sex"),
    5: ("seg", "ter", "qua", "sex", "sab"), 6: ("seg", "ter", "qua", "qui", "sex", "sab"),
    7: ("seg", "ter", "qua", "qui", "sex", "sab"),
}
VOLUME_ROTULOS = ("baixo", "minimo eficaz", "faixa ideal", "alto")

LINHA_DO_TEMPO = {
    "natural": [
        ("Dias 1-7", "Adaptacao a dieta. Fome e queda de energia no deficit; peso oscila por agua e glicogenio."),
        ("Semanas 2-4", "Peso estabiliza na tendencia real. Forca sobe por adaptacao neural."),
        ("Semanas 5-8", "Mudanca visivel no espelho e nas medidas. Ajuste calorias se o peso travar 2 semanas."),
        ("Semanas 9-12", "Ganho ou perda consolidado. Reavalie metas e recalcule com o peso novo."),
    ],
    "trt": [
        ("Dias 1-7", "Pouca mudanca fisica. Possivel melhora de disposicao e libido."),
        ("Semanas 2-4", "Retencao leve de agua, recuperacao melhor entre treinos, apetite maior."),
        ("Semanas 5-8", "Forca e volume muscular sobem. Hematocrito e pressao podem subir: medir."),
        ("Semanas 9-12", "Composicao corporal muda de forma clara. Hora de repetir exames com o medico."),
    ],
    "hormonizado": [
        ("Dias 1-7", "Retencao de agua (+1 a 2 kg na balanca sem ser gordura), apetite maior, pump mais forte."),
        ("Semanas 2-4", "Forca sobe rapido, recuperacao acelera. Pele oleosa, acne e pressao alta podem aparecer."),
        ("Semanas 5-8", "Ganho muscular visivel. Tendoes nao acompanham o musculo: suba carga devagar. "
                        "Colesterol HDL cai, hematocrito sobe, sono e humor podem oscilar."),
        ("Semanas 9-12", "Pico de resposta. O eixo hormonal natural esta suprimido; fertilidade reduzida. "
                         "Exames obrigatorios antes de qualquer decisao sobre continuar ou parar."),
    ],
}

CHECKLIST_BASE = [
    "Pesar em jejum, mesmo horario, e usar a media semanal, nao o dia isolado.",
    "Medir cintura 1x por semana e tirar foto no mesmo local e luz.",
    "Pesar a comida na balanca nas primeiras 4 semanas, no minimo.",
    "Dormir 7-9 h. Sono ruim derruba recuperacao e aumenta fome.",
    "Treino de forca com progressao de carga; 8-10 mil passos por dia.",
]

CHECKLIST_HORMONAL = [
    "Acompanhamento com medico (endocrinologista ou medico do esporte) antes, durante e depois.",
    "Exames de base e a cada 8-12 semanas: hemograma (hematocrito), lipidograma, TGO/TGP/GGT, "
    "creatinina/ureia, testosterona total e livre, estradiol, LH/FSH, prolactina, PSA, glicemia.",
    "Medir pressao arterial em casa 3x por semana. Acima de 14x9 repetido: medico.",
    "Cardio 3-4x por semana, 20-40 min: protege coracao e controla pressao.",
    "Sodio controlado, potassio via comida (banana, batata, feijao), alcool no minimo.",
    "Sinais de alerta, procurar atendimento: dor no peito, falta de ar, dor/inchaco em uma perna, "
    "dor de cabeca forte, pele ou olhos amarelados, mama dolorida ou com nodulo.",
    "Nunca compartilhar agulhas; material esteril e descarte correto.",
]


@dataclass
class Resultado:
    perfil: str
    objetivo: str
    biotipo: str
    experiencia: str
    tmb: float
    gasto_total: float
    calorias: float
    ajuste_kcal: float
    proteina_g: float
    carbo_g: float
    gordura_g: float
    agua_l: float
    fibra_g: float
    variacao_kg_semana: float
    gordura_pct: Optional[float] = None
    gordura_origem: str = "nao informada"
    composicao: dict = field(default_factory=dict)
    ciclo_carbo: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    refeicoes: list = field(default_factory=list)
    cardapio: list = field(default_factory=list)
    projecao: list = field(default_factory=list)
    forca: list = field(default_factory=list)
    treino: dict = field(default_factory=dict)
    exames: list = field(default_factory=list)
    pressao: dict = field(default_factory=dict)
    historico: dict = field(default_factory=dict)
    suplementos: list = field(default_factory=list)
    notas: list = field(default_factory=list)
    avisos: list = field(default_factory=list)


def classificar(valor, limites, rotulos):
    """Devolve o rotulo da faixa em que o valor cai (limites em ordem crescente)."""
    return rotulos[sum(1 for limite in limites if valor >= limite)]


def calcular_tmb(peso, altura, idade, sexo, gordura):
    """Katch-McArdle se houver % de gordura; senao Mifflin-St Jeor."""
    if gordura is not None:
        massa_magra = peso * (1 - gordura / 100.0)
        LOG.debug("Katch-McArdle, massa magra=%.1f kg", massa_magra)
        return 370 + 21.6 * massa_magra
    base = 10 * peso + 6.25 * altura - 5 * idade
    LOG.debug("Mifflin-St Jeor, base=%.1f", base)
    return base + 5 if sexo == "m" else base - 161


def ajuste_idade(idade):
    """Devolve (proteina extra em g/kg, fator de ritmo, nota) conforme a faixa etaria."""
    if idade < 30:
        return 0.0, 1.0, "Idade: recuperacao no auge; o corpo tolera volume alto de treino."
    if idade < 40:
        return 0.0, 0.95, "Idade: recuperacao ainda boa; sono e aquecimento passam a pesar mais."
    if idade < 50:
        return 0.2, 0.85, "Idade 40+: mais proteina, ritmo mais conservador e 1 dia extra de descanso."
    return 0.3, 0.75, "Idade 50+: proteina alta, progressao lenta de carga e check-up cardiologico anual."


def gordura_navy(sexo, altura, cintura, pescoco, quadril):
    """Estimativa de % de gordura pelo metodo da Marinha dos EUA (medidas em cm)."""
    if sexo == "m":
        diferenca = cintura - pescoco
        if diferenca <= 0:
            raise ValueError("cintura precisa ser maior que o pescoco para estimar a gordura")
        densidade = 1.0324 - 0.19077 * math.log10(diferenca) + 0.15456 * math.log10(altura)
    else:
        if quadril is None:
            raise ValueError("para sexo 'f' a estimativa de gordura exige --quadril")
        diferenca = cintura + quadril - pescoco
        if diferenca <= 0:
            raise ValueError("medidas de cintura, quadril e pescoco inconsistentes")
        densidade = 1.29579 - 0.35004 * math.log10(diferenca) + 0.22100 * math.log10(altura)
    if densidade <= 0:
        raise ValueError("medidas corporais inconsistentes para estimar a gordura")
    estimativa = 495.0 / densidade - 450.0
    LOG.debug("Navy: densidade=%.4f gordura=%.1f%%", densidade, estimativa)
    return min(max(estimativa, 3.0), 60.0)


def analisar_composicao(peso, altura, sexo, gordura, cintura):
    metros = altura / 100.0
    comp = {"imc": round(peso / metros ** 2, 1)}
    if gordura is not None:
        magra = peso * (1 - gordura / 100.0)
        ffmi = magra / metros ** 2
        ffmi_norm = ffmi + 6.1 * (1.8 - metros)
        comp.update(
            massa_magra_kg=round(magra, 1), massa_gorda_kg=round(peso - magra, 1),
            ffmi=round(ffmi, 1), ffmi_normalizado=round(ffmi_norm, 1),
            ffmi_classe=classificar(ffmi_norm, FFMI_FAIXAS[sexo], FFMI_ROTULOS),
        )
    if cintura is not None:
        comp["cintura_altura"] = round(cintura / altura, 2)
    return comp


def calcular_ciclo_carbo(carbo, calorias, treinos):
    """Mais carboidrato no dia de treino, menos no descanso, mesma media semanal."""
    descansos = 7 - treinos
    if treinos <= 0 or descansos <= 0 or carbo <= 0:
        return {}
    fator_treino = min(1.35, (7 - 0.75 * descansos) / treinos)
    carbo_treino = carbo * fator_treino
    carbo_descanso = (7 * carbo - treinos * carbo_treino) / descansos
    return {
        "treinos_semana": treinos,
        "carbo_treino_g": round(carbo_treino),
        "carbo_descanso_g": round(carbo_descanso),
        "kcal_treino": round(calorias + (carbo_treino - carbo) * 4),
        "kcal_descanso": round(calorias + (carbo_descanso - carbo) * 4),
    }


def calcular_meta(peso, gordura, alvo, variacao, calorias, gasto):
    """Tempo ate a gordura alvo, com 1 semana na manutencao a cada 8 de deficit."""
    magra = peso * (1 - gordura / 100.0)
    peso_alvo = magra / (1 - alvo / 100.0)
    perder = peso - peso_alvo
    semanas_deficit = math.ceil(perder / abs(variacao))
    pausas = (semanas_deficit - 1) // 8
    fases, restante = [], semanas_deficit
    while restante > 0:
        bloco = min(8, restante)
        fases.append({"fase": "deficit", "semanas": bloco, "kcal": round(calorias)})
        restante -= bloco
        if restante > 0:
            fases.append({"fase": "pausa na manutencao", "semanas": 1, "kcal": round(gasto)})
    return {
        "gordura_alvo_pct": alvo, "peso_alvo_kg": round(peso_alvo, 1), "perder_kg": round(perder, 1),
        "semanas_deficit": semanas_deficit, "semanas_pausa": pausas,
        "semanas_total": semanas_deficit + pausas, "fases": fases,
    }


def montar_cardapio(refeicoes):
    """Cardapio exemplo: resolve as gramas de 3 alimentos por refeicao (Gauss-Seidel)."""
    cardapio = []
    for indice, alvo in enumerate(refeicoes):
        chaves = MODELOS_REFEICAO[indice % len(MODELOS_REFEICAO)]
        fontes = [tuple(v / 100.0 for v in ALIMENTOS[c][1:]) for c in chaves]
        (pp, pc, pg), (cp, cc, cg), (gp, gc, gg) = fontes
        qp = qc = qg = 0.0
        for _ in range(25):
            qp = max(0.0, (alvo["proteina_g"] - qc * cp - qg * gp) / pp)
            qc = max(0.0, (alvo["carbo_g"] - qp * pc - qg * gc) / cc)
            qg = max(0.0, (alvo["gordura_g"] - qp * pg - qc * cg) / gg)
        passo_gordura = 1 if gg >= 0.4 else 5
        gramas = [round(qp / 5) * 5, round(qc / 5) * 5, round(qg / passo_gordura) * passo_gordura]
        prot = sum(g * f[0] for g, f in zip(gramas, fontes))
        carb = sum(g * f[1] for g, f in zip(gramas, fontes))
        gord = sum(g * f[2] for g, f in zip(gramas, fontes))
        cardapio.append({
            "refeicao": alvo["refeicao"],
            "itens": [{"alimento": ALIMENTOS[c][0], "gramas": g} for c, g in zip(chaves, gramas) if g > 0],
            "proteina_g": round(prot), "carbo_g": round(carb), "gordura_g": round(gord),
            "kcal": round(prot * 4 + carb * 4 + gord * 9),
        })
    return cardapio


def analisar_forca(levantamentos, peso, sexo):
    """1RM estimado (media de Epley e Brzycki), forca relativa e cargas de treino."""
    saida = []
    for nome, carga, reps in levantamentos:
        if reps == 1:
            rm = carga
        else:
            rm = (carga * (1 + reps / 30.0) + carga * 36.0 / (37 - reps)) / 2
        item = {
            "exercicio": nome, "carga_kg": carga, "reps": reps,
            "rm_estimado_kg": round(rm, 1), "relativo": round(rm / peso, 2),
            "nivel": classificar(rm / peso, PADROES_FORCA[nome][sexo], NIVEIS_FORCA) if nome in PADROES_FORCA else None,
            "cargas_treino": {f"{p}%": round(rm * p / 100 / 2.5) * 2.5 for p in (90, 85, 80, 75, 70)},
        }
        saida.append(item)
    return saida


def montar_treino(dias, experiencia, objetivo, perfil, idade, forca):
    """Divisao semanal com series, repeticoes, volume por grupo, progressao e cardio."""
    if dias <= 0:
        return {}
    if dias == 3 and experiencia != "iniciante":
        chaves = ("push", "pull", "legs")
    else:
        chaves = DIVISOES[min(dias, 6)]

    series_composto = {"iniciante": 3, "intermediario": 4, "avancado": 4}[experiencia]
    series_isolado = {"iniciante": 2, "intermediario": 3, "avancado": 4}[experiencia]
    if idade >= 50:
        series_composto, series_isolado = max(2, series_composto - 1), max(2, series_isolado - 1)
    if objetivo == "manter":
        series_isolado = max(2, series_isolado - 1)
    reps_composto = "8-12" if experiencia == "iniciante" else "6-10"
    fracao_carga = 0.70 if experiencia == "iniciante" else 0.75
    rm_conhecido = {item["exercicio"]: item["rm_estimado_kg"] for item in forca}

    sessoes, volume = [], {}
    for dia, chave in zip(DIAS_TREINO[dias], chaves):
        titulo, codigos = MODELOS_TREINO[chave]
        exercicios = []
        for codigo in codigos:
            rotulo, grupo, composto, chave_rm = EXERCICIOS[codigo]
            series = series_composto if composto else series_isolado
            carga = None
            if chave_rm in rm_conhecido:
                carga = round(rm_conhecido[chave_rm] * fracao_carga / 2.5) * 2.5
            exercicios.append({
                "exercicio": rotulo, "grupo": grupo, "series": series,
                "reps": REPS_ESPECIAIS.get(codigo, reps_composto if composto else "10-15"),
                "descanso": "2-3 min" if composto else "60-90 s", "carga_sugerida_kg": carga,
            })
            volume[grupo] = volume.get(grupo, 0) + series
        sessoes.append({"dia": dia, "treino": titulo, "exercicios": exercicios})
    if dias == 7:
        sessoes.append({"dia": "dom", "treino": "Recuperacao ativa: 30-40 min de caminhada e mobilidade",
                        "exercicios": []})

    if objetivo == "secar":
        cardio = "3-4 sessoes de 25-40 min em ritmo de conversa (zona 2), longe do treino de pernas."
    elif perfil != "natural":
        cardio = "3 sessoes de 20-30 min em ritmo de conversa: a prioridade e a saude do coracao."
    elif objetivo == "crescer":
        cardio = "2 sessoes leves de 20 min: mantem o condicionamento sem roubar recuperacao."
    else:
        cardio = "2-3 sessoes de 20-30 min em ritmo de conversa."

    notas = []
    if objetivo == "secar":
        notas.append("No deficit a prioridade e manter a carga na barra; nao troque peso por repeticoes altas.")
    if perfil != "natural":
        notas.append("Musculo ganha forca antes de tendao e ligamento: suba carga no ritmo da progressao, sem saltos.")
    if experiencia == "iniciante" and dias >= 5:
        notas.append("Iniciante progride igual com 3-4 dias por semana; os dias extras sao opcionais.")
    if dias <= 2:
        notas.append("Com ate 2 treinos o volume por grupo fica baixo: serve para manter ou para quem esta comecando.")
    if dias == 7:
        notas.append("Sem nenhum dia livre a recuperacao cai: o setimo dia e apenas recuperacao ativa.")
    if idade >= 40:
        notas.append("40+: aquecimento mais longo e series de aproximacao antes de toda carga pesada.")

    return {
        "dias_semana": dias,
        "sessoes": sessoes,
        "volume_semanal": {
            grupo: {"series": total, "classe": classificar(total, (6, 10, 21), VOLUME_ROTULOS)}
            for grupo, total in sorted(volume.items())
        },
        "aquecimento": "5-10 min de cardio leve e 2-3 series progressivas do primeiro exercicio.",
        "progressao": "Ao bater o topo da faixa de repeticoes em todas as series, suba 2,5 kg (superiores) "
                      "ou 5 kg (inferiores).",
        "intensidade": "Termine cada serie com 1-3 repeticoes de sobra; falha so na ultima serie dos isolados.",
        "semana_leve": f"A cada {'4-6' if idade >= 40 else '6-8'} semanas: metade das series, mesma carga.",
        "cardio": cardio,
        "notas": notas,
    }


def avaliar_exames(itens, sexo):
    """Compara cada marcador com a faixa generica de adulto. A referencia do laudo prevalece."""
    saida = []
    for nome, valor in itens:
        unidade, faixas, nota = EXAMES[nome]
        faixa = faixas.get(sexo)
        if faixa is None:
            situacao, referencia = "sem faixa generica", "usar a referencia do laudo"
        else:
            minimo, maximo = faixa
            if minimo is not None and maximo is not None:
                referencia = f"{minimo:g}-{maximo:g}"
            elif minimo is not None:
                referencia = f">= {minimo:g}"
            else:
                referencia = f"<= {maximo:g}"
            if minimo is not None and valor < minimo:
                situacao = "abaixo"
            elif maximo is not None and valor > maximo:
                situacao = "acima"
            else:
                situacao = "dentro"
        if nome == "hematocrito" and valor > 54:
            situacao = "acima (critico)"
            nota = "Acima de 54%: risco real de trombose. Procurar medico sem demora."
        saida.append({
            "marcador": nome, "valor": valor, "unidade": unidade, "referencia": referencia,
            "situacao": situacao, "nota": nota if situacao not in ("dentro", "sem faixa generica") else "",
        })
    return saida


def avaliar_pressao(sistolica, diastolica):
    nivel = max(
        sum(1 for limite in (120, 130, 140, 160, 180) if sistolica >= limite),
        sum(1 for limite in (80, 85, 90, 100, 110) if diastolica >= limite),
    )
    return {"sistolica": sistolica, "diastolica": diastolica, "nivel": nivel, "classe": PRESSAO_ROTULOS[nivel]}


def listar_suplementos(peso):
    cafeina = int(min(400, round(peso * 3 / 10) * 10))
    return [
        f"Creatina monoidratada: {3 if peso < 70 else 5} g por dia, todos os dias, qualquer horario.",
        f"Cafeina: ate {cafeina} mg, 30-60 min antes do treino; evitar depois das 15 h.",
        "Proteina em po (whey ou vegetal): so para fechar a meta diaria de proteina.",
        "Vitamina D e omega-3: apenas se exame ou dieta mostrarem falta.",
    ]


def recomendar_ajuste(objetivo, esperado, real):
    if objetivo == "secar":
        if real > esperado * 0.5:
            return "Perda abaixo do esperado: reduza 150 kcal (carboidrato) ou some 2 mil passos por dia."
        if real < esperado * 1.5:
            return "Perda rapida demais: suba 150 kcal para proteger a massa magra."
    elif objetivo == "crescer":
        if real < esperado * 0.5:
            return "Ganho abaixo do esperado: suba 150 kcal (carboidrato)."
        if real > esperado * 1.5:
            return "Ganho rapido demais: reduza 150 kcal, o excesso vira gordura."
    else:
        if real > 0.25:
            return "Peso subindo na manutencao: reduza 150 kcal."
        if real < -0.25:
            return "Peso caindo na manutencao: suba 150 kcal."
    return "Ritmo dentro do esperado: mantenha o plano."


def registrar_historico(caminho, data, peso, gordura, cintura, calorias, objetivo, esperado):
    """Acrescenta o registro do dia ao CSV e compara o ritmo real com o esperado."""
    registros = []
    existe = os.path.exists(caminho) and os.path.getsize(caminho) > 0
    if existe:
        with open(caminho, newline="", encoding="utf-8") as arquivo:
            leitor = csv.DictReader(arquivo)
            if leitor.fieldnames != CAMPOS_HISTORICO:
                raise ValueError(f"cabecalho inesperado em '{caminho}'; esperado: {','.join(CAMPOS_HISTORICO)}")
            for numero, linha in enumerate(leitor, start=2):
                try:
                    valor_peso = float(linha["peso"])
                    if not math.isfinite(valor_peso) or valor_peso <= 0:
                        raise ValueError("peso invalido")
                    registros.append((datetime.date.fromisoformat(linha["data"]), valor_peso))
                except (TypeError, ValueError):
                    LOG.warning("Linha %d de '%s' ignorada: formato invalido", numero, caminho)
        with open(caminho, "rb") as arquivo:
            arquivo.seek(-1, os.SEEK_END)
            termina_em_quebra = arquivo.read(1) == b"\n"
    with open(caminho, "a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_HISTORICO)
        if not existe:
            escritor.writeheader()
        elif not termina_em_quebra:
            arquivo.write("\n")
        escritor.writerow({
            "data": data.isoformat(), "peso": f"{peso:g}",
            "gordura": "" if gordura is None else f"{gordura:.1f}",
            "cintura": "" if cintura is None else f"{cintura:g}",
            "calorias": f"{calorias:.0f}",
        })
    registros.append((data, peso))
    LOG.info("Historico atualizado em '%s' (%d registros)", caminho, len(registros))

    serie = sorted(dict(registros).items())
    historico = {"arquivo": caminho, "registros": len(serie), "ritmo_esperado_kg_semana": round(esperado, 2)}
    if len(serie) < 2:
        historico["recomendacao"] = "Primeiro registro salvo. Registre o peso toda semana para medir o ritmo real."
        return historico
    fim_data, fim_peso = serie[-1]
    limite = fim_data - datetime.timedelta(days=28)
    anteriores = [par for par in serie[:-1] if par[0] >= limite]
    base_data, base_peso = anteriores[0] if anteriores else serie[-2]
    dias = (fim_data - base_data).days
    historico["dias_analisados"] = dias
    if dias < 7:
        historico["recomendacao"] = "Menos de 7 dias entre registros: cedo demais para medir ritmo."
        return historico
    real = (fim_peso - base_peso) / (dias / 7.0)
    historico["ritmo_real_kg_semana"] = round(real, 2)
    if dias < 14:
        historico["recomendacao"] = "Menos de 14 dias de dados: continue registrando antes de mexer nas calorias."
    else:
        historico["recomendacao"] = recomendar_ajuste(objetivo, esperado, real)
    return historico


def calcular(args):
    perfil = PERFIS[args.perfil]
    biotipo = BIOTIPOS[args.biotipo]
    prot_extra, fator_ritmo, nota_idade = ajuste_idade(args.idade)
    avisos = []
    notas = [biotipo["nota"], nota_idade]

    gordura, origem = args.gordura, "informada"
    if gordura is None and args.cintura is not None and args.pescoco is not None:
        gordura = gordura_navy(args.sexo, args.altura, args.cintura, args.pescoco, args.quadril)
        origem = "estimada por fita (US Navy)"
        avisos.append("Gordura estimada por fita metrica: margem de erro de 3 a 4 pontos percentuais.")
    elif gordura is None:
        origem = "nao informada"

    tmb = calcular_tmb(args.peso, args.altura, args.idade, args.sexo, gordura)
    gasto = tmb * ATIVIDADE[args.atividade] * biotipo["gasto"]

    if args.objetivo == "secar":
        ajuste = -args.peso * perfil["corte"] * fator_ritmo * KCAL_POR_KG / 7
    elif args.objetivo == "crescer":
        ajuste = args.peso * perfil["ganho"] * fator_ritmo * EXPERIENCIA[args.experiencia] * KCAL_POR_KG / 7
    else:
        ajuste = 0.0

    calorias = gasto + ajuste
    piso = 1500.0 if args.sexo == "m" else 1200.0
    if calorias < piso:
        avisos.append(f"Meta calculada ({calorias:.0f} kcal) abaixo do piso seguro; fixada em {piso:.0f} kcal.")
        calorias = piso
        ajuste = calorias - gasto

    # Proteina sobre massa magra estimada quando a gordura e alta, para nao inflar o valor
    peso_ref = args.peso
    if gordura is not None and gordura > 25:
        peso_ref = args.peso * (1 - gordura / 100.0) / 0.80
        LOG.debug("Peso de referencia ajustado para proteina: %.1f kg", peso_ref)

    proteina = (perfil["prot"][args.objetivo] + prot_extra) * peso_ref
    gordura_g = max(0.6, perfil["gord"] + biotipo["gord"]) * args.peso
    carbo = (calorias - proteina * 4 - gordura_g * 9) / 4

    if carbo < 50:
        gordura_g = max(0.6 * args.peso, (calorias - proteina * 4 - 50 * 4) / 9)
        carbo = (calorias - proteina * 4 - gordura_g * 9) / 4
        avisos.append("Carboidrato muito baixo; gordura reduzida ao minimo para abrir espaco.")
    if carbo < 0:
        carbo = 0.0
        avisos.append(f"Proteina e gordura minimas somam {proteina * 4 + gordura_g * 9:.0f} kcal, acima da meta. "
                      "Aumente a atividade ou reduza o deficit.")

    variacao = ajuste * 7 / KCAL_POR_KG
    projecao = [{"semana": s, "peso_kg": round(args.peso + variacao * s, 1)} for s in range(1, args.semanas + 1)]

    n = args.refeicoes
    refeicoes = [
        {"refeicao": i + 1, "proteina_g": round(proteina / n), "carbo_g": round(carbo / n),
         "gordura_g": round(gordura_g / n), "kcal": round(calorias / n)}
        for i in range(n)
    ]

    meta = {}
    if args.gordura_alvo is not None:
        if args.objetivo != "secar":
            avisos.append("--gordura-alvo so e usado com objetivo 'secar'; ignorado.")
        elif gordura is None:
            avisos.append("--gordura-alvo exige --gordura ou medidas de cintura e pescoco; ignorado.")
        elif args.gordura_alvo >= gordura:
            avisos.append("Gordura alvo maior ou igual a atual; nada a calcular.")
        elif variacao >= 0:
            avisos.append("Sem deficit efetivo; nao ha como estimar o tempo ate a gordura alvo.")
        else:
            meta = calcular_meta(args.peso, gordura, args.gordura_alvo, variacao, calorias, gasto)
            if args.gordura_alvo < (8 if args.sexo == "m" else 16):
                avisos.append("Gordura alvo muito baixa: sustentavel so por pouco tempo e com acompanhamento.")

    pressao = avaliar_pressao(*args.pressao) if args.pressao else {}
    exames = avaliar_exames(args.exame or [], args.sexo)
    forca = analisar_forca(args.levantamento or [], args.peso, args.sexo)
    treino = {}
    if args.treino:
        treino = montar_treino(args.treinos_semana, args.experiencia, args.objetivo, args.perfil, args.idade, forca)
        if not treino:
            avisos.append("--treino exige --treinos-semana maior que zero; plano de treino nao gerado.")

    if args.perfil != "natural":
        avisos.append("Retencao de agua nas primeiras semanas mascara a balanca: confie em cintura e fotos.")
    if args.perfil == "hormonizado" and args.idade < 21:
        avisos.append("Abaixo de 21 anos o risco para o eixo hormonal e crescimento e maior. Converse com um medico.")
    if args.objetivo == "secar" and gordura is not None and gordura < (10 if args.sexo == "m" else 18):
        avisos.append("Gordura ja baixa: deficit agressivo custa massa magra e saude hormonal.")
    if args.cintura is not None and args.cintura / args.altura > 0.5:
        avisos.append("Cintura acima de metade da altura: risco cardiometabolico aumentado.")
    if pressao and pressao["nivel"] >= 3:
        avisos.append("Pressao em faixa de hipertensao: cortar cafeina e estimulantes e procurar medico.")
    elif pressao and pressao["nivel"] == 2:
        avisos.append("Pressao no limite: reduzir sodio, manter cardio e repetir a medida em dias diferentes.")
    fora = [e["marcador"] for e in exames if e["situacao"] not in ("dentro", "sem faixa generica")]
    if fora:
        avisos.append("Exames fora da faixa (" + ", ".join(fora) + "): leve o laudo ao medico. "
                      "Nao ajuste nada por conta propria.")

    res = Resultado(
        perfil=args.perfil, objetivo=args.objetivo, biotipo=args.biotipo, experiencia=args.experiencia,
        tmb=round(tmb), gasto_total=round(gasto), calorias=round(calorias), ajuste_kcal=round(ajuste),
        proteina_g=round(proteina), carbo_g=round(carbo), gordura_g=round(gordura_g),
        agua_l=round(args.peso * 0.04, 1), fibra_g=round(calorias / 1000 * 14),
        variacao_kg_semana=round(variacao, 2),
        gordura_pct=None if gordura is None else round(gordura, 1), gordura_origem=origem,
        composicao=analisar_composicao(args.peso, args.altura, args.sexo, gordura, args.cintura),
        ciclo_carbo=calcular_ciclo_carbo(carbo, calorias, args.treinos_semana),
        meta=meta, refeicoes=refeicoes,
        cardapio=montar_cardapio(refeicoes) if args.cardapio else [],
        projecao=projecao,
        forca=forca, treino=treino,
        exames=exames, pressao=pressao,
        suplementos=listar_suplementos(args.peso), notas=notas, avisos=avisos,
    )
    if args.registrar:
        res.historico = registrar_historico(
            args.registrar, args.data or datetime.date.today(), args.peso, gordura,
            args.cintura, calorias, args.objetivo, variacao,
        )
    return res


def imprimir(res):
    linha = "=" * 70
    print(linha)
    print(f" MAROMBA CALC v2 | perfil: {res.perfil} | objetivo: {res.objetivo} | biotipo: {res.biotipo}")
    print(linha)
    print(" ENERGIA E MACROS")
    print(f"  Taxa metabolica basal : {res.tmb:.0f} kcal")
    print(f"  Gasto total diario    : {res.gasto_total:.0f} kcal")
    print(f"  Meta diaria           : {res.calorias:.0f} kcal ({res.ajuste_kcal:+.0f})")
    print(f"  Proteina              : {res.proteina_g:.0f} g")
    print(f"  Carboidrato           : {res.carbo_g:.0f} g")
    print(f"  Gordura               : {res.gordura_g:.0f} g")
    print(f"  Agua                  : {res.agua_l} L/dia")
    print(f"  Fibra                 : {res.fibra_g:.0f} g/dia")
    print(f"  Ritmo esperado        : {res.variacao_kg_semana:+.2f} kg/semana")

    if res.ciclo_carbo:
        c = res.ciclo_carbo
        print(f"\n CICLO DE CARBOIDRATO ({c['treinos_semana']} treinos por semana)")
        print(f"  Dia de treino   : {c['carbo_treino_g']} g de carboidrato | {c['kcal_treino']} kcal")
        print(f"  Dia de descanso : {c['carbo_descanso_g']} g de carboidrato | {c['kcal_descanso']} kcal")

    comp = res.composicao
    print("\n COMPOSICAO CORPORAL")
    print(f"  IMC                   : {comp['imc']}")
    if res.gordura_pct is not None:
        print(f"  Gordura               : {res.gordura_pct}% ({res.gordura_origem})")
        print(f"  Massa magra / gorda   : {comp['massa_magra_kg']} kg / {comp['massa_gorda_kg']} kg")
        print(f"  FFMI normalizado      : {comp['ffmi_normalizado']} ({comp['ffmi_classe']})")
    else:
        print("  Gordura               : nao informada (use --gordura ou --cintura e --pescoco)")
    if "cintura_altura" in comp:
        print(f"  Cintura / altura      : {comp['cintura_altura']} (ideal ate 0.50)")

    if res.meta:
        m = res.meta
        print(f"\n META: {m['gordura_alvo_pct']:g}% DE GORDURA")
        print(f"  Peso alvo             : {m['peso_alvo_kg']} kg (perder {m['perder_kg']} kg, massa magra mantida)")
        print(f"  Tempo estimado        : {m['semanas_total']} semanas "
              f"({m['semanas_deficit']} de deficit + {m['semanas_pausa']} de pausa)")
        for fase in m["fases"]:
            print(f"   - {fase['fase']}: {fase['semanas']} semana(s) a {fase['kcal']} kcal")

    print("\n DIVISAO POR REFEICAO")
    for r in res.refeicoes:
        print(f"  {r['refeicao']}: {r['kcal']} kcal | P {r['proteina_g']} g | C {r['carbo_g']} g | G {r['gordura_g']} g")

    if res.cardapio:
        print("\n CARDAPIO EXEMPLO (peso do alimento pronto)")
        for r in res.cardapio:
            itens = " + ".join(f"{i['gramas']} g {i['alimento']}" for i in r["itens"])
            print(f"  {r['refeicao']}: {itens}")
            print(f"     = {r['kcal']} kcal | P {r['proteina_g']} g | C {r['carbo_g']} g | G {r['gordura_g']} g")

    print("\n PROJECAO DE PESO")
    for p in res.projecao:
        print(f"  Semana {p['semana']:>2}: {p['peso_kg']} kg")

    if res.forca:
        print("\n FORCA")
        for f in res.forca:
            nivel = f" | nivel: {f['nivel']}" if f["nivel"] else ""
            print(f"  {f['exercicio']}: {f['carga_kg']:g} kg x {f['reps']} -> 1RM ~{f['rm_estimado_kg']} kg "
                  f"({f['relativo']}x o peso corporal){nivel}")
            print("     cargas: " + " | ".join(f"{k} = {v:g} kg" for k, v in f["cargas_treino"].items()))

    if res.treino:
        t = res.treino
        print(f"\n PLANO DE TREINO ({t['dias_semana']} dia(s) por semana)")
        for sessao in t["sessoes"]:
            print(f"  {sessao['dia'].upper()} - {sessao['treino']}")
            for e in sessao["exercicios"]:
                carga = f" | ~{e['carga_sugerida_kg']:g} kg" if e["carga_sugerida_kg"] else ""
                print(f"     {e['exercicio']:<30} {e['series']} x {e['reps']:<8} descanso {e['descanso']}{carga}")
        print("  Volume semanal (series diretas por grupo):")
        for grupo, v in t["volume_semanal"].items():
            print(f"     {grupo:<12} {v['series']:>2} series ({v['classe']})")
        print("     Conta so o trabalho direto: supino e remada tambem treinam triceps e biceps.")
        print(f"  Aquecimento : {t['aquecimento']}")
        print(f"  Progressao  : {t['progressao']}")
        print(f"  Intensidade : {t['intensidade']}")
        print(f"  Semana leve : {t['semana_leve']}")
        print(f"  Cardio      : {t['cardio']}")
        for nota in t["notas"]:
            print(f"  - {nota}")

    if res.exames:
        print("\n EXAMES (faixa generica de adulto; a referencia do seu laudo prevalece)")
        for e in res.exames:
            print(f"  {e['marcador']}: {e['valor']:g} {e['unidade']} | ref. {e['referencia']} | {e['situacao'].upper()}")
            if e["nota"]:
                print(f"     {e['nota']}")

    if res.pressao:
        p = res.pressao
        print(f"\n PRESSAO ARTERIAL: {p['sistolica']}x{p['diastolica']} mmHg -> {p['classe']}")

    if res.historico:
        h = res.historico
        print(f"\n HISTORICO ({h['registros']} registro(s) em {h['arquivo']})")
        if "ritmo_real_kg_semana" in h:
            print(f"  Ritmo real     : {h['ritmo_real_kg_semana']:+.2f} kg/semana em {h['dias_analisados']} dias")
            print(f"  Ritmo esperado : {h['ritmo_esperado_kg_semana']:+.2f} kg/semana")
        print(f"  {h['recomendacao']}")

    print("\n SUPLEMENTOS COM EVIDENCIA")
    for item in res.suplementos:
        print(f"  - {item}")

    print("\n O QUE ACONTECE COM O CORPO")
    for periodo, texto in LINHA_DO_TEMPO[res.perfil]:
        print(f"  [{periodo}] {texto}")

    print("\n CHECKLIST")
    for item in CHECKLIST_BASE + (CHECKLIST_HORMONAL if res.perfil != "natural" else []):
        print(f"  - {item}")

    print("\n NOTAS")
    for nota in res.notas:
        print(f"  - {nota}")
    print("  - Recalcule a cada 4 kg de mudanca ou quando o peso travar por 2 semanas.")

    if res.avisos:
        print("\n AVISOS")
        for aviso in res.avisos:
            print(f"  ! {aviso}")
    print(linha)


def intervalo(minimo, maximo):
    def validar(valor):
        try:
            numero = float(str(valor).replace(",", "."))
        except ValueError:
            raise argparse.ArgumentTypeError(f"'{valor}' nao e um numero")
        if not minimo <= numero <= maximo:
            raise argparse.ArgumentTypeError(f"valor {valor} fora do intervalo {minimo}-{maximo}")
        return numero
    return validar


def inteiro(minimo, maximo):
    def validar(valor):
        try:
            numero = int(valor)
        except ValueError:
            raise argparse.ArgumentTypeError(f"'{valor}' nao e um inteiro")
        if not minimo <= numero <= maximo:
            raise argparse.ArgumentTypeError(f"valor {numero} fora do intervalo {minimo}-{maximo}")
        return numero
    return validar


def tipo_levantamento(valor):
    try:
        nome, resto = valor.split(":", 1)
        carga, reps = resto.lower().split("x", 1)
        nome, carga, reps = nome.strip().lower(), float(carga.replace(",", ".")), int(reps)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{valor}' invalido; use NOME:CARGAxREPS, ex.: supino:100x5")
    if not nome:
        raise argparse.ArgumentTypeError("nome do exercicio vazio")
    if not 1 <= carga <= 600:
        raise argparse.ArgumentTypeError(f"carga {valor} fora do intervalo 1-600 kg")
    if not 1 <= reps <= 15:
        raise argparse.ArgumentTypeError("repeticoes fora do intervalo 1-15 (acima disso o 1RM perde precisao)")
    return nome, carga, reps


def tipo_exame(valor):
    try:
        nome, numero = valor.split("=", 1)
        nome, numero = nome.strip().lower(), float(numero.replace(",", "."))
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{valor}' invalido; use MARCADOR=VALOR, ex.: hematocrito=48")
    if nome not in EXAMES:
        raise argparse.ArgumentTypeError(f"marcador '{nome}' desconhecido; opcoes: {', '.join(sorted(EXAMES))}")
    if not math.isfinite(numero) or numero < 0:
        raise argparse.ArgumentTypeError(f"valor invalido para '{nome}'")
    return nome, numero


def tipo_pressao(valor):
    try:
        sistolica, diastolica = (int(parte) for parte in valor.lower().split("x", 1))
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{valor}' invalido; use SISTOLICAxDIASTOLICA em mmHg, ex.: 125x80")
    if not (60 <= sistolica <= 260 and 30 <= diastolica <= 160 and sistolica > diastolica):
        raise argparse.ArgumentTypeError(f"pressao '{valor}' fora de valores plausiveis (mmHg, ex.: 125x80)")
    return sistolica, diastolica


def tipo_data(valor):
    try:
        return datetime.date.fromisoformat(valor)
    except ValueError:
        raise argparse.ArgumentTypeError(f"data '{valor}' invalida; use AAAA-MM-DD")


def montar_parser():
    p = argparse.ArgumentParser(
        description="Macros, composicao corporal, forca, exames e historico para quem treina.",
        epilog="Marcadores de --exame: " + ", ".join(sorted(EXAMES))
               + ". Exercicios com classificacao em --levantamento: " + ", ".join(sorted(PADROES_FORCA)) + ".",
    )
    corpo = p.add_argument_group("corpo")
    corpo.add_argument("--peso", type=intervalo(35, 250), help="peso em kg (obrigatorio)")
    corpo.add_argument("--altura", type=intervalo(130, 230), help="altura em cm (obrigatorio)")
    corpo.add_argument("--idade", type=inteiro(18, 90), help="idade em anos, 18+ (obrigatorio)")
    corpo.add_argument("--sexo", choices=["m", "f"], default="m")
    corpo.add_argument("--gordura", type=intervalo(3, 60), help="percentual de gordura, se conhecido")
    corpo.add_argument("--cintura", type=intervalo(40, 200), help="cintura em cm, na altura do umbigo")
    corpo.add_argument("--pescoco", type=intervalo(20, 70), help="pescoco em cm (estima gordura junto com a cintura)")
    corpo.add_argument("--quadril", type=intervalo(50, 200), help="quadril em cm (exigido na estimativa para sexo f)")
    corpo.add_argument("--biotipo", choices=list(BIOTIPOS), default="mesomorfo")

    plano = p.add_argument_group("plano")
    plano.add_argument("--objetivo", choices=["secar", "manter", "crescer"], default="secar")
    plano.add_argument("--perfil", choices=list(PERFIS), default="natural")
    plano.add_argument("--experiencia", choices=list(EXPERIENCIA), default="iniciante", help="tempo de treino serio")
    plano.add_argument("--atividade", choices=list(ATIVIDADE), default="moderado")
    plano.add_argument("--treinos-semana", type=inteiro(0, 7), default=5, help="dias de treino por semana")
    plano.add_argument("--gordura-alvo", type=intervalo(4, 50), help="percentual de gordura desejado (objetivo secar)")
    plano.add_argument("--semanas", type=inteiro(1, 52), default=12, help="semanas de projecao")
    plano.add_argument("--refeicoes", type=inteiro(2, 8), default=4, help="refeicoes por dia")
    plano.add_argument("--cardapio", action="store_true", help="gera cardapio exemplo com gramas por alimento")
    plano.add_argument("--treino", action="store_true",
                       help="gera plano de treino semanal conforme --treinos-semana e --experiencia")

    acomp = p.add_argument_group("acompanhamento")
    acomp.add_argument("--levantamento", type=tipo_levantamento, action="append", metavar="NOME:CARGAxREPS",
                       help="estima 1RM; repetivel. Ex.: supino:100x5")
    acomp.add_argument("--exame", type=tipo_exame, action="append", metavar="MARCADOR=VALOR",
                       help="confere resultado de exame contra a faixa de referencia; repetivel")
    acomp.add_argument("--pressao", type=tipo_pressao, metavar="SISxDIA", help="pressao arterial em mmHg. Ex.: 125x80")
    acomp.add_argument("--registrar", metavar="ARQUIVO.csv", help="salva o registro do dia e mede o ritmo real")
    acomp.add_argument("--data", type=tipo_data, help="data do registro, AAAA-MM-DD (padrao: hoje)")

    saida = p.add_argument_group("saida e configuracao")
    saida.add_argument("--config", metavar="ARQUIVO.json", help="valores padrao em JSON; a linha de comando prevalece")
    saida.add_argument("--json", action="store_true", help="saida em JSON")
    saida.add_argument("--log-file", default=None, help="arquivo de log")
    saida.add_argument("-v", "--verbose", action="store_true")
    saida.add_argument("--debug", action="store_true")
    return p


def argumentos_da_config(caminho, chaves_validas):
    """Converte o JSON de configuracao em argumentos, validados pelo mesmo parser."""
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, ValueError) as erro:
        raise ValueError(f"nao foi possivel ler a config '{caminho}': {erro}")
    if not isinstance(dados, dict):
        raise ValueError(f"a config '{caminho}' precisa ser um objeto JSON")
    argumentos = []
    for chave, valor in dados.items():
        destino = str(chave).replace("-", "_")
        if destino not in chaves_validas or destino == "config":
            raise ValueError(f"chave desconhecida na config: '{chave}'")
        opcao = "--" + destino.replace("_", "-")
        if valor is None or valor is False:
            continue
        if valor is True:
            argumentos.append(opcao)
        elif isinstance(valor, list):
            for item in valor:
                argumentos.append(f"{opcao}={item}")
        elif isinstance(valor, dict):
            raise ValueError(f"valor invalido para '{chave}' na config")
        else:
            argumentos.append(f"{opcao}={valor}")
    return argumentos


def configurar_log(args):
    nivel = logging.DEBUG if args.debug else logging.INFO if args.verbose else logging.WARNING
    handlers = [logging.StreamHandler(sys.stderr)]
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file, encoding="utf-8"))
    logging.basicConfig(level=nivel, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = montar_parser()

    previa = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    previa.add_argument("--config")
    caminho_config = previa.parse_known_args(argv)[0].config
    if caminho_config:
        try:
            argv = argumentos_da_config(caminho_config, set(vars(parser.parse_args([])))) + argv
        except ValueError as erro:
            print(f"Erro: {erro}", file=sys.stderr)
            return 2

    args = parser.parse_args(argv)
    faltando = [f"--{nome}" for nome in ("peso", "altura", "idade") if getattr(args, nome) is None]
    if faltando:
        parser.error("obrigatorio informar " + ", ".join(faltando) + " (linha de comando ou --config)")

    try:
        configurar_log(args)
    except OSError as erro:
        print(f"Erro ao abrir arquivo de log: {erro}", file=sys.stderr)
        return 2

    LOG.info("Calculando: perfil=%s objetivo=%s peso=%.1f", args.perfil, args.objetivo, args.peso)
    try:
        res = calcular(args)
    except OSError as erro:
        LOG.error("Falha ao gravar o historico: %s", erro)
        return 2
    except (ValueError, ZeroDivisionError) as erro:
        LOG.error("Falha no calculo: %s", erro)
        return 1

    try:
        if args.json:
            saida = asdict(res)
            saida["linha_do_tempo"] = [{"periodo": a, "descricao": b} for a, b in LINHA_DO_TEMPO[res.perfil]]
            saida["checklist"] = CHECKLIST_BASE + (CHECKLIST_HORMONAL if res.perfil != "natural" else [])
            print(json.dumps(saida, ensure_ascii=False, indent=2))
        else:
            imprimir(res)
        sys.stdout.flush()
    except BrokenPipeError:
        # Saida cortada por quem le (ex.: "| head"); encerra sem traceback
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    return 0


if __name__ == "__main__":
    sys.exit(main())
