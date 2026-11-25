# App Maromba

Dieta, treino, exames e progresso para quem treina, em duas formas com a mesma lógica:

- **App web** (`web/`): página única feita para o telefone. Abra `web/index.html` no navegador.
- **Linha de comando** (`maromba_calc.py`): um arquivo, Python 3.8+, sem dependências.

As duas versões dão os mesmos números: um teste compara uma contra a outra em 1.500 entradas aleatórias.

## O que faz

| Área | Entrega |
| --- | --- |
| Dieta | Gasto calórico, meta diária, proteína, carboidrato, gordura, água e fibra |
| Ajustes | Perfil (natural, trt, hormonizado), biótipo, idade e tempo de treino |
| Ciclo de carboidrato | Mais carboidrato no dia de treino, menos no descanso, mesma média semanal |
| Cardápio | Exemplo com gramas de cada alimento por refeição |
| Composição | IMC, gordura estimada por fita métrica, massa magra, FFMI, cintura/altura |
| Meta | Peso alvo e semanas até o percentual de gordura desejado, com pausas na manutenção |
| Treino | Divisão semanal, séries, repetições, volume por grupo, progressão e cardio |
| Força | 1RM estimado, nível relativo ao peso corporal e cargas de treino |
| Exames | Confere resultados contra faixas de referência de adulto e classifica a pressão |
| Histórico | Registra o peso e compara o ritmo real com o esperado |
| Linha do tempo | O que esperar do corpo nas primeiras 12 semanas e checklist de controle |

## O que não faz

Não calcula dose, não sugere substância e não planeja ciclo. O perfil `trt` ou `hormonizado` muda
proteína, gordura da dieta (só no hormonizado), ritmo de perda ou ganho, cardio e os textos de
acompanhamento (linha do tempo, checklist com a lista de exames, avisos). Uso de hormônios exige
médico e exames; a ferramenta não substitui nenhum dos dois.

Proteções embutidas: piso de 1.500 kcal (homens) e 1.200 kcal (mulheres), nenhum déficit com IMC
abaixo de 18,5, meta de gordura recusada abaixo da gordura essencial, e avisos para pressão e exames
fora da faixa.

## App web

Abra `web/index.html`. Ele carrega com um exemplo preenchido; ao alterar qualquer campo, passa a
guardar os seus dados no próprio navegador. Abas: Dieta, Treino, Saúde, Progresso e Dados.

Arquivos:

- `web/index.html`: estrutura e estilo.
- `web/app.js`: formulário, desenho e armazenamento.
- `web/calc.js`: os cálculos, espelho de `maromba_calc.py`.
- `web/dados.js`: tabelas (alimentos, exercícios, faixas de exame). **Gerado**, não edite à mão.

Depois de mudar qualquer tabela em `maromba_calc.py`, regenere os dados:

```bash
python3 tools/gerar_dados.py
```

## Linha de comando

```bash
python3 maromba_calc.py --peso 85 --altura 178 --idade 28
```

Relatório completo:

```bash
python3 maromba_calc.py --peso 85 --altura 178 --idade 28 \
  --cintura 88 --pescoco 39 --biotipo mesomorfo \
  --objetivo secar --perfil natural --experiencia intermediario \
  --atividade moderado --treinos-semana 5 --gordura-alvo 12 \
  --cardapio --treino \
  --levantamento supino:100x5 --levantamento agachamento:140x5 \
  --exame hematocrito=47 --exame hdl=45 --pressao 125x80 \
  --registrar historico.csv
```

`--peso`, `--altura` e `--idade` são obrigatórios. `python3 maromba_calc.py --help` lista tudo.
Os nomes das opções têm de ser escritos por extenso (abreviações são recusadas).

### Opções principais

| Opção | Valores | Padrão |
| --- | --- | --- |
| `--sexo` | m, f | m |
| `--objetivo` | secar, manter, crescer | secar |
| `--perfil` | natural, trt, hormonizado | natural |
| `--biotipo` | ectomorfo, mesomorfo, endomorfo | mesomorfo |
| `--experiencia` | iniciante, intermediario, avancado | iniciante |
| `--atividade` | sedentario, leve, moderado, intenso, atleta | moderado |
| `--treinos-semana` | 0 a 7 | 5 |
| `--gordura` | percentual de gordura, se conhecido | estimado por `--cintura` e `--pescoco` (mais `--quadril` com `--sexo f`) |
| `--quadril` | quadril em cm; exigido com `--sexo f` para estimar a gordura por fita | nenhum |
| `--gordura-alvo` | percentual desejado (objetivo secar) | sem meta |
| `--cardapio` | gera o cardápio exemplo | desligado |
| `--treino` | gera o plano de treino | desligado |
| `--levantamento` | `NOME:CARGAxREPS`, repetível | nenhum |
| `--exame` | `MARCADOR=VALOR`, repetível | nenhum |
| `--pressao` | `SISTOLICAxDIASTOLICA` em mmHg | nenhuma |
| `--registrar` | caminho do CSV de histórico | não grava |
| `--json` | saída em JSON | texto |

Exercícios com classificação de nível: `supino`, `agachamento`, `terra`, `desenvolvimento`.
Qualquer outro nome recebe apenas o 1RM estimado.

Marcadores aceitos em `--exame`: `colesterol_total`, `creatinina`, `estradiol`, `fsh`, `ggt`,
`glicemia`, `hdl`, `hematocrito`, `hemoglobina`, `ldl`, `lh`, `prolactina`, `psa`,
`testosterona_total`, `tgo`, `tgp`, `triglicerides`, `tsh`. As faixas são genéricas de adulto;
a referência impressa no laudo prevalece.

### Arquivo de configuração

Copie `config.exemplo.json` para `config.json`, ajuste os valores e rode:

```bash
python3 maromba_calc.py --config config.json
```

O que vier na linha de comando prevalece sobre o arquivo. Para as opções repetíveis
(`levantamento`, `exame`), a lista da linha de comando substitui a do arquivo.

O exemplo traz `"registrar": "historico.csv"`: cada execução acrescenta uma linha ao histórico.
Remova essa chave se quiser rodar simulações sem gravar.

### Histórico

`--registrar historico.csv` acrescenta uma linha por execução (`--data AAAA-MM-DD` para outra data,
nunca no futuro). Com 14 dias ou mais de registros, o relatório compara o ritmo real com o esperado
e recomenda manter, subir ou reduzir de 50 a 150 kcal, conforme o tamanho do ajuste do plano. Com
as calorias já no piso, recomenda mais passos em vez de cortar comida.

### Códigos de saída

`0` sucesso, `1` erro de cálculo (medidas inconsistentes, histórico com formato errado),
`2` erro de uso ou de arquivo.

## Testes

```bash
python3 -m unittest discover -s tests -v
```

O teste de paridade entre Python e JavaScript (`tests/test_web.py`) usa Node.js; sem ele, é pulado.
