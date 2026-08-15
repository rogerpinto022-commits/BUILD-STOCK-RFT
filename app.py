from datetime import datetime
import pandas as pd
import plotly.express as px
import sqlite3
import streamlit as st

st.set_page_config(
    page_title="Controle Completo de Estoque", page_icon="📦", layout="wide"
)

DB_NAME = "estoque_completo.db"


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT,
            descricao TEXT,
            marca TEXT,
            lote TEXT,
            validade TEXT,
            qtd_palete REAL,
            entrada REAL,
            total REAL,
            unidade_medida TEXT,
            data_reg TEXT
        )
    """)
  conn.commit()
  conn.close()


init_db()


def run_query(query, params=(), fetch=True):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(query, params)
  if fetch:
    res = cursor.fetchall()
    conn.close()
    return res
  else:
    conn.commit()
    conn.close()


st.title("📦 Sistema de Controle Detalhado de Estoque")

# Abas principais (Adicionada a aba de Exclusão)
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "📥 Cadastrar / Entrada",
    "📤 Registrar Saída",
    "📊 Ver Estoque Atual",
    "🗑️ Excluir Registro",
    "📋 Histórico Detalhado",
    "📈 Gráfico de Estoque",
])

with aba1:
  st.header("Cadastrar Novo Lote / Entrada de Material")
  with st.form("form_entrada", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
      item_id = st.text_input("ID do Item (Ex: 1, 2, 7')").strip()
      descricao = st.text_input("Descrição do Material").strip().upper()
      marca = st.text_input("Marca").strip().upper()
      lote = st.text_input("Lote").strip().upper()
      validade = st.text_input(
          "Validade (Ex: 00/00/0000 ou 07/05/2023)"
      ).strip()

    with col2:
      qtd_palete = st.number_input(
          "Qtd por Palete", min_value=0.0, value=1.0, step=1.0
      )
      entrada = st.number_input(
          "Quantidade de Entrada", min_value=0.0, value=1.0, step=1.0
      )
      unidade_medida = (
          st.selectbox(
              "Unidade de Medida",
              ["KILOS", "UNIDADES", "PACOTES", "ROLOS", "METROS"],
          )
          .strip()
          .upper()
      )

    btn_enviar = st.form_submit_button("Salvar Registro")

    if btn_enviar:
      if not descricao or not item_id:
        st.error("Preencha pelo menos o ID e a Descrição do Material.")
      else:
        base_calc = qtd_palete if qtd_palete > 0 else 1
        total = entrada * base_calc
        data_reg = datetime.now().strftime("%d/%m/%Y")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
                INSERT INTO produtos (item_id, descricao, marca, lote, validade, qtd_palete, entrada, total, unidade_medida, data_reg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                descricao,
                marca,
                lote,
                validade,
                qtd_palete,
                entrada,
                total,
                unidade_medida,
                data_reg,
            ),
        )
        conn.commit()
        conn.close()
        st.success(
            f"Registro salvo com sucesso para o material: {descricao}!"
        )

with aba2:
  st.header("Registrar Saída / Baixa")
  registros = run_query(
      "SELECT id, item_id, descricao, marca, lote, total, unidade_medida FROM"
      " produtos WHERE total > 0"
  )

  if not registros:
    st.warning("Nenhum material com saldo disponível no estoque.")
  else:
    opcoes = {
        f"ID {r[1]} - {r[2]} ({r[3]}) [Lote: {r[4]}] - Saldo: {r[5]} {r[6]}": r[0]
        for r in registros
    }
    escolha = st.selectbox(
        "Selecione o Item/Lote para dar Baixa", list(opcoes.keys())
    )
    id_prod = opcoes[escolha]

    info = run_query(
        "SELECT total, unidade_medida FROM produtos WHERE id = ?", (id_prod,)
    )[0]
    saldo_atual, unidade = info

    with st.form("form_saida"):
      qtd_saida = st.number_input(
          f"Quantidade de Saída ({unidade})",
          min_value=0.0,
          max_value=float(saldo_atual),
          step=1.0,
      )
      btn_saida = st.form_submit_button("Confirmar Saída")

      if btn_saida:
        if qtd_saida > saldo_atual:
          st.error("A quantidade de saída não pode ser maior que o saldo!")
        else:
          novo_total = saldo_atual - qtd_saida
          conn = sqlite3.connect(DB_NAME)
          cursor = conn.cursor()
          cursor.execute(
              "UPDATE produtos SET total = ? WHERE id = ?",
              (novo_total, id_prod),
          )
          conn.commit()
          conn.close()
          st.success(
              f"Saída registrada! Novo saldo deste lote: {novo_total} {unidade}"
          )

with aba3:
  st.header("📊 Saldo Atual, Cálculo Automático e Edição")
  st.info(
      "A coluna **TOTAL** recalcula automaticamente (QTD/PALETE × ENTRADA) ao"
      " salvar as alterações, ou você pode ajustá-la manualmente."
  )

  dados = run_query("""
        SELECT id, item_id, descricao, marca, lote, validade, qtd_palete, entrada, total, unidade_medida, data_reg 
        FROM produtos
    """)

  if dados:
    df = pd.DataFrame(
        dados,
        columns=[
            "DB_ID",
            "ID",
            "DESCRIÇÃO",
            "MARCA",
            "LOTE",
            "VALIDADE",
            "QTD/PALETE",
            "ENTRADA",
            "TOTAL",
            "UNIDADE DE MEDIDA",
            "DATA",
        ],
    )

    df_editado = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="tabela_estoque_editavel",
    )

    if st.button("💾 Salvar Alterações e Recalcular Totais"):
      conn = sqlite3.connect(DB_NAME)
      cursor = conn.cursor()

      for index, row in df_editado.iterrows():
        qtd_p = float(row["QTD/PALETE"])
        qtd_e = float(row["ENTRADA"])

        if qtd_p > 1:
          total_calculado = qtd_p * qtd_e
        else:
          total_calculado = float(row["TOTAL"])

        cursor.execute(
            """
                    UPDATE produtos 
                    SET item_id = ?, descricao = ?, marca = ?, lote = ?, validade = ?, 
                        qtd_palete = ?, entrada = ?, total = ?, unidade_medida = ?, data_reg = ?
                    WHERE id = ?
                """,
            (
                str(row["ID"]),
                str(row["DESCRIÇÃO"]),
                str(row["MARCA"]),
                str(row["LOTE"]),
                str(row["VALIDADE"]),
                qtd_p,
                qtd_e,
                total_calculado,
                str(row["UNIDADE DE MEDIDA"]),
                str(row["DATA"]),
                int(row["DB_ID"]),
            ),
        )
      conn.commit()
      conn.close()
      st.success("Totais recalculados e alterações salvas com sucesso!")
      st.rerun()
  else:
    st.info("O estoque está vazio.")

with aba4:
  st.header("🗑️ Excluir Registro ou Material do Estoque")
  st.warning(
      "Atenção: A exclusão de um registro é permanente e remove o lote/item do"
      " banco de dados."
  )

  registros_excluir = run_query(
      "SELECT id, item_id, descricao, marca, lote FROM produtos"
  )

  if not registros_excluir:
    st.info("Nenhum registro disponível para exclusão.")
  else:
    opcoes_exc = {
        f"DB_ID: {r[0]} | ID: {r[1]} - {r[2]} ({r[3]}) [Lote: {r[4]}]": r[0]
        for r in registros_excluir
    }
    selecionado_exc = st.selectbox(
        "Selecione o registro que deseja apagar", list(opcoes_exc.keys())
    )
    id_para_excluir = opcoes_exc[selecionado_exc]

    if st.button(
        "🗑️ Confirmar Exclusão deste Registro", type="primary"
    ):
      conn = sqlite3.connect(DB_NAME)
      cursor = conn.cursor()
      cursor.execute("DELETE FROM produtos WHERE id = ?", (id_para_excluir,))
      conn.commit()
      conn.close()
      st.success("Registro excluído com sucesso do estoque!")
      st.rerun()

with aba5:
  st.header("📋 Histórico Completo")
  dados_hist = run_query("""
        SELECT item_id, descricao, marca, lote, validade, qtd_palete, entrada, total, unidade_medida, data_reg 
        FROM produtos 
        ORDER BY id DESC
    """)
  if dados_hist:
    df_hist = pd.DataFrame(
        dados_hist,
        columns=[
            "ID",
            "DESCRIÇÃO",
            "MARCA",
            "LOTE",
            "VALIDADE",
            "QTD/PALETE",
            "ENTRADA",
            "TOTAL",
            "UNIDADE DE MEDIDA",
            "DATA",
        ],
    )
    st.dataframe(df_hist, use_container_width=True)
  else:
    st.info("Nenhum registro encontrado.")

with aba6:
  st.header("📈 Gráfico de Estoque Total por Descrição")
  dados_graf = run_query(
      "SELECT descricao, SUM(total) FROM produtos GROUP BY descricao"
  )

  if dados_graf:
    df_graf = pd.DataFrame(
        dados_graf, columns=["Descrição", "Soma Total em Estoque"]
    )
    fig = px.bar(
        df_graf,
        x="Descrição",
        y="Soma Total em Estoque",
        color="Descrição",
        text="Soma Total em Estoque",
        title="Volume Total Agrupado por Descrição de Material",
    )
    fig.update_traces(texttemplate="%{text}", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)
  else:
    st.info("Cadastre materiais para visualizar o gráfico.")