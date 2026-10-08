# Inzira AI

**An Explainable Machine Learning System for Matching Low-Income Rwandan Households with Income-Generating Opportunities**

**NISR 2026 Big Data Hackathon**  
**Track 2: Financial Inclusion & Poverty Reduction**

## 1. Project Overview

**Inzira AI** is a proposed machine learning solution aimed at supporting poverty reduction and financial inclusion in Rwanda through data-driven analysis of household socioeconomic conditions.

The project's long-term vision is to help connect low-income households with suitable income-generating opportunities based on their characteristics, capabilities, and available resources.

For the current formative implementation, we developed a **household welfare classification prototype** using Rwanda's Integrated Household Living Conditions Survey (EICV7, 2023–2024).

The prototype uses a **Multilayer Perceptron (MLP)** neural network to classify households into three welfare categories based on socioeconomic indicators such as household composition, employment activity, vocational training, livestock ownership, and access to essential infrastructure.

**Current implementation:** Household welfare classification.

**Future development:** Explainable household profiling and personalized income-generating opportunity recommendations.

The current notebook does not yet implement livelihood recommendation matching or model explainability techniques.

## 2. Problem Statement

Households experiencing economic vulnerability in Rwanda have different needs, skills, living conditions, and access to economic opportunities.

These differences can make it difficult to design interventions that adequately reflect the circumstances of individual households.

Inzira AI explores how machine learning can identify patterns in household socioeconomic characteristics and support a more informed understanding of household welfare.

By building a household welfare classification model, the project establishes an initial technical foundation for a future system that could recommend relevant livelihood opportunities using additional verified opportunity data.

## 3. Project Objectives

The project aims to:

1. Analyze household socioeconomic information from Rwanda's EICV7 survey.
2. Integrate household-level and individual-level survey records.
3. Engineer relevant features associated with household welfare.
4. Develop a three-class household welfare classification model using an MLP neural network.
5. Evaluate model performance using accuracy, precision, recall, F1-score, and a confusion matrix.
6. Monitor training and validation performance using TensorBoard.
7. Establish a foundation for future explainable livelihood recommendation capabilities.

## 4. Dataset Information

### 4.1 Dataset Source

The project uses the **Integrated Household Living Conditions Survey (EICV7), 2023–2024**, provided by the **National Institute of Statistics of Rwanda (NISR)**.

The dataset contains socioeconomic information relating to household characteristics, living conditions, employment, education, and other aspects of household welfare.

### 4.2 Dataset Access Links

**Official NISR Microdata Portal:**

https://microdata.statistics.gov.rw/index.php/catalog/119

**Alternative Google Drive Dataset Link:**

https://drive.google.com/file/d/16Z_b3Fwm1-uY7mdELnKUJRK660BDxYlQ/view?usp=sharing

The Google Drive link is intended as an alternative for authorized reviewers who experience difficulties accessing the official NISR portal. Its use and publication must comply with NISR's applicable data-sharing permissions.

### 4.3 Dataset Files Used

The implementation uses three Stata files from the EICV7 microdata archive.

| Dataset file | Description |
|---|---|
| `CS_EICV7_poverty_file.dta` | Household welfare categories used as the prediction target |
| `CS_S01_S5_S7_Household.dta` | Household living conditions and socioeconomic characteristics |
| `CS_S0_S1_S2_S3_S4_S6A_S6B_S6C_Person.dta` | Individual demographic, vocational training, and economic activity information |

All three files are stored inside the `Cross_Section/` folder within the dataset ZIP archive.

The merged modeling dataset contains **15,054 unique households**.

### 4.4 Selected Features

The model uses household characteristics including:

- Province, district, and urban/rural residence
- Number of sleeping rooms
- Electricity and internet access
- Livestock ownership
- Household size and age characteristics
- Vocational training participation
- Agricultural activity
- Wage employment
- Non-farm business activity

Variables directly derived from household consumption, expenditure, or welfare classification were excluded from the model inputs to reduce target leakage.

## 5. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Programming language |
| Google Colab | Development and execution environment |
| pandas | Data loading and manipulation |
| NumPy | Numerical operations |
| scikit-learn | Preprocessing, data splitting, and evaluation |
| TensorFlow/Keras | Neural network development and training |
| TensorBoard | Training and validation monitoring |
| Matplotlib | Data visualization |

