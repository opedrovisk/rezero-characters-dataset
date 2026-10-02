# rezero-characters-dataset

Dataset de personagens de *Re:Zero − Starting Life in Another World*, construído a partir do
[Re:Zero Wiki](https://rezero.fandom.com) com a API oficial do MediaWiki. Este repositório reúne
os scripts de coleta e tratamento e os arquivos CSV resultantes.

📊 **Dataset no Kaggle:** <https://www.kaggle.com/datasets/pedrohmarcondes/rezero-characters>

> Projeto de fã, sem afiliação com os detentores da obra nem com a Fandom.
> Os dados contêm **spoilers**.

## Os dados em resumo

| Arquivo | Linhas | Descrição |
|---|---|---|
| `characters.csv` | 342 | Uma linha por personagem: campos da infobox + textos principais do artigo |
| `character_sections.csv` | 1.319 | Formato longo: uma linha por seção de artigo (`page_id`, `name`, `section`, `text`) |

- Coleta feita em **01/10/2026**.
- Os valores estão como aparecem no wiki (texto livre, sem normalização). Campos com vários
  itens usam ` ; ` como separador.
- Colunas bem preenchidas: `race` (340/342), `status` (339), `gender` (338), `appearance` (328),
  `personality` (285), `history` (274).
- Colunas esparsas: `weight`, `authority` e `affinity` (menos de 30 linhas cada).

### Colunas de `characters.csv`

| Grupo | Colunas |
|---|---|
| Identificação | `page_id`, `name`, `name_jp`, `name_romaji`, `alias`, `nickname`, `url` |
| Infobox | `gender`, `race`, `age`, `birthday`, `height`, `weight`, `hair_color`, `eye_color`, `status`, `occupation`, `previous_occupation`, `affiliation`, `previous_affiliation`, `relatives`, `magic`, `authority`, `divine_protection`, `affinity`, `weapon`, `equipment`, `first_light_novel`, `first_manga`, `first_anime`, `first_game`, `voice_jp`, `voice_en` |
| Texto | `intro`, `appearance`, `personality`, `history`, `abilities_text` |
| Metadados | `categories`, `linked_pages`, `extra_json`, `last_revised`, `scraped_at` |

Valores vazios indicam que o campo não existe ou está em branco na página do wiki.

## Início rápido

```python
import pandas as pd

chars = pd.read_csv("characters.csv")
sections = pd.read_csv("character_sections.csv")

print(chars[["name", "gender", "race", "status"]].head())
print(chars["gender"].value_counts())
```

## Conteúdo do repositório

| Arquivo | Função |
|---|---|
| `collect_dataset.py` | Lista as páginas da categoria `Characters` (com subcategorias) e baixa o wikitext delas |
| `parse.py` | Extrai a infobox `{{Character}}`, limpa as marcações wiki e separa os artigos em seções |
| `raw_pages.jsonl` | Saída bruta da coleta (uma página por linha, com o wikitext) |
| `characters.csv`, `character_sections.csv` | Tabelas finais |

## Como reproduzir o dataset

```bash
pip install -r requirements.txt

# 1. Baixar as páginas brutas (pode ser interrompido e retomado; use seu e-mail no User-Agent)
python collect_dataset.py --email seu_email@exemplo.com

# 2. Converter para os dois arquivos CSV
python parse.py
```

O `collect_dataset.py` usa a API oficial, faz pausas entre as requisições e envia um
`User-Agent` identificado. Se for rodar de novo, mantenha esse cuidado. Opções úteis:
`--category`, `--no-recurse` e `--delay`. O `parse.py` aceita `--input` e `--out`.

Páginas sem a infobox `{{Character}}` (grupos, lugares, batalhas) são descartadas: foram
coletadas 437 páginas e 342 delas são personagens.

## Limitações conhecidas

- Os campos são texto livre: `status` pode ser `Deceased (body) ; Alive (soul)` e `age` pode ser
  `Looks around 11 or 12 ; Unknown (400+) (actual)`.
- `race` é muito desbalanceada (233 dos 342 personagens são `Human`).
- O wiki mistura light novel, web novel, anime, mangá e histórias *What-If/IF*, então alguns
  campos descrevem mais de uma versão do personagem.
- Erros de digitação nos títulos de seção do próprio wiki só foram corrigidos em parte
  (por exemplo, `Apearance`).

## Próximos passos

- [ ] Colunas normalizadas (por exemplo, `status` principal e `age` numérica)
- [ ] Experimentos de classificação com SVM sobre o texto dos artigos
- [ ] Grafo de relações opcional, construído a partir de `linked_pages`

## Licença e atribuição
 
- **Dados:** o texto vem do [Re:Zero Wiki](https://rezero.fandom.com) e está disponível sob a
  licença [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Os arquivos CSV são
  redistribuídos sob a mesma licença, com atribuição ao Re:Zero Wiki e aos seus colaboradores.
  Os autores de cada página estão no histórico de edições (link na coluna `url`).
  Imagens não estão incluídas.
  **Alterações:** o conteúdo foi modificado em relação ao original. O texto foi extraído pela API do
  MediaWiki, limpo (marcações wiki, notas de rodapé e caixas de navegação removidas) e reorganizado
  em tabelas CSV.
- **Código:** distribuído sob a [Licença MIT](LICENSE).
