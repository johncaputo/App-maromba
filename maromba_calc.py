#!/usr/bin/env python3
"""maromba_calc.py v2 - Macros, composição corporal, força e saúde na academia.

Perfis: natural, trt, hormonizado. Objetivos: secar, manter, crescer.
Não calcula dose, substância nem ciclo: calcula dieta, projeta peso, mede
progresso e confere exames contra faixas de referência. Uso de hormônios
exige acompanhamento médico e exames.
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
DEFICIT_MINIMO = 0.05   # kg por semana; abaixo disso o deficit nao e mensuravel
META_MAX_SEMANAS = 104  # acima disso a estimativa de tempo ate a meta nao e apresentada
DESVIO_MAX_CARDAPIO = 4  # gramas de macro que uma refeicao do cardapio pode fugir do alvo
HISTORICO_MAX_DIAS = 60  # registro base mais antigo que isso nao mede o ritmo atual
IMC_MINIMO_PARA_SECAR = 18.5
PROTEINA_MINIMA = 1.6    # g por kg do peso de referencia quando as calorias nao comportam o plano
AGUA_MAXIMA_L = 5.0

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
                  "nota": "Ectomorfo: gasta mais e come pouco. Mais carboidrato e refeições densas."},
    "mesomorfo": {"gasto": 1.00, "gord": 0.0,
                  "nota": "Mesomorfo: responde bem à distribuição padrão de macros."},
    "endomorfo": {"gasto": 0.95, "gord": 0.2,
                  "nota": "Endomorfo: acumula gordura fácil. Menos carboidrato, mais gordura e passos diários."},
}

# Fracao do ritmo maximo de ganho muscular conforme tempo de treino
EXPERIENCIA = {"iniciante": 1.0, "intermediario": 0.6, "avancado": 0.35}

FFMI_FAIXAS = {"m": (18, 20, 22, 23.5, 25), "f": (14, 16, 18, 19.5, 21)}
FFMI_ROTULOS = ("abaixo da média", "média", "acima da média", "excelente",
                "próximo do limite natural", "acima do limite natural típico")

# Limiares de 1RM / peso corporal (aproximados)
PADROES_FORCA = {
    "supino": {"m": (0.75, 1.25, 1.75, 2.0), "f": (0.5, 0.75, 1.0, 1.5)},
    "agachamento": {"m": (1.25, 1.5, 2.25, 2.75), "f": (0.75, 1.25, 1.5, 2.0)},
    "terra": {"m": (1.5, 2.0, 2.5, 3.0), "f": (1.0, 1.25, 1.75, 2.25)},
    "desenvolvimento": {"m": (0.55, 0.8, 1.1, 1.4), "f": (0.35, 0.5, 0.75, 1.0)},
}
NIVEIS_FORCA = ("iniciante", "novato", "intermediário", "avançado", "elite")

PRESSAO_ROTULOS = ("ótima", "normal", "pré-hipertensão", "hipertensão estágio 1",
                   "hipertensão estágio 2", "hipertensão estágio 3")

NOTA_EXAME_PADRAO = "Fora da faixa: leve o laudo ao médico."
NOTA_EXAME_GRAVE = ("Valor muito acima da faixa: treino, dieta ou massa muscular não explicam. "
                    "Procurar médico sem demora.")
# acima deste multiplo do limite superior a situacao vira critica
EXAMES_GRAVE = {"tgo": 3.0, "tgp": 3.0, "creatinina": 1.5, "triglicerides": 3.0}
PSA_LIMITE_ATE_50_ANOS = 2.5

# marcador: (unidade, faixa de adulto por sexo (min, max) ou None, nota por direcao do desvio)
EXAMES = {
    "hematocrito": ("%", {"m": (40, 52), "f": (36, 46)},
                    {"abaixo": "Hematócrito baixo pode indicar anemia. Médico.",
                     "acima": "Sangue mais espesso sobe o risco de trombose. Hidratação e médico."}),
    "hemoglobina": ("g/dL", {"m": (13.5, 17.5), "f": (12.0, 15.5)},
                    {"abaixo": "Hemoglobina baixa pode indicar anemia. Médico.",
                     "acima": "Avaliar junto com o hematócrito."}),
    "hdl": ("mg/dL", {"m": (40, None), "f": (50, None)},
            {"abaixo": "HDL baixo eleva risco cardiovascular. Cardio, fibras e gordura boa ajudam."}),
    "ldl": ("mg/dL", {"m": (None, 130), "f": (None, 130)},
            {"acima": "LDL alto: rever gordura saturada e levar ao médico."}),
    "triglicerides": ("mg/dL", {"m": (None, 150), "f": (None, 150)},
                      {"acima": "Reduzir açúcar, álcool e excesso calórico."}),
    "colesterol_total": ("mg/dL", {"m": (None, 190), "f": (None, 190)},
                         {"acima": "Interpretar junto com HDL e LDL."}),
    "tgo": ("U/L", {"m": (None, 40), "f": (None, 32)},
            {"acima": "Treino pesado eleva TGO/TGP por lesão muscular; GGT ajuda a separar do fígado."}),
    "tgp": ("U/L", {"m": (None, 41), "f": (None, 33)},
            {"acima": "Treino pesado eleva TGO/TGP por lesão muscular; GGT ajuda a separar do fígado."}),
    "ggt": ("U/L", {"m": (None, 60), "f": (None, 40)}, {"acima": "GGT alta aponta sobrecarga do fígado. Médico."}),
    "creatinina": ("mg/dL", {"m": (0.7, 1.3), "f": (0.6, 1.1)},
                   {"acima": "Muita massa muscular e creatina elevam o valor sem doença renal; "
                             "confirmar com o médico."}),
    "glicemia": ("mg/dL", {"m": (70, 99), "f": (70, 99)},
                 {"abaixo": "Glicemia baixa em jejum: com tontura ou suor frio, médico.",
                  "acima": "Glicemia em jejum acima da faixa. Repetir e levar ao médico."}),
    "testosterona_total": ("ng/dL", {"m": (300, 1000), "f": (15, 70)},
                           {"abaixo": "Abaixo da faixa fisiológica (coleta pela manhã). Quem define conduta é o médico.",
                            "acima": "Acima da faixa fisiológica. Quem define conduta é o médico."}),
    "estradiol": ("pg/mL", {"m": (10, 40), "f": None},
                  {"abaixo": "Fora da faixa: avaliar com o médico, sem automedicação.",
                   "acima": "Fora da faixa: avaliar com o médico, sem automedicação."}),
    "lh": ("mUI/mL", {"m": (1.7, 8.6), "f": None},
           {"abaixo": "LH baixo indica eixo hormonal suprimido; afeta fertilidade."}),
    "fsh": ("mUI/mL", {"m": (1.5, 12.4), "f": None},
            {"abaixo": "FSH baixo indica eixo hormonal suprimido; afeta fertilidade."}),
    "prolactina": ("ng/mL", {"m": (4, 15), "f": (5, 23)}, {"acima": "Prolactina alta pede investigação médica."}),
    "psa": ("ng/mL", {"m": (None, 4.0), "f": None}, {"acima": "PSA acima da faixa para a idade: urologista."}),
    "tsh": ("mUI/L", {"m": (0.4, 4.5), "f": (0.4, 4.5)},
            {"abaixo": "Tireoide fora da faixa muda o gasto calórico. Médico.",
             "acima": "Tireoide fora da faixa muda o gasto calórico. Médico."}),
}

# por 100 g: (rotulo, proteina, carboidrato, gordura)
ALIMENTOS = {
    "whey": ("Whey protein (pó)", 80.0, 8.0, 6.0),
    "frango": ("Peito de frango grelhado", 31.0, 0.0, 3.6),
    "tilapia": ("Tilápia grelhada", 26.0, 0.0, 2.7),
    "patinho": ("Patinho grelhado", 32.0, 0.0, 7.0),
    "arroz": ("Arroz branco cozido", 2.5, 28.0, 0.2),
    "batata_doce": ("Batata-doce cozida", 0.6, 18.4, 0.1),
    "aveia": ("Aveia em flocos", 14.0, 66.0, 8.5),
    "pao_frances": ("Pão francês", 8.0, 58.0, 3.0),
    "banana": ("Banana", 1.3, 26.0, 0.1),
    "macarrao": ("Macarrão cozido", 5.0, 30.0, 1.0),
    "azeite": ("Azeite de oliva", 0.0, 0.0, 100.0),
    "pasta_amendoim": ("Pasta de amendoim", 25.0, 20.0, 50.0),
    "castanha": ("Castanha-do-pará", 14.0, 12.0, 66.0),
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
    "agachamento": ("Agachamento livre", "quadríceps", True, "agachamento"),
    "leg_press": ("Leg press 45", "quadríceps", True, None),
    "afundo": ("Afundo com halteres", "quadríceps", True, None),
    "cadeira_extensora": ("Cadeira extensora", "quadríceps", False, None),
    "terra": ("Levantamento terra", "posterior", True, "terra"),
    "stiff": ("Stiff com barra", "posterior", True, None),
    "mesa_flexora": ("Mesa flexora", "posterior", False, None),
    "elevacao_pelvica": ("Elevação pélvica", "glúteos", True, None),
    "panturrilha": ("Panturrilha em pé", "panturrilha", False, None),
    "supino": ("Supino reto com barra", "peito", True, "supino"),
    "supino_inclinado": ("Supino inclinado com halteres", "peito", True, None),
    "crucifixo": ("Crucifixo na máquina", "peito", False, None),
    "desenvolvimento": ("Desenvolvimento com barra", "ombros", True, "desenvolvimento"),
    "elevacao_lateral": ("Elevação lateral", "ombros", False, None),
    "face_pull": ("Face pull na polia", "ombros", False, None),
    "barra_fixa": ("Barra fixa (ou graviton)", "costas", True, None),
    "puxada": ("Puxada frontal na polia", "costas", True, None),
    "remada_curvada": ("Remada curvada com barra", "costas", True, None),
    "remada_baixa": ("Remada baixa na polia", "costas", True, None),
    "rosca_direta": ("Rosca direta", "bíceps", False, None),
    "rosca_martelo": ("Rosca martelo", "bíceps", False, None),
    "triceps_corda": ("Tríceps na polia com corda", "tríceps", False, None),
    "triceps_testa": ("Tríceps testa", "tríceps", False, None),
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
    "push": ("Empurrar A: peito, ombros e tríceps",
             ("supino", "supino_inclinado", "desenvolvimento", "elevacao_lateral", "triceps_corda",
              "triceps_testa")),
    "pull": ("Puxar A: costas e bíceps",
             ("barra_fixa", "remada_curvada", "puxada", "face_pull", "rosca_direta", "rosca_martelo")),
    "legs": ("Pernas A",
             ("agachamento", "stiff", "leg_press", "mesa_flexora", "panturrilha", "prancha")),
    "push_b": ("Empurrar B: ombros, peito e tríceps",
               ("desenvolvimento", "supino_inclinado", "crucifixo", "elevacao_lateral", "triceps_testa",
                "triceps_corda")),
    "pull_b": ("Puxar B: costas e bíceps",
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
    5: ("seg", "ter", "qua", "sex", "sáb"), 6: ("seg", "ter", "qua", "qui", "sex", "sáb"),
    7: ("seg", "ter", "qua", "qui", "sex", "sáb"),
}
VOLUME_ROTULOS = ("baixo", "mínimo eficaz", "faixa ideal", "alto")

LINHA_DO_TEMPO = {
    "natural": [
        ("Dias 1-7", "Adaptação à dieta. Fome e queda de energia no déficit; peso oscila por água e glicogênio."),
        ("Semanas 2-4", "Peso estabiliza na tendência real. Força sobe por adaptação neural."),
        ("Semanas 5-8", "Mudança visível no espelho e nas medidas. Ajuste calorias se o peso travar 2 semanas."),
        ("Semanas 9-12", "Ganho ou perda consolidado. Reavalie metas e recalcule com o peso novo."),
    ],
    "trt": [
        ("Dias 1-7", "Pouca mudança física. Possível melhora de disposição e libido."),
        ("Semanas 2-4", "Retenção leve de água, recuperação melhor entre treinos, apetite maior."),
        ("Semanas 5-8", "Força e volume muscular sobem. Hematócrito e pressão podem subir: medir."),
        ("Semanas 9-12", "Composição corporal muda de forma clara. Hora de repetir exames com o médico."),
    ],
    "hormonizado": [
        ("Dias 1-7", "Retenção de água (+1 a 2 kg na balança sem ser gordura), apetite maior, pump mais forte. "
                     "O eixo hormonal natural fica suprimido durante todo o uso, com fertilidade reduzida."),
        ("Semanas 2-4", "Força sobe rápido, recuperação acelera. Pele oleosa, acne e pressão alta podem aparecer."),
        ("Semanas 5-8", "Ganho muscular visível. Tendões não acompanham o músculo: suba carga devagar. "
                        "Colesterol HDL cai, hematócrito sobe, sono e humor podem oscilar."),
        ("Semanas 9-12", "Composição corporal muda de forma clara. Hora de repetir exames com o médico."),
    ],
}

CHECKLIST_BASE = [
    "Pesar em jejum, mesmo horário, e usar a média semanal, não o dia isolado.",
    "Medir cintura 1x por semana e tirar foto no mesmo local e luz.",
    "Pesar a comida na balança nas primeiras 4 semanas, no mínimo.",
    "Dormir 7-9 h. Sono ruim derruba recuperação e aumenta fome.",
    "Treino de força com progressão de carga; 8-10 mil passos por dia.",
]

CHECKLIST_HORMONAL = [
    "Acompanhamento com médico (endocrinologista ou médico do esporte) antes, durante e depois.",
    "Exames de base e a cada 8-12 semanas: hemograma (hematócrito), lipidograma, TGO/TGP/GGT, "
    "creatinina/ureia, testosterona total e livre, estradiol, LH/FSH, prolactina, PSA, glicemia.",
    "Medir pressão arterial em casa 3x por semana. A partir de 13x8 repetido: médico.",
    "Cardio 3-4x por semana, 20-40 min: protege coração e controla pressão.",
    "Sódio controlado, potássio via comida (banana, batata, feijão), álcool no mínimo.",
    "Sinais de alerta, procurar atendimento: dor no peito, falta de ar, dor/inchaço em uma perna, "
    "dor de cabeça forte, pele ou olhos amarelados, mama dolorida ou com nódulo.",
    "Nunca compartilhar agulhas; material estéril e descarte correto.",
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
    gordura_origem: str = "não informada"
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
    linha_do_tempo: list = field(default_factory=list)
    checklist: list = field(default_factory=list)
    notas: list = field(default_factory=list)
    avisos: list = field(default_factory=list)


def classificar(valor, limites, rotulos):
    """Devolve o rótulo da faixa em que o valor cai (limites em ordem crescente)."""
    return rotulos[sum(1 for limite in limites if valor >= limite)]


def calcular_tmb(peso, altura, idade, sexo, gordura):
    """Katch-McArdle se houver % de gordura; senão Mifflin-St Jeor."""
    if gordura is not None:
        massa_magra = peso * (1 - gordura / 100.0)
        LOG.debug("Katch-McArdle, massa magra=%.1f kg", massa_magra)
        return 370 + 21.6 * massa_magra
    base = 10 * peso + 6.25 * altura - 5 * idade
    LOG.debug("Mifflin-St Jeor, base=%.1f", base)
    return base + 5 if sexo == "m" else base - 161


def ajuste_idade(idade):
    """Devolve (proteína extra em g/kg, fator de ritmo, nota) conforme a faixa etária."""
    if idade < 30:
        return 0.0, 1.0, "Idade: recuperação no auge; o corpo tolera volume alto de treino."
    if idade < 40:
        return 0.0, 0.95, "Idade: recuperação ainda boa; sono e aquecimento passam a pesar mais."
    if idade < 50:
        return 0.2, 0.85, "Idade 40+: mais proteína, ritmo mais conservador e 1 dia extra de descanso."
    return 0.3, 0.75, "Idade 50+: proteína alta, progressão lenta de carga e check-up cardiológico anual."


def gordura_navy(sexo, altura, cintura, pescoco, quadril):
    """Estimativa de % de gordura pelo método da Marinha dos EUA (medidas em cm)."""
    if sexo == "m":
        diferenca = cintura - pescoco
        if diferenca <= 0:
            raise ValueError("cintura precisa ser maior que o pescoço para estimar a gordura")
        densidade = 1.0324 - 0.19077 * math.log10(diferenca) + 0.15456 * math.log10(altura)
    else:
        if quadril is None:
            raise ValueError("para o sexo feminino a estimativa de gordura exige a medida do quadril")
        diferenca = cintura + quadril - pescoco
        if diferenca <= 0:
            raise ValueError("medidas de cintura, quadril e pescoço inconsistentes")
        densidade = 1.29579 - 0.35004 * math.log10(diferenca) + 0.22100 * math.log10(altura)
    if densidade <= 0:
        raise ValueError("medidas corporais inconsistentes para estimar a gordura")
    estimativa = 495.0 / densidade - 450.0
    LOG.debug("Navy: densidade=%.4f gordura=%.1f%%", densidade, estimativa)
    if not 3.0 <= estimativa <= 60.0:
        raise ValueError("medidas fora da faixa válida do método de fita; confira cintura e pescoço "
                         "ou informe o percentual de gordura")
    return estimativa


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
            # com muita gordura a massa magra estimada infla e o FFMI deixa de dizer algo sobre musculo
            ffmi_classe=("não interpretável com gordura alta" if gordura > (25 if sexo == "m" else 35)
                         else classificar(ffmi_norm, FFMI_FAIXAS[sexo], FFMI_ROTULOS)),
        )
    if cintura is not None:
        comp["cintura_altura"] = round(cintura / altura, 2)
    return comp


def calcular_ciclo_carbo(carbo, calorias, treinos, piso=0.0):
    """Mais carboidrato no dia de treino, menos no descanso, mesma média semanal.

    O dia de descanso nunca fica abaixo do piso de calorias; sem folga para isso, não há ciclo.
    """
    descansos = 7 - treinos
    if treinos <= 0 or descansos <= 0 or carbo <= 0:
        return {}
    fator_treino = min(1.35, (7 - 0.75 * descansos) / treinos)
    carbo_treino = carbo * fator_treino
    carbo_descanso = (7 * carbo - treinos * carbo_treino) / descansos
    minimo_descanso = carbo - (calorias - piso) / 4.0
    if carbo_descanso < minimo_descanso:
        carbo_descanso = minimo_descanso
        carbo_treino = (7 * carbo - descansos * carbo_descanso) / treinos
    if carbo - carbo_descanso < 5:
        return {}
    return {
        "treinos_semana": treinos,
        "carbo_treino_g": round(carbo_treino),
        "carbo_descanso_g": round(carbo_descanso),
        "kcal_treino": round(calorias + (carbo_treino - carbo) * 4),
        "kcal_descanso": round(calorias + (carbo_descanso - carbo) * 4),
    }


def calcular_meta(peso, gordura, alvo, variacao, calorias, gasto):
    """Tempo até a gordura alvo, com 1 semana na manutenção a cada 8 de déficit."""
    magra = peso * (1 - gordura / 100.0)
    peso_alvo = magra / (1 - alvo / 100.0)
    perder = peso - peso_alvo
    semanas_deficit = math.ceil(round(perder / abs(variacao), 6))
    pausas = (semanas_deficit - 1) // 8
    fases, restante = [], semanas_deficit
    while restante > 0:
        bloco = min(8, restante)
        fases.append({"fase": "déficit", "semanas": bloco, "kcal": round(calorias)})
        restante -= bloco
        if restante > 0:
            fases.append({"fase": "pausa na manutenção", "semanas": 1, "kcal": round(gasto)})
    return {
        "gordura_alvo_pct": alvo, "peso_alvo_kg": round(peso_alvo, 1), "perder_kg": round(perder, 1),
        "semanas_deficit": semanas_deficit, "semanas_pausa": pausas,
        "semanas_total": semanas_deficit + pausas, "fases": fases,
    }


def resolver_refeicao(chaves, alvo):
    """Gramas de 3 alimentos (proteína, carboidrato, gordura) para um alvo de macros (Gauss-Seidel)."""
    fontes = [tuple(v / 100.0 for v in ALIMENTOS[c][1:]) for c in chaves]
    (pp, pc, pg), (cp, cc, cg), (gp, gc, gg) = fontes
    qp = qc = qg = 0.0
    for _ in range(25):
        qp = max(0.0, (alvo["proteina_g"] - qc * cp - qg * gp) / pp)
        qc = max(0.0, (alvo["carbo_g"] - qp * pc - qg * gc) / cc)
        qg = max(0.0, (alvo["gordura_g"] - qp * pg - qc * cg) / gg)
    passo_gordura = 1 if gg >= 0.4 else 5
    gramas = [round(qp / 5) * 5, round(qc / 5) * 5, round(qg / passo_gordura) * passo_gordura]
    # soma explicita: sum() de floats muda de algoritmo entre versoes do Python
    macros = [gramas[0] * fontes[0][i] + gramas[1] * fontes[1][i] + gramas[2] * fontes[2][i] for i in range(3)]
    return gramas, macros


def montar_cardapio(refeicoes):
    """Cardápio exemplo: por refeição, usa o primeiro modelo do rodízio que fecha os macros."""
    cardapio = []
    total = len(MODELOS_REFEICAO)
    for indice, alvo in enumerate(refeicoes):
        melhor = None
        for deslocamento in range(total):
            chaves = MODELOS_REFEICAO[(indice + deslocamento) % total]
            gramas, macros = resolver_refeicao(chaves, alvo)
            desvio = max(abs(m - alvo[k]) for m, k in zip(macros, ("proteina_g", "carbo_g", "gordura_g")))
            if melhor is None or desvio < melhor[0]:
                melhor = (desvio, chaves, gramas, macros)
            if desvio <= DESVIO_MAX_CARDAPIO:
                break
        desvio, chaves, gramas, (prot, carb, gord) = melhor
        cardapio.append({
            "refeicao": alvo["refeicao"],
            "itens": [{"alimento": ALIMENTOS[c][0], "gramas": g} for c, g in zip(chaves, gramas) if g > 0],
            "proteina_g": round(prot), "carbo_g": round(carb), "gordura_g": round(gord),
            "kcal": round(prot * 4 + carb * 4 + gord * 9),
            "aproximado": desvio > DESVIO_MAX_CARDAPIO,
        })
    return cardapio


def analisar_forca(levantamentos, peso, sexo):
    """1RM estimado (média de Epley e Brzycki), força relativa e cargas de treino."""
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
    """Divisão semanal com séries, repetições, volume por grupo, progressão e cardio."""
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
    # mesma carga da tabela de forca: 70% do 1RM para iniciante, 75% para os demais
    faixa_carga = "70%" if experiencia == "iniciante" else "75%"
    carga_conhecida = {item["exercicio"]: item["cargas_treino"][faixa_carga] for item in forca}

    sessoes, volume = [], {}
    for dia, chave in zip(DIAS_TREINO[dias], chaves):
        titulo, codigos = MODELOS_TREINO[chave]
        exercicios = []
        for codigo in codigos:
            rotulo, grupo, composto, chave_rm = EXERCICIOS[codigo]
            series = series_composto if composto else series_isolado
            carga = carga_conhecida.get(chave_rm)
            exercicios.append({
                "exercicio": rotulo, "grupo": grupo, "series": series,
                "reps": REPS_ESPECIAIS.get(codigo, reps_composto if composto else "10-15"),
                "descanso": "2-3 min" if composto else "60-90 s", "carga_sugerida_kg": carga,
            })
            volume[grupo] = volume.get(grupo, 0) + series
        sessoes.append({"dia": dia, "treino": titulo, "exercicios": exercicios})
    if dias == 7:
        sessoes.append({"dia": "dom", "treino": "Recuperação ativa: 30-40 min de caminhada e mobilidade",
                        "exercicios": []})

    if objetivo == "secar":
        cardio = "3-4 sessões de 25-40 min em ritmo de conversa (zona 2), longe do treino de pernas."
    elif perfil != "natural":
        cardio = "3 sessões de 20-30 min em ritmo de conversa: a prioridade é a saúde do coração."
    elif objetivo == "crescer":
        cardio = "2 sessões leves de 20 min: mantém o condicionamento sem roubar recuperação."
    else:
        cardio = "2-3 sessões de 20-30 min em ritmo de conversa."

    notas = []
    if objetivo == "secar":
        notas.append("No déficit a prioridade é manter a carga na barra; não troque peso por repetições altas.")
    if perfil != "natural":
        notas.append("Músculo ganha força antes de tendão e ligamento: suba carga no ritmo da progressão, sem saltos.")
    if experiencia == "iniciante" and dias >= 5:
        notas.append("Iniciante progride igual com 3-4 dias por semana; os dias extras são opcionais.")
    if dias <= 2:
        notas.append("Com até 2 treinos o volume por grupo fica baixo: serve para manter ou para quem está começando.")
    if dias == 7:
        notas.append("Sem nenhum dia livre a recuperação cai: o sétimo dia é apenas recuperação ativa.")
    if idade >= 40:
        notas.append("40+: aquecimento mais longo e séries de aproximação antes de toda carga pesada.")

    return {
        "dias_semana": dias,
        "sessoes": sessoes,
        "volume_semanal": {
            grupo: {"series": total, "classe": classificar(total, (6, 10, 21), VOLUME_ROTULOS)}
            for grupo, total in sorted(volume.items())
        },
        "aquecimento": "5-10 min de cardio leve e 2-3 séries progressivas do primeiro exercício.",
        "progressao": "Ao bater o topo da faixa de repetições em todas as séries, suba 2,5 kg (superiores) "
                      "ou 5 kg (inferiores).",
        "intensidade": "Termine cada série com 1-3 repetições de sobra; falha só na última série dos isolados.",
        "semana_leve": f"A cada {'4-6' if idade >= 40 else '6-8'} semanas: metade das séries, mesma carga.",
        "cardio": cardio,
        "notas": notas,
    }


def avaliar_exames(itens, sexo, idade):
    """Compara cada marcador com a faixa genérica de adulto. A referência do laudo prevalece."""
    saida = []
    for nome, valor in itens:
        unidade, faixas, notas = EXAMES[nome]
        faixa = faixas.get(sexo)
        if nome == "psa" and faixa is not None and idade < 50:
            faixa = (None, PSA_LIMITE_ATE_50_ANOS)
        nota = ""
        if faixa is None:
            situacao, referencia = "sem faixa genérica", "usar a referência do laudo"
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
            if situacao != "dentro":
                nota = notas.get(situacao) or NOTA_EXAME_PADRAO
            if situacao == "acima" and nome in EXAMES_GRAVE and valor > maximo * EXAMES_GRAVE[nome]:
                situacao, nota = "acima (crítico)", NOTA_EXAME_GRAVE
        if nome == "hematocrito" and valor > 54:
            situacao = "acima (crítico)"
            nota = "Acima de 54%: risco real de trombose. Procurar médico sem demora."
        saida.append({"marcador": nome, "valor": valor, "unidade": unidade, "referencia": referencia,
                      "situacao": situacao, "nota": nota})
    return saida


def avaliar_pressao(sistolica, diastolica):
    nivel = max(
        sum(1 for limite in (120, 130, 140, 160, 180) if sistolica >= limite),
        sum(1 for limite in (80, 85, 90, 100, 110) if diastolica >= limite),
    )
    classe = PRESSAO_ROTULOS[nivel]
    if nivel == 0 and (sistolica < 90 or diastolica < 60):
        classe = "baixa"
    return {"sistolica": sistolica, "diastolica": diastolica, "nivel": nivel, "classe": classe}


def listar_suplementos(peso, nivel_pressao=0):
    cafeina = int(min(400, round(peso * 3 / 10) * 10))
    return [
        f"Creatina monoidratada: {3 if peso < 70 else 5} g por dia, todos os dias, qualquer horário.",
        ("Cafeína: evitar até liberação médica (pressão elevada)." if nivel_pressao >= 3 else
         f"Cafeína: até {cafeina} mg, 30-60 min antes do treino; evitar depois das 15 h."),
        "Proteína em pó (whey ou vegetal): só para fechar a meta diária de proteína.",
        "Vitamina D e ômega-3: apenas se exame ou dieta mostrarem falta.",
    ]


def montar_checklist(perfil, sexo):
    if perfil == "natural":
        return list(CHECKLIST_BASE)
    hormonal = CHECKLIST_HORMONAL
    if sexo == "f":  # PSA e marcador de prostata
        hormonal = [item.replace("prolactina, PSA, glicemia", "prolactina, glicemia") for item in hormonal]
    return CHECKLIST_BASE + hormonal


def recomendar_ajuste(objetivo, esperado, real, calorias, ajuste, piso):
    """Compara o ritmo real com o esperado; tolerância mínima de 0,1 kg por semana."""
    tolerancia = max(0.1, abs(esperado) * 0.5)
    passo = int(min(150, max(50, round(abs(ajuste) / 20.0) * 10)))
    if objetivo == "secar":
        if esperado > -DEFICIT_MINIMO:
            return "Plano sem déficit efetivo: para secar, aumente o gasto com passos e cardio."
        if real > esperado + tolerancia:
            if calorias - passo < piso:
                return "Perda abaixo do esperado e calorias já no piso: some 2 mil passos por dia, sem cortar comida."
            return f"Perda abaixo do esperado: reduza {passo} kcal (carboidrato) ou some 2 mil passos por dia."
        if real < esperado - tolerancia:
            return f"Perda rápida demais: suba {passo} kcal para proteger a massa magra."
    elif objetivo == "crescer":
        if real < esperado - tolerancia:
            return f"Ganho abaixo do esperado: suba {passo} kcal (carboidrato)."
        if real > esperado + tolerancia:
            return f"Ganho rápido demais: reduza {passo} kcal, o excesso vira gordura."
    else:
        if real > 0.25:
            return "Peso subindo na manutenção: reduza 150 kcal."
        if real < -0.25:
            return "Peso caindo na manutenção: suba 150 kcal."
    return "Ritmo dentro do esperado: mantenha o plano."


def registrar_historico(caminho, data, peso, gordura, cintura, calorias, objetivo, esperado, ajuste, piso):
    """Acrescenta o registro do dia ao CSV e compara o ritmo real com o esperado."""
    registros = []
    hoje = max(datetime.date.today(), data)
    existe = os.path.exists(caminho) and os.path.getsize(caminho) > 0
    if existe:
        with open(caminho, newline="", encoding="utf-8") as arquivo:
            leitor = csv.DictReader(arquivo, strict=True)
            try:
                if leitor.fieldnames != CAMPOS_HISTORICO:
                    raise ValueError(f"cabeçalho inesperado em '{caminho}'; esperado: {','.join(CAMPOS_HISTORICO)}")
                for numero, linha in enumerate(leitor, start=2):
                    try:
                        valor_peso = float(linha["peso"])
                        if not math.isfinite(valor_peso) or valor_peso <= 0:
                            raise ValueError("peso inválido")
                        data_linha = datetime.date.fromisoformat(linha["data"])
                    except (TypeError, ValueError):
                        LOG.warning("Linha %d de '%s' ignorada: formato inválido", numero, caminho)
                        continue
                    if data_linha > hoje:
                        LOG.warning("Linha %d de '%s' ignorada: data no futuro", numero, caminho)
                        continue
                    registros.append((data_linha, valor_peso))
            except csv.Error as erro:
                raise ValueError(f"histórico '{caminho}' ilegível: {erro}")
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
    LOG.info("Histórico atualizado em '%s' (%d registros)", caminho, len(registros))
    historico = {"arquivo": caminho}
    historico.update(analisar_historico(registros, objetivo, esperado, calorias, ajuste, piso))
    return historico


def analisar_historico(registros, objetivo, esperado, calorias, ajuste, piso):
    """Ritmo real de peso a partir de pares (data, peso); o ultimo registro de cada data prevalece."""
    serie = sorted(dict(registros).items())
    historico = {"registros": len(serie), "ritmo_esperado_kg_semana": round(esperado, 2)}
    if len(serie) < 2:
        historico["recomendacao"] = "Primeiro registro salvo. Registre o peso toda semana para medir o ritmo real."
        return historico
    fim_data, fim_peso = serie[-1]
    elegiveis = [par for par in serie[:-1] if (fim_data - par[0]).days >= 7]
    if not elegiveis:
        historico["dias_analisados"] = (fim_data - serie[0][0]).days
        historico["recomendacao"] = "Menos de 7 dias entre registros: cedo demais para medir ritmo."
        return historico
    na_janela = [par for par in elegiveis if (fim_data - par[0]).days <= 28]
    base_data, base_peso = na_janela[0] if na_janela else elegiveis[-1]
    dias = (fim_data - base_data).days
    historico["dias_analisados"] = dias
    if dias > HISTORICO_MAX_DIAS:
        historico["recomendacao"] = ("Registro anterior com mais de 60 dias: registre o peso por 2 semanas "
                                     "para medir o ritmo atual.")
        return historico
    real = (fim_peso - base_peso) / (dias / 7.0)
    historico["ritmo_real_kg_semana"] = round(real, 2)
    if dias < 14:
        historico["recomendacao"] = "Menos de 14 dias de dados: continue registrando antes de mexer nas calorias."
    else:
        historico["recomendacao"] = recomendar_ajuste(objetivo, esperado, real, calorias, ajuste, piso)
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
        avisos.append("Gordura estimada por fita métrica: margem de erro de 3 a 4 pontos percentuais.")
    elif gordura is None:
        origem = "não informada"

    tmb = calcular_tmb(args.peso, args.altura, args.idade, args.sexo, gordura)
    gasto = tmb * ATIVIDADE[args.atividade] * biotipo["gasto"]

    imc = args.peso / (args.altura / 100.0) ** 2
    baixo_peso = args.objetivo == "secar" and imc < IMC_MINIMO_PARA_SECAR
    if baixo_peso:
        ajuste = 0.0
        avisos.append("IMC abaixo de 18,5: déficit não aplicado, plano na manutenção. "
                      "Procure médico ou nutricionista antes de tentar perder peso.")
    elif args.objetivo == "secar":
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

    # Proteina sobre o peso que a pessoa teria com 20% de gordura; sem gordura conhecida, sobre o peso
    # no IMC 25. Evita inflar a proteina de quem tem muito peso em gordura.
    if gordura is not None:
        peso_ref = min(args.peso, args.peso * (1 - gordura / 100.0) / 0.80)
    else:
        peso_ref = min(args.peso, 25.0 * (args.altura / 100.0) ** 2)
    LOG.debug("Peso de referência para proteína: %.1f kg", peso_ref)

    proteina = (perfil["prot"][args.objetivo] + prot_extra) * peso_ref
    gordura_g = max(0.6, perfil["gord"] + biotipo["gord"]) * args.peso
    carbo = (calorias - proteina * 4 - gordura_g * 9) / 4

    if carbo < 50:
        gordura_g = max(0.6 * args.peso, (calorias - proteina * 4 - 50 * 4) / 9)
        carbo = (calorias - proteina * 4 - gordura_g * 9) / 4
        avisos.append("Carboidrato muito baixo; gordura reduzida ao mínimo para abrir espaço.")
    if carbo < 50:
        # nem com a gordura no minimo sobram 50 g de carboidrato: a proteina cede ate o seu minimo
        proteina_minima = PROTEINA_MINIMA * peso_ref
        if proteina > proteina_minima:
            proteina = max(proteina_minima, (calorias - gordura_g * 9 - 50 * 4) / 4)
            carbo = (calorias - proteina * 4 - gordura_g * 9) / 4
            avisos.append(f"As calorias não comportam a proteína planejada: reduzida para {proteina:.0f} g "
                          "para manter algum carboidrato. Para comer mais, aumente a atividade.")
    if carbo < 0:
        carbo = 0.0
        minimo = proteina * 4 + gordura_g * 9
        avisos.append(f"Proteína e gordura mínimas somam {minimo:.0f} kcal, acima da meta de {calorias:.0f}; "
                      f"plano recalculado para {minimo:.0f} kcal. Para perder mais rápido, aumente a atividade.")
        calorias = minimo
        ajuste = calorias - gasto

    variacao = ajuste * 7 / KCAL_POR_KG
    sem_deficit = args.objetivo == "secar" and variacao > -DEFICIT_MINIMO
    if sem_deficit and not baixo_peso:
        avisos.append("Plano sem déficit efetivo: as calorias mínimas já encostam no seu gasto. "
                      "Para secar, aumente o gasto com passos e cardio.")
    projecao = [{"semana": s, "peso_kg": round(args.peso + variacao * s, 1)} for s in range(1, args.semanas + 1)]

    n = args.refeicoes
    refeicoes = []
    for i in range(n):
        prato = {"refeicao": i + 1, "proteina_g": round(proteina / n), "carbo_g": round(carbo / n),
                 "gordura_g": round(gordura_g / n)}
        # kcal da refeicao sai dos proprios macros arredondados, para a linha fechar
        prato["kcal"] = prato["proteina_g"] * 4 + prato["carbo_g"] * 4 + prato["gordura_g"] * 9
        refeicoes.append(prato)

    meta = {}
    if args.gordura_alvo is not None:
        if args.objetivo != "secar":
            avisos.append("Gordura alvo só é usada com o objetivo secar; ignorada.")
        elif gordura is None:
            avisos.append("Gordura alvo exige o percentual de gordura atual ou as medidas de cintura e pescoço; ignorada.")
        elif args.gordura_alvo >= gordura:
            avisos.append("Gordura alvo maior ou igual à atual; nada a calcular.")
        elif args.gordura_alvo < (5 if args.sexo == "m" else 12):
            avisos.append("Gordura alvo abaixo da gordura essencial do corpo: meta não calculada.")
        elif not sem_deficit:
            meta = calcular_meta(args.peso, gordura, args.gordura_alvo, variacao, calorias, gasto)
            if meta["semanas_total"] > META_MAX_SEMANAS:
                avisos.append(f"No ritmo atual a gordura alvo levaria {meta['semanas_total']} semanas: meta fora "
                              "de alcance com este plano. Aumente a atividade ou escolha um alvo intermediário.")
                meta = {}
            if args.gordura_alvo < (8 if args.sexo == "m" else 16):
                avisos.append("Gordura alvo muito baixa: sustentável só por pouco tempo e com acompanhamento.")
    if meta:
        # a projecao segue as fases da meta: pausa na manutencao nao perde peso e o alvo e o piso
        ritmos = [variacao if fase["fase"] == "déficit" else 0.0 for fase in meta["fases"]
                  for _ in range(fase["semanas"])]
        atual, projecao = args.peso, []
        for s in range(1, args.semanas + 1):
            atual = max(meta["peso_alvo_kg"], atual + (ritmos[s - 1] if s <= len(ritmos) else 0.0))
            projecao.append({"semana": s, "peso_kg": round(atual, 1)})

    pressao = avaliar_pressao(*args.pressao) if args.pressao else {}
    exames = avaliar_exames(args.exame or [], args.sexo, args.idade)
    forca = analisar_forca(args.levantamento or [], args.peso, args.sexo)
    treino = {}
    if args.treino:
        treino = montar_treino(args.treinos_semana, args.experiencia, args.objetivo, args.perfil, args.idade, forca)
        if not treino:
            avisos.append("Plano de treino exige ao menos 1 treino por semana; não gerado.")

    if args.perfil != "natural":
        avisos.append("Retenção de água nas primeiras semanas mascara a balança: confie em cintura e fotos.")
    if args.perfil == "hormonizado" and args.idade < 21:
        avisos.append("Abaixo de 21 anos o risco para o eixo hormonal e crescimento é maior. Converse com um médico.")
    if args.objetivo == "secar" and gordura is not None and gordura < (10 if args.sexo == "m" else 18):
        avisos.append("Gordura já baixa: déficit agressivo custa massa magra e saúde hormonal.")
    if args.cintura is not None and round(args.cintura / args.altura, 2) > 0.5:
        avisos.append("Cintura acima de metade da altura: risco cardiometabólico aumentado.")
    if pressao and pressao["nivel"] == 5:
        avisos.append("Pressão em nível de crise: procure atendimento agora e não treine pesado até ser avaliado.")
    elif pressao and pressao["classe"] == "baixa":
        avisos.append("Pressão baixa: com tontura ou fraqueza, procure médico.")
    elif pressao and pressao["nivel"] >= 3:
        avisos.append("Pressão em faixa de hipertensão: cortar cafeína e estimulantes e procurar médico.")
    elif pressao and pressao["nivel"] == 2:
        avisos.append("Pressão no limite: reduzir sódio, manter cardio e repetir a medida em dias diferentes.")
    fora = [e["marcador"] for e in exames if e["situacao"] not in ("dentro", "sem faixa genérica")]
    if fora:
        avisos.append("Exames fora da faixa (" + ", ".join(fora) + "): leve o laudo ao médico. "
                      "Não ajuste nada por conta própria.")

    res = Resultado(
        perfil=args.perfil, objetivo=args.objetivo, biotipo=args.biotipo, experiencia=args.experiencia,
        tmb=round(tmb), gasto_total=round(gasto), calorias=round(calorias), ajuste_kcal=round(ajuste),
        proteina_g=round(proteina), carbo_g=round(carbo), gordura_g=round(gordura_g),
        agua_l=round(min(args.peso * 0.04, AGUA_MAXIMA_L), 1), fibra_g=round(calorias / 1000 * 14),
        variacao_kg_semana=round(variacao, 2),
        gordura_pct=None if gordura is None else round(gordura, 1), gordura_origem=origem,
        composicao=analisar_composicao(args.peso, args.altura, args.sexo, gordura, args.cintura),
        ciclo_carbo=calcular_ciclo_carbo(carbo, calorias, args.treinos_semana, piso),
        meta=meta, refeicoes=refeicoes,
        cardapio=montar_cardapio(refeicoes) if args.cardapio else [],
        projecao=projecao,
        forca=forca, treino=treino,
        exames=exames, pressao=pressao,
        suplementos=listar_suplementos(args.peso, pressao["nivel"] if pressao else 0),
        linha_do_tempo=[{"periodo": periodo, "descricao": texto} for periodo, texto in LINHA_DO_TEMPO[args.perfil]],
        checklist=montar_checklist(args.perfil, args.sexo),
        notas=notas, avisos=avisos,
    )
    if args.registrar:
        res.historico = registrar_historico(
            args.registrar, args.data or datetime.date.today(), args.peso, gordura,
            args.cintura, calorias, "manter" if baixo_peso else args.objetivo, variacao, ajuste, piso,
        )
    return res


def imprimir(res):
    linha = "=" * 70
    print(linha)
    print(f" MAROMBA CALC v2 | perfil: {res.perfil} | objetivo: {res.objetivo} | biótipo: {res.biotipo}")
    print(linha)
    print(" ENERGIA E MACROS")
    print(f"  Taxa metabólica basal : {res.tmb:.0f} kcal")
    print(f"  Gasto total diário    : {res.gasto_total:.0f} kcal")
    print(f"  Meta diária           : {res.calorias:.0f} kcal ({res.ajuste_kcal:+.0f})")
    print(f"  Proteína              : {res.proteina_g:.0f} g")
    print(f"  Carboidrato           : {res.carbo_g:.0f} g")
    print(f"  Gordura               : {res.gordura_g:.0f} g")
    print(f"  Água                  : {res.agua_l} L/dia")
    print(f"  Fibra                 : {res.fibra_g:.0f} g/dia")
    print(f"  Ritmo esperado        : {res.variacao_kg_semana + 0.0:+.2f} kg/semana")

    if res.ciclo_carbo:
        c = res.ciclo_carbo
        print(f"\n CICLO DE CARBOIDRATO ({c['treinos_semana']} treinos por semana)")
        print(f"  Dia de treino   : {c['carbo_treino_g']} g de carboidrato | {c['kcal_treino']} kcal")
        print(f"  Dia de descanso : {c['carbo_descanso_g']} g de carboidrato | {c['kcal_descanso']} kcal")

    comp = res.composicao
    print("\n COMPOSIÇÃO CORPORAL")
    print(f"  IMC                   : {comp['imc']}")
    if res.gordura_pct is not None:
        print(f"  Gordura               : {res.gordura_pct}% ({res.gordura_origem})")
        print(f"  Massa magra / gorda   : {comp['massa_magra_kg']} kg / {comp['massa_gorda_kg']} kg")
        print(f"  FFMI normalizado      : {comp['ffmi_normalizado']} ({comp['ffmi_classe']})")
    else:
        print("  Gordura               : não informada (use --gordura ou --cintura e --pescoco)")
    if "cintura_altura" in comp:
        print(f"  Cintura / altura      : {comp['cintura_altura']:.2f} (ideal até 0.50)")

    if res.meta:
        m = res.meta
        print(f"\n META: {m['gordura_alvo_pct']:g}% DE GORDURA")
        print(f"  Peso alvo             : {m['peso_alvo_kg']} kg (perder {m['perder_kg']} kg, massa magra mantida)")
        print(f"  Tempo estimado        : {m['semanas_total']} semanas "
              f"({m['semanas_deficit']} de déficit + {m['semanas_pausa']} de pausa)")
        for fase in m["fases"]:
            print(f"   - {fase['fase']}: {fase['semanas']} semana(s) a {fase['kcal']} kcal")

    print("\n DIVISÃO POR REFEIÇÃO")
    for r in res.refeicoes:
        print(f"  {r['refeicao']}: {r['kcal']} kcal | P {r['proteina_g']} g | C {r['carbo_g']} g | G {r['gordura_g']} g")

    if res.cardapio:
        print("\n CARDÁPIO EXEMPLO (peso do alimento pronto)")
        for r in res.cardapio:
            itens = " + ".join(f"{i['gramas']} g {i['alimento']}" for i in r["itens"])
            print(f"  {r['refeicao']}: {itens}")
            aproximado = " (aproximado: ajuste as porções)" if r["aproximado"] else ""
            print(f"     = {r['kcal']} kcal | P {r['proteina_g']} g | C {r['carbo_g']} g "
                  f"| G {r['gordura_g']} g{aproximado}")

    print("\n PROJEÇÃO DE PESO")
    for p in res.projecao:
        print(f"  Semana {p['semana']:>2}: {p['peso_kg']} kg")

    if res.forca:
        print("\n FORÇA")
        for f in res.forca:
            nivel = f" | nível: {f['nivel']}" if f["nivel"] else ""
            print(f"  {f['exercicio']}: {f['carga_kg']:g} kg x {f['reps']} -> 1RM ~{f['rm_estimado_kg']:g} kg "
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
        print("  Volume semanal (séries diretas por grupo):")
        for grupo, v in t["volume_semanal"].items():
            print(f"     {grupo:<12} {v['series']:>2} séries ({v['classe']})")
        print("     Conta só o trabalho direto: supino e remada também treinam tríceps e bíceps.")
        print(f"  Aquecimento : {t['aquecimento']}")
        print(f"  Progressão  : {t['progressao']}")
        print(f"  Intensidade : {t['intensidade']}")
        print(f"  Semana leve : {t['semana_leve']}")
        print(f"  Cardio      : {t['cardio']}")
        for nota in t["notas"]:
            print(f"  - {nota}")

    if res.exames:
        print("\n EXAMES (faixa genérica de adulto; a referência do seu laudo prevalece)")
        for e in res.exames:
            print(f"  {e['marcador']}: {e['valor']:g} {e['unidade']} | ref. {e['referencia']} | {e['situacao'].upper()}")
            if e["nota"]:
                print(f"     {e['nota']}")

    if res.pressao:
        p = res.pressao
        print(f"\n PRESSÃO ARTERIAL: {p['sistolica']}x{p['diastolica']} mmHg -> {p['classe']}")

    if res.historico:
        h = res.historico
        print(f"\n HISTÓRICO ({h['registros']} registro(s) em {h['arquivo']})")
        if "ritmo_real_kg_semana" in h:
            print(f"  Ritmo real     : {h['ritmo_real_kg_semana']:+.2f} kg/semana em {h['dias_analisados']} dias")
            print(f"  Ritmo esperado : {h['ritmo_esperado_kg_semana']:+.2f} kg/semana")
        print(f"  {h['recomendacao']}")

    print("\n SUPLEMENTOS COM EVIDÊNCIA")
    for item in res.suplementos:
        print(f"  - {item}")

    print("\n O QUE ACONTECE COM O CORPO")
    for etapa in res.linha_do_tempo:
        print(f"  [{etapa['periodo']}] {etapa['descricao']}")

    print("\n CHECKLIST")
    for item in res.checklist:
        print(f"  - {item}")

    print("\n NOTAS")
    for nota in res.notas:
        print(f"  - {nota}")
    print("  - Recalcule a cada 4 kg de mudança ou quando o peso travar por 2 semanas.")

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
            raise argparse.ArgumentTypeError(f"'{valor}' não é um número")
        if not minimo <= numero <= maximo:
            raise argparse.ArgumentTypeError(f"valor {valor} fora do intervalo {minimo}-{maximo}")
        return numero
    return validar


def inteiro(minimo, maximo):
    def validar(valor):
        try:
            numero = int(valor)
        except ValueError:
            raise argparse.ArgumentTypeError(f"'{valor}' não é um inteiro")
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
        raise argparse.ArgumentTypeError(f"'{valor}' inválido; use NOME:CARGAxREPS, ex.: supino:100x5")
    if not nome:
        raise argparse.ArgumentTypeError("nome do exercício vazio")
    if not 1 <= carga <= 600:
        raise argparse.ArgumentTypeError(f"carga {valor} fora do intervalo 1-600 kg")
    if not 1 <= reps <= 15:
        raise argparse.ArgumentTypeError("repetições fora do intervalo 1-15 (acima disso o 1RM perde precisão)")
    return nome, carga, reps


def tipo_exame(valor):
    try:
        nome, numero = valor.split("=", 1)
        nome, numero = nome.strip().lower(), float(numero.replace(",", "."))
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{valor}' inválido; use MARCADOR=VALOR, ex.: hematocrito=48")
    if nome not in EXAMES:
        raise argparse.ArgumentTypeError(f"marcador '{nome}' desconhecido; opções: {', '.join(sorted(EXAMES))}")
    if not math.isfinite(numero) or numero < 0:
        raise argparse.ArgumentTypeError(f"valor inválido para '{nome}'")
    return nome, numero


def tipo_pressao(valor):
    try:
        sistolica, diastolica = (int(parte) for parte in valor.lower().split("x", 1))
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{valor}' inválido; use SISTOLICAxDIASTOLICA em mmHg, ex.: 125x80")
    if not (60 <= sistolica <= 260 and 30 <= diastolica <= 160 and sistolica > diastolica):
        raise argparse.ArgumentTypeError(f"pressão '{valor}' fora de valores plausíveis (mmHg, ex.: 125x80)")
    return sistolica, diastolica


def tipo_data(valor):
    try:
        return datetime.date.fromisoformat(valor)
    except ValueError:
        raise argparse.ArgumentTypeError(f"data '{valor}' inválida; use AAAA-MM-DD")


def montar_parser():
    p = argparse.ArgumentParser(
        allow_abbrev=False,
        description="Macros, composição corporal, força, exames e histórico para quem treina.",
        epilog="Marcadores de --exame: " + ", ".join(sorted(EXAMES))
               + ". Exercícios com classificação em --levantamento: " + ", ".join(sorted(PADROES_FORCA)) + ".",
    )
    corpo = p.add_argument_group("corpo")
    corpo.add_argument("--peso", type=intervalo(35, 250), help="peso em kg (obrigatório)")
    corpo.add_argument("--altura", type=intervalo(130, 230), help="altura em cm (obrigatório)")
    corpo.add_argument("--idade", type=inteiro(18, 90), help="idade em anos, 18+ (obrigatório)")
    corpo.add_argument("--sexo", choices=["m", "f"], default="m")
    corpo.add_argument("--gordura", type=intervalo(3, 60), help="percentual de gordura, se conhecido")
    corpo.add_argument("--cintura", type=intervalo(40, 200), help="cintura em cm (homens: na altura do umbigo; mulheres: na parte mais estreita)")
    corpo.add_argument("--pescoco", type=intervalo(20, 70), help="pescoço em cm (estima gordura junto com a cintura)")
    corpo.add_argument("--quadril", type=intervalo(50, 200), help="quadril em cm (exigido na estimativa para sexo f)")
    corpo.add_argument("--biotipo", choices=list(BIOTIPOS), default="mesomorfo")

    plano = p.add_argument_group("plano")
    plano.add_argument("--objetivo", choices=["secar", "manter", "crescer"], default="secar")
    plano.add_argument("--perfil", choices=list(PERFIS), default="natural")
    plano.add_argument("--experiencia", choices=list(EXPERIENCIA), default="iniciante", help="tempo de treino sério")
    plano.add_argument("--atividade", choices=list(ATIVIDADE), default="moderado")
    plano.add_argument("--treinos-semana", type=inteiro(0, 7), default=5, help="dias de treino por semana")
    plano.add_argument("--gordura-alvo", type=intervalo(4, 50), help="percentual de gordura desejado (objetivo secar)")
    plano.add_argument("--semanas", type=inteiro(1, 52), default=12, help="semanas de projeção")
    plano.add_argument("--refeicoes", type=inteiro(2, 8), default=4, help="refeições por dia")
    plano.add_argument("--cardapio", action="store_true", help="gera cardápio exemplo com gramas por alimento")
    plano.add_argument("--treino", action="store_true",
                       help="gera plano de treino semanal conforme --treinos-semana e --experiencia")

    acomp = p.add_argument_group("acompanhamento")
    acomp.add_argument("--levantamento", type=tipo_levantamento, action="append", metavar="NOME:CARGAxREPS",
                       help="estima 1RM; repetível. Ex.: supino:100x5")
    acomp.add_argument("--exame", type=tipo_exame, action="append", metavar="MARCADOR=VALOR",
                       help="confere resultado de exame contra a faixa de referência; repetível")
    acomp.add_argument("--pressao", type=tipo_pressao, metavar="SISxDIA", help="pressão arterial em mmHg. Ex.: 125x80")
    acomp.add_argument("--registrar", metavar="ARQUIVO.csv", help="salva o registro do dia e mede o ritmo real")
    acomp.add_argument("--data", type=tipo_data, help="data do registro, AAAA-MM-DD (padrão: hoje)")

    saida = p.add_argument_group("saída e configuração")
    saida.add_argument("--config", metavar="ARQUIVO.json", help="valores padrão em JSON; a linha de comando prevalece")
    saida.add_argument("--json", action="store_true", help="saída em JSON")
    saida.add_argument("--log-file", default=None, help="arquivo de log")
    saida.add_argument("-v", "--verbose", action="store_true")
    saida.add_argument("--debug", action="store_true")
    return p


def argumentos_da_config(caminho, chaves_validas):
    """Converte o JSON de configuração em argumentos, validados pelo mesmo parser."""
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, ValueError, RecursionError) as erro:
        raise ValueError(f"não foi possível ler a config '{caminho}': {erro}")
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
            raise ValueError(f"valor inválido para '{chave}' na config")
        else:
            argumentos.append(f"{opcao}={valor}")
    return argumentos


def configurar_log(args):
    nivel = logging.DEBUG if args.debug else logging.INFO if args.verbose else logging.WARNING
    handlers = [logging.StreamHandler(sys.stderr)]
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file, encoding="utf-8"))
    logging.basicConfig(level=nivel, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=handlers, force=True)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = montar_parser()

    # 1a leitura: so a linha de comando (resolve --help e acha o --config); 2a: config + linha de comando
    so_cli = parser.parse_args(argv)
    args = so_cli
    if so_cli.config is not None:
        try:
            if not so_cli.config:
                raise ValueError("--config recebeu um caminho vazio")
            args = parser.parse_args(argumentos_da_config(so_cli.config, set(vars(so_cli))) + argv)
        except ValueError as erro:
            print(f"Erro: {erro}", file=sys.stderr)
            return 2
        # listas informadas na linha de comando substituem as da config, em vez de somar
        for nome in ("exame", "levantamento"):
            if getattr(so_cli, nome):
                setattr(args, nome, getattr(so_cli, nome))

    faltando = [f"--{nome}" for nome in ("peso", "altura", "idade") if getattr(args, nome) is None]
    if faltando:
        parser.error("obrigatório informar " + ", ".join(faltando) + " (linha de comando ou --config)")
    for nome in ("registrar", "log_file"):
        if getattr(args, nome) == "":
            parser.error(f"--{nome.replace('_', '-')} recebeu um caminho vazio")
    if args.data is not None and args.data > datetime.date.today():
        parser.error("--data não pode estar no futuro")

    try:
        configurar_log(args)
    except (OSError, ValueError) as erro:
        print(f"Erro ao abrir arquivo de log: {erro}", file=sys.stderr)
        return 2

    LOG.info("Calculando: perfil=%s objetivo=%s peso=%.1f", args.perfil, args.objetivo, args.peso)
    try:
        res = calcular(args)
    except OSError as erro:
        LOG.error("Falha ao gravar o histórico: %s", erro)
        return 2
    except (ValueError, ZeroDivisionError) as erro:
        LOG.error("Falha no cálculo: %s", erro)
        return 1

    try:
        if args.json:
            print(json.dumps(asdict(res), ensure_ascii=False, indent=2))
        else:
            imprimir(res)
        sys.stdout.flush()
    except BrokenPipeError:
        # Saida cortada por quem le (ex.: "| head"); encerra sem traceback
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    except (OSError, ValueError) as erro:
        # disco cheio, saida fechada ou terminal que nao representa os caracteres
        print(f"Erro ao escrever o relatorio: {erro}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
