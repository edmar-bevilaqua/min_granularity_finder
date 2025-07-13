import pandas as pd
import re
import os
import streamlit as st
from itertools import combinations
from maps.constants import EXCEL_EXTENSIONS


class GranularityAnalyzer:
    def __init__(self, df=None):
        self.df = df

    def initial_cleaning(self):
        self.df = self.df.dropna(axis=1, how="all")
        self.df = self.df.dropna(axis=0, how="all")
        return self.df

    def detect_date_columns(self, threshold=0.9):
        date_patterns = re.compile(
            r"\b(data|in[ií]cio|fim|validade|date)\b", re.IGNORECASE
        )
        date_columns = []
        for col in self.df.columns:
            if pd.api.types.is_numeric_dtype(self.df[col]):
                continue
            try:
                converted = pd.to_datetime(self.df[col], errors="coerce", dayfirst=True)
                if converted.notna().sum() / len(
                    self.df
                ) >= threshold or date_patterns.search(str(col)):
                    date_columns.append(col)
            except Exception:
                continue
        return date_columns

    def detect_metric_columns(self):
        metric_patterns = re.compile(
            r"(pre[cç]o|valor|m[eé]dia|media|mediana|movel|margem|volume|quantidade|qtd|custo|venda|price|value|avg|min|max|wholesale|retail|unit|ranking|score|desvio|desempenho|percentual|estat|frequ[eê]ncia)",
            re.IGNORECASE,
        )
        return [col for col in self.df.columns if metric_patterns.search(str(col))]

    def detect_aggregated_columns(self):
        common_words = ["sku", "uf", "produto", "estado", "regiao"]
        general_names = ["chave", "agrupamento", "combinação", "agrup", "combina"]
        aggregated_columns = []
        for col in self.df.columns:
            col_norm = str(col).lower()
            if "+" in col_norm or col_norm in general_names:
                aggregated_columns.append(col)
            elif sum(p in col_norm for p in common_words) >= 2:
                aggregated_columns.append(col)
        return aggregated_columns

    def evaluate_granularities(self, selected_columns, top_k=2):
        dates = set(self.detect_date_columns())
        metrics = set(self.detect_metric_columns())
        aggregated = set(self.detect_aggregated_columns())
        forbidden = dates | metrics | aggregated
        available_columns = [c for c in selected_columns if c not in forbidden]
        if not available_columns:
            return []
        n_rows = len(self.df)
        granularities = []
        for r in range(1, len(available_columns) + 1):
            for combo in combinations(available_columns, r):
                try:
                    n_unique = self.df.groupby(list(combo)).ngroups
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
    def preview_file(uploaded_file, nrows=15):
        name = uploaded_file.name
        extension = os.path.splitext(name)[1].lower()
        uploaded_file.seek(0)
        if extension in [".csv", ".txt"]:
            df = pd.read_csv(uploaded_file, header=None, nrows=nrows, engine="python")
        elif extension in EXCEL_EXTENSIONS:
            df = pd.read_excel(uploaded_file, header=None, nrows=nrows)
        else:
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
            return None
        if all(str(col).isdigit() for col in df.columns):
            uploaded_file.seek(0)
            if extension in [".csv", ".txt"]:
                df = pd.read_csv(uploaded_file, header=None, engine="python")
            else:
                df = pd.read_excel(uploaded_file, header=None)
            df.columns = [f"Column{i+1}" for i in range(len(df.columns))]
        return df
