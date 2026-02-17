#  Competitive Programming Problem Solver with CAMEL Agents & Firecrawl

This project enables users to input problems from competitive programming platforms (Codeforces or LeetCode) and receive AI-generated Python solutions. It integrates:

-  Web scraping via Firecrawl
-  Multi-agent reasoning with CAMEL AI
-  Code execution and validation against sample tests
-  Streamlit interface for user interaction
-  Auto-fix functionality for Codeforces problems

---

##  Features

- **Multi-Platform Support**: Solves problems from both Codeforces and LeetCode
- **Problem Retrieval**: Fetches problem statements using Firecrawl
- **Sample Extraction**: Parses and extracts sample inputs/outputs from problem descriptions
- **AI-Powered Solution**: Utilizes CAMEL AI agents to generate Python solutions
- **Automated Testing**: Executes generated code against extracted samples
- **Auto-Fix Capability**: Iteratively improves solutions for Codeforces problems
- **Platform-Specific Handling**: Different solution approaches for Codeforces vs LeetCode

---

##  Requirements

Install Python packages:

```bash
pip install -r requirements.txt
```

---

## ️ Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/camel-ai/camel.git
   cd examples/usecases/codeforces_question_solver
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:

   Create a `.env` file in the root directory and add your API keys:

   ```env
   FIRECRAWL_API_KEY=your_firecrawl_api_key
   OPENAI_API_KEY=your_openai_api_key
   FIRECRAWL_API_KEY='your_firecrawl_key'
   ```

---

##  Run the App

Start the Streamlit application:

```bash
streamlit run app.py
```

Then, open the provided URL in your browser to interact with the app.

---

##  File Structure

```
├── app.py             # Main Streamlit application
├── requirements.txt   # Python dependencies
├── .env               # Environment variables
└── README.md          # Project documentation
```

---

##  Powered By

- [CAMEL AI](https://github.com/camel-ai/camel): Multi-agent reasoning framework
- [Firecrawl](https://github.com/mendableai/firecrawl): Web scraping and data extraction
- [Streamlit](https://streamlit.io/): Web application framework

---

##  Example Usage

1. **Select Platform**: Choose Codeforces or LeetCode
2. **Input Problem ID**:
   - For Codeforces: Enter problem ID (e.g., `2116B`)
   - For LeetCode: Enter problem slug (e.g., `reverse-integer`)
3. **Process**:
   - Fetches problem statement using Firecrawl
   - Extracts sample inputs/outputs
   - Generates Python solution using CAMEL AI
   - For Codeforces: Optionally auto-fixes solution based on test failures
4. **Output**: Displays generated code, and test results

---

##  Notes

- Ensure your API keys are valid and have sufficient quota
- Solution accuracy depends on problem complexity and AI capabilities
- Always review generated code before using in competitions
- Auto-fix is currently only available for Codeforces problems

---

##  Acknowledgements

- [CAMEL AI](https://github.com/camel-ai/camel) for multi-agent reasoning
- [Firecrawl](https://github.com/mendableai/firecrawl) for web scraping
- [Streamlit](https://streamlit.io/) for the web interface

---

Feel free to contribute by submitting issues or pull requests!