The notebook was developed for Google Colab and uses its available Python environment. No separate `requirements.txt` file is required for the intended execution setup.

## 6. How to Run the Project

Follow the instructions below to reproduce the machine learning pipeline.

### Step 1: Open Google Colab

Visit:

https://colab.research.google.com/

Open the notebook named:

`Inzira_AI_NISR_2026.ipynb`

You can download the notebook from this GitHub repository and upload it to Google Colab.

### Step 2: Download the Dataset

Obtain an authorized copy of the EICV7 dataset from the official NISR portal or another permitted access method.

**Official source:**

https://microdata.statistics.gov.rw/index.php/catalog/119

**Alternative Google Drive link:**

https://drive.google.com/file/d/16Z_b3Fwm1-uY7mdELnKUJRK660BDxYlQ/view?usp=sharing

After downloading the dataset, ensure the ZIP archive is named:

`Microdata.zip`

**Important:** Keep the dataset as a ZIP file. The notebook reads the required `.dta` files directly from the archive, so manual extraction is unnecessary.

### Step 3: Upload the Dataset to Google Colab

1. Open `Inzira_AI_NISR_2026.ipynb` in Google Colab.
2. Locate the left sidebar.
3. Click the **Files** icon.
4. Select **Upload**.
5. Choose `Microdata.zip` from your computer.
6. Wait for the upload to complete.
7. Confirm that `Microdata.zip` appears in the Colab file browser.

The notebook expects the dataset at the following location:

`/content/Microdata.zip`

Ensure the file is uploaded before executing the dataset-loading cells.

### Step 4: Run the Notebook

After uploading the dataset:

1. Click **Runtime** in the Google Colab menu.
2. Select **Run all**.
3. Allow the notebook to execute its cells in sequence.
4. Wait for data preparation, preprocessing, model training, and evaluation to complete.

The notebook performs the following operations:

- Loads the EICV7 survey files.
- Examines household records and welfare categories.
- Creates household-level features.
- Merges the selected datasets.
- Preprocesses numerical and categorical variables.
- Splits the dataset into training, validation, and testing sets.
- Builds and trains the MLP neural network.
- Records training metrics using TensorBoard.
- Evaluates the model on the test dataset.
- Verifies the completed pipeline.

**The model is intentionally trained for exactly one placeholder epoch**, in accordance with the formative assignment requirements.

### Step 5: Review the Results

After execution, review the notebook outputs for:

- Training and validation accuracy
- Training and validation loss
- TensorBoard visualizations
- Test accuracy and macro F1-score
- Classification report
- Confusion matrix
- Final pipeline verification

The verified development run ended with:

`FINAL STATUS: PIPELINE VERIFICATION PASSED`

This message indicates that the pipeline completed its implemented verification checks.

**Note:** Google Colab uses temporary runtime storage. If the runtime resets, the dataset may need to be uploaded again.

## 7. Machine Learning Methodology

### 7.1 Data Preparation

The project combines household, individual, and welfare records using a common household identifier.

Individual-level information is aggregated into household-level indicators, including demographic characteristics and participation in selected economic activities.

The merged dataset contains **15,054 households**.

### 7.2 Data Preprocessing

The preprocessing pipeline includes:

- Separating the welfare target from model predictors
- Converting welfare category codes into three classification labels
- Handling missing numerical values using median imputation
- Standardizing numerical features
- One-hot encoding categorical features
- Fitting preprocessing transformations using training data only

After preprocessing, the model receives **48 input features**.

### 7.3 Dataset Splitting

The dataset is divided using stratified sampling.

| Dataset | Households | Percentage |
|---|---:|---:|
| Training | 10,537 | 70% |
| Validation | 2,258 | 15% |
| Testing | 2,259 | 15% |
| **Total** | **15,054** | **100%** |

Stratification helps preserve the distribution of the three welfare categories across the splits.

### 7.4 Model Architecture

The model is a **Multilayer Perceptron (MLP)** implemented using TensorFlow/Keras.

| Layer | Configuration |
|---|---|
| Input layer | 48 features |
| First hidden layer | 64 neurons, ReLU |
| Second hidden layer | 32 neurons, ReLU |
| Output layer | 3 neurons, Softmax |

**Training configuration:**

- Optimizer: Adam
- Learning rate: 0.001
- Loss function: Sparse categorical crossentropy
- Training duration: 1 placeholder epoch
- Trainable parameters: 5,315
- Class weights: Applied to address class imbalance

