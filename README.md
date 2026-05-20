# Project Dependency Risk Analyzer

### A Residuated Quantale Application

This application is a decision-support tool for Project Managers. It uses **Quantale logic** to calculate the aggregated risk of multiple dependencies and determine the "Safety Buffer" available before a project hits a failure state.

## 1. What is the domain? (What does Q represent?)
The domain is **Project Management & Risk Assessment**. 
The set **Q** represents discrete **Project Health Statuses**:
*   `blocked`: The project has come to a complete halt (Bottom $\bot$).
*   `over_budget`: The project is running but financial limits are exceeded.
*   `behind_schedule`: The project is running but timeline limits are exceeded.
*   `healthy`: The project is performing within normal parameters.
*   `success`: The project goals have been fully achieved (Top $\top$).

**The Partial Order ($\le$):** 
The hierarchy is non-total. While `blocked < healthy`, the risks `over_budget` and `behind_schedule` are **incomparable**. This models the reality that a money problem is not "better" or "worse" than a time problem—they are different types of risk.

## 2. What does $\otimes$ model in this domain?
The multiplication operation $\otimes$ models **Dependency Bottlenecks**. 
In project management, if Task A depends on Task B, the resulting status is limited by the "weakest link." 

*   **Logic:** We define $a \otimes b$ as the **Lattice Meet** ($a \land b$). 
*   **Example:** If you have a `healthy` project but it depends on an `over_budget` vendor, the effective status of the project is `over_budget`.
*   **Identity ($e$):** The identity element is `success`. Adding a perfectly successful dependency to a project does not change its current health.

## 3. What question does the right residual answer?
The right residual ($a \to c$) answers the question of **Risk Budgeting**:

> *"If my current project status is **a**, and I have a strict safety requirement that the final outcome must not drop below status **c**, what is the **maximum allowable risk** (lowest status) I can accept from a new subcontractor or dependency?"*

This allows managers to solve for the "missing link" in a project chain to ensure they stay within their "Resilience Buffer."

## 4. How do I run the app?
The app is built using **Streamlit**. 

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run the application:**
    ```bash
    streamlit run app.py
    ```

## 5. What does a sample output look like?

**Scenario: Assessing a New Contractor**
*   **Current Dependency Statuses:** `healthy`, `success`, `success`.
*   **Calculated Aggregated Health:** `HEALTHY` (The bottleneck).
*   **Management Limit:** The project must stay at least `behind_schedule`.
*   **User Input:** 
    *   Current Health: `healthy`
    *   Safety Limit: `behind_schedule`
*   **Calculated Risk Budget:** `BEHIND_SCHEDULE`
*   **System Advice:** *"You have a resilience buffer. Your new contractor can be as low as 'behind_schedule' without crashing the project below your safety limit."*
