// Logica do App Maromba no navegador. Espelha maromba_calc.py funcao por funcao;
// tests/test_web.py compara as duas implementacoes caso a caso.
// Nao calcula dose, substancia nem ciclo.
(function (raiz, fabrica) {
  if (typeof module === "object" && module.exports) module.exports = fabrica(require("./dados.js"));
  else raiz.MarombaCalc = fabrica(raiz.MAROMBA_DADOS);
})(typeof self !== "undefined" ? self : this, function (D) {
  "use strict";

  var tem = function (objeto, chave) {
    return chave != null && Object.prototype.hasOwnProperty.call(objeto, chave);
  };

  // Arredondamento igual ao round() do Python: decide pelo valor decimal exato, empate vai para o par.
  function arred(x, casas) {
    casas = casas || 0;
    if (!isFinite(x)) return x;
    var negativo = x < 0;
    var partes = Math.abs(x).toFixed(80).split(".");
    var mantidos = partes[0] + partes[1].slice(0, casas);
    var resto = partes[1].slice(casas);
    var primeiro = resto.charCodeAt(0) - 48;
    var restoZero = /^0*$/.test(resto.slice(1));
    var ultimo = mantidos.charCodeAt(mantidos.length - 1) - 48;
    var sobe = primeiro > 5 || (primeiro === 5 && (!restoZero || ultimo % 2 === 1));
    var valor = (Number(mantidos) + (sobe ? 1 : 0)) / Math.pow(10, casas);
    return negativo ? -valor : valor;
  }

  var texto0 = function (x) { return String(arred(x)); };

  function classificar(valor, limites, rotulos) {
    var indice = 0;
    for (var i = 0; i < limites.length; i++) if (valor >= limites[i]) indice++;
    return rotulos[indice];
  }

  function calcularTmb(peso, altura, idade, sexo, gordura) {
    if (gordura != null) return 370 + 21.6 * (peso * (1 - gordura / 100));
    var base = 10 * peso + 6.25 * altura - 5 * idade;
    return sexo === "m" ? base + 5 : base - 161;
  }

  function ajusteIdade(idade) {
    if (idade < 30) return [0.0, 1.0, "Idade: recuperação no auge; o corpo tolera volume alto de treino."];
    if (idade < 40) return [0.0, 0.95, "Idade: recuperação ainda boa; sono e aquecimento passam a pesar mais."];
    if (idade < 50) return [0.2, 0.85, "Idade 40+: mais proteína, ritmo mais conservador e 1 dia extra de descanso."];
    return [0.3, 0.75, "Idade 50+: proteína alta, progressão lenta de carga e check-up cardiológico anual."];
  }

  function gorduraNavy(sexo, altura, cintura, pescoco, quadril) {
    var diferenca, densidade;
    if (sexo === "m") {
      diferenca = cintura - pescoco;
      if (diferenca <= 0) throw new Error("cintura precisa ser maior que o pescoço para estimar a gordura");
      densidade = 1.0324 - 0.19077 * Math.log10(diferenca) + 0.15456 * Math.log10(altura);
    } else {
      if (quadril == null) throw new Error("para o sexo feminino a estimativa de gordura exige a medida do quadril");
      diferenca = cintura + quadril - pescoco;
      if (diferenca <= 0) throw new Error("medidas de cintura, quadril e pescoço inconsistentes");
      densidade = 1.29579 - 0.35004 * Math.log10(diferenca) + 0.22100 * Math.log10(altura);
    }
    if (densidade <= 0) throw new Error("medidas corporais inconsistentes para estimar a gordura");
    var estimativa = 495.0 / densidade - 450.0;
    if (!(estimativa >= 3.0 && estimativa <= 60.0)) {
      throw new Error("medidas fora da faixa válida do método de fita; confira cintura e pescoço " +
        "ou informe o percentual de gordura");
    }
    return estimativa;
  }

  function analisarComposicao(peso, altura, sexo, gordura, cintura) {
    var metros = altura / 100;
    var comp = { imc: arred(peso / (metros * metros), 1) };
    if (gordura != null) {
      var magra = peso * (1 - gordura / 100);
      var ffmi = magra / (metros * metros);
      var ffmiNorm = ffmi + 6.1 * (1.8 - metros);
      comp.massa_magra_kg = arred(magra, 1);
      comp.massa_gorda_kg = arred(peso - magra, 1);
      comp.ffmi = arred(ffmi, 1);
      comp.ffmi_normalizado = arred(ffmiNorm, 1);
      comp.ffmi_classe = gordura > (sexo === "m" ? 25 : 35)
        ? "não interpretável com gordura alta"
        : classificar(ffmiNorm, D.FFMI_FAIXAS[sexo], D.FFMI_ROTULOS);
    }
    if (cintura != null) comp.cintura_altura = arred(cintura / altura, 2);
    return comp;
  }

  function calcularCicloCarbo(carbo, calorias, treinos, piso) {
    piso = piso || 0;
    var descansos = 7 - treinos;
    if (treinos <= 0 || descansos <= 0 || carbo <= 0) return {};
    var fatorTreino = Math.min(1.35, (7 - 0.75 * descansos) / treinos);
    var carboTreino = carbo * fatorTreino;
    var carboDescanso = (7 * carbo - treinos * carboTreino) / descansos;
    var minimoDescanso = carbo - (calorias - piso) / 4.0;
    if (carboDescanso < minimoDescanso) {
      carboDescanso = minimoDescanso;
      carboTreino = (7 * carbo - descansos * carboDescanso) / treinos;
    }
    if (carbo - carboDescanso < 5) return {};
    return {
      treinos_semana: treinos,
      carbo_treino_g: arred(carboTreino),
      carbo_descanso_g: arred(carboDescanso),
      kcal_treino: arred(calorias + (carboTreino - carbo) * 4),
      kcal_descanso: arred(calorias + (carboDescanso - carbo) * 4)
    };
  }

  function calcularMeta(peso, gordura, alvo, variacao, calorias, gasto) {
    var magra = peso * (1 - gordura / 100);
    var pesoAlvo = magra / (1 - alvo / 100);
    var perder = peso - pesoAlvo;
    var semanasDeficit = Math.ceil(arred(perder / Math.abs(variacao), 6));
    var pausas = Math.floor((semanasDeficit - 1) / 8);
    var fases = [];
    var restante = semanasDeficit;
    while (restante > 0) {
      var bloco = Math.min(8, restante);
      fases.push({ fase: "déficit", semanas: bloco, kcal: arred(calorias) });
      restante -= bloco;
      if (restante > 0) fases.push({ fase: "pausa na manutenção", semanas: 1, kcal: arred(gasto) });
    }
    return {
      gordura_alvo_pct: alvo, peso_alvo_kg: arred(pesoAlvo, 1), perder_kg: arred(perder, 1),
      semanas_deficit: semanasDeficit, semanas_pausa: pausas,
      semanas_total: semanasDeficit + pausas, fases: fases
    };
  }

  function resolverRefeicao(chaves, alvo) {
    var fontes = chaves.map(function (c) {
      var a = D.ALIMENTOS[c];
      return [a[1] / 100, a[2] / 100, a[3] / 100];
    });
    var pp = fontes[0][0], pc = fontes[0][1], pg = fontes[0][2];
    var cp = fontes[1][0], cc = fontes[1][1], cg = fontes[1][2];
    var gp = fontes[2][0], gc = fontes[2][1], gg = fontes[2][2];
    var qp = 0, qc = 0, qg = 0;
    for (var i = 0; i < 25; i++) {
      qp = Math.max(0, (alvo.proteina_g - qc * cp - qg * gp) / pp);
      qc = Math.max(0, (alvo.carbo_g - qp * pc - qg * gc) / cc);
      qg = Math.max(0, (alvo.gordura_g - qp * pg - qc * cg) / gg);
    }
    var passoGordura = gg >= 0.4 ? 1 : 5;
    var gramas = [arred(qp / 5) * 5, arred(qc / 5) * 5, arred(qg / passoGordura) * passoGordura];
    var macros = [0, 1, 2].map(function (m) {
      var soma = 0;
      for (var k = 0; k < 3; k++) soma += gramas[k] * fontes[k][m];
      return soma;
    });
    return [gramas, macros];
  }

  function montarCardapio(refeicoes) {
    var total = D.MODELOS_REFEICAO.length;
    var campos = ["proteina_g", "carbo_g", "gordura_g"];
    return refeicoes.map(function (alvo, indice) {
      var melhor = null;
      for (var deslocamento = 0; deslocamento < total; deslocamento++) {
        var chaves = D.MODELOS_REFEICAO[(indice + deslocamento) % total];
        var solucao = resolverRefeicao(chaves, alvo);
        var desvio = 0;
        for (var m = 0; m < 3; m++) desvio = Math.max(desvio, Math.abs(solucao[1][m] - alvo[campos[m]]));
        if (melhor === null || desvio < melhor.desvio) {
          melhor = { desvio: desvio, chaves: chaves, gramas: solucao[0], macros: solucao[1] };
        }
        if (desvio <= D.DESVIO_MAX_CARDAPIO) break;
      }
      var itens = [];
      melhor.chaves.forEach(function (c, k) {
        if (melhor.gramas[k] > 0) itens.push({ alimento: D.ALIMENTOS[c][0], gramas: melhor.gramas[k] });
      });
      var prot = melhor.macros[0], carb = melhor.macros[1], gord = melhor.macros[2];
      return {
        refeicao: alvo.refeicao, itens: itens,
        proteina_g: arred(prot), carbo_g: arred(carb), gordura_g: arred(gord),
        kcal: arred(prot * 4 + carb * 4 + gord * 9),
        aproximado: melhor.desvio > D.DESVIO_MAX_CARDAPIO
      };
    });
  }

  function analisarForca(levantamentos, peso, sexo) {
    return levantamentos.map(function (item) {
      var nome = item[0], carga = item[1], reps = item[2];
      var rm = reps === 1 ? carga : (carga * (1 + reps / 30.0) + carga * 36.0 / (37 - reps)) / 2;
      var cargas = {};
      [90, 85, 80, 75, 70].forEach(function (p) { cargas[p + "%"] = arred(rm * p / 100 / 2.5) * 2.5; });
      return {
        exercicio: nome, carga_kg: carga, reps: reps,
        rm_estimado_kg: arred(rm, 1), relativo: arred(rm / peso, 2),
        nivel: tem(D.PADROES_FORCA, nome) ? classificar(rm / peso, D.PADROES_FORCA[nome][sexo], D.NIVEIS_FORCA) : null,
        cargas_treino: cargas
      };
    });
  }

  function montarTreino(dias, experiencia, objetivo, perfil, idade, forca) {
    if (dias <= 0) return {};
    var chaves = dias === 3 && experiencia !== "iniciante" ? ["push", "pull", "legs"] : D.DIVISOES[Math.min(dias, 6)];
    var seriesComposto = { iniciante: 3, intermediario: 4, avancado: 4 }[experiencia];
    var seriesIsolado = { iniciante: 2, intermediario: 3, avancado: 4 }[experiencia];
    if (idade >= 50) {
      seriesComposto = Math.max(2, seriesComposto - 1);
      seriesIsolado = Math.max(2, seriesIsolado - 1);
    }
    if (objetivo === "manter") seriesIsolado = Math.max(2, seriesIsolado - 1);
    var repsComposto = experiencia === "iniciante" ? "8-12" : "6-10";
    var faixaCarga = experiencia === "iniciante" ? "70%" : "75%";
    var cargaConhecida = Object.create(null);
    forca.forEach(function (item) { cargaConhecida[item.exercicio] = item.cargas_treino[faixaCarga]; });

    var sessoes = [];
    var volume = Object.create(null);
    var diasSemana = D.DIAS_TREINO[dias];
    for (var i = 0; i < Math.min(diasSemana.length, chaves.length); i++) {
      var modelo = D.MODELOS_TREINO[chaves[i]];
      var exercicios = modelo[1].map(function (codigo) {
        var e = D.EXERCICIOS[codigo];
        var composto = e[2], chaveRm = e[3];
        var series = composto ? seriesComposto : seriesIsolado;
        var carga = chaveRm != null && chaveRm in cargaConhecida ? cargaConhecida[chaveRm] : null;
        volume[e[1]] = (volume[e[1]] || 0) + series;
        return {
          exercicio: e[0], grupo: e[1], series: series,
          reps: tem(D.REPS_ESPECIAIS, codigo) ? D.REPS_ESPECIAIS[codigo] : (composto ? repsComposto : "10-15"),
          descanso: composto ? "2-3 min" : "60-90 s", carga_sugerida_kg: carga
        };
      });
      sessoes.push({ dia: diasSemana[i], treino: modelo[0], exercicios: exercicios });
    }
    if (dias === 7) {
      sessoes.push({ dia: "dom", treino: "Recuperação ativa: 30-40 min de caminhada e mobilidade", exercicios: [] });
    }

    var cardio;
    if (objetivo === "secar") cardio = "3-4 sessões de 25-40 min em ritmo de conversa (zona 2), longe do treino de pernas.";
    else if (perfil !== "natural") cardio = "3 sessões de 20-30 min em ritmo de conversa: a prioridade é a saúde do coração.";
    else if (objetivo === "crescer") cardio = "2 sessões leves de 20 min: mantém o condicionamento sem roubar recuperação.";
    else cardio = "2-3 sessões de 20-30 min em ritmo de conversa.";

    var notas = [];
    if (objetivo === "secar") notas.push("No déficit a prioridade é manter a carga na barra; não troque peso por repetições altas.");
    if (perfil !== "natural") notas.push("Músculo ganha força antes de tendão e ligamento: suba carga no ritmo da progressão, sem saltos.");
    if (experiencia === "iniciante" && dias >= 5) notas.push("Iniciante progride igual com 3-4 dias por semana; os dias extras são opcionais.");
    if (dias <= 2) notas.push("Com até 2 treinos o volume por grupo fica baixo: serve para manter ou para quem está começando.");
    if (dias === 7) notas.push("Sem nenhum dia livre a recuperação cai: o sétimo dia é apenas recuperação ativa.");
    if (idade >= 40) notas.push("40+: aquecimento mais longo e séries de aproximação antes de toda carga pesada.");

    var volumeSemanal = {};
    Object.keys(volume).sort().forEach(function (grupo) {
      volumeSemanal[grupo] = { series: volume[grupo], classe: classificar(volume[grupo], [6, 10, 21], D.VOLUME_ROTULOS) };
    });

    return {
      dias_semana: dias,
      sessoes: sessoes,
      volume_semanal: volumeSemanal,
      aquecimento: "5-10 min de cardio leve e 2-3 séries progressivas do primeiro exercício.",
      progressao: "Ao bater o topo da faixa de repetições em todas as séries, suba 2,5 kg (superiores) ou 5 kg (inferiores).",
      intensidade: "Termine cada série com 1-3 repetições de sobra; falha só na última série dos isolados.",
      semana_leve: "A cada " + (idade >= 40 ? "4-6" : "6-8") + " semanas: metade das séries, mesma carga.",
      cardio: cardio,
      notas: notas
    };
  }

  function avaliarExames(itens, sexo, idade) {
    return itens.map(function (item) {
      var nome = item[0], valor = item[1];
      var definicao = D.EXAMES[nome];
      var unidade = definicao[0], faixa = definicao[1][sexo], notas = definicao[2];
      if (nome === "psa" && faixa != null && idade < 50) faixa = [null, D.PSA_LIMITE_ATE_50_ANOS];
      var situacao, referencia, nota = "";
      if (faixa == null) {
        situacao = "sem faixa genérica";
        referencia = "usar a referência do laudo";
      } else {
        var minimo = faixa[0], maximo = faixa[1];
        if (minimo != null && maximo != null) referencia = String(minimo) + "-" + String(maximo);
        else if (minimo != null) referencia = ">= " + String(minimo);
        else referencia = "<= " + String(maximo);
        if (minimo != null && valor < minimo) situacao = "abaixo";
        else if (maximo != null && valor > maximo) situacao = "acima";
        else situacao = "dentro";
        if (situacao !== "dentro") nota = notas[situacao] || D.NOTA_EXAME_PADRAO;
        if (situacao === "acima" && tem(D.EXAMES_GRAVE, nome) && valor > maximo * D.EXAMES_GRAVE[nome]) {
          situacao = "acima (crítico)";
          nota = D.NOTA_EXAME_GRAVE;
        }
      }
      if (nome === "hematocrito" && valor > 54) {
        situacao = "acima (crítico)";
        nota = "Acima de 54%: risco real de trombose. Procurar médico sem demora.";
      }
      return { marcador: nome, valor: valor, unidade: unidade, referencia: referencia, situacao: situacao, nota: nota };
    });
  }

  function avaliarPressao(sistolica, diastolica) {
    var a = 0, b = 0;
    [120, 130, 140, 160, 180].forEach(function (limite) { if (sistolica >= limite) a++; });
    [80, 85, 90, 100, 110].forEach(function (limite) { if (diastolica >= limite) b++; });
    var nivel = Math.max(a, b);
    var classe = D.PRESSAO_ROTULOS[nivel];
    if (nivel === 0 && (sistolica < 90 || diastolica < 60)) classe = "baixa";
    return { sistolica: sistolica, diastolica: diastolica, nivel: nivel, classe: classe };
  }

  function listarSuplementos(peso, nivelPressao) {
    var cafeina = Math.min(400, arred(peso * 3 / 10) * 10);
    return [
      "Creatina monoidratada: " + (peso < 70 ? 3 : 5) + " g por dia, todos os dias, qualquer horário.",
      nivelPressao >= 3
        ? "Cafeína: evitar até liberação médica (pressão elevada)."
        : "Cafeína: até " + cafeina + " mg, 30-60 min antes do treino; evitar depois das 15 h.",
      "Proteína em pó (whey ou vegetal): só para fechar a meta diária de proteína.",
      "Vitamina D e ômega-3: apenas se exame ou dieta mostrarem falta."
    ];
  }

  function montarChecklist(perfil, sexo) {
    if (perfil === "natural") return D.CHECKLIST_BASE.slice();
    var hormonal = D.CHECKLIST_HORMONAL;
    if (sexo === "f") {
      hormonal = hormonal.map(function (item) { return item.replace("prolactina, PSA, glicemia", "prolactina, glicemia"); });
    }
    return D.CHECKLIST_BASE.concat(hormonal);
  }

  function recomendarAjuste(objetivo, esperado, real, calorias, ajuste, piso) {
    var tolerancia = Math.max(0.1, Math.abs(esperado) * 0.5);
    var passo = Math.min(150, Math.max(50, arred(Math.abs(ajuste) / 20.0) * 10));
    if (objetivo === "secar") {
      if (esperado > -D.DEFICIT_MINIMO) return "Plano sem déficit efetivo: para secar, aumente o gasto com passos e cardio.";
      if (real > esperado + tolerancia) {
        if (calorias - passo < piso) return "Perda abaixo do esperado e calorias já no piso: some 2 mil passos por dia, sem cortar comida.";
        return "Perda abaixo do esperado: reduza " + passo + " kcal (carboidrato) ou some 2 mil passos por dia.";
      }
      if (real < esperado - tolerancia) return "Perda rápida demais: suba " + passo + " kcal para proteger a massa magra.";
    } else if (objetivo === "crescer") {
      if (real < esperado - tolerancia) return "Ganho abaixo do esperado: suba " + passo + " kcal (carboidrato).";
      if (real > esperado + tolerancia) return "Ganho rápido demais: reduza " + passo + " kcal, o excesso vira gordura.";
    } else {
      if (real > 0.25) return "Peso subindo na manutenção: reduza 150 kcal.";
      if (real < -0.25) return "Peso caindo na manutenção: suba 150 kcal.";
    }
    return "Ritmo dentro do esperado: mantenha o plano.";
  }

  var diasEntre = function (a, b) {
    var pa = a.split("-"), pb = b.split("-");
    return Math.round((Date.UTC(+pb[0], pb[1] - 1, +pb[2]) - Date.UTC(+pa[0], pa[1] - 1, +pa[2])) / 86400000);
  };

  // registros: lista de [data "AAAA-MM-DD", peso]; o ultimo registro de cada data prevalece.
  function analisarHistorico(registros, objetivo, esperado, calorias, ajuste, piso) {
    var porData = Object.create(null);
    registros.forEach(function (r) { porData[r[0]] = r[1]; });
    var serie = Object.keys(porData).sort().map(function (d) { return [d, porData[d]]; });
    var historico = { registros: serie.length, ritmo_esperado_kg_semana: arred(esperado, 2) };
    if (serie.length < 2) {
      historico.recomendacao = "Primeiro registro salvo. Registre o peso toda semana para medir o ritmo real.";
      return historico;
    }
    var fim = serie[serie.length - 1];
    var anteriores = serie.slice(0, -1);
    var elegiveis = anteriores.filter(function (par) { return diasEntre(par[0], fim[0]) >= 7; });
    if (!elegiveis.length) {
      historico.dias_analisados = diasEntre(serie[0][0], fim[0]);
      historico.recomendacao = "Menos de 7 dias entre registros: cedo demais para medir ritmo.";
      return historico;
    }
    var naJanela = elegiveis.filter(function (par) { return diasEntre(par[0], fim[0]) <= 28; });
    var base = naJanela.length ? naJanela[0] : elegiveis[elegiveis.length - 1];
    var dias = diasEntre(base[0], fim[0]);
    historico.dias_analisados = dias;
    if (dias > D.HISTORICO_MAX_DIAS) {
      historico.recomendacao = "Registro anterior com mais de 60 dias: registre o peso por 2 semanas " +
        "para medir o ritmo atual.";
      return historico;
    }
    var real = (fim[1] - base[1]) / (dias / 7.0);
    historico.ritmo_real_kg_semana = arred(real, 2);
    historico.recomendacao = dias < 14
      ? "Menos de 14 dias de dados: continue registrando antes de mexer nas calorias."
      : recomendarAjuste(objetivo, esperado, real, calorias, ajuste, piso);
    return historico;
  }

  // entrada: mesmos campos das opcoes de maromba_calc.py (peso, altura, idade, sexo, gordura, cintura,
  // pescoco, quadril, biotipo, objetivo, perfil, experiencia, atividade, treinos_semana, gordura_alvo,
  // semanas, refeicoes, cardapio, treino, levantamento [[nome, carga, reps]], exame [[marcador, valor]],
  // pressao [sistolica, diastolica] ou null). Lanca Error quando as medidas sao inconsistentes.
  function calcular(e) {
    var perfil = D.PERFIS[e.perfil];
    var biotipo = D.BIOTIPOS[e.biotipo];
    var idade = ajusteIdade(e.idade);
    var protExtra = idade[0], fatorRitmo = idade[1];
    var avisos = [];
    var notas = [biotipo.nota, idade[2]];

    var gordura = e.gordura == null ? null : e.gordura;
    var origem = "informada";
    if (gordura === null && e.cintura != null && e.pescoco != null) {
      gordura = gorduraNavy(e.sexo, e.altura, e.cintura, e.pescoco, e.quadril == null ? null : e.quadril);
      origem = "estimada por fita (US Navy)";
      avisos.push("Gordura estimada por fita métrica: margem de erro de 3 a 4 pontos percentuais.");
    } else if (gordura === null) {
      origem = "não informada";
    }

    var tmb = calcularTmb(e.peso, e.altura, e.idade, e.sexo, gordura);
    var gasto = tmb * D.ATIVIDADE[e.atividade] * biotipo.gasto;

    var ajuste;
    var metrosAltura = e.altura / 100.0;
    var imc = e.peso / (metrosAltura * metrosAltura);
    var baixoPeso = e.objetivo === "secar" && imc < D.IMC_MINIMO_PARA_SECAR;
    if (baixoPeso) {
      ajuste = 0.0;
      avisos.push("IMC abaixo de 18,5: déficit não aplicado, plano na manutenção. " +
        "Procure médico ou nutricionista antes de tentar perder peso.");
    } else if (e.objetivo === "secar") ajuste = -e.peso * perfil.corte * fatorRitmo * D.KCAL_POR_KG / 7;
    else if (e.objetivo === "crescer") ajuste = e.peso * perfil.ganho * fatorRitmo * D.EXPERIENCIA[e.experiencia] * D.KCAL_POR_KG / 7;
    else ajuste = 0.0;

    var calorias = gasto + ajuste;
    var piso = e.sexo === "m" ? 1500.0 : 1200.0;
    if (calorias < piso) {
      avisos.push("Meta calculada (" + texto0(calorias) + " kcal) abaixo do piso seguro; fixada em " + texto0(piso) + " kcal.");
      calorias = piso;
      ajuste = calorias - gasto;
    }

    var pesoRef = gordura !== null
      ? Math.min(e.peso, e.peso * (1 - gordura / 100.0) / 0.80)
      : Math.min(e.peso, 25.0 * (metrosAltura * metrosAltura));

    var proteina = (perfil.prot[e.objetivo] + protExtra) * pesoRef;
    var gorduraG = Math.max(0.6, perfil.gord + biotipo.gord) * e.peso;
    var carbo = (calorias - proteina * 4 - gorduraG * 9) / 4;

    if (carbo < 50) {
      gorduraG = Math.max(0.6 * e.peso, (calorias - proteina * 4 - 50 * 4) / 9);
      carbo = (calorias - proteina * 4 - gorduraG * 9) / 4;
      avisos.push("Carboidrato muito baixo; gordura reduzida ao mínimo para abrir espaço.");
    }
    if (carbo < 50) {
      var proteinaMinima = D.PROTEINA_MINIMA * pesoRef;
      if (proteina > proteinaMinima) {
        proteina = Math.max(proteinaMinima, (calorias - gorduraG * 9 - 50 * 4) / 4);
        carbo = (calorias - proteina * 4 - gorduraG * 9) / 4;
        avisos.push("As calorias não comportam a proteína planejada: reduzida para " + texto0(proteina) +
          " g para manter algum carboidrato. Para comer mais, aumente a atividade.");
      }
    }
    if (carbo < 0) {
      carbo = 0.0;
      var minimo = proteina * 4 + gorduraG * 9;
      avisos.push("Proteína e gordura mínimas somam " + texto0(minimo) + " kcal, acima da meta de " + texto0(calorias) +
        "; plano recalculado para " + texto0(minimo) + " kcal. Para perder mais rápido, aumente a atividade.");
      calorias = minimo;
      ajuste = calorias - gasto;
    }

    var variacao = ajuste * 7 / D.KCAL_POR_KG;
    var semDeficit = e.objetivo === "secar" && variacao > -D.DEFICIT_MINIMO;
    if (semDeficit && !baixoPeso) {
      avisos.push("Plano sem déficit efetivo: as calorias mínimas já encostam no seu gasto. " +
        "Para secar, aumente o gasto com passos e cardio.");
    }
    var projecao = [];
    for (var s = 1; s <= e.semanas; s++) projecao.push({ semana: s, peso_kg: arred(e.peso + variacao * s, 1) });

    var n = e.refeicoes;
    var refeicoes = [];
    for (var i = 0; i < n; i++) {
      var prato = { refeicao: i + 1, proteina_g: arred(proteina / n), carbo_g: arred(carbo / n), gordura_g: arred(gorduraG / n) };
      prato.kcal = prato.proteina_g * 4 + prato.carbo_g * 4 + prato.gordura_g * 9;
      refeicoes.push(prato);
    }

    var meta = {};
    if (e.gordura_alvo != null) {
      if (e.objetivo !== "secar") {
        avisos.push("Gordura alvo só é usada com o objetivo secar; ignorada.");
      } else if (gordura === null) {
        avisos.push("Gordura alvo exige o percentual de gordura atual ou as medidas de cintura e pescoço; ignorada.");
      } else if (e.gordura_alvo >= gordura) {
        avisos.push("Gordura alvo maior ou igual à atual; nada a calcular.");
      } else if (e.gordura_alvo < (e.sexo === "m" ? 5 : 12)) {
        avisos.push("Gordura alvo abaixo da gordura essencial do corpo: meta não calculada.");
      } else if (!semDeficit) {
        meta = calcularMeta(e.peso, gordura, e.gordura_alvo, variacao, calorias, gasto);
        if (meta.semanas_total > D.META_MAX_SEMANAS) {
          avisos.push("No ritmo atual a gordura alvo levaria " + meta.semanas_total + " semanas: meta fora " +
            "de alcance com este plano. Aumente a atividade ou escolha um alvo intermediário.");
          meta = {};
        }
        if (e.gordura_alvo < (e.sexo === "m" ? 8 : 16)) {
          avisos.push("Gordura alvo muito baixa: sustentável só por pouco tempo e com acompanhamento.");
        }
      }
    }

    if (Object.keys(meta).length) {
      var ritmos = [];
      meta.fases.forEach(function (fase) {
        for (var k = 0; k < fase.semanas; k++) ritmos.push(fase.fase === "déficit" ? variacao : 0.0);
      });
      var atual = e.peso;
      projecao = [];
      for (var w = 1; w <= e.semanas; w++) {
        atual = Math.max(meta.peso_alvo_kg, atual + (w <= ritmos.length ? ritmos[w - 1] : 0.0));
        projecao.push({ semana: w, peso_kg: arred(atual, 1) });
      }
    }

    var pressao = e.pressao ? avaliarPressao(e.pressao[0], e.pressao[1]) : {};
    var exames = avaliarExames(e.exame || [], e.sexo, e.idade);
    var forca = analisarForca(e.levantamento || [], e.peso, e.sexo);
    var treino = {};
    if (e.treino) {
      treino = montarTreino(e.treinos_semana, e.experiencia, e.objetivo, e.perfil, e.idade, forca);
      if (!Object.keys(treino).length) avisos.push("Plano de treino exige ao menos 1 treino por semana; não gerado.");
    }

    if (e.perfil !== "natural") avisos.push("Retenção de água nas primeiras semanas mascara a balança: confie em cintura e fotos.");
    if (e.perfil === "hormonizado" && e.idade < 21) {
      avisos.push("Abaixo de 21 anos o risco para o eixo hormonal e crescimento é maior. Converse com um médico.");
    }
    if (e.objetivo === "secar" && gordura !== null && gordura < (e.sexo === "m" ? 10 : 18)) {
      avisos.push("Gordura já baixa: déficit agressivo custa massa magra e saúde hormonal.");
    }
    if (e.cintura != null && arred(e.cintura / e.altura, 2) > 0.5) {
      avisos.push("Cintura acima de metade da altura: risco cardiometabólico aumentado.");
    }
    if (pressao.nivel === 5) avisos.push("Pressão em nível de crise: procure atendimento agora e não treine pesado até ser avaliado.");
    else if (pressao.classe === "baixa") avisos.push("Pressão baixa: com tontura ou fraqueza, procure médico.");
    else if (pressao.nivel >= 3) avisos.push("Pressão em faixa de hipertensão: cortar cafeína e estimulantes e procurar médico.");
    else if (pressao.nivel === 2) avisos.push("Pressão no limite: reduzir sódio, manter cardio e repetir a medida em dias diferentes.");
    var fora = exames.filter(function (x) { return x.situacao !== "dentro" && x.situacao !== "sem faixa genérica"; })
      .map(function (x) { return x.marcador; });
    if (fora.length) {
      avisos.push("Exames fora da faixa (" + fora.join(", ") + "): leve o laudo ao médico. Não ajuste nada por conta própria.");
    }

    return {
      perfil: e.perfil, objetivo: e.objetivo, biotipo: e.biotipo, experiencia: e.experiencia,
      tmb: arred(tmb), gasto_total: arred(gasto), calorias: arred(calorias), ajuste_kcal: arred(ajuste),
      proteina_g: arred(proteina), carbo_g: arred(carbo), gordura_g: arred(gorduraG),
      agua_l: arred(Math.min(e.peso * 0.04, D.AGUA_MAXIMA_L), 1), fibra_g: arred(calorias / 1000 * 14),
      variacao_kg_semana: arred(variacao, 2),
      gordura_pct: gordura === null ? null : arred(gordura, 1), gordura_origem: origem,
      composicao: analisarComposicao(e.peso, e.altura, e.sexo, gordura, e.cintura == null ? null : e.cintura),
      ciclo_carbo: calcularCicloCarbo(carbo, calorias, e.treinos_semana, piso),
      meta: meta, refeicoes: refeicoes,
      cardapio: e.cardapio ? montarCardapio(refeicoes) : [],
      projecao: projecao, forca: forca, treino: treino, exames: exames, pressao: pressao,
      historico: {},
      suplementos: listarSuplementos(e.peso, pressao.nivel || 0),
      linha_do_tempo: D.LINHA_DO_TEMPO[e.perfil].map(function (par) { return { periodo: par[0], descricao: par[1] }; }),
      checklist: montarChecklist(e.perfil, e.sexo),
      notas: notas, avisos: avisos,
      // valores sem arredondar, usados pela analise do historico
      interno: { calorias: calorias, ajuste: ajuste, piso: piso, variacao: variacao, objetivo: baixoPeso ? "manter" : e.objetivo }
    };
  }

  return {
    DADOS: D, arred: arred, classificar: classificar, calcular: calcular,
    analisarHistorico: analisarHistorico, analisarForca: analisarForca, avaliarPressao: avaliarPressao,
    avaliarExames: avaliarExames, calcularCicloCarbo: calcularCicloCarbo, gorduraNavy: gorduraNavy
  };
});
