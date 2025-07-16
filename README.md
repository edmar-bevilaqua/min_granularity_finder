# min_granularity_finder
---

**min_granularity_finder** is a Streamlit-based tool designed to help users identify the minimum granularity of tabular datasets (such as CSV or Excel files) without running into combinatorial explosion. This is particularly useful for data analysts and engineers who need to understand the uniqueness and aggregation levels of their data quickly and interactively.

## Features

- Upload CSV, TXT, or Excel files and preview the first rows.
- Select the correct header row for your dataset.
- Automatically or manually analyze column combinations to find the minimum granularity.
- Visual feedback on the uniqueness of combinations.
- Handles files with many columns and mixed data types.

## How to Run Locally

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/min_granularity_finder.git
   cd min_granularity_finder
   ```

2. **Create and activate a virtual environment (recommended):**
    Go to the root of the project (`min_granularity_finder/`) and run:

   ```bash
   poetry install
   ```

3. **Run the application:**

   ```bash
   streamlit run main.py
   ```

4. **Open your browser and go to** [http://localhost:8501](http://localhost:8501) **to use the app.**

## Contributing

If you want to contribute to the development of the granularity detection logic or improve the app in any way, feel free to open issues or submit pull requests. Collaboration is welcome!

---

**Author:** Edmar Junyor Bevilaqua  
**License:** MIT
