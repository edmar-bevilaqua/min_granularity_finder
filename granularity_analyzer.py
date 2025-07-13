import pandas as pd
import re
import os
import streamlit as st
from itertools import combinations
from constants import (
    EXCEL_EXTENSIONS,
)

class GranularityAnalyzer:
    def __init__(self, df=None):
        self.df = df

    @staticmethod
    def initial_cleaning(df):
        df = df.dropna(axis=1, how="all")
        df = df.dropna(axis=0, how="all")
        return df

    @staticmethod
    def detect_date_columns(df, threshold=0.9):
        date_patterns = re.compile(r"\b(data|in[ií]cio|fim|validade|date)\b", re.IGNORECASE)
        date_columns = []
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                continue
            try:
                converted = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                if converted.notna().sum() / len(df) >= threshold or date_patterns.search(str(col)):
                    date_columns.append(col)
            except Exception:
                continue
        return date_columns

    @staticmethod
    def detect_metric_columns(df):
        metric_patterns = re.compile(
            r"(pre[cç]o|valor|m[eé]dia|media|mediana|movel|margem|volume|quantidade|qtd|custo|venda|price|value|avg|min|max|wholesale|retail|unit|ranking|score|desvio|desempenho|percentual|estat|frequ[eê]ncia)",
            re.IGNORECASE,
        )
        return [col for col in df.columns if metric_patterns.search(str(col))]

    @staticmethod
    def detect_aggregated_columns(df):
        common_words = ["sku", "uf", "produto", "estado", "regiao"]
        general_names = ["chave", "agrupamento", "combinação", "agrup", "combina"]
        aggregated_columns = []
        for col in df.columns:
            col_norm = str(col).lower()
            if "+" in col_norm or col_norm in general_names:
                aggregated_columns.append(col)
            elif sum(p in col_norm for p in common_words) >= 2:
                aggregated_columns.append(col)
        return aggregated_columns

    @staticmethod
    def evaluate_granularities(df, selected_columns, top_k=2):
        dates = set(GranularityAnalyzer.detect_date_columns(df))
        metrics = set(GranularityAnalyzer.detect_metric_columns(df))
        aggregated = set(GranularityAnalyzer.detect_aggregated_columns(df))
        forbidden = dates | metrics | aggregated
        available_columns = [c for c in selected_columns if c not in forbidden]
        if not available_columns:
            st.warning(
                "No candidate columns for granularity (all are dates, metrics or aggregated)."
            )
            return []
        n_rows = len(df)
        granularities = []
        for r in range(1, len(available_columns) + 1):
            for combo in combinations(available_columns, r):
                try:
                    n_unique = df.groupby(list(combo)).ngroups
                    granularities.append((list(combo), n_unique))
                except Exception:
                    continue
        granularities.sort(key=lambda x: (-x[1], len(x[0])))
        filtered, seen = [], []
        for cols, unique in granularities:
            if not any(unique == u and set(pc).issubset(cols) for pc, u in seen):
                filtered.append((cols, unique))
                seen.append((cols, unique))
        best = filtered[:top_k]
        return [(cols, unique, n_rows) for cols, unique in best]

    @staticmethod
    def preview_file(uploaded_file, nrows=50):
        name = uploaded_file.name
        extension = os.path.splitext(name)[1].lower()
        uploaded_file.seek(0)
        if extension in [".csv", ".txt"]:
            df = pd.read_csv(uploaded_file, header=None, nrows=nrows, engine="python")
        elif extension in EXCEL_EXTENSIONS:
            df = pd.read_excel(uploaded_file, header=None, nrows=nrows)
        else:
            st.error(f"Unsupported extension: {extension}")
            return None
        return df

    @staticmethod
    def load_file(uploaded_file, header_row=0):
        name = uploaded_file.name
        extension = os.path.splitext(name)[1].lower()
        uploaded_file.seek(0)
        if extension in [".csv", ".txt"]:
            df = pd.read_csv(uploaded_file, header=header_row, engine="python")
        elif extension in EXCEL_EXTENSIONS:
            df = pd.read_excel(uploaded_file, header=header_row)
        else:
            st.error(f"Unsupported extension: {extension}")
            return None

        # If first row is not header
        if all(str(col).isdigit() for col in df.columns):
            uploaded_file.seek(0)
            if extension in [".csv", ".txt"]:
                df = pd.read_csv(uploaded_file, header=None, engine="python")
            else:
                df = pd.read_excel(uploaded_file, header=None)
            df.columns = [f"Column{i+1}" for i in range(len(df.columns))]

        return df