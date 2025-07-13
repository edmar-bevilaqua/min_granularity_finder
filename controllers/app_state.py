import streamlit as st
import pandas as pd


class AppState:
    def __init__(self):
        self._state = st.session_state

    @property
    def preview_df(self):
        return self._state.get("preview_df", None)

    @preview_df.setter
    def preview_df(self, value):
        self._state["preview_df"] = value

    @property
    def header_row(self):
        return self._state.get("header_row", 0)

    @header_row.setter
    def header_row(self, value):
        self._state["header_row"] = value

    @property
    def df(self):
        return self._state.get("df", None)

    @df.setter
    def df(self, value):
        self._state["df"] = value
