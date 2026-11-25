// Executa web/calc.js sobre os casos gerados por tests/test_web.py e devolve os resultados em JSON.
// Uso: node tests/paridade.js casos.json
"use strict";
const fs = require("fs");
const path = require("path");
const calc = require(path.join(__dirname, "..", "web", "calc.js"));

const casos = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const saida = { calcular: [], historico: [], arred: [] };

for (const entrada of casos.calcular) {
  try {
    const resultado = calc.calcular(entrada);
    delete resultado.interno;
    saida.calcular.push({ ok: resultado });
  } catch (erro) {
    saida.calcular.push({ erro: String(erro.message) });
  }
}
for (const h of casos.historico) {
  saida.historico.push(calc.analisarHistorico(h.registros, h.objetivo, h.esperado, h.calorias, h.ajuste, h.piso));
}
for (const [valor, casas] of casos.arred) {
  saida.arred.push(calc.arred(valor, casas));
}
process.stdout.write(JSON.stringify(saida));
