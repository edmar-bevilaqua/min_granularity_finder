import streamlit as st
import pandas as pd
import os
import re
from itertools import combinations
from controllers.app_state import AppState
from controllers.granularity_analyzer import GranularityAnalyzer
from maps.constants import (
    SUPPORTED_EXTENSIONS,
)


class GranularityApp:
    def __init__(self):
        self.state = AppState()
        self.analyzer = None

    def run(self):
        st.title("Granularity Analyzer")
        st.markdown(
            f"""
            **Currently supported file extensions:**  
            `{'`, `'.join(SUPPORTED_EXTENSIONS)}`
            """
        )
        uploaded_file = st.file_uploader(
            "Import file", type=SUPPORTED_EXTENSIONS, label_visibility="hidden"
        )
        if not uploaded_file:
            st.info("Upload a file to start.")
            return

        if not self.show_preview(uploaded_file):
            return

        header_row = self.select_header_row()
        if header_row is None:
            return

        if not self.load_full_file(uploaded_file, header_row):
            return

        self.show_summary()
        self.show_analysis_options()

    def show_preview(self, uploaded_file):
        if self.state.preview_df is None:
            self.state.preview_df = GranularityAnalyzer.preview_file(uploaded_file)
        preview_df = self.state.preview_df
        if preview_df is not None:
            try:
                st.dataframe(preview_df)
            except Exception:
                st.warning(
                    "Problem displaying the preview. Converting all columns to text for visualization."
                )
                st.dataframe(preview_df.astype(str))
            return True
        st.error("Could not preview file.")
        return False

    def select_header_row(self):
        preview_df = self.state.preview_df
        if preview_df is None:
            return None
        header_row = st.number_input(
            "Select row number to be used as header row (0 = first row displayed above):",
            min_value=0,
            max_value=len(preview_df) - 1,
            value=self.state.header_row,
            step=1,
            key="header_row_input",
        )
        self.state.header_row = header_row
        return header_row

    def load_full_file(self, uploaded_file, header_row):
        if st.button("Load full file with selected header row"):
            df = GranularityAnalyzer.load_file(uploaded_file, header_row=header_row)
            if df is not None:
                self.analyzer = GranularityAnalyzer(df)
                self.analyzer.initial_cleaning()
                self.state.df = self.analyzer.df
                st.success(f"File loaded: **{uploaded_file.name}**")
                try:
                    st.dataframe(self.analyzer.df.head())
                except Exception:
                    st.warning(
                        "Problem displaying the DataFrame. Converting all columns to text for visualization."
                    )
                    st.dataframe(self.analyzer.df.astype(str).head())
                return True
            else:
                st.error("Failed to load file.")
                return False
        elif self.state.df is not None:
            self.analyzer = GranularityAnalyzer(self.state.df)
            st.success(f"File loaded: **{uploaded_file.name}**")
            try:
                st.dataframe(self.analyzer.df.head())
            except Exception:
                st.warning(
                    "Problem displaying the DataFrame. Converting all columns to text for visualization."
                )
                st.dataframe(self.analyzer.df.astype(str).head())
            return True
        return False

    def show_summary(self):
        if self.analyzer is None or self.analyzer.df is None:
            return
        st.markdown("---")
        st.subheader("DataFrame Summary:")
        st.write(f"**Number of rows:** {len(self.analyzer.df)}")
        st.write(f"**Number of columns:** {len(self.analyzer.df.columns)}")
        st.markdown("#### Columns:")
        if len(self.analyzer.df.columns) > 25:
            st.write("Too many columns to display. Displaying in compact mode...")
            type_groups = {}
            for col in self.analyzer.df.columns:
                dtype = str(self.analyzer.df[col].dtype)
                type_groups.setdefault(dtype, []).append(col)
            for dtype, cols in type_groups.items():
                with st.expander(f"{dtype} columns ({len(cols)})"):
                    for col in cols:
                        st.markdown(f"- {col}")
        else:
            for col in self.analyzer.df.columns:
                st.markdown(f"- {col} (`{self.analyzer.df[col].dtype}`)")

    def show_analysis_options(self):
        if self.analyzer is None or self.analyzer.df is None:
            st.warning("No DataFrame loaded.")
            return

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
            key="analysis_mode_radio",
        )

        if mode == "Automatic (all columns)":
            if st.button("Execute granularity analysis", key="auto_granularity_btn"):
                forbidden = list(
                    set(
                        self.analyzer.detect_metric_columns()
                        + self.analyzer.detect_date_columns()
                        + self.analyzer.detect_aggregated_columns()
                    )
                )
                if forbidden:
                    st.info(
                        f"The columns below seem to be dates, metrics or already aggregated keys and will not be used as key:\n{forbidden}"
                    )
                result = self.analyzer.evaluate_granularities(
                    list(self.analyzer.df.columns)
                )
                self.show_granularity_result(result)
        else:  # Manual
            columns = list(self.analyzer.df.columns)
            selected_columns = st.multiselect(
                "Choose columns for granularity analysis:",
                columns,
                key="granularity_columns",
            )
            if selected_columns:
                if st.button(
                    "Execute granularity analysis", key="manual_granularity_btn"
                ):
                    selected_metrics = [
                        c
                        for c in selected_columns
                        if c in self.analyzer.detect_metric_columns()
                    ]
                    if selected_metrics:
                        st.info(
                            f"The columns {selected_metrics} seem to be metrics or dependent variables and will not be used as key."
                        )
                    result = self.analyzer.evaluate_granularities(selected_columns)
                    self.show_granularity_result(result)
            else:
                st.info("Select at least one column to start the analysis.")

    def show_granularity_result(self, result):
        if result:
            st.markdown("### Granularity analysis result:")
            for i, (cols, unique, n_rows) in enumerate(result):
                emoji = "✅" if i == 0 else "🔁"
                st.write(f"{emoji} Option {i+1}: {cols}")
                st.write(f"• {unique} unique combinations in {n_rows} rows.")
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
