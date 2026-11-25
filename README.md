# App Maromba

Calculadora de linha de comando para quem treina: dieta, composicao corporal, treino, forca,
exames e historico de peso em um unico relatorio. Um arquivo, Python 3.8+, sem dependencias.

## O que faz

| Area | Entrega |
| --- | --- |
| Dieta | Gasto calorico, meta diaria, proteina, carboidrato, gordura, agua e fibra |
| Ajustes | Perfil (natural, trt, hormonizado), biotipo, idade e tempo de treino |
| Ciclo de carboidrato | Mais carboidrato no dia de treino, menos no descanso, mesma media semanal |
| Cardapio | Exemplo com gramas de cada alimento por refeicao (`--cardapio`) |
| Composicao | IMC, gordura estimada por fita metrica, massa magra, FFMI, cintura/altura |
| Meta | Peso alvo e semanas ate o percentual de gordura desejado, com pausas na manutencao |
| Treino | Divisao semanal, series, repeticoes, volume por grupo, progressao e cardio (`--treino`) |
| Forca | 1RM estimado, nivel relativo ao peso corporal e cargas de treino |
| Exames | Confere resultados contra faixas de referencia de adulto e classifica a pressao |
| Historico | Grava o peso em CSV e compara o ritmo real com o esperado |
| Linha do tempo | O que esperar do corpo nas primeiras 12 semanas e checklist de controle |

## O que nao faz

Nao calcula dose, nao sugere substancia e nao planeja ciclo. O perfil `trt` ou `hormonizado`
muda apenas proteina, ritmo de perda ou ganho, cardio e a lista de exames a acompanhar.
Uso de hormonios exige medico e exames; a ferramenta nao substitui nenhum dos dois.

## Uso

```bash
python3 maromba_calc.py --peso 85 --altura 178 --idade 28
```

Relatorio completo:

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

`--peso`, `--altura` e `--idade` sao obrigatorios. `python3 maromba_calc.py --help` lista tudo.

### Opcoes principais

| Opcao | Valores | Padrao |
| --- | --- | --- |
| `--objetivo` | secar, manter, crescer | secar |
| `--perfil` | natural, trt, hormonizado | natural |
| `--biotipo` | ectomorfo, mesomorfo, endomorfo | mesomorfo |
| `--experiencia` | iniciante, intermediario, avancado | iniciante |
| `--atividade` | sedentario, leve, moderado, intenso, atleta | moderado |
| `--treinos-semana` | 0 a 7 | 5 |
| `--gordura` | percentual de gordura, se conhecido | estimado por `--cintura` e `--pescoco` |
| `--gordura-alvo` | percentual desejado (objetivo secar) | sem meta |
| `--levantamento` | `NOME:CARGAxREPS`, repetivel | nenhum |
| `--exame` | `MARCADOR=VALOR`, repetivel | nenhum |
| `--pressao` | `SISTOLICAxDIASTOLICA` em mmHg | nenhuma |
| `--registrar` | caminho do CSV de historico | nao grava |
| `--json` | saida em JSON | texto |

Exercicios com classificacao de nivel: `supino`, `agachamento`, `terra`, `desenvolvimento`.
Qualquer outro nome recebe apenas o 1RM estimado.

Marcadores aceitos em `--exame`: `colesterol_total`, `creatinina`, `estradiol`, `fsh`, `ggt`,
`glicemia`, `hdl`, `hematocrito`, `hemoglobina`, `ldl`, `lh`, `prolactina`, `psa`,
`testosterona_total`, `tgo`, `tgp`, `triglicerides`, `tsh`. As faixas sao genericas de adulto;
a referencia impressa no laudo prevalece.

### Arquivo de configuracao

Copie `config.exemplo.json` para `config.json`, ajuste os valores e rode:

```bash
python3 maromba_calc.py --config config.json
```

O que vier na linha de comando prevalece sobre o arquivo. Opcoes repetiveis (`levantamento`,
`exame`) somam as duas origens.

### Historico

`--registrar historico.csv` acrescenta uma linha por execucao (`--data AAAA-MM-DD` para outra
data). Com 14 dias ou mais de registros, o relatorio compara o ritmo real com o esperado e
recomenda manter, subir ou reduzir 150 kcal.

### Codigos de saida

`0` sucesso, `1` erro de calculo (medidas inconsistentes, historico com formato errado),
`2` erro de uso ou de arquivo.

## Testes

```bash
python3 -m unittest discover -s tests -v
```
