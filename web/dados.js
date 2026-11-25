// Arquivo gerado por tools/gerar_dados.py a partir de maromba_calc.py. Nao edite a mao.
(function (raiz, dados) {
  if (typeof module === "object" && module.exports) module.exports = dados;
  else raiz.MAROMBA_DADOS = dados;
})(typeof self !== "undefined" ? self : this, {
 "KCAL_POR_KG": 7700.0,
 "DEFICIT_MINIMO": 0.05,
 "META_MAX_SEMANAS": 104,
 "DESVIO_MAX_CARDAPIO": 4,
 "HISTORICO_MAX_DIAS": 60,
 "IMC_MINIMO_PARA_SECAR": 18.5,
 "PROTEINA_MINIMA": 1.6,
 "AGUA_MAXIMA_L": 5.0,
 "NOTA_EXAME_PADRAO": "Fora da faixa: leve o laudo ao médico.",
 "NOTA_EXAME_GRAVE": "Valor muito acima da faixa: treino, dieta ou massa muscular não explicam. Procurar médico sem demora.",
 "EXAMES_GRAVE": {
  "tgo": 3.0,
  "tgp": 3.0,
  "creatinina": 1.5,
  "triglicerides": 3.0
 },
 "PSA_LIMITE_ATE_50_ANOS": 2.5,
 "ATIVIDADE": {
  "sedentario": 1.2,
  "leve": 1.375,
  "moderado": 1.55,
  "intenso": 1.725,
  "atleta": 1.9
 },
 "PERFIS": {
  "natural": {
   "prot": {
    "secar": 2.2,
    "manter": 1.8,
    "crescer": 1.8
   },
   "gord": 0.8,
   "corte": 0.006,
   "ganho": 0.0025
  },
  "trt": {
   "prot": {
    "secar": 2.4,
    "manter": 2.0,
    "crescer": 2.0
   },
   "gord": 0.8,
   "corte": 0.007,
   "ganho": 0.003
  },
  "hormonizado": {
   "prot": {
    "secar": 2.6,
    "manter": 2.2,
    "crescer": 2.2
   },
   "gord": 0.9,
   "corte": 0.009,
   "ganho": 0.005
  }
 },
 "BIOTIPOS": {
  "ectomorfo": {
   "gasto": 1.05,
   "gord": -0.1,
   "nota": "Ectomorfo: gasta mais e come pouco. Mais carboidrato e refeições densas."
  },
  "mesomorfo": {
   "gasto": 1.0,
   "gord": 0.0,
   "nota": "Mesomorfo: responde bem à distribuição padrão de macros."
  },
  "endomorfo": {
   "gasto": 0.95,
   "gord": 0.2,
   "nota": "Endomorfo: acumula gordura fácil. Menos carboidrato, mais gordura e passos diários."
  }
 },
 "EXPERIENCIA": {
  "iniciante": 1.0,
  "intermediario": 0.6,
  "avancado": 0.35
 },
 "FFMI_FAIXAS": {
  "m": [
   18,
   20,
   22,
   23.5,
   25
  ],
  "f": [
   14,
   16,
   18,
   19.5,
   21
  ]
 },
 "FFMI_ROTULOS": [
  "abaixo da média",
  "média",
  "acima da média",
  "excelente",
  "próximo do limite natural",
  "acima do limite natural típico"
 ],
 "PADROES_FORCA": {
  "supino": {
   "m": [
    0.75,
    1.25,
    1.75,
    2.0
   ],
   "f": [
    0.5,
    0.75,
    1.0,
    1.5
   ]
  },
  "agachamento": {
   "m": [
    1.25,
    1.5,
    2.25,
    2.75
   ],
   "f": [
    0.75,
    1.25,
    1.5,
    2.0
   ]
  },
  "terra": {
   "m": [
    1.5,
    2.0,
    2.5,
    3.0
   ],
   "f": [
    1.0,
    1.25,
    1.75,
    2.25
   ]
  },
  "desenvolvimento": {
   "m": [
    0.55,
    0.8,
    1.1,
    1.4
   ],
   "f": [
    0.35,
    0.5,
    0.75,
    1.0
   ]
  }
 },
 "NIVEIS_FORCA": [
  "iniciante",
  "novato",
  "intermediário",
  "avançado",
  "elite"
 ],
 "PRESSAO_ROTULOS": [
  "ótima",
  "normal",
  "pré-hipertensão",
  "hipertensão estágio 1",
  "hipertensão estágio 2",
  "hipertensão estágio 3"
 ],
 "EXAMES": {
  "hematocrito": [
   "%",
   {
    "m": [
     40,
     52
    ],
    "f": [
     36,
     46
    ]
   },
   {
    "abaixo": "Hematócrito baixo pode indicar anemia. Médico.",
    "acima": "Sangue mais espesso sobe o risco de trombose. Hidratação e médico."
   }
  ],
  "hemoglobina": [
   "g/dL",
   {
    "m": [
     13.5,
     17.5
    ],
    "f": [
     12.0,
     15.5
    ]
   },
   {
    "abaixo": "Hemoglobina baixa pode indicar anemia. Médico.",
    "acima": "Avaliar junto com o hematócrito."
   }
  ],
  "hdl": [
   "mg/dL",
   {
    "m": [
     40,
     null
    ],
    "f": [
     50,
     null
    ]
   },
   {
    "abaixo": "HDL baixo eleva risco cardiovascular. Cardio, fibras e gordura boa ajudam."
   }
  ],
  "ldl": [
   "mg/dL",
   {
    "m": [
     null,
     130
    ],
    "f": [
     null,
     130
    ]
   },
   {
    "acima": "LDL alto: rever gordura saturada e levar ao médico."
   }
  ],
  "triglicerides": [
   "mg/dL",
   {
    "m": [
     null,
     150
    ],
    "f": [
     null,
     150
    ]
   },
   {
    "acima": "Reduzir açúcar, álcool e excesso calórico."
   }
  ],
  "colesterol_total": [
   "mg/dL",
   {
    "m": [
     null,
     190
    ],
    "f": [
     null,
     190
    ]
   },
   {
    "acima": "Interpretar junto com HDL e LDL."
   }
  ],
  "tgo": [
   "U/L",
   {
    "m": [
     null,
     40
    ],
    "f": [
     null,
     32
    ]
   },
   {
    "acima": "Treino pesado eleva TGO/TGP por lesão muscular; GGT ajuda a separar do fígado."
   }
  ],
  "tgp": [
   "U/L",
   {
    "m": [
     null,
     41
    ],
    "f": [
     null,
     33
    ]
   },
   {
    "acima": "Treino pesado eleva TGO/TGP por lesão muscular; GGT ajuda a separar do fígado."
   }
  ],
  "ggt": [
   "U/L",
   {
    "m": [
     null,
     60
    ],
    "f": [
     null,
     40
    ]
   },
   {
    "acima": "GGT alta aponta sobrecarga do fígado. Médico."
   }
  ],
  "creatinina": [
   "mg/dL",
   {
    "m": [
     0.7,
     1.3
    ],
    "f": [
     0.6,
     1.1
    ]
   },
   {
    "acima": "Muita massa muscular e creatina elevam o valor sem doença renal; confirmar com o médico."
   }
  ],
  "glicemia": [
   "mg/dL",
   {
    "m": [
     70,
     99
    ],
    "f": [
     70,
     99
    ]
   },
   {
    "abaixo": "Glicemia baixa em jejum: com tontura ou suor frio, médico.",
    "acima": "Glicemia em jejum acima da faixa. Repetir e levar ao médico."
   }
  ],
  "testosterona_total": [
   "ng/dL",
   {
    "m": [
     300,
     1000
    ],
    "f": [
     15,
     70
    ]
   },
   {
    "abaixo": "Abaixo da faixa fisiológica (coleta pela manhã). Quem define conduta é o médico.",
    "acima": "Acima da faixa fisiológica. Quem define conduta é o médico."
   }
  ],
  "estradiol": [
   "pg/mL",
   {
    "m": [
     10,
     40
    ],
    "f": null
   },
   {
    "abaixo": "Fora da faixa: avaliar com o médico, sem automedicação.",
    "acima": "Fora da faixa: avaliar com o médico, sem automedicação."
   }
  ],
  "lh": [
   "mUI/mL",
   {
    "m": [
     1.7,
     8.6
    ],
    "f": null
   },
   {
    "abaixo": "LH baixo indica eixo hormonal suprimido; afeta fertilidade."
   }
  ],
  "fsh": [
   "mUI/mL",
   {
    "m": [
     1.5,
     12.4
    ],
    "f": null
   },
   {
    "abaixo": "FSH baixo indica eixo hormonal suprimido; afeta fertilidade."
   }
  ],
  "prolactina": [
   "ng/mL",
   {
    "m": [
     4,
     15
    ],
    "f": [
     5,
     23
    ]
   },
   {
    "acima": "Prolactina alta pede investigação médica."
   }
  ],
  "psa": [
   "ng/mL",
   {
    "m": [
     null,
     4.0
    ],
    "f": null
   },
   {
    "acima": "PSA acima da faixa para a idade: urologista."
   }
  ],
  "tsh": [
   "mUI/L",
   {
    "m": [
     0.4,
     4.5
    ],
    "f": [
     0.4,
     4.5
    ]
   },
   {
    "abaixo": "Tireoide fora da faixa muda o gasto calórico. Médico.",
    "acima": "Tireoide fora da faixa muda o gasto calórico. Médico."
   }
  ]
 },
 "ALIMENTOS": {
  "whey": [
   "Whey protein (pó)",
   80.0,
   8.0,
   6.0
  ],
  "frango": [
   "Peito de frango grelhado",
   31.0,
   0.0,
   3.6
  ],
  "tilapia": [
   "Tilápia grelhada",
   26.0,
   0.0,
   2.7
  ],
  "patinho": [
   "Patinho grelhado",
   32.0,
   0.0,
   7.0
  ],
  "arroz": [
   "Arroz branco cozido",
   2.5,
   28.0,
   0.2
  ],
  "batata_doce": [
   "Batata-doce cozida",
   0.6,
   18.4,
   0.1
  ],
  "aveia": [
   "Aveia em flocos",
   14.0,
   66.0,
   8.5
  ],
  "pao_frances": [
   "Pão francês",
   8.0,
   58.0,
   3.0
  ],
  "banana": [
   "Banana",
   1.3,
   26.0,
   0.1
  ],
  "macarrao": [
   "Macarrão cozido",
   5.0,
   30.0,
   1.0
  ],
  "azeite": [
   "Azeite de oliva",
   0.0,
   0.0,
   100.0
  ],
  "pasta_amendoim": [
   "Pasta de amendoim",
   25.0,
   20.0,
   50.0
  ],
  "castanha": [
   "Castanha-do-pará",
   14.0,
   12.0,
   66.0
  ],
  "abacate": [
   "Abacate",
   1.2,
   6.0,
   8.4
  ]
 },
 "MODELOS_REFEICAO": [
  [
   "whey",
   "aveia",
   "pasta_amendoim"
  ],
  [
   "frango",
   "arroz",
   "azeite"
  ],
  [
   "tilapia",
   "batata_doce",
   "azeite"
  ],
  [
   "patinho",
   "macarrao",
   "azeite"
  ],
  [
   "frango",
   "pao_frances",
   "abacate"
  ],
  [
   "whey",
   "banana",
   "castanha"
  ]
 ],
 "EXERCICIOS": {
  "agachamento": [
   "Agachamento livre",
   "quadríceps",
   true,
   "agachamento"
  ],
  "leg_press": [
   "Leg press 45",
   "quadríceps",
   true,
   null
  ],
  "afundo": [
   "Afundo com halteres",
   "quadríceps",
   true,
   null
  ],
  "cadeira_extensora": [
   "Cadeira extensora",
   "quadríceps",
   false,
   null
  ],
  "terra": [
   "Levantamento terra",
   "posterior",
   true,
   "terra"
  ],
  "stiff": [
   "Stiff com barra",
   "posterior",
   true,
   null
  ],
  "mesa_flexora": [
   "Mesa flexora",
   "posterior",
   false,
   null
  ],
  "elevacao_pelvica": [
   "Elevação pélvica",
   "glúteos",
   true,
   null
  ],
  "panturrilha": [
   "Panturrilha em pé",
   "panturrilha",
   false,
   null
  ],
  "supino": [
   "Supino reto com barra",
   "peito",
   true,
   "supino"
  ],
  "supino_inclinado": [
   "Supino inclinado com halteres",
   "peito",
   true,
   null
  ],
  "crucifixo": [
   "Crucifixo na máquina",
   "peito",
   false,
   null
  ],
  "desenvolvimento": [
   "Desenvolvimento com barra",
   "ombros",
   true,
   "desenvolvimento"
  ],
  "elevacao_lateral": [
   "Elevação lateral",
   "ombros",
   false,
   null
  ],
  "face_pull": [
   "Face pull na polia",
   "ombros",
   false,
   null
  ],
  "barra_fixa": [
   "Barra fixa (ou graviton)",
   "costas",
   true,
   null
  ],
  "puxada": [
   "Puxada frontal na polia",
   "costas",
   true,
   null
  ],
  "remada_curvada": [
   "Remada curvada com barra",
   "costas",
   true,
   null
  ],
  "remada_baixa": [
   "Remada baixa na polia",
   "costas",
   true,
   null
  ],
  "rosca_direta": [
   "Rosca direta",
   "bíceps",
   false,
   null
  ],
  "rosca_martelo": [
   "Rosca martelo",
   "bíceps",
   false,
   null
  ],
  "triceps_corda": [
   "Tríceps na polia com corda",
   "tríceps",
   false,
   null
  ],
  "triceps_testa": [
   "Tríceps testa",
   "tríceps",
   false,
   null
  ],
  "prancha": [
   "Prancha",
   "core",
   false,
   null
  ],
  "abdominal": [
   "Abdominal na polia",
   "core",
   false,
   null
  ]
 },
 "REPS_ESPECIAIS": {
  "prancha": "30-60 s",
  "abdominal": "12-20",
  "panturrilha": "10-15"
 },
 "MODELOS_TREINO": {
  "full_a": [
   "Corpo inteiro A",
   [
    "agachamento",
    "supino",
    "remada_curvada",
    "elevacao_lateral",
    "rosca_direta",
    "prancha"
   ]
  ],
  "full_b": [
   "Corpo inteiro B",
   [
    "terra",
    "desenvolvimento",
    "puxada",
    "leg_press",
    "triceps_corda",
    "abdominal"
   ]
  ],
  "full_c": [
   "Corpo inteiro C",
   [
    "leg_press",
    "supino_inclinado",
    "remada_baixa",
    "mesa_flexora",
    "elevacao_lateral",
    "panturrilha"
   ]
  ],
  "push": [
   "Empurrar A: peito, ombros e tríceps",
   [
    "supino",
    "supino_inclinado",
    "desenvolvimento",
    "elevacao_lateral",
    "triceps_corda",
    "triceps_testa"
   ]
  ],
  "pull": [
   "Puxar A: costas e bíceps",
   [
    "barra_fixa",
    "remada_curvada",
    "puxada",
    "face_pull",
    "rosca_direta",
    "rosca_martelo"
   ]
  ],
  "legs": [
   "Pernas A",
   [
    "agachamento",
    "stiff",
    "leg_press",
    "mesa_flexora",
    "panturrilha",
    "prancha"
   ]
  ],
  "push_b": [
   "Empurrar B: ombros, peito e tríceps",
   [
    "desenvolvimento",
    "supino_inclinado",
    "crucifixo",
    "elevacao_lateral",
    "triceps_testa",
    "triceps_corda"
   ]
  ],
  "pull_b": [
   "Puxar B: costas e bíceps",
   [
    "terra",
    "remada_baixa",
    "puxada",
    "face_pull",
    "rosca_martelo",
    "rosca_direta"
   ]
  ],
  "legs_b": [
   "Pernas B",
   [
    "leg_press",
    "elevacao_pelvica",
    "afundo",
    "cadeira_extensora",
    "mesa_flexora",
    "panturrilha",
    "abdominal"
   ]
  ],
  "upper": [
   "Superiores A",
   [
    "supino",
    "remada_curvada",
    "desenvolvimento",
    "puxada",
    "rosca_direta",
    "triceps_corda"
   ]
  ],
  "lower": [
   "Inferiores A",
   [
    "agachamento",
    "stiff",
    "leg_press",
    "mesa_flexora",
    "panturrilha",
    "prancha"
   ]
  ],
  "upper_b": [
   "Superiores B",
   [
    "supino_inclinado",
    "barra_fixa",
    "elevacao_lateral",
    "remada_baixa",
    "rosca_martelo",
    "triceps_testa"
   ]
  ],
  "lower_b": [
   "Inferiores B",
   [
    "terra",
    "leg_press",
    "afundo",
    "cadeira_extensora",
    "panturrilha",
    "abdominal"
   ]
  ]
 },
 "DIVISOES": {
  "1": [
   "full_a"
  ],
  "2": [
   "full_a",
   "full_b"
  ],
  "3": [
   "full_a",
   "full_b",
   "full_c"
  ],
  "4": [
   "upper",
   "lower",
   "upper_b",
   "lower_b"
  ],
  "5": [
   "push",
   "pull",
   "legs",
   "upper_b",
   "lower_b"
  ],
  "6": [
   "push",
   "pull",
   "legs",
   "push_b",
   "pull_b",
   "legs_b"
  ]
 },
 "DIAS_TREINO": {
  "1": [
   "seg"
  ],
  "2": [
   "seg",
   "qui"
  ],
  "3": [
   "seg",
   "qua",
   "sex"
  ],
  "4": [
   "seg",
   "ter",
   "qui",
   "sex"
  ],
  "5": [
   "seg",
   "ter",
   "qua",
   "sex",
   "sáb"
  ],
  "6": [
   "seg",
   "ter",
   "qua",
   "qui",
   "sex",
   "sáb"
  ],
  "7": [
   "seg",
   "ter",
   "qua",
   "qui",
   "sex",
   "sáb"
  ]
 },
 "VOLUME_ROTULOS": [
  "baixo",
  "mínimo eficaz",
  "faixa ideal",
  "alto"
 ],
 "LINHA_DO_TEMPO": {
  "natural": [
   [
    "Dias 1-7",
    "Adaptação à dieta. Fome e queda de energia no déficit; peso oscila por água e glicogênio."
   ],
   [
    "Semanas 2-4",
    "Peso estabiliza na tendência real. Força sobe por adaptação neural."
   ],
   [
    "Semanas 5-8",
    "Mudança visível no espelho e nas medidas. Ajuste calorias se o peso travar 2 semanas."
   ],
   [
    "Semanas 9-12",
    "Ganho ou perda consolidado. Reavalie metas e recalcule com o peso novo."
   ]
  ],
  "trt": [
   [
    "Dias 1-7",
    "Pouca mudança física. Possível melhora de disposição e libido."
   ],
   [
    "Semanas 2-4",
    "Retenção leve de água, recuperação melhor entre treinos, apetite maior."
   ],
   [
    "Semanas 5-8",
    "Força e volume muscular sobem. Hematócrito e pressão podem subir: medir."
   ],
   [
    "Semanas 9-12",
    "Composição corporal muda de forma clara. Hora de repetir exames com o médico."
   ]
  ],
  "hormonizado": [
   [
    "Dias 1-7",
    "Retenção de água (+1 a 2 kg na balança sem ser gordura), apetite maior, pump mais forte. O eixo hormonal natural fica suprimido durante todo o uso, com fertilidade reduzida."
   ],
   [
    "Semanas 2-4",
    "Força sobe rápido, recuperação acelera. Pele oleosa, acne e pressão alta podem aparecer."
   ],
   [
    "Semanas 5-8",
    "Ganho muscular visível. Tendões não acompanham o músculo: suba carga devagar. Colesterol HDL cai, hematócrito sobe, sono e humor podem oscilar."
   ],
   [
    "Semanas 9-12",
    "Composição corporal muda de forma clara. Hora de repetir exames com o médico."
   ]
  ]
 },
 "CHECKLIST_BASE": [
  "Pesar em jejum, mesmo horário, e usar a média semanal, não o dia isolado.",
  "Medir cintura 1x por semana e tirar foto no mesmo local e luz.",
  "Pesar a comida na balança nas primeiras 4 semanas, no mínimo.",
  "Dormir 7-9 h. Sono ruim derruba recuperação e aumenta fome.",
  "Treino de força com progressão de carga; 8-10 mil passos por dia."
 ],
 "CHECKLIST_HORMONAL": [
  "Acompanhamento com médico (endocrinologista ou médico do esporte) antes, durante e depois.",
  "Exames de base e a cada 8-12 semanas: hemograma (hematócrito), lipidograma, TGO/TGP/GGT, creatinina/ureia, testosterona total e livre, estradiol, LH/FSH, prolactina, PSA, glicemia.",
  "Medir pressão arterial em casa 3x por semana. A partir de 13x8 repetido: médico.",
  "Cardio 3-4x por semana, 20-40 min: protege coração e controla pressão.",
  "Sódio controlado, potássio via comida (banana, batata, feijão), álcool no mínimo.",
  "Sinais de alerta, procurar atendimento: dor no peito, falta de ar, dor/inchaço em uma perna, dor de cabeça forte, pele ou olhos amarelados, mama dolorida ou com nódulo.",
  "Nunca compartilhar agulhas; material estéril e descarte correto."
 ]
});
