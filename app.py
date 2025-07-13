import streamlit as st
import pandas as pd
import os
import re
from itertools import combinations
from app_state import AppState
from granularity_analyzer import GranularityAnalyzer
from constants import (
    SUPPORTED_EXTENSIONS,
)

st.title("Granularity Analyzer")

st.markdown(
    """
    **Currently supported file extensions:**  
    `.csv`, `.txt`, `.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.odf`, `.ods`, `.odt`
"""
)
state = AppState()

uploaded_file = st.file_uploader(
    "Import file", type=SUPPORTED_EXTENSIONS, label_visibility="visible"
)

if uploaded_file is not None:
    # Preview
    if state.preview_df is None:
        preview_df = GranularityAnalyzer.preview_file(uploaded_file)
        state.preview_df = preview_df
    else:
        preview_df = state.preview_df

    if preview_df is not None:
        st.write(f"File preview: **{uploaded_file.name}**")
        st.dataframe(preview_df)
        header_row = st.number_input(
            "Select row number to be used as header row (0 = first row displayed above):",
            min_value=0,
            max_value=len(preview_df) - 1,
            value=state.header_row,
            step=1,
            key="header_row_input"
        )
        state.header_row = header_row

        if st.button("Load full file with selected header row"):
            df = GranularityAnalyzer.load_file(uploaded_file, header_row=header_row)
            if df is not None:
                df = GranularityAnalyzer.initial_cleaning(df)
                state.df = df
                st.success(f"File loaded: **{uploaded_file.name}**")
                st.dataframe(df.head())
            else:
                st.error("Failed to load file.")
        elif state.df is not None:
            df = state.df
            st.success(f"File loaded: **{uploaded_file.name}**")
            st.dataframe(df.head())
        else:
            df = None

        if state.df is not None:
            df = state.df
            st.markdown("---")
            st.subheader("DataFrame Summary:")
            st.write(f"**Number of rows:** {len(df)}")
            st.write(f"**Number of columns:** {len(df.columns)}")
            st.markdown("#### Columns:")
            if len(df.columns) > 25:
                st.write(
                    "Too many columns to display. Please select a subset for analysis."
                )
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
                            GranularityAnalyzer.detect_metric_columns(df)
                            + GranularityAnalyzer.detect_date_columns(df)
                            + GranularityAnalyzer.detect_aggregated_columns(df)
                        )
                    )
                    if forbidden:
                        st.info(
                            f"The columns below seem to be dates, metrics or already aggregated keys and will not be used as key:\n{forbidden}"
                        )
                    result = GranularityAnalyzer.evaluate_granularities(df, list(df.columns))
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
                            if c in GranularityAnalyzer.detect_metric_columns(df)
                        ]
                        if selected_metrics:
                            st.info(
                                f"The columns {selected_metrics} seem to be metrics or dependent variables and will not be used as key."
                            )
                        result = GranularityAnalyzer.evaluate_granularities(df, selected_columns)
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