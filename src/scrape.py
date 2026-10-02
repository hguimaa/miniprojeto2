"""
Etapa 1 — coleta de dados de tabuademares.com/br/paraiba/joao-pessoa.

Objetivo: gravar em data/raw/ os CSVs que as Etapas 2 e 3 vão consumir.

    mares_<ano>.csv      tábua de marés do ano (4 marés por dia)
    mares_previsao.csv   marés do mês corrente, para cruzar com a previsão
    ondas.csv            altura de onda hora a hora (~7 dias à frente)
    vento.csv            velocidade do vento hora a hora (~7 dias à frente)

As funções abaixo estão vazias de propósito. Abra o site no navegador, use o
DevTools para descobrir onde cada dado vive no HTML e implemente o parse.
As colunas de cada CSV são sua decisão — só precisam sustentar as etapas
seguintes (ver README).

Rodar com: uv run python src/scrape.py
"""

import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Os imports acima são o ponto de partida: você vai usar todos eles.
# Seu editor pode marcá-los como não usados até você preencher as funções.

URL_BASE = "https://tabuademares.com/br/paraiba/joao-pessoa"
URL_ONDAS = f"{URL_BASE}/previsao/ondas"
URL_VENTO = f"{URL_BASE}/previsao/vento"

# Servidores rejeitam clientes sem User-Agent. Identifique-se.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Segundos de pausa entre requests. Não tire isso.
PAUSA = 1.5

DIR_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def baixar_html(url: str, dados_post: dict | None = None) -> str:

    if dados_post is None:
        resp = requests.get(url, headers=HEADERS)
    else:
        resp = requests.post(url, headers=HEADERS, data=dados_post)
    resp.raise_for_status()
    return resp.text


def parsear_mares(html: str, ano: int, mes: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tabela = soup.find("table", id="tabla_mareas")
    eventos = []

    # Só a primeira <tr> de cada dia tem onclick="Day('2026-09-1')".
    for linha in tabela.find_all("tr", onclick=True):
        ano_linha, mes_linha, dia = linha["onclick"].split("'")[1].split("-")
        if int(ano_linha) != ano or int(mes_linha) != mes:
            continue

        # Cada <td> desta classe é uma maré do dia.
        for celula in linha.find_all("td", class_="tabla_mareas_marea"):
            hora = celula.find("div", class_="tabla_mareas_marea_hora")
            if hora is None:  # dias com só 3 marés têm uma célula vazia
                continue
            altura = celula.find("span", class_="tabla_mareas_marea_altura_numero")
            # A div-ícone da maré alta tem a classe "..._pleamar".
            alta = celula.find("div", class_="tabla_mareas_marea_pleamar")

            eventos.append(
                {
                    "data": f"{ano_linha}-{mes_linha}-{dia.zfill(2)}",
                    "hora": hora.get_text(strip=True),
                    "altura": altura.get_text(strip=True),
                    "tipo": "preamar" if alta else "baixamar",
                }
            )

    return eventos


MESES = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}


def parsear_previsao(html: str, ano: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    previsoes = []

    for ficha in soup.find("div", class_="fichas").find_all("div", class_="ficha"):
        dia = ficha.find("span", class_="dia").get_text(strip=True)
        mes = MESES[ficha.find("span", class_="mes").get_text(strip=True)]
        data = f"{ano}-{mes:02d}-{dia}"

        for bloco in ficha.find_all("div", class_="f_temp_horas"):
            hora, direcao = bloco.find_all("div", class_="f_temp_hora")
            valor = bloco.find("div", class_="grafico_temp_barra_relleno")

            previsoes.append(
                {
                    "data": data,
                    "hora": hora.get_text(strip=True),
                    "valor": valor.get_text(strip=True),
                    "direcao": direcao.get_text(strip=True),
                }
            )

    return previsoes


def coletar_mares_do_ano(ano: int) -> pd.DataFrame:
    eventos = []

    for mes in range(1, 13):
        html = baixar_html(URL_BASE, {"fecha": f"{ano}-{mes:02d}-01"})
        eventos += parsear_mares(html, ano, mes)
        time.sleep(PAUSA)

    return pd.DataFrame(eventos)


def main(ano: int = 2025) -> None:
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    hoje = datetime.now()

    # 1. marés do ano
    mares_ano = coletar_mares_do_ano(ano)
    mares_ano.to_csv(DIR_RAW / f"mares_{ano}.csv", index=False)
    print(f"mares_{ano}.csv: {len(mares_ano)} linhas")

    # 2. marés do mês
    html = baixar_html(URL_BASE)
    mares_mes = pd.DataFrame(parsear_mares(html, hoje.year, hoje.month))
    mares_mes.to_csv(DIR_RAW / "mares_previsao.csv", index=False)
    print(f"mares_previsao.csv: {len(mares_mes)} linhas")
    time.sleep(PAUSA)

    # 3. previsão de ondas
    html = baixar_html(URL_ONDAS)
    ondas = pd.DataFrame(parsear_previsao(html, hoje.year))
    ondas.to_csv(DIR_RAW / "ondas.csv", index=False)
    print(f"ondas.csv: {len(ondas)} linhas")
    time.sleep(PAUSA)


    # 4. previsão de vento
    html = baixar_html(URL_VENTO)
    ventos = pd.DataFrame(parsear_previsao(html, hoje.year))
    ventos.to_csv(DIR_RAW / "vento.csv", index=False)
    print(f"vento.csv: {len(ventos)} linhas")
    time.sleep(PAUSA)

if __name__ == "__main__":
    main()
