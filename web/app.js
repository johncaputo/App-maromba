// Interface do App Maromba. Os calculos ficam em calc.js; aqui so formulario, desenho e armazenamento.
(function () {
  "use strict";
  var C = window.MarombaCalc;
  var D = C.DADOS;
  var CHAVE = "app-maromba:v1";
  var SEMANAS = 12;
  var ABAS = ["dieta", "treino", "saude", "progresso", "dados"];

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (t) {
    return String(t).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var nf = function (x, casas) {
    return Number(x).toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: casas || 0 });
  };
  // numero com sinal e casas fixas, para ritmos lado a lado terem o mesmo formato
  var sinal = function (x, casas) {
    var v = C.arred(x, casas || 0);
    return (v < 0 ? "−" : v > 0 ? "+" : "") +
      Math.abs(v).toLocaleString("pt-BR", { minimumFractionDigits: casas || 0, maximumFractionDigits: casas || 0 });
  };
  var faixa = function (t) { return String(t).replace(/(\d)-(\d)/g, "$1–$2"); };
  var txt = function (t) { return esc(faixa(t)); };
  var clone = function (o) { return JSON.parse(JSON.stringify(o)); };
  var maiuscula = function (t) { return t.charAt(0).toUpperCase() + t.slice(1); };
  var isoLocal = function (d) {
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  };
  var hojeISO = function () { return isoLocal(new Date()); };
  var isoMenosDias = function (dias) { var d = new Date(); d.setDate(d.getDate() - dias); return isoLocal(d); };
  var dataBR = function (iso) { var p = iso.split("-"); return p[2] + "/" + p[1] + (p[0] !== hojeISO().slice(0, 4) ? "/" + p[0].slice(2) : ""); };
  var diasEntre = function (a, b) {
    var pa = a.split("-"), pb = b.split("-");
    return Math.round((Date.UTC(+pb[0], pb[1] - 1, +pb[2]) - Date.UTC(+pa[0], pa[1] - 1, +pa[2])) / 86400000);
  };
  var dataValida = function (iso) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(iso))) return false;
    var p = iso.split("-"), d = new Date(Date.UTC(+p[0], p[1] - 1, +p[2]));
    return d.getUTCFullYear() === +p[0] && d.getUTCMonth() === p[1] - 1 && d.getUTCDate() === +p[2];
  };

  var ROT = {
    exame: {
      hematocrito: "Hematócrito", hemoglobina: "Hemoglobina", hdl: "Colesterol HDL", ldl: "Colesterol LDL",
      triglicerides: "Triglicérides", colesterol_total: "Colesterol total", tgo: "TGO (AST)", tgp: "TGP (ALT)",
      ggt: "GGT", creatinina: "Creatinina", glicemia: "Glicemia em jejum", testosterona_total: "Testosterona total",
      estradiol: "Estradiol", lh: "LH", fsh: "FSH", prolactina: "Prolactina", psa: "PSA", tsh: "TSH"
    },
    levantamento: { supino: "Supino reto", agachamento: "Agachamento livre", terra: "Levantamento terra", desenvolvimento: "Desenvolvimento" },
    situacao: {
      "dentro": ["Dentro da faixa", "bom"], "abaixo": ["Abaixo da faixa", "atencao"], "acima": ["Acima da faixa", "atencao"],
      "acima (crítico)": ["Muito acima: urgente", "critico"], "sem faixa genérica": ["Use a faixa do laudo", ""]
    },
    pressao: ["bom", "bom", "atencao", "serio", "critico", "critico"]
  };

  var CAMPOS = {
    peso: { min: 35, max: 250, obrig: true, nome: "Peso", un: "kg" },
    altura: { min: 130, max: 230, obrig: true, nome: "Altura", un: "cm" },
    idade: { min: 18, max: 90, obrig: true, inteiro: true, nome: "Idade", un: "anos" },
    gordura: { min: 3, max: 60, nome: "Gordura", un: "%" },
    cintura: { min: 40, max: 200, nome: "Cintura", un: "cm" },
    pescoco: { min: 20, max: 70, nome: "Pescoço", un: "cm" },
    quadril: { min: 50, max: 200, nome: "Quadril", un: "cm" },
    gordura_alvo: { min: 4, max: 50, nome: "Gordura alvo", un: "%" }
  };
  var ESCOLHAS = {
    sexo: ["m", "f"], biotipo: Object.keys(D.BIOTIPOS), objetivo: ["secar", "manter", "crescer"],
    perfil: Object.keys(D.PERFIS), experiencia: Object.keys(D.EXPERIENCIA), atividade: Object.keys(D.ATIVIDADE)
  };
  var PASSOS = { treinos_semana: [0, 7], refeicoes: [2, 8] };

  var EXEMPLO = {
    peso: 85, altura: 178, idade: 28, sexo: "m", gordura: null, cintura: 88, pescoco: 39, quadril: null,
    biotipo: "mesomorfo", objetivo: "secar", perfil: "natural", experiencia: "intermediario", atividade: "moderado",
    treinos_semana: 5, gordura_alvo: 12, refeicoes: 4,
    levantamento: [["supino", 100, 5], ["agachamento", 140, 5]], exame: [], pressao: null
  };
  var estadoExemplo = function () {
    return {
      entrada: clone(EXEMPLO), exemplo: true, atualizado: 0,
      historico: [[21, 86.6], [14, 86.0], [7, 85.6], [0, 85.0]].map(function (p) { return { data: isoMenosDias(p[0]), peso: p[1] }; })
    };
  };

  var estado = estadoExemplo();
  var resultado = null;
  var editouNestaVisita = false;
  var invalidos = {};
  var remoto = { doc: null, ocupado: false, pendente: false, ok: false, relogio: null };

  // ---------- armazenamento ----------
  function numeroEm(v, min, max, inteiro) {
    if (typeof v !== "number" || !isFinite(v) || v < min || v > max) return undefined;
    if (inteiro && Math.round(v) !== v) return undefined;
    return v;
  }

  // Tudo que vem do armazenamento e conferido de novo: nada entra no estado sem passar pelos mesmos limites do formulario.
  function normalizar(bruto) {
    if (!bruto || typeof bruto !== "object" || !bruto.entrada || typeof bruto.entrada !== "object") return null;
    var e = bruto.entrada, s = clone(EXEMPLO);
    s.levantamento = []; s.exame = []; s.pressao = null;
    var ok = true;
    Object.keys(CAMPOS).forEach(function (id) {
      var c = CAMPOS[id], v = numeroEm(e[id], c.min, c.max, c.inteiro);
      if (v === undefined) { if (c.obrig) ok = false; s[id] = c.obrig ? s[id] : null; } else s[id] = v;
    });
    if (!ok) return null;
    Object.keys(ESCOLHAS).forEach(function (id) { if (ESCOLHAS[id].indexOf(e[id]) >= 0) s[id] = e[id]; });
    Object.keys(PASSOS).forEach(function (id) {
      var v = numeroEm(e[id], PASSOS[id][0], PASSOS[id][1], true);
      if (v !== undefined) s[id] = v;
    });
    if (Array.isArray(e.levantamento)) {
      e.levantamento.slice(0, 12).forEach(function (l) {
        if (!Array.isArray(l) || typeof l[0] !== "string") return;
        var nome = l[0].trim().toLowerCase().slice(0, 40);
        var carga = numeroEm(l[1], 1, 600), reps = numeroEm(l[2], 1, 15, true);
        if (nome && carga !== undefined && reps !== undefined) s.levantamento.push([nome, carga, reps]);
      });
    }
    if (Array.isArray(e.exame)) {
      e.exame.slice(0, 30).forEach(function (x) {
        if (!Array.isArray(x) || !Object.prototype.hasOwnProperty.call(D.EXAMES, x[0])) return;
        var v = numeroEm(x[1], 0, 100000);
        if (v !== undefined) s.exame.push([x[0], v]);
      });
    }
    if (Array.isArray(e.pressao)) {
      var sis = numeroEm(e.pressao[0], 60, 260, true), dia = numeroEm(e.pressao[1], 30, 160, true);
      if (sis !== undefined && dia !== undefined && sis > dia) s.pressao = [sis, dia];
    }
    var historico = [], hoje = hojeISO(), vistos = {};
    if (Array.isArray(bruto.historico)) {
      bruto.historico.slice(0, 400).forEach(function (h) {
        if (!h || !dataValida(h.data) || h.data > hoje || vistos[h.data]) return;
        var p = numeroEm(h.peso, 35, 250);
        if (p !== undefined) { vistos[h.data] = true; historico.push({ data: h.data, peso: p }); }
      });
    }
    return { entrada: s, historico: historico, exemplo: false, atualizado: numeroEm(bruto.atualizado, 0, 1e15) || 0 };
  }

  function paraSalvar() { return { entrada: clone(estado.entrada), historico: clone(estado.historico), atualizado: estado.atualizado }; }
  function lerLocal() { try { return normalizar(JSON.parse(localStorage.getItem(CHAVE))); } catch (erro) { return null; } }
  function gravarLocal() { try { localStorage.setItem(CHAVE, JSON.stringify(paraSalvar())); return true; } catch (erro) { return false; } }
  function apagarLocal() { try { localStorage.removeItem(CHAVE); } catch (erro) { /* sem armazenamento */ } }

  function statusSalvo(okLocal) {
    var alvo = $("#status-salvo");
    if (estado.exemplo) alvo.textContent = "Exemplo: nada é salvo até você alterar um campo.";
    else if (remoto.ok) alvo.textContent = "Dados salvos na sua conta e neste aparelho.";
    else if (okLocal) alvo.textContent = "Dados salvos neste aparelho.";
    else alvo.textContent = "Não foi possível salvar neste aparelho: os dados valem só enquanto a página estiver aberta.";
  }

  function enviarRemoto() {
    if (!remoto.doc || estado.exemplo) return;
    if (remoto.ocupado) { remoto.pendente = true; return; }
    remoto.ocupado = true;
    remoto.doc.set(paraSalvar()).then(function () { remoto.ok = true; }, function () { remoto.ok = false; remoto.doc = null; })
      .then(function () {
        remoto.ocupado = false;
        statusSalvo(true);
        if (remoto.pendente) { remoto.pendente = false; enviarRemoto(); }
      });
  }

  function salvar() {
    if (estado.exemplo) { statusSalvo(true); return; }
    estado.atualizado = Date.now();
    statusSalvo(gravarLocal());
    clearTimeout(remoto.relogio);
    remoto.relogio = setTimeout(enviarRemoto, 1500);
  }

  function comPrazo(promessa, ms) {
    return new Promise(function (resolver, rejeitar) {
      var relogio = setTimeout(function () { rejeitar(new Error("prazo")); }, ms);
      promessa.then(function (v) { clearTimeout(relogio); resolver(v); }, function (e) { clearTimeout(relogio); rejeitar(e); });
    });
  }

  // Dentro do Claude, os dados tambem ficam na area privada de quem esta vendo; fora dele, so no aparelho.
  function abrirRemoto() {
    if (!window.claude || typeof window.claude.use !== "function") return;
    Promise.all([window.claude.use("db"), window.claude.use("user")]).then(function (caps) {
      if (!caps[0] || !caps[1]) return null;
      return caps[1].id().then(function (id) {
        if (!id) return null;
        remoto.doc = caps[0].doc("data/users/" + id + "/app-maromba");
        return comPrazo(remoto.doc.get(), 10000);
      });
    }).then(function (snap) {
      if (!snap) return;
      var salvo = snap.exists ? normalizar(snap.data()) : null;
      remoto.ok = true;
      if (salvo && salvo.atualizado > estado.atualizado && !editouNestaVisita) {
        estado = salvo;
        gravarLocal();
        preencherFormulario();
        atualizar();
      } else if (!estado.exemplo && (!salvo || estado.atualizado > salvo.atualizado)) {
        enviarRemoto();
      }
      statusSalvo(true);
    }).catch(function () { remoto.doc = null; remoto.ok = false; });
  }

  // ---------- formulario ----------
  function lerNumero(texto) {
    var t = String(texto).trim().replace(",", ".");
    if (t === "") return null;
    return /^\d+(\.\d+)?$/.test(t) ? Number(t) : NaN;
  }
  var paraCampo = function (v) { return v == null ? "" : String(v).replace(".", ","); };

  function marcarErro(entrada, alvoErro, mensagem) {
    if (entrada) entrada.setAttribute("aria-invalid", mensagem ? "true" : "false");
    alvoErro.textContent = mensagem || "";
    alvoErro.hidden = !mensagem;
  }

  function validarCampo(id) {
    var c = CAMPOS[id], entrada = $("#f-" + id), v = lerNumero(entrada.value), msg = "";
    if (v === null) { if (c.obrig) msg = c.nome + " é obrigatório."; }
    else if (isNaN(v) || v < c.min || v > c.max || (c.inteiro && Math.round(v) !== v)) {
      msg = id === "idade" && v < 18 ? "O app é para maiores de 18 anos." : c.nome + " entre " + c.min + " e " + c.max + " " + c.un + ".";
    }
    marcarErro(entrada, $("#e-" + id), msg);
    if (msg) { invalidos[id] = true; return; }
    delete invalidos[id];
    estado.entrada[id] = v;
  }

  function preencherFormulario() {
    var e = estado.entrada;
    Object.keys(CAMPOS).forEach(function (id) {
      $("#f-" + id).value = paraCampo(e[id]);
      marcarErro($("#f-" + id), $("#e-" + id), "");
    });
    invalidos = {};
    ["sexo", "biotipo", "objetivo", "experiencia"].forEach(function (nome) {
      $$('input[name="' + nome + '"]').forEach(function (r) { r.checked = r.value === e[nome]; });
    });
    $("#f-perfil").value = e.perfil;
    $("#f-atividade").value = e.atividade;
    Object.keys(PASSOS).forEach(function (id) { $("#f-" + id).textContent = e[id]; });
    $("#p-sis").value = e.pressao ? e.pressao[0] : "";
    $("#p-dia").value = e.pressao ? e.pressao[1] : "";
    $("#h-data").value = hojeISO();
    $("#h-data").max = hojeISO();
    $("#h-peso").value = paraCampo(e.peso);
  }

  function sairDoExemplo() {
    editouNestaVisita = true;
    if (!estado.exemplo) return;
    estado.exemplo = false;
    estado.entrada.levantamento = [];
    estado.historico = [];
  }

  function mudou() { atualizar(); salvar(); }

  // ---------- desenho ----------
  var par = function (rotulo, valor) { return "<dt>" + esc(rotulo) + "</dt><dd>" + valor + "</dd>"; };
  var lista = function (itens) { return '<ul class="lista">' + itens.map(function (i) { return "<li>" + txt(i) + "</li>"; }).join("") + "</ul>"; };
  var marcaExemplo = function () { return estado.exemplo ? ' <span class="marca">exemplo</span>' : ""; };

  function placas(carga) {
    var lado = (carga - 20) / 2;
    if (lado <= 0) return "";
    var html = "";
    [25, 20, 15, 10, 5, 2.5, 1.25].forEach(function (p) {
      while (lado >= p - 1e-9) {
        html += '<i class="' + (p >= 10 ? "p" + p : p === 5 ? "p5" : "pp") + '">' + nf(p, 2) + "</i>";
        lado -= p;
      }
    });
    return '<span class="placas" title="Barra de 20 kg mais estas anilhas de cada lado"><i class="barra"></i>' + html + "</span>";
  }

  function renderResumo(r) {
    var partes = [["Proteína", r.proteina_g, r.proteina_g * 4, "s1"], ["Carboidrato", r.carbo_g, r.carbo_g * 4, "s2"], ["Gordura", r.gordura_g, r.gordura_g * 9, "s3"]];
    var total = partes.reduce(function (s, p) { return s + p[2]; }, 0) || 1;
    var barra = "", legenda = "", descricao = [];
    partes.forEach(function (p) {
      var pct = Math.round(p[2] / total * 100);
      descricao.push(p[0].toLowerCase() + " " + pct + "%");
      if (p[2] > 0) barra += '<span class="seg ' + p[3] + '" style="flex:' + p[2] + ' 1 0">' + (pct >= 12 ? pct + "%" : "") + "</span>";
      legenda += '<li><i class="sw ' + p[3] + '"></i><span>' + p[0] + "</span><b>" + nf(p[1]) + " g</b></li>";
    });
    var gasto = r.ajuste_kcal < 0 ? nf(-r.ajuste_kcal) + " kcal abaixo do gasto" : r.ajuste_kcal > 0 ? nf(r.ajuste_kcal) + " kcal acima do gasto" : "igual ao gasto diário";
    var ritmo = r.variacao_kg_semana ? "ritmo esperado de " + sinal(r.variacao_kg_semana, 2) + " kg por semana" : "peso estável";
    $("#resumo").innerHTML =
      '<p class="rotulo">Meta diária</p>' +
      '<p class="heroi">' + nf(r.calorias) + ' <span class="un">kcal</span></p>' +
      '<p class="sub">' + maiuscula(gasto) + " · " + ritmo + "</p>" +
      '<div class="macrobar" role="img" aria-label="Divisão das calorias: ' + esc(descricao.join(", ")) + '">' + barra + "</div>" +
      '<ul class="legenda">' + legenda + "</ul>";
  }

  function renderAvisos(r) {
    var alvo = $("#avisos"), avisos = r.avisos.slice();
    if (Object.keys(invalidos).length) avisos.unshift("Há campos inválidos em Dados: o plano usa o último valor válido de cada um.");
    alvo.hidden = !avisos.length;
    var critico = r.pressao.nivel === 5 || r.exames.some(function (x) { return x.situacao === "acima (crítico)"; });
    alvo.className = "callout" + (critico ? " critico" : "");
    alvo.innerHTML = "<h3>Atenção</h3><ul>" + avisos.map(function (a) {
      // o motor lista os exames pela chave interna; aqui entram os nomes que a pessoa ve
      var legivel = a.replace(/^(Exames fora da faixa \()([^)]*)(\))/, function (tudo, antes, chaves, depois) {
        return antes + chaves.split(", ").map(function (k) { return ROT.exame[k] || k; }).join(", ") + depois;
      });
      return "<li>" + txt(legivel) + "</li>";
    }).join("") + "</ul>";
  }

  function renderDieta(r) {
    var h = "<h2>Energia</h2><div class='bloco'><dl class='pares'>" +
      par("Taxa metabólica basal", nf(r.tmb) + " kcal") + par("Gasto total diário", nf(r.gasto_total) + " kcal") +
      par("Meta diária", nf(r.calorias) + " kcal") + par("Água", nf(r.agua_l, 1) + " L por dia") +
      par("Fibra", nf(r.fibra_g) + " g por dia") + "</dl></div>";

    if (r.ciclo_carbo.treinos_semana) {
      var c = r.ciclo_carbo;
      h += "<h2>Dia de treino e dia de descanso</h2><div class='duas'>" +
        "<div class='bloco tile'><p class='rotulo'>Dia de treino</p><p class='valor'>" + nf(c.carbo_treino_g) + " <small>g de carbo</small></p><p class='sub num'>" + nf(c.kcal_treino) + " kcal</p></div>" +
        "<div class='bloco tile'><p class='rotulo'>Dia de descanso</p><p class='valor'>" + nf(c.carbo_descanso_g) + " <small>g de carbo</small></p><p class='sub num'>" + nf(c.kcal_descanso) + " kcal</p></div>" +
        "</div><p class='sub' style='margin-top:8px'>Proteína e gordura não mudam. A média da semana continua na meta.</p>";
    }

    h += "<h2>Refeições</h2><p class='sub'>Cardápio exemplo, com o peso do alimento pronto. Troque por equivalentes mantendo os macros.</p><div class='pilha' style='margin-top:12px'>";
    r.refeicoes.forEach(function (alvo, i) {
      var prato = r.cardapio[i];
      h += "<div class='bloco'><div class='cab'><h3>Refeição " + alvo.refeicao + "</h3><span class='dir'>" + nf(alvo.kcal) + " kcal · P " +
        alvo.proteina_g + " · C " + alvo.carbo_g + " · G " + alvo.gordura_g + "</span></div>";
      if (prato) {
        h += "<ul class='itens'>" + prato.itens.map(function (it) { return "<li><span>" + esc(it.alimento) + "</span><span>" + nf(it.gramas) + " g</span></li>"; }).join("") + "</ul>";
        if (prato.aproximado) h += "<p class='sub' style='margin-top:6px'>Aproximado: estes alimentos não fecham exatamente os macros da refeição.</p>";
      }
      h += "</div>";
    });
    h += "</div>";

    if (r.meta.fases) {
      var m = r.meta;
      h += "<h2>Meta: " + nf(m.gordura_alvo_pct, 1) + "% de gordura</h2><div class='bloco'><dl class='pares'>" +
        par("Peso alvo", nf(m.peso_alvo_kg, 1) + " kg") + par("A perder, mantendo a massa magra", nf(m.perder_kg, 1) + " kg") +
        par("Tempo estimado", m.semanas_total + " semanas") + "</dl>" +
        "<div class='fases' role='img' aria-label='" + m.semanas_deficit + " semanas de déficit e " + m.semanas_pausa + " de pausa'>" +
        m.fases.map(function (f) { return "<span class='" + (f.fase === "déficit" ? "" : "pausa") + "' style='flex:" + f.semanas + " 1 0'></span>"; }).join("") + "</div>" +
        "<ul class='legenda'><li><i class='sw s1'></i><span>Déficit</span><b>" + m.semanas_deficit + " sem a " + nf(r.calorias) + " kcal</b></li>" +
        (m.semanas_pausa ? "<li><i class='sw soft'></i><span>Pausa na manutenção</span><b>" + m.semanas_pausa + " sem a " + nf(r.gasto_total) + " kcal</b></li>" : "") +
        "</ul><p class='sub' style='margin-top:8px'>A cada 8 semanas de déficit, 1 semana comendo o gasto diário para recuperar.</p></div>";
    }

    h += "<h2>Projeção de peso em " + SEMANAS + " semanas</h2><div class='bloco'><div class='grafico' id='g-projecao'></div>" +
      "<details class='tabela'><summary>Ver em tabela</summary><table><tr><th>Semana</th><th>Peso</th></tr>" +
      r.projecao.map(function (p) { return "<tr><td>" + p.semana + "</td><td>" + nf(p.peso_kg, 1) + " kg</td></tr>"; }).join("") + "</table></details></div>";

    h += "<h2>Suplementos com evidência</h2>" + lista(r.suplementos);
    h += "<h2>Notas</h2>" + lista(r.notas.concat(["Recalcule a cada 4 kg de mudança ou quando o peso travar por 2 semanas."]));
    $("#aba-dieta").innerHTML = h;
  }

  function renderTreino(r) {
    var t = r.treino, h = "";
    if (!t.sessoes) {
      h = "<p class='vazio'>Sem treinos na semana. Aumente “Treinos por semana” em Dados para gerar o plano.</p>";
    } else {
      h += "<h2>Plano da semana</h2><p class='sub'>" + t.dias_semana + (t.dias_semana === 1 ? " dia" : " dias") + ". Séries × repetições, com o descanso entre séries.</p><div class='pilha' style='margin-top:12px'>";
      t.sessoes.forEach(function (s) {
        h += "<details class='bloco sessao' open><summary><span class='dia'>" + esc(s.dia.toUpperCase()) + "</span><h3>" + txt(s.treino) + "</h3></summary>";
        if (s.exercicios.length) {
          h += "<ul class='exs'>" + s.exercicios.map(function (e) {
            var carga = e.carga_sugerida_kg ? "<span>carga ~" + nf(e.carga_sugerida_kg, 1) + " kg</span>" + placas(e.carga_sugerida_kg) : "";
            return "<li><div class='ex-linha'><b>" + esc(e.exercicio) + "</b><span>" + e.series + " × " + txt(e.reps) + "</span></div>" +
              "<div class='ex-sub'><span>descanso " + txt(e.descanso) + "</span>" + carga + "</div></li>";
          }).join("") + "</ul>";
        }
        h += "</details>";
      });
      h += "</div>";

      var grupos = Object.keys(t.volume_semanal);
      var teto = Math.max(24, Math.max.apply(null, grupos.map(function (g) { return t.volume_semanal[g].series; })));
      h += "<h2>Volume semanal</h2><p class='sub'>Séries diretas por grupo muscular. A faixa marcada, de 10 a 20, é a ideal para ganhar músculo.</p><div class='bloco volume' style='margin-top:12px'>";
      grupos.forEach(function (g) {
        var v = t.volume_semanal[g];
        h += "<div class='vol'><span>" + esc(maiuscula(g)) + "</span><div class='trilho'><i class='ideal' style='left:" + (10 / teto * 100) + "%;width:" + (10 / teto * 100) + "%'></i>" +
          "<i class='barra' style='width:" + (v.series / teto * 100) + "%'></i></div><span class='val'>" + v.series + " <small>" + esc(v.classe) + "</small></span></div>";
      });
      h += "</div><p class='sub' style='margin-top:8px'>Conta só o trabalho direto: supino e remada também treinam tríceps e bíceps.</p>";

      h += "<h2>Como executar</h2><div class='bloco pilha'>" +
        [["Aquecimento", t.aquecimento], ["Progressão", t.progressao], ["Intensidade", t.intensidade], ["Semana leve", t.semana_leve], ["Cardio", t.cardio]]
          .map(function (p) { return "<p><b>" + p[0] + ".</b> " + txt(p[1]) + "</p>"; }).join("") + "</div>";
      if (t.notas.length) h += "<div style='margin-top:12px'>" + lista(t.notas) + "</div>";
    }
    $("#treino-plano").innerHTML = h;

    var c = "";
    r.forca.forEach(function (f, i) {
      var nome = ROT.levantamento[f.exercicio] || maiuscula(f.exercicio);
      c += "<div class='bloco'><div class='cab'><h3>" + esc(nome) + marcaExemplo() + "</h3><span class='dir'>" + nf(f.carga_kg, 2) + " kg × " + f.reps + "</span></div>" +
        "<p style='margin-top:6px'>Carga máxima estimada (1RM): <b>" + nf(f.rm_estimado_kg, 1) + " kg</b>, " + nf(f.relativo, 2) + "× o peso corporal.</p>";
      if (f.nivel) {
        c += "<div class='escala' role='img' aria-label='Nível: " + esc(f.nivel) + "'>" + D.NIVEIS_FORCA.map(function (n) {
          return "<span class='" + (n === f.nivel ? "ativo" : "") + "'>" + esc(n) + "</span>";
        }).join("") + "</div>";
      }
      c += "<div class='cargas'>" + Object.keys(f.cargas_treino).map(function (k) {
        return "<div><small>" + k + "</small><b>" + nf(f.cargas_treino[k], 1) + "</b></div>";
      }).join("") + "</div><p class='sub' style='margin-top:6px'>Cargas em kg para cada percentual do 1RM.</p>" +
        "<div class='acoes' style='margin-top:10px'><button type='button' class='botao mini' data-acao='rm-carga' data-i='" + i + "'>Remover</button></div></div>";
    });
    $("#treino-cargas").innerHTML = c || "<p class='vazio'>Nenhuma carga informada ainda.</p>";
  }

  function renderSaude(r) {
    var p = r.pressao, hp;
    if (p.classe) {
      var classe = p.classe === "baixa" ? "atencao" : ROT.pressao[p.nivel];
      hp = "<p><span class='pill " + classe + "'>" + esc(maiuscula(p.classe)) + "</span> <span class='num'>" + p.sistolica + " por " + p.diastolica + " mmHg</span></p>" +
        "<div class='escala' role='img' aria-label='Classificação: " + esc(p.classe) + "'>" + D.PRESSAO_ROTULOS.map(function (rot, i) {
          return "<span class='" + (i === p.nivel && p.classe !== "baixa" ? "ativo" : "") + "'>" + esc(rot.replace("pré-hipertensão", "limite").replace("hipertensão ", "")) + "</span>";
        }).join("") + "</div>";
    } else {
      hp = "<p class='sub'>Informe as duas medidas para ver a classificação. Meça sentado, depois de 5 minutos de descanso.</p>";
    }
    $("#saude-pressao").innerHTML = hp;

    var hx = "";
    r.exames.forEach(function (x, i) {
      var s = ROT.situacao[x.situacao] || [x.situacao, ""];
      hx += "<div class='bloco'><div class='cab'><h3>" + esc(ROT.exame[x.marcador] || x.marcador) + "</h3><span class='pill " + s[1] + "'>" + esc(s[0]) + "</span></div>" +
        "<p style='margin-top:6px' class='num'><b>" + nf(x.valor, 2) + " " + esc(x.unidade) + "</b> <span class='sub'>· referência " + txt(x.referencia.replace(">=", "a partir de").replace("<=", "até")) + "</span></p>" +
        (x.nota ? "<p style='margin-top:4px'>" + txt(x.nota) + "</p>" : "") +
        "<div class='acoes' style='margin-top:10px'><button type='button' class='botao mini' data-acao='rm-exame' data-i='" + i + "'>Remover</button></div></div>";
    });
    $("#saude-exames").innerHTML = hx || "<p class='vazio'>Nenhum exame informado ainda.</p>";

    $("#saude-texto").innerHTML =
      "<h2>O que esperar em 12 semanas</h2><ol class='linha-tempo'>" + r.linha_do_tempo.map(function (e) {
        return "<li><b>" + txt(e.periodo) + "</b>" + txt(e.descricao) + "</li>";
      }).join("") + "</ol><h2>Checklist de controle</h2>" + lista(r.checklist);
  }

  function seriePeso() {
    return estado.historico.slice().sort(function (a, b) { return a.data < b.data ? -1 : 1; });
  }

  function renderProgresso(r) {
    var serie = seriePeso(), h = "";
    if (!serie.length) {
      h = "<p class='vazio'>Nenhum peso registrado. Registre hoje e volte toda semana, no mesmo horário: com 14 dias o app compara o seu ritmo real com o esperado.</p>";
    } else {
      var a = C.analisarHistorico(serie.map(function (s) { return [s.data, s.peso]; }), r.interno.objetivo, r.interno.variacao, r.interno.calorias, r.interno.ajuste, r.interno.piso);
      h += "<h2>Seu ritmo" + marcaExemplo() + "</h2><div class='duas'>" +
        "<div class='bloco tile'><p class='rotulo'>Ritmo real</p><p class='valor'>" + (a.ritmo_real_kg_semana === undefined ? "—" : sinal(a.ritmo_real_kg_semana, 2)) + " <small>kg/sem</small></p>" +
        "<p class='sub'>" + (a.dias_analisados === undefined ? "falta registro" : "em " + a.dias_analisados + " dias") + "</p></div>" +
        "<div class='bloco tile'><p class='rotulo'>Ritmo esperado</p><p class='valor'>" + sinal(a.ritmo_esperado_kg_semana, 2) + " <small>kg/sem</small></p><p class='sub'>pelo plano atual</p></div></div>" +
        "<p style='margin-top:10px'><b>" + txt(a.recomendacao) + "</b></p>";
      if (serie.length > 1) {
        h += "<div class='bloco' style='margin-top:12px'><ul class='legenda' style='margin-top:0'><li><i class='sw linha s1'></i><span>Peso registrado</span></li><li><i class='sw linha ref'></i><span>Ritmo esperado</span></li></ul>" +
          "<div class='grafico' id='g-historico'></div></div>";
      }
      h += "<h2>Registros</h2><div class='bloco'>" + serie.slice().reverse().map(function (s) {
        return "<div class='reg'><div class='txt'><b class='num'>" + nf(s.peso, 1) + " kg</b><small>" + dataBR(s.data) + "</small></div>" +
          "<button type='button' class='botao mini' data-acao='rm-peso' data-data='" + s.data + "'>Remover</button></div>";
      }).join("") + "</div>";
    }
    $("#progresso-saida").innerHTML = h;
  }

  // ---------- graficos ----------
  function ticksLimpos(min, max, n) {
    var bruto = (max - min) / n, pot = Math.pow(10, Math.floor(Math.log10(bruto))), f = bruto / pot;
    var passo = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * pot;
    var ticks = [];
    for (var v = Math.floor(min / passo) * passo; v < max + passo; v += passo) ticks.push(Number(v.toFixed(6)));
    return ticks;
  }

  // cfg: { series: [{nome, ref, pontos: [{x, y}]}], rotulosX: [{x, texto}], fmtX(x), descricao }
  // A primeira serie e a principal: ganha area, ponto final com rotulo e conduz a mira.
  function graficoLinha(alvo, cfg) {
    if (!alvo || !alvo.clientWidth) return;
    var L = alvo.clientWidth, A = 210, m = { e: 46, d: 66, t: 16, b: 28 };
    var xs = [], ys = [];
    cfg.series.forEach(function (s) { s.pontos.forEach(function (p) { xs.push(p.x); ys.push(p.y); }); });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    if (x0 === x1) x1 = x0 + 1;
    var ymin = Math.min.apply(null, ys), ymax = Math.max.apply(null, ys);
    if (ymax - ymin < 1) { ymin -= 0.5; ymax += 0.5; }
    var ticks = ticksLimpos(ymin, ymax, 4), y0 = ticks[0], y1 = ticks[ticks.length - 1];
    var px = function (x) { return m.e + (x - x0) / (x1 - x0) * (L - m.e - m.d); };
    var py = function (y) { return m.t + (1 - (y - y0) / (y1 - y0)) * (A - m.t - m.b); };
    var caminho = function (pontos) { return pontos.map(function (p, i) { return (i ? "L" : "M") + px(p.x).toFixed(1) + " " + py(p.y).toFixed(1); }).join(" "); };
    var casas = ticks.some(function (t) { return t % 1 !== 0; }) ? 1 : 0;

    var s = '<svg viewBox="0 0 ' + L + " " + A + '" height="' + A + '" role="img" aria-label="' + esc(cfg.descricao) + '">';
    ticks.forEach(function (t, i) {
      s += '<line class="' + (i ? "grade" : "base") + '" x1="' + m.e + '" x2="' + (L - m.d) + '" y1="' + py(t) + '" y2="' + py(t) + '"/>' +
        '<text x="' + (m.e - 8) + '" y="' + (py(t) + 4) + '" text-anchor="end">' + nf(t, casas) + "</text>";
    });
    cfg.rotulosX.forEach(function (rx, i) {
      var ancora = i === 0 ? "start" : i === cfg.rotulosX.length - 1 ? "end" : "middle";
      s += '<text x="' + px(rx.x) + '" y="' + (A - 8) + '" text-anchor="' + ancora + '">' + esc(rx.texto) + "</text>";
    });
    var principal = cfg.series[0].pontos, fim = principal[principal.length - 1];
    s += '<path class="a1" d="' + caminho(principal) + " L" + px(fim.x).toFixed(1) + " " + py(y0) + " L" + px(principal[0].x).toFixed(1) + " " + py(y0) + ' Z"/>';
    cfg.series.slice(1).forEach(function (serie) { s += '<path class="lref" d="' + caminho(serie.pontos) + '"/>'; });
    s += '<path class="l1" d="' + caminho(principal) + '"/>';
    s += '<line class="mira" y1="' + m.t + '" y2="' + (A - m.b) + '" visibility="hidden"/>' +
      '<circle class="p1" cx="' + px(fim.x) + '" cy="' + py(fim.y) + '" r="5"/>' +
      '<text class="fim" x="' + (px(fim.x) + 10) + '" y="' + (py(fim.y) + 4) + '">' + nf(fim.y, 1) + " kg</text>" +
      '<circle class="p1 foco" r="5" visibility="hidden"/></svg><div class="dica" hidden></div>';
    alvo.innerHTML = s;

    var svg = $("svg", alvo), mira = $(".mira", alvo), foco = $(".foco", alvo), dica = $(".dica", alvo);
    function mover(ev) {
      var caixa = svg.getBoundingClientRect(), alvoX = (ev.clientX - caixa.left) * (L / caixa.width), perto = principal[0];
      principal.forEach(function (p) { if (Math.abs(px(p.x) - alvoX) < Math.abs(px(perto.x) - alvoX)) perto = p; });
      mira.setAttribute("x1", px(perto.x)); mira.setAttribute("x2", px(perto.x)); mira.setAttribute("visibility", "visible");
      foco.setAttribute("cx", px(perto.x)); foco.setAttribute("cy", py(perto.y)); foco.setAttribute("visibility", "visible");
      dica.textContent = "";
      var titulo = document.createElement("div");
      titulo.textContent = cfg.fmtX(perto.x);
      dica.appendChild(titulo);
      cfg.series.forEach(function (serie) {
        var ponto = serie.pontos.filter(function (p) { return p.x === perto.x; })[0];
        if (!ponto) return;
        var linha = document.createElement("div"), chave = document.createElement("span"), valor = document.createElement("b");
        chave.className = "k" + (serie.ref ? " ref" : "");
        valor.textContent = nf(ponto.y, 1) + " kg";
        linha.appendChild(chave); linha.appendChild(valor);
        linha.appendChild(document.createTextNode(" " + serie.nome));
        dica.appendChild(linha);
      });
      dica.hidden = false;
      var esquerda = px(perto.x) * (caixa.width / L) - dica.offsetWidth / 2;
      dica.style.left = Math.max(0, Math.min(caixa.width - dica.offsetWidth, esquerda)) + "px";
    }
    function sair() { mira.setAttribute("visibility", "hidden"); foco.setAttribute("visibility", "hidden"); dica.hidden = true; }
    svg.addEventListener("pointermove", mover);
    svg.addEventListener("pointerdown", mover);
    svg.addEventListener("pointerleave", sair);
  }

  function desenharGraficos() {
    if (!resultado) return;
    var r = resultado;
    var projecao = [{ x: 0, y: estado.entrada.peso }].concat(r.projecao.map(function (p) { return { x: p.semana, y: p.peso_kg }; }));
    graficoLinha($("#g-projecao"), {
      series: [{ nome: "peso projetado", pontos: projecao }],
      rotulosX: [{ x: 0, texto: "hoje" }, { x: SEMANAS / 2, texto: "semana " + SEMANAS / 2 }, { x: SEMANAS, texto: "semana " + SEMANAS }],
      fmtX: function (x) { return x === 0 ? "Hoje" : "Semana " + x; },
      descricao: "Peso projetado de " + nf(estado.entrada.peso, 1) + " kg hoje a " + nf(projecao[projecao.length - 1].y, 1) + " kg na semana " + SEMANAS
    });

    var serie = seriePeso();
    if (serie.length > 1 && $("#g-historico")) {
      var inicio = serie[0].data, datas = {};
      var reais = serie.map(function (s) { var x = diasEntre(inicio, s.data); datas[x] = s.data; return { x: x, y: s.peso }; });
      var esperados = reais.map(function (p) { return { x: p.x, y: C.arred(serie[0].peso + r.interno.variacao * p.x / 7, 1) }; });
      var ultimo = reais[reais.length - 1];
      graficoLinha($("#g-historico"), {
        series: [{ nome: "registrado", pontos: reais }, { nome: "esperado", ref: true, pontos: esperados }],
        rotulosX: [{ x: 0, texto: dataBR(inicio) }, { x: ultimo.x, texto: dataBR(serie[serie.length - 1].data) }],
        fmtX: function (x) { return dataBR(datas[x]); },
        descricao: "Peso registrado de " + nf(reais[0].y, 1) + " kg a " + nf(ultimo.y, 1) + " kg em " + ultimo.x + " dias"
      });
    }
  }

  // ---------- ciclo principal ----------
  function atualizar() {
    var entrada = clone(estado.entrada);
    entrada.semanas = SEMANAS; entrada.cardapio = true; entrada.treino = true;
    var erro = $("#erro-calculo");
    try {
      resultado = C.calcular(entrada);
      erro.hidden = true;
    } catch (falha) {
      erro.hidden = false;
      erro.innerHTML = "<h3>Não deu para calcular</h3><ul><li>" + esc(maiuscula(String(falha.message))) + ". O plano abaixo usa os dados anteriores.</li></ul>";
      if (!resultado) return;
    }
    $("#faixa-exemplo").hidden = !estado.exemplo;
    renderResumo(resultado);
    renderAvisos(resultado);
    renderDieta(resultado);
    renderTreino(resultado);
    renderSaude(resultado);
    renderProgresso(resultado);
    desenharGraficos();
  }

  function abaAtual() {
    var h = location.hash.replace("#", "");
    return ABAS.indexOf(h) >= 0 ? h : "dieta";
  }
  function mostrarAba() {
    var aba = abaAtual();
    $$("[data-painel]").forEach(function (p) { p.hidden = p.getAttribute("data-painel") !== aba; });
    $$(".abas a").forEach(function (l) {
      if (l.getAttribute("data-aba") === aba) l.setAttribute("aria-current", "page"); else l.removeAttribute("aria-current");
    });
    desenharGraficos();
  }

  // ---------- eventos ----------
  function ligarEventos() {
    var form = $("#form-dados");
    form.addEventListener("submit", function (ev) { ev.preventDefault(); });
    form.addEventListener("input", function (ev) {
      var id = ev.target.id.replace("f-", "");
      if (!CAMPOS[id]) return;
      sairDoExemplo();
      validarCampo(id);
      mudou();
    });
    form.addEventListener("change", function (ev) {
      var alvo = ev.target;
      if (alvo.type === "radio" && ESCOLHAS[alvo.name]) { sairDoExemplo(); estado.entrada[alvo.name] = alvo.value; mudou(); }
      else if (alvo.id === "f-perfil" || alvo.id === "f-atividade") { sairDoExemplo(); estado.entrada[alvo.id.replace("f-", "")] = alvo.value; mudou(); }
    });
    form.addEventListener("click", function (ev) {
      var botao = ev.target.closest("[data-passo]");
      if (!botao) return;
      var id = botao.getAttribute("data-campo"), lim = PASSOS[id];
      var novo = Math.max(lim[0], Math.min(lim[1], estado.entrada[id] + Number(botao.getAttribute("data-passo"))));
      if (novo === estado.entrada[id]) return;
      sairDoExemplo();
      estado.entrada[id] = novo;
      $("#f-" + id).textContent = novo;
      mudou();
    });

    var btnExemplo = $("#btn-exemplo"), relogioExemplo = null;
    btnExemplo.addEventListener("click", function () {
      if (btnExemplo.getAttribute("data-confirmar") !== "1") {
        btnExemplo.setAttribute("data-confirmar", "1");
        btnExemplo.textContent = "Apagar meus dados e voltar ao exemplo";
        btnExemplo.className = "botao perigo";
        relogioExemplo = setTimeout(function () {
          btnExemplo.removeAttribute("data-confirmar"); btnExemplo.textContent = "Voltar ao exemplo"; btnExemplo.className = "botao sec";
        }, 6000);
        return;
      }
      clearTimeout(relogioExemplo);
      btnExemplo.removeAttribute("data-confirmar"); btnExemplo.textContent = "Voltar ao exemplo"; btnExemplo.className = "botao sec";
      estado = estadoExemplo();
      editouNestaVisita = true;
      apagarLocal();
      if (remoto.doc) remoto.doc.delete().catch(function () { /* fica para a proxima gravacao */ });
      preencherFormulario();
      atualizar();
      statusSalvo(true);
    });

    // cargas
    $("#c-exercicio").addEventListener("change", function () { $("#c-nome-campo").hidden = $("#c-exercicio").value !== "outro"; });
    $("#form-carga").addEventListener("submit", function (ev) {
      ev.preventDefault();
      var tipo = $("#c-exercicio").value, nome = tipo === "outro" ? $("#c-nome").value.trim().toLowerCase().slice(0, 40) : tipo;
      var carga = lerNumero($("#c-carga").value), reps = lerNumero($("#c-reps").value), msg = "";
      if (!nome) msg = "Diga o nome do exercício.";
      else if (carga === null || isNaN(carga) || carga < 1 || carga > 600) msg = "Carga entre 1 e 600 kg.";
      else if (reps === null || isNaN(reps) || reps < 1 || reps > 15 || Math.round(reps) !== reps) msg = "Repetições entre 1 e 15: acima disso a estimativa perde precisão.";
      else if (!estado.exemplo && estado.entrada.levantamento.length >= 12) msg = "Limite de 12 cargas: remova uma para adicionar outra.";
      marcarErro(null, $("#c-erro"), msg);
      if (msg) return;
      sairDoExemplo();
      estado.entrada.levantamento = estado.entrada.levantamento.filter(function (l) { return l[0] !== nome; });
      estado.entrada.levantamento.push([nome, carga, reps]);
      $("#c-carga").value = ""; $("#c-reps").value = ""; $("#c-nome").value = "";
      mudou();
    });

    // exames
    var seletor = $("#x-marcador");
    Object.keys(D.EXAMES).sort(function (a, b) { return ROT.exame[a].localeCompare(ROT.exame[b], "pt-BR"); }).forEach(function (m) {
      var op = document.createElement("option");
      op.value = m; op.textContent = ROT.exame[m];
      seletor.appendChild(op);
    });
    var unidade = function () { $("#x-unidade").textContent = D.EXAMES[seletor.value][0]; };
    seletor.addEventListener("change", unidade);
    unidade();
    $("#form-exame").addEventListener("submit", function (ev) {
      ev.preventDefault();
      var valor = lerNumero($("#x-valor").value), marcador = seletor.value;
      var msg = valor === null || isNaN(valor) || valor > 100000 ? "Digite o valor que aparece no laudo." : "";
      marcarErro($("#x-valor"), $("#x-erro"), msg);
      if (msg) return;
      sairDoExemplo();
      estado.entrada.exame = estado.entrada.exame.filter(function (x) { return x[0] !== marcador; });
      estado.entrada.exame.push([marcador, valor]);
      $("#x-valor").value = "";
      mudou();
    });

    // pressao
    var lerPressao = function () {
      var sis = lerNumero($("#p-sis").value), dia = lerNumero($("#p-dia").value), msg = "";
      if (sis === null && dia === null) { if (estado.entrada.pressao) { sairDoExemplo(); estado.entrada.pressao = null; mudou(); } marcarErro(null, $("#p-erro"), ""); return; }
      if (sis === null || dia === null) { marcarErro(null, $("#p-erro"), ""); return; }
      if (isNaN(sis) || isNaN(dia) || sis < 60 || sis > 260 || dia < 30 || dia > 160 || sis <= dia || Math.round(sis) !== sis || Math.round(dia) !== dia) {
        msg = "Confira as medidas: a sistólica (60 a 260) é sempre maior que a diastólica (30 a 160).";
      }
      marcarErro(null, $("#p-erro"), msg);
      if (msg) return;
      sairDoExemplo();
      estado.entrada.pressao = [sis, dia];
      mudou();
    };
    $("#p-sis").addEventListener("input", lerPressao);
    $("#p-dia").addEventListener("input", lerPressao);

    // peso
    $("#form-peso").addEventListener("submit", function (ev) {
      ev.preventDefault();
      var data = $("#h-data").value, peso = lerNumero($("#h-peso").value), msg = "";
      if (!dataValida(data) || data > hojeISO()) msg = "Escolha uma data de hoje para trás.";
      else if (peso === null || isNaN(peso) || peso < 35 || peso > 250) msg = "Peso entre 35 e 250 kg.";
      else if (!estado.exemplo && estado.historico.length >= 400) msg = "Limite de 400 registros: remova os mais antigos.";
      marcarErro(null, $("#h-erro"), msg);
      if (msg) return;
      sairDoExemplo();
      estado.historico = estado.historico.filter(function (h) { return h.data !== data; });
      estado.historico.push({ data: data, peso: peso });
      var maisRecente = seriePeso().slice(-1)[0];
      if (maisRecente.data === data && !invalidos.peso) {
        estado.entrada.peso = peso;
        $("#f-peso").value = paraCampo(peso);
      }
      mudou();
    });

    // remocoes
    document.addEventListener("click", function (ev) {
      var botao = ev.target.closest("[data-acao]");
      if (!botao) return;
      var acao = botao.getAttribute("data-acao"), i = Number(botao.getAttribute("data-i"));
      if (acao === "rm-carga") { var eraExemplo = estado.exemplo; sairDoExemplo(); if (!eraExemplo) estado.entrada.levantamento.splice(i, 1); }
      else if (acao === "rm-exame") { sairDoExemplo(); estado.entrada.exame.splice(i, 1); }
      else if (acao === "rm-peso") {
        var eraEx = estado.exemplo, data = botao.getAttribute("data-data");
        sairDoExemplo();
        if (!eraEx) estado.historico = estado.historico.filter(function (h) { return h.data !== data; });
      } else return;
      mudou();
    });

    window.addEventListener("hashchange", mostrarAba);
    var relogioTamanho = null;
    window.addEventListener("resize", function () { clearTimeout(relogioTamanho); relogioTamanho = setTimeout(desenharGraficos, 150); });
  }

  // ---------- inicio ----------
  var salvo = lerLocal();
  if (salvo) estado = salvo;
  ligarEventos();
  preencherFormulario();
  mostrarAba();
  atualizar();
  statusSalvo(true);
  abrirRemoto();
})();