The model produces probability estimates for the three household welfare categories.

### 7.5 TensorBoard Integration

TensorBoard is used to monitor model training and validation performance.

The notebook records training information, including:

- Training loss
- Validation loss
- Training accuracy
- Validation accuracy
- Model parameter histograms

These visualizations help demonstrate the functioning training process and provide a foundation for further model experimentation.

## 8. Preliminary Model Results

The verified one-epoch implementation produced the following results:

| Evaluation metric | Result |
|---|---:|
| Training accuracy | 58.43% |
| Validation accuracy | 61.78% |
| Test accuracy | 61.27% |
| Test macro F1-score | 0.4331 |
| Majority-class baseline accuracy | 76.23% |
| Majority-class baseline macro F1-score | 0.2884 |

The dataset contains an uneven distribution of welfare categories. Consequently, accuracy alone does not fully describe model performance.

Although the model's overall test accuracy is lower than the majority-class baseline, its macro F1-score is higher, indicating improved average performance across the three classes.

These results are preliminary and should not be interpreted as evidence that the model is ready for practical deployment.

## 9. Pipeline Verification

The notebook includes a final verification function that checks:

1. The expected number of unique households.
2. The combined size of the training, validation, and testing sets.
3. The processed feature dimensions.
4. The validity of processed model inputs.
5. The completion of exactly one training epoch.
6. The dimensions of model predictions.
7. The presence of TensorBoard event files.

The completed development run returned:

**FINAL STATUS: PIPELINE VERIFICATION PASSED**

This confirms that the implemented pipeline successfully executed its verification checks during development.

## 10. Project Limitations

### Class Imbalance

The three household welfare categories are not equally represented. This affects classification performance and requires attention to metrics beyond accuracy.

### Limited Model Training

The model was trained for one placeholder epoch to meet the formative assignment requirements. Additional experimentation is needed to assess its full predictive potential.

### Survey Data Limitations

The EICV7 survey provides observational household data. It does not establish whether a particular livelihood intervention will improve household income.

### Generalization

The current random household-level data split does not fully address potential survey-cluster or geographic dependencies.

### Privacy and Fairness

Household socioeconomic information requires responsible data handling. Future development should assess privacy, representativeness, fairness, and the potential effects of using geographic or socioeconomic indicators in predictions.

### Recommendation Functionality

The current implementation performs welfare classification only. It does not yet match households to specific livelihood opportunities or explain individual predictions.

## 11. Future Improvements

Future development of Inzira AI may include:

1. Further training and optimization of the welfare classification model.
2. Comparing the MLP with alternative machine learning approaches.
3. Adding model explainability methods such as SHAP.
4. Evaluating performance across geographic and socioeconomic groups.
5. Incorporating verified information about available income-generating opportunities.
6. Developing a personalized livelihood opportunity recommendation component.
7. Building an accessible user interface for relevant stakeholders.

## 12. Repository Structure

```text
Inzira-AI/
│
├── Inzira_AI_NISR_2026.ipynb
├── README.md
└── .gitignore
```

**File descriptions:**

- `Inzira_AI_NISR_2026.ipynb` — Complete Google Colab notebook containing the machine learning pipeline.
- `README.md` — Project overview, dataset access information, execution instructions, and implementation details.
- `.gitignore` — Prevents raw survey data and temporary generated files from being included in Git commits.

The dataset is intentionally not stored in this repository.

## 13. Data Attribution and Responsible Use

The EICV7 (2023–2024) dataset is provided by the **National Institute of Statistics of Rwanda (NISR)**.

Users should refer to the official NISR microdata catalog for applicable access conditions, citation requirements, and redistribution permissions.

Inzira AI is an academic prototype developed for the NISR 2026 Big Data Hackathon. It is not an official NISR product or a validated household support decision system.

## 14. Project Status

**Current status:** Formative machine learning prototype completed.

The implementation includes:

- EICV7 data loading and inspection
- Household-level feature engineering
- Dataset merging and preprocessing
- Three-class welfare classification using an MLP
- One-epoch model training
- TensorBoard monitoring
- Model evaluation
- End-to-end pipeline verification

**Project:** Inzira AI  
**Hackathon:** NISR 2026 Big Data Hackathon  
**Track:** Financial Inclusion & Poverty Reduction