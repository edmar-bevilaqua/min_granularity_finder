import streamlit as st
import pandas as pd
import os
import re
from itertools import combinations

SUPPORTED_EXTENSIONS = [
    ".csv",
    ".txt",
    ".xls",
    ".xlsx",
    ".xlsm",
    ".xlsb",
    ".odf",
    ".ods",
    ".odt",
]
EXCEL_EXTENSIONS = [".xls", ".xlsx", ".xlsm", ".xlsb", ".odf", ".ods", ".odt"]


class GranularityAnalyzer:
    def __init__(self):
        self.df = None

    def preview_file(self, uploaded_file, nrows=50):
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

    def load_file(self, uploaded_file, header_row=0):
        name = uploaded_file.name
        extension = os.path.splitext(name)[1].lower()

        if extension in [".csv", ".txt"]:
            df = pd.read_csv(uploaded_file, header=header_row, engine="python")
        elif extension in EXCEL_EXTENSIONS:
            df = pd.read_excel(uploaded_file, header=header_row)
        else:
            st.error(f"Unsupported extension: {extension}")
            return None

        # If first row is not header
        if all(str(col).isdigit() for col in df.columns):
            if extension in [".csv", ".txt"]:
                df = pd.read_csv(uploaded_file, header=None, engine="python")
            else:
                df = pd.read_excel(uploaded_file, header=None)
            df.columns = [f"Column{i+1}" for i in range(len(df.columns))]

        return df


def initial_cleaning(df):
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")
    return df


def detect_date_columns(df, threshold=0.9):
    date_patterns = re.compile(r"\b(data|in[ií]cio|fim|validade|date)\b", re.IGNORECASE)
    date_columns = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        try:
            converted = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            if converted.notna().sum() / len(df) >= threshold or date_patterns.search(
                str(col)
            ):
                date_columns.append(col)
        except:
            continue
    return date_columns


def detect_metric_columns(df):
    metric_patterns = re.compile(
        r"(pre[cç]o|valor|m[eé]dia|media|mediana|movel|margem|volume|quantidade|qtd|custo|venda|price|value|avg|min|max|wholesale|retail|unit|ranking|score|desvio|desempenho|percentual|estat|frequ[eê]ncia)",
        re.IGNORECASE,
    )
    return [col for col in df.columns if metric_patterns.search(str(col))]


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


def evaluate_granularities(df, selected_columns, top_k=2):
    dates = set(detect_date_columns(df))
    metrics = set(detect_metric_columns(df))
    aggregated = set(detect_aggregated_columns(df))
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


st.title("Granularity Analyzer")

st.markdown(
    """
    **Currently supported file extensions:**  
    `.csv`, `.txt`, `.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.odf`, `.ods`, `.odt`
"""
)
uploaded_file = st.file_uploader(
    "import", type=SUPPORTED_EXTENSIONS, label_visibility="hidden"
)
if uploaded_file is not None:
    analyzer = GranularityAnalyzer()
    preview_df = analyzer.preview_file(uploaded_file)
    if preview_df is not None:
        st.write(f"File preview: \t **{uploaded_file.name}**")
        st.dataframe(preview_df)
        header_row = st.number_input(
            "Select row number to be used as header row (0 = first row displayed above):",
            min_value=0,
            max_value=len(preview_df) - 1,
            value=0,
            step=1,
        )
        if st.button("Load full file with selected header row"):
            df = analyzer.load_file(uploaded_file, header_row=header_row)
            if df is not None:
                df = initial_cleaning(df)
                st.write(f"File loaded: **{uploaded_file.name}**")
                st.dataframe(df.head())

            st.markdown("---")
            st.subheader("DataFrame Summary:")
            st.write(f"**Number of rows:** {len(df)}")
            st.write(f"**Number of columns:** {len(df.columns)}")
            st.markdown("#### Columns:")
            if len(df.columns) > 25:
                st.write(
                    "Too many columns to display. Please select a subset for analysis."
                )

                # Agrupa colunas por tipo
                type_groups = {}
                for col in df.columns:
                    dtype = str(df[col].dtype)
                    type_groups.setdefault(dtype, []).append(col)

                for dtype, cols in type_groups.items():
                    with st.expander(f"{dtype} columns ({len(cols)})"):
                        for col in cols:
                            st.markdown(f"- {col}")
            else:
                for col in df.columns:
                    st.markdown(f"- {col} (`{df[col].dtype}`)")

            st.markdown("---")
            st.subheader("Choose analysis mode:")
            mode = st.radio(
                "mode_radio_button",
                ["Automatic (all columns)", "Manual (choose columns)"],
                captions=[
                    "High risk of combination explosion with many columns.",
                    "Select specific columns to analyze granularity.",
                ],
                label_visibility="hidden",
            )

            if st.button("Execute granularity analysis"):
                if mode == "Automatic (all columns)":
                    forbidden = list(
                        set(
                            detect_metric_columns(df)
                            + detect_date_columns(df)
                            + detect_aggregated_columns(df)
                        )
                    )
                    if forbidden:
                        st.info(
                            f"The columns below seem to be dates, metrics or already aggregated keys and will not be used as key:\n{forbidden}"
                        )
                    result = evaluate_granularities(df, list(df.columns))
                    if result:
                        st.markdown("### Granularity analysis result:")
                        for i, (cols, unique, n_rows) in enumerate(result):
                            emoji = "✅" if i == 0 else "🔁"
                            st.write(f"{emoji} Option {i+1}: {cols}")
                            st.write(
                                f"• {unique} unique combinations in {n_rows} rows."
                            )
                            if unique == n_rows:
                                st.success("Each row is unique — maximum granularity.")
                            elif unique > n_rows * 0.9:
                                st.info("Most rows are unique — great granularity.")
                            elif unique > n_rows * 0.5:
                                st.warning("Reasonable granularity.")
                            else:
                                st.error("Low granularity.")
                    else:
                        st.warning("Could not calculate granularities.")

                else:  # Manual
                    columns = list(df.columns)
                    selected_columns = st.multiselect(
                        "Choose columns for granularity analysis:", columns
                    )
                    if selected_columns:
                        selected_metrics = [
                            c
                            for c in selected_columns
                            if c in detect_metric_columns(df)
                        ]
                        if selected_metrics:
                            st.info(
                                f"The columns {selected_metrics} seem to be metrics or dependent variables and will not be used as key."
                            )
                        result = evaluate_granularities(df, selected_columns)
                        if result:
                            st.markdown("### Granularity analysis result:")
                            for i, (cols, unique, n_rows) in enumerate(result):
                                emoji = "✅" if i == 0 else "🔁"
                                st.write(f"{emoji} Option {i+1}: {cols}")
                                st.write(
                                    f"• {unique} unique combinations in {n_rows} rows."
                                )
                                if unique == n_rows:
                                    st.success(
                                        "Each row is unique — maximum granularity."
                                    )
                                elif unique > n_rows * 0.9:
                                    st.info("Most rows are unique — great granularity.")
                                elif unique > n_rows * 0.5:
                                    st.warning("Reasonable granularity.")
                                else:
                                    st.error("Low granularity.")
                        else:
                            st.warning("Could not calculate granularities.")
                    else:
                        st.info("Select at least one column to start the analysis.")
