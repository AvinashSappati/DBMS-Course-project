This document outlines the testing methodology and validation pipeline used to ensure the Text-to-SQL engine works dynamically across varying database schemas without requiring model retraining.

## 1. The Validation Pipeline
To prevent the execution of malformed or hallucinated queries, the system passes all generated SQL through a two-step validation process before returning it to the user.

1. **Syntax Validation (Level 1):** Utilizes the `sqlparse` library to evaluate the structural integrity of the generated query. If the model generates incomplete SQL (e.g., missing a `FROM` clause or unbalanced parentheses), it is flagged immediately.
2. **Semantic Validation (Level 2):** The engine cross-references the generated SQL against the active database schema. It extracts all table names following `FROM` or `JOIN` operations and verifies they actually exist in the provided schema. This catches AI "hallucinations" where the model invents tables that do not exist.

---

## 2. Dynamic Schema Hot-Swapping
The system is designed for zero-downtime database switching. When a user uploads a new schema, the engine parses the DDL, generates new BGE embeddings for the retriever, and hot-swaps the active schema in memory. The heavy T5 model remains on the GPU, dropping response times from ~15 seconds to <2 seconds on subsequent queries.

---

## 3. Testing Scenarios & Edge Cases

Below are the results of testing the engine against multiple distinct database domains and edge cases.

### Scenario A: Standard Execution (University Database)
* **Input Schema:** `Students(id INT PK, name VARCHAR)`, `Courses(course_id INT PK, title VARCHAR)`
* **User Query:** "List all the student names."
* **Result:** `SELECT name FROM Students`
* **Status:** `ok`
* **Engine Response:** Query generated successfully. Passes both syntax and semantic checks.

### Scenario B: Cross-Domain Execution (Employee Database)
* **Input Schema:** `Employees(emp_id INT PK, salary INT)`, `Departments(dept_id INT PK, dept_name VARCHAR)`
* **User Query:** "Show me the salaries of all employees."
* **Result:** `SELECT salary FROM Employees`
* **Status:** `ok`
* **Engine Response:** Successfully mapped vocabulary to a completely different domain without retraining.

### Scenario C: Ambiguity Rejection (Low BGE Confidence)
* **Input Schema:** `Cars(id INT PK, model VARCHAR, price INT)`
* **User Query:** "What is the weather like today?"
* **Result:** `None`
* **Status:** `vague`
* **Engine Response:** The retriever's BGE confidence score fell below the `0.30` threshold. The system actively rejected the prompt and asked the user for clarification, preventing garbage SQL generation.

### Scenario D: Hallucination Catch (Validation Failed)
* **Input Schema:** `Library(book_id INT PK, title VARCHAR)`
* **User Query:** "Find the names of the authors."
* **Result:** `SELECT author_name FROM Authors`
* **Status:** `validation_failed`
* **Engine Response:** The model hallucinated an `Authors` table. The Semantic Validator caught the error, flagged the query, and returned a warning to the user that the query is unsafe to execute.
